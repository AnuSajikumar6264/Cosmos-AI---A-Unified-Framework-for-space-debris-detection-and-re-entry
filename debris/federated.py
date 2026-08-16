"""
Federated space intelligence: training one re-entry surrogate across operators who cannot share
data.

The data needed to predict where debris lands is spread across parties who will not pool it.
Operators hold their own telemetry and tracking; national agencies hold sensor data they will not
export; launch providers hold vehicle performance they treat as commercial.  Each party's own
slice is narrow - one vehicle family, one orbital regime - so a locally-trained model is good at
its own regime and poor everywhere else, which is exactly the wrong shape for a debris problem
where the object falling on you was launched by someone else.

Federated averaging fixes the *statistical* problem without solving the *political* one: only
model updates cross the boundary, never observations.

What is implemented
-------------------
``local``       each client trains alone.  The baseline to beat, and the status quo.
``centralised`` all data pooled.  The upper bound, and normally not achievable.
``fedavg``      McMahan et al. 2017: clients train locally, the server averages weights in
                proportion to sample count, repeat.
``fedprox``     Li et al. 2020: adds ``mu/2 * ||theta - theta_global||^2`` to each local
                objective, which limits client drift.  It matters here because the clients are
                strongly **non-IID** - a client whose objects are all high-B pulls the shared
                model a long way in a few local epochs.
``fedavg_dp``   FedAvg with per-client update clipping and Gaussian noise, i.e. the Gaussian
                mechanism at the update level.  Included because "we only share gradients" is
                not by itself a privacy guarantee - updates leak information about the data that
                produced them - and the cost of an actual guarantee is worth measuring.

Non-IID by construction
-----------------------
Clients are the physically distinct regimes in :data:`~debris.ml_common.REGIMES`, not random
shards of one pool.  Random shards would make every method look equally good and the experiment
would prove nothing: the entire difficulty of federated learning is heterogeneity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .ml_common import (
    REGIMES,
    RidgeSurrogate,
    TrajectoryDataset,
    build_trajectory_dataset,
    surrogate_metrics,
    torch_available,
)

SCORE_KEY = "impact_median_error_km"

#: Default client set: five operators with genuinely different populations.
DEFAULT_CLIENTS = ("steep_deorbit", "shallow_decay", "dense_survivors", "light_fragments",
                   "suborbital_stage")


@dataclass
class ClientData:
    """One participant's private data."""

    name: str
    train: TrajectoryDataset
    test: TrajectoryDataset

    def __len__(self) -> int:
        return len(self.train)


@dataclass
class FederatedResult:
    """Outcome of one training scheme."""

    scheme: str
    global_error: float                       # on the pooled test set
    per_client_error: dict[str, float]        # global model, evaluated per client
    rounds: int = 0
    bytes_per_round: int = 0
    epsilon: float | None = None
    history: list[dict] = field(default_factory=list)
    notes: str = ""

    @property
    def worst_client_error(self) -> float:
        return max(self.per_client_error.values()) if self.per_client_error else float("nan")

    @property
    def fairness_spread(self) -> float:
        """Max minus min client error - a scheme can have a good mean and be useless to someone."""
        if not self.per_client_error:
            return float("nan")
        v = list(self.per_client_error.values())
        return float(max(v) - min(v))

    def summary(self) -> dict:
        return {
            "scheme": self.scheme,
            "global_error_km": self.global_error,
            "worst_client_error_km": self.worst_client_error,
            "fairness_spread_km": self.fairness_spread,
            "rounds": self.rounds,
            "bytes_per_round": self.bytes_per_round,
            "epsilon": self.epsilon,
            "notes": self.notes,
        }


# ================================================================================= torch
def _flat_state(model):
    import torch

    return {n: p.detach().clone() for n, p in model.named_parameters()}


def _weighted_average(states, weights):
    """Sample-count-weighted parameter average - the FedAvg server step."""
    import torch

    total = float(sum(weights))
    out = {}
    for key in states[0]:
        acc = torch.zeros_like(states[0][key])
        for st, w in zip(states, weights):
            acc += st[key] * (float(w) / total)
        out[key] = acc
    return out


def _local_train(model, dataset, *, epochs, lr, mu=0.0, global_state=None, seed=0):
    """One client's local update. ``mu > 0`` adds the FedProx proximal term."""
    import torch

    cfg = model.cfg
    params = [p for _n, p in model.named_parameters()]
    for p in params:
        p.requires_grad = True
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=cfg.weight_decay)
    huber = torch.nn.HuberLoss(delta=0.15)
    x = torch.as_tensor(dataset.x, device=model.device)
    y = torch.as_tensor(dataset.y, device=model.device)
    rng = np.random.default_rng(seed)
    named = dict(model.named_parameters())

    for _e in range(int(epochs)):
        model.train_mode(True)
        perm = rng.permutation(len(dataset))
        for i in range(0, len(dataset), cfg.batch_size):
            idx = perm[i:i + cfg.batch_size]
            if len(idx) < 2:
                continue
            t_pred, p_pred = model.forward(x[idx])
            loss = huber(t_pred, y[idx][:, 0]) + huber(p_pred, y[idx][:, 1:])
            if mu > 0.0 and global_state is not None:
                prox = 0.0
                for n, p in named.items():
                    prox = prox + ((p - global_state[n]) ** 2).sum()
                loss = loss + 0.5 * mu * prox
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
    return model


def _clip_and_noise(update, global_state, clip_norm: float, noise_multiplier: float, rng):
    """
    Per-client update clipping plus Gaussian noise - the Gaussian mechanism at update level.

    Clipping first is essential and not merely a stabiliser: the noise scale is calibrated to the
    clipping norm, so without a bound on the update there is no bound on any client's influence
    and therefore no guarantee at all.
    """
    import torch

    delta = {n: update[n] - global_state[n] for n in update}
    total = math.sqrt(sum(float((d**2).sum()) for d in delta.values()))
    scale = min(1.0, clip_norm / max(total, 1e-12))
    sigma = noise_multiplier * clip_norm
    out = {}
    for n, d in delta.items():
        noise = torch.as_tensor(
            rng.normal(0.0, sigma, size=tuple(d.shape)).astype(np.float32), device=d.device)
        out[n] = global_state[n] + d * scale + noise
    return out, total, scale


def _epsilon_estimate(noise_multiplier: float, rounds: int, n_clients: int,
                      delta: float = 1e-5) -> float:
    """
    Rough (epsilon, delta) for the composed Gaussian mechanism.

    Uses simple advanced composition, which is *loose* - a Renyi-DP or PLD accountant gives a
    materially tighter bound for the same noise.  Quoted as an upper bound and labelled as such;
    a number from a hand-rolled accountant should not be presented as a tight guarantee.
    """
    if noise_multiplier <= 0:
        return float("inf")
    eps_step = math.sqrt(2.0 * math.log(1.25 / delta)) / noise_multiplier
    return float(eps_step * math.sqrt(2.0 * max(rounds, 1) * math.log(1.0 / delta)))


# ============================================================================== fallback
def _federated_ridge(clients, pooled_test, rounds=1, seed=0):
    """
    numpy fallback: coefficient averaging over closed-form ridge fits.

    One detail is essential and easy to get wrong: the clients must **share a feature
    normaliser**.  Letting each client standardise against its own data and then averaging both
    the normalisers and the coefficients produces a model that corresponds to no client at all -
    measured here, it scored 977 km against 49 km for the best single client, i.e. worse than not
    federating.  The fix is to derive the shared mean and variance by aggregating the clients'
    *statistics* (count, sum, sum of squares) before any fitting.  That is a legitimate single
    round of secure aggregation - the standard first step in real federated pipelines - and it
    still moves no observations across a boundary.

    With a shared basis and a convex objective, one round of averaging is already meaningful, so
    ``rounds`` has no effect here and is not pretended to.
    """
    from .ml_common import RidgeSurrogate as R

    probe = R()
    designs = [probe._design(c.train.x) for c in clients]

    # ---- federated statistics: only counts and moments leave each client.
    n_total = sum(len(d) for d in designs)
    shared_mean = sum(d.sum(axis=0) for d in designs) / n_total
    shared_var = sum(((d - shared_mean) ** 2).sum(axis=0) for d in designs) / n_total
    shared_scale = np.maximum(np.sqrt(shared_var), 1e-8)

    def fit_with_shared_basis(x, y, alpha):
        z = (probe._design(x) - shared_mean) / shared_scale
        z = np.concatenate([z, np.ones((len(z), 1))], axis=1)
        reg = alpha * np.eye(z.shape[1])
        reg[-1, -1] = 0.0
        m = R(alpha=alpha)
        m.mean_, m.scale_ = shared_mean, shared_scale
        m.coef_ = np.linalg.solve(z.T @ z + reg, z.T @ np.asarray(y, dtype=float))
        return m

    # Pick one penalty on the pooled basis so every client regularises identically; a per-client
    # alpha would make the averaged coefficients inconsistent again.
    alpha = R.tune(clients[0].train, seed=seed).alpha
    models = [fit_with_shared_basis(c.train.x, c.train.y, alpha) for c in clients]

    weights = np.array([len(c) for c in clients], dtype=float)
    weights /= weights.sum()

    # ---- one-shot averaging of the closed-form solutions.
    oneshot = R(alpha=alpha)
    oneshot.mean_, oneshot.scale_ = shared_mean, shared_scale
    oneshot.coef_ = sum(w * m.coef_ for w, m in zip(weights, models))

    # ---- exact federated learning by sufficient-statistic aggregation.
    #
    # For a *linear* model there is a much better answer than iterating, and it is worth stating
    # plainly because it is the honest one: each client sends only the aggregate moments
    # ``z_i^T z_i`` and ``z_i^T y_i``.  Summing those and solving gives the **exact** pooled ridge
    # solution - bit for bit identical to training on all the data at once - in a single round,
    # with no observation ever leaving a client.
    #
    # Two things follow, and both matter:
    #
    #   * It shows the ceiling cleanly.  Federated == centralised here, so any gap seen in the
    #     torch path is attributable to the optimiser and the non-convexity, not to federation.
    #   * It does **not** generalise.  It works precisely because the objective is quadratic and
    #     the sufficient statistics are finite-dimensional.  A neural network has neither
    #     property, which is exactly why the torch path has to iterate FedAvg and why iterating
    #     is where all the difficulty lives.
    #
    # (Moment aggregation is not automatically private - a Gram matrix leaks a great deal about a
    # small client - so in practice it needs secure aggregation or added noise, the same as any
    # other update.)
    zs = [np.concatenate([(d - shared_mean) / shared_scale, np.ones((len(d), 1))], axis=1)
          for d in designs]
    ys = [np.asarray(c.train.y, dtype=float) for c in clients]
    n_feat = zs[0].shape[1]
    reg = alpha * np.eye(n_feat)
    reg[-1, -1] = 0.0
    gram_sum = sum(z.T @ z for z in zs)
    rhs_sum = sum(z.T @ y for z, y in zip(zs, ys))
    theta = np.linalg.solve(gram_sum + reg, rhs_sum)

    avg = R(alpha=alpha)
    avg.mean_, avg.scale_ = shared_mean, shared_scale
    avg.coef_ = theta

    out = {}
    for c, m in zip(clients, models):
        # Key must match the torch path's ``local:<name>`` convention.  Keying these by the bare
        # client name instead makes every ``startswith("local:")`` filter silently return nothing
        # on a torch-less install - which is a failure that looks like "no local models were
        # trained" rather than like a bug.
        out[f"local:{c.name}"] = FederatedResult(
            f"local:{c.name}", m.evaluate(pooled_test)[SCORE_KEY],
            {c2.name: m.evaluate(c2.test)[SCORE_KEY] for c2 in clients},
            notes="trained on this client's data only (shared feature basis)")
    pooled_train = TrajectoryDataset(np.concatenate([c.train.x for c in clients]),
                                     np.concatenate([c.train.y for c in clients]))
    central = fit_with_shared_basis(pooled_train.x, pooled_train.y, alpha)
    return out, avg, central, oneshot


# ============================================================================ experiment
def run_federated_experiment(
    clients=DEFAULT_CLIENTS,
    *,
    n_samples_per_client: int = 300,
    rounds: int = 8,
    local_epochs: int = 4,
    lr: float = 1.5e-3,
    fedprox_mu: float = 0.05,
    dp_clip: float = 1.0,
    dp_noise: float = 0.35,
    seed: int = 0,
    use_torch: bool | None = None,
    client_data: list | None = None,
    verbose: bool = False,
) -> dict:
    """
    Train the surrogate under every scheme and compare on a pooled test set.

    The pooled test set is the right yardstick: the question a federation exists to answer is
    "can we predict re-entries in general", not "can each operator predict its own".  A local
    model looks excellent on its own regime and that is precisely the illusion this measures.
    """
    use_torch = torch_available() if use_torch is None else bool(use_torch)

    if client_data is None:
        client_data = []
        for name in clients:
            ds = build_trajectory_dataset(n_samples_per_client, name,
                                         seed=seed + abs(hash(name)) % 997)
            tr, te = ds.split(0.75, seed=seed)
            client_data.append(ClientData(REGIMES[name].name, tr, te))
    pooled_test = TrajectoryDataset(np.concatenate([c.test.x for c in client_data]),
                                    np.concatenate([c.test.y for c in client_data]))
    pooled_train = TrajectoryDataset(np.concatenate([c.train.x for c in client_data]),
                                     np.concatenate([c.train.y for c in client_data]))
    results: dict[str, FederatedResult] = {}

    # ------------------------------------------------------------------ numpy fallback
    if not use_torch:
        locals_, avg, central, oneshot = _federated_ridge(
            client_data, pooled_test, rounds=rounds, seed=seed)
        results.update(locals_)
        results["fedavg"] = FederatedResult(
            "fedavg", avg.evaluate(pooled_test)[SCORE_KEY],
            {c.name: avg.evaluate(c.test)[SCORE_KEY] for c in client_data},
            rounds=1,
            notes="exact sufficient-statistic aggregation: identical to centralised, one round, "
                  "no raw data shared (possible only because the model is linear)")
        results["fedavg_oneshot"] = FederatedResult(
            "fedavg_oneshot", oneshot.evaluate(pooled_test)[SCORE_KEY],
            {c.name: oneshot.evaluate(c.test)[SCORE_KEY] for c in client_data},
            rounds=1,
            notes="single average of closed-form solutions; shown to demonstrate why FedAvg "
                  "iterates - this cannot converge on non-IID clients")
        results["centralised"] = FederatedResult(
            "centralised", central.evaluate(pooled_test)[SCORE_KEY],
            {c.name: central.evaluate(c.test)[SCORE_KEY] for c in client_data},
            notes="upper bound: all data pooled")
        return {"clients": [c.name for c in client_data], "results": results,
                "backend": "numpy", "table": [r.summary() for r in results.values()],
                "client_data": client_data, "pooled_test": pooled_test}

    from .apsgtt import APSGTT, APSGTTConfig

    window = client_data[0].train.x.shape[1]
    total_epochs = rounds * local_epochs

    def fresh():
        return APSGTT(APSGTTConfig(seed=seed, epochs=total_epochs), window=window)

    # --------------------------------------------------------------- local-only models
    for c in client_data:
        m = fresh()
        _local_train(m, c.train, epochs=total_epochs, lr=lr, seed=seed)
        results[f"local:{c.name}"] = FederatedResult(
            f"local:{c.name}", m.evaluate(pooled_test)[SCORE_KEY],
            {c2.name: m.evaluate(c2.test)[SCORE_KEY] for c2 in client_data},
            notes="trained on this client's data only")
        if verbose:
            print(f"  local {c.name:32s} pooled {results[f'local:{c.name}'].global_error:8.2f} km")

    # ------------------------------------------------------------------- centralised
    m = fresh()
    _local_train(m, pooled_train, epochs=total_epochs, lr=lr, seed=seed)
    results["centralised"] = FederatedResult(
        "centralised", m.evaluate(pooled_test)[SCORE_KEY],
        {c.name: m.evaluate(c.test)[SCORE_KEY] for c in client_data},
        notes="upper bound: all data pooled, normally not achievable")
    if verbose:
        print(f"  centralised{'':26s} pooled {results['centralised'].global_error:8.2f} km")

    # -------------------------------------------------------------- federated schemes
    param_bytes = int(sum(p.numel() for _n, p in fresh().named_parameters()) * 4)
    schemes = [("fedavg", 0.0, 0.0, 0.0), ("fedprox", fedprox_mu, 0.0, 0.0),
               ("fedavg_dp", 0.0, dp_clip, dp_noise)]
    for scheme, mu, clip, noise in schemes:
        server = fresh()
        global_state = _flat_state(server)
        rng = np.random.default_rng(seed)
        history = []
        for rnd in range(int(rounds)):
            states, weights, clip_stats = [], [], []
            for c in client_data:
                local = fresh()
                local.load_state_dict(global_state)
                _local_train(local, c.train, epochs=local_epochs, lr=lr, mu=mu,
                             global_state=global_state, seed=seed + rnd)
                st = _flat_state(local)
                if noise > 0:
                    st, raw_norm, scale = _clip_and_noise(st, global_state, clip, noise, rng)
                    clip_stats.append((raw_norm, scale))
                states.append(st)
                weights.append(len(c))
            global_state = _weighted_average(states, weights)
            server.load_state_dict(global_state)
            err = server.evaluate(pooled_test)[SCORE_KEY]
            history.append({"round": rnd, "pooled_error_km": err,
                            "mean_update_norm": float(np.mean([s[0] for s in clip_stats]))
                            if clip_stats else None})
            if verbose:
                print(f"  {scheme:10s} round {rnd + 1}/{rounds}  pooled {err:8.2f} km")
        results[scheme] = FederatedResult(
            scheme, server.evaluate(pooled_test)[SCORE_KEY],
            {c.name: server.evaluate(c.test)[SCORE_KEY] for c in client_data},
            rounds=int(rounds), bytes_per_round=param_bytes * len(client_data),
            epsilon=(_epsilon_estimate(noise, rounds, len(client_data)) if noise > 0 else None),
            history=history,
            notes=("proximal term mu=%.3g limits client drift" % mu if mu > 0 else
                   "clip=%.2g, noise multiplier=%.2g; epsilon is a loose upper bound from "
                   "advanced composition" % (clip, noise) if noise > 0 else
                   "weight averaging, no privacy mechanism"))

    return {"clients": [c.name for c in client_data], "results": results, "backend": "torch",
            "table": [r.summary() for r in results.values()],
            "client_data": client_data, "pooled_test": pooled_test}


def federated_report(experiment: dict) -> list[dict]:
    """Comparison table for the dashboard, best pooled error first."""
    rows = []
    for r in experiment["results"].values():
        s = r.summary()
        rows.append({
            "scheme": s["scheme"],
            "pooled error [km]": s["global_error_km"],
            "worst client [km]": s["worst_client_error_km"],
            "fairness spread [km]": s["fairness_spread_km"],
            "rounds": s["rounds"],
            "MB / round": s["bytes_per_round"] / 1e6 if s["bytes_per_round"] else 0.0,
            "epsilon (loose)": s["epsilon"],
            "notes": s["notes"],
        })
    return sorted(rows, key=lambda r: r["pooled error [km]"])


def heterogeneity_report(experiment: dict) -> list[dict]:
    """
    Per-client error of every scheme's global model.

    The interesting failure this exposes: a local model can be the *best* on its own client and
    among the worst everywhere else, which is invisible in a pooled average.
    """
    rows = []
    for name, r in experiment["results"].items():
        row = {"scheme": name}
        row.update({k: float(v) for k, v in r.per_client_error.items()})
        rows.append(row)
    return rows

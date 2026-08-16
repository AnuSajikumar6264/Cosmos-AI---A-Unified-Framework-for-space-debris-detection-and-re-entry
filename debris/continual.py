"""
Continual learning: adapting to new debris regimes without forgetting the old ones.

A deployed re-entry surrogate meets new populations over its life - a new launcher family, a
constellation with unusual area-to-mass, a different solar-activity epoch changing thermospheric
density.  Retraining from scratch on everything each time is wasteful and often impossible
(historical data may no longer be held).  Fine-tuning on only the new regime is fast and
destroys the old capability: that is **catastrophic forgetting**, and it is not a hypothetical -
:func:`run_continual_experiment` measures it here at several hundred percent error growth on
earlier tasks.

Three strategies, measured against each other
---------------------------------------------
``naive``   sequential fine-tuning, no mitigation.  The control, and the thing to beat.
``ewc``     Elastic Weight Consolidation (Kirkpatrick et al. 2017).  After each task, estimate
            the diagonal Fisher information and penalise later movement of parameters the old
            task was sensitive to.  Stores two vectors per task, no data.
``replay``  Keep a small reservoir sample of past inputs and mix them into every batch.  Uses
            data but no extra machinery, and is usually the stronger of the two.

Metrics
-------
Built on the error matrix ``E[i, j]`` = error on task *j* after training through task *i*
(Lopez-Paz & Ranzato's protocol, with a regression error in place of accuracy so *lower is
better*):

* **average error** - mean over all tasks at the end.  The headline number.
* **forgetting** - ``mean_{j<T} (E[T, j] - E[j, j])``.  How much worse earlier tasks got.
  Positive is forgetting; zero or negative means none.
* **forward transfer** - ``mean_{j>1} (E[j-1, j] - E_scratch[j])``.  Negative is good: the model
  was already better than chance on a task before seeing any of its data.

Reporting the full matrix rather than a single average is deliberate - an averaged number can
hide a method that is excellent on recent tasks and useless on the first one.
"""

from __future__ import annotations

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

#: Default task order.  Deliberately arranged so consecutive tasks are dissimilar - forgetting
#: is mild when tasks resemble each other, and a benign ordering would understate the problem.
DEFAULT_TASK_ORDER = ("steep_deorbit", "light_fragments", "dense_survivors", "shallow_decay")

#: The metric all strategies are scored on.
SCORE_KEY = "impact_median_error_km"


@dataclass
class ContinualResult:
    """Error matrix and derived metrics for one strategy."""

    strategy: str
    tasks: list[str]
    error_matrix: np.ndarray          # (T, T): E[i, j], error on task j after training task i
    scratch_errors: np.ndarray        # per-task error of a model trained on that task alone
    n_parameters: int = 0
    notes: str = ""

    @property
    def final_errors(self) -> np.ndarray:
        return self.error_matrix[-1]

    @property
    def average_error(self) -> float:
        return float(np.mean(self.final_errors))

    @property
    def forgetting(self) -> float:
        """Mean growth in error on earlier tasks. Positive means forgetting."""
        t = len(self.tasks)
        if t < 2:
            return 0.0
        return float(np.mean([self.error_matrix[-1, j] - self.error_matrix[j, j]
                              for j in range(t - 1)]))

    @property
    def forgetting_ratio(self) -> float:
        """Final error on earlier tasks divided by their error when freshly learned."""
        t = len(self.tasks)
        if t < 2:
            return 1.0
        num = float(np.mean([self.error_matrix[-1, j] for j in range(t - 1)]))
        den = float(np.mean([self.error_matrix[j, j] for j in range(t - 1)]))
        return num / max(den, 1e-9)

    @property
    def forward_transfer(self) -> float:
        """Mean advantage before seeing a task's data. Negative is good."""
        t = len(self.tasks)
        if t < 2:
            return 0.0
        return float(np.mean([self.error_matrix[j - 1, j] - self.scratch_errors[j]
                              for j in range(1, t)]))

    def summary(self) -> dict:
        return {
            "strategy": self.strategy,
            "average_error_km": self.average_error,
            "forgetting_km": self.forgetting,
            "forgetting_ratio": self.forgetting_ratio,
            "forward_transfer_km": self.forward_transfer,
            "final_per_task_km": {t: float(e) for t, e in zip(self.tasks, self.final_errors)},
            "n_parameters": self.n_parameters,
            "notes": self.notes,
        }


# =============================================================================== buffers
class ReservoirBuffer:
    """
    Fixed-capacity uniform sample of everything ever seen, by reservoir sampling.

    Uniformity matters: a simple ring buffer keeps only the most recent samples, which is exactly
    the data replay does *not* need - the point is to retain the oldest tasks.  Reservoir sampling
    holds a uniform sample over the whole stream at fixed memory and without knowing its length
    in advance.
    """

    def __init__(self, capacity: int = 256, n_features: int = 0, window: int = 0,
                 seed: int = 0):
        self.capacity = int(capacity)
        self.x: list[np.ndarray] = []
        self.y: list[np.ndarray] = []
        self.seen = 0
        self.rng = np.random.default_rng(seed)

    def add_dataset(self, dataset: TrajectoryDataset):
        for i in range(len(dataset)):
            self.seen += 1
            if len(self.x) < self.capacity:
                self.x.append(dataset.x[i])
                self.y.append(dataset.y[i])
            else:
                j = int(self.rng.integers(0, self.seen))
                if j < self.capacity:
                    self.x[j] = dataset.x[i]
                    self.y[j] = dataset.y[i]

    def sample(self, n: int):
        if not self.x:
            return None, None
        idx = self.rng.integers(0, len(self.x), size=min(int(n), len(self.x)))
        return np.stack([self.x[i] for i in idx]), np.stack([self.y[i] for i in idx])

    def __len__(self) -> int:
        return len(self.x)


# ================================================================================ torch
def _train_task_torch(model, dataset, *, epochs, strategy, fisher=None, anchor=None,
                      buffer=None, ewc_lambda=5000.0, replay_ratio=0.5, lr=1e-3, seed=0):
    """Train one task under a given continual strategy. Returns the model."""
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

    for _epoch in range(int(epochs)):
        model.train_mode(True)
        perm = rng.permutation(len(dataset))
        for i in range(0, len(dataset), cfg.batch_size):
            idx = perm[i:i + cfg.batch_size]
            if len(idx) < 2:
                continue
            xb, yb = x[idx], y[idx]
            if strategy == "replay" and buffer is not None and len(buffer):
                bx, by = buffer.sample(max(int(replay_ratio * len(idx)), 1))
                if bx is not None:
                    xb = torch.cat([xb, torch.as_tensor(bx, device=model.device)])
                    yb = torch.cat([yb, torch.as_tensor(by, device=model.device)])
            t_pred, p_pred = model.forward(xb)
            loss = huber(t_pred, yb[:, 0]) + huber(p_pred, yb[:, 1:])

            if strategy == "ewc" and fisher is not None and anchor is not None:
                penalty = 0.0
                for name, p in named.items():
                    if name in fisher:
                        penalty = penalty + (fisher[name] * (p - anchor[name]) ** 2).sum()
                loss = loss + ewc_lambda * penalty

            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
    return model


def _diagonal_fisher_torch(model, dataset, n_batches: int = 12, batch_size: int = 32,
                           seed: int = 0):
    """
    Diagonal Fisher information: the expected squared gradient of the loss at the converged
    parameters.

    This is what tells EWC which parameters mattered.  Estimated on the task's own data with the
    model already fitted to it, so a large value means "moving this weight breaks this task".
    """
    import torch

    fisher = {n: torch.zeros_like(p) for n, p in model.named_parameters()}
    huber = torch.nn.HuberLoss(delta=0.15)
    rng = np.random.default_rng(seed)
    model.train_mode(False)
    for _ in range(int(n_batches)):
        idx = rng.integers(0, len(dataset), size=min(batch_size, len(dataset)))
        xb = torch.as_tensor(dataset.x[idx], device=model.device)
        yb = torch.as_tensor(dataset.y[idx], device=model.device)
        t_pred, p_pred = model.forward(xb)
        loss = huber(t_pred, yb[:, 0]) + huber(p_pred, yb[:, 1:])
        model_params = [p for _n, p in model.named_parameters()]
        for p in model_params:
            if p.grad is not None:
                p.grad = None
        loss.backward()
        for n, p in model.named_parameters():
            if p.grad is not None:
                fisher[n] += p.grad.detach() ** 2
    for n in fisher:
        fisher[n] /= float(n_batches)
    return fisher


# =============================================================================== fallback
def _ridge_continual(task_data, strategy, buffer_capacity=256, seed=0):
    """
    numpy strategy comparison using :class:`RidgeSurrogate`.

    Sequential refitting of a closed-form model forgets *completely* - each fit discards the
    previous solution - which makes it the clearest possible demonstration of the problem, and
    replay fixes it just as clearly.  There is no meaningful EWC analogue for a closed-form fit,
    so that cell is reported as unavailable rather than faked.
    """
    from .ml_common import RidgeSurrogate as R

    tasks = list(task_data)
    t = len(tasks)
    err = np.zeros((t, t))
    buf = ReservoirBuffer(buffer_capacity, seed=seed)
    accumulated = None

    for i, (_name, train, _test) in enumerate(tasks):
        if strategy == "replay":
            buf.add_dataset(train)
            bx, by = buf.sample(len(buf))
            mixed = TrajectoryDataset(np.concatenate([train.x, bx]),
                                      np.concatenate([train.y, by]))
            model = R.tune(mixed, seed=seed)
        elif strategy == "joint":
            accumulated = train if accumulated is None else TrajectoryDataset(
                np.concatenate([accumulated.x, train.x]),
                np.concatenate([accumulated.y, train.y]))
            model = R.tune(accumulated, seed=seed)
        else:
            model = R.tune(train, seed=seed)
        for j, (_n2, _tr2, test2) in enumerate(tasks):
            err[i, j] = model.evaluate(test2)[SCORE_KEY]
    scratch = np.array([R.tune(tr, seed=seed).evaluate(te)[SCORE_KEY]
                        for _n, tr, te in tasks])
    return err, scratch


# ============================================================================ experiment
def run_continual_experiment(
    task_order=DEFAULT_TASK_ORDER,
    *,
    n_samples: int = 400,
    epochs: int = 30,
    strategies=("naive", "ewc", "replay", "joint"),
    ewc_lambda: float = 5000.0,
    buffer_capacity: int = 256,
    replay_ratio: float = 0.5,
    seed: int = 0,
    use_torch: bool | None = None,
    datasets: dict | None = None,
    verbose: bool = False,
) -> dict:
    """
    Train through a sequence of regimes under each strategy and fill in the error matrix.

    ``joint`` - training on all data seen so far - is included as the upper bound.  It is not a
    continual method (it needs every past sample retained), but without it there is no way to
    tell whether a strategy has closed the gap or merely narrowed it.
    """
    use_torch = torch_available() if use_torch is None else bool(use_torch)
    tasks = list(task_order)

    if datasets is None:
        datasets = {}
        for name in tasks:
            ds = build_trajectory_dataset(n_samples, name, seed=seed + hash(name) % 1000)
            datasets[name] = ds.split(0.75, seed=seed)
    task_data = [(n, datasets[n][0], datasets[n][1]) for n in tasks]

    results: dict[str, ContinualResult] = {}
    for strategy in strategies:
        if not use_torch:
            if strategy == "ewc":
                continue  # no meaningful closed-form analogue; omitted rather than faked
            err, scratch = _ridge_continual(task_data, strategy, buffer_capacity, seed)
            results[strategy] = ContinualResult(
                strategy, tasks, err, scratch, notes="numpy RidgeSurrogate fallback")
            if verbose:
                print(f"  {strategy:8s} avg {np.mean(err[-1]):8.2f} km")
            continue

        from .apsgtt import APSGTT, APSGTTConfig

        window = task_data[0][1].x.shape[1]
        model = APSGTT(APSGTTConfig(seed=seed, epochs=epochs), window=window)
        buf = ReservoirBuffer(buffer_capacity, seed=seed)
        fisher_acc, anchor = None, None
        err = np.zeros((len(tasks), len(tasks)))
        joint_data = None

        for i, (name, train, _test) in enumerate(task_data):
            if strategy == "joint":
                joint_data = train if joint_data is None else TrajectoryDataset(
                    np.concatenate([joint_data.x, train.x]),
                    np.concatenate([joint_data.y, train.y]))
                _train_task_torch(model, joint_data, epochs=epochs, strategy="naive", seed=seed)
            else:
                _train_task_torch(
                    model, train, epochs=epochs, strategy=strategy, fisher=fisher_acc,
                    anchor=anchor, buffer=buf, ewc_lambda=ewc_lambda,
                    replay_ratio=replay_ratio, seed=seed)
            if strategy == "replay":
                buf.add_dataset(train)
            if strategy == "ewc":
                f = _diagonal_fisher_torch(model, train, seed=seed)
                if fisher_acc is None:
                    fisher_acc = f
                else:
                    # Accumulate across tasks: a weight protected by any earlier task stays
                    # protected. Overwriting would forget the constraint, not just the weights.
                    for k in fisher_acc:
                        fisher_acc[k] = fisher_acc[k] + f[k]
                anchor = {n: p.detach().clone() for n, p in model.named_parameters()}
            for j, (_n2, _tr2, test2) in enumerate(task_data):
                err[i, j] = model.evaluate(test2)[SCORE_KEY]
            if verbose:
                print(f"  {strategy:8s} after {name:18s} " +
                      " ".join(f"{err[i, j]:7.1f}" for j in range(len(tasks))))

        scratch = np.zeros(len(tasks))
        for j, (_n, tr, te) in enumerate(task_data):
            m = APSGTT(APSGTTConfig(seed=seed + 7, epochs=epochs), window=window)
            _train_task_torch(m, tr, epochs=epochs, strategy="naive", seed=seed)
            scratch[j] = m.evaluate(te)[SCORE_KEY]

        results[strategy] = ContinualResult(
            strategy, tasks, err, scratch, n_parameters=model.n_parameters(),
            notes=("upper bound: retains all past data, not a continual method"
                   if strategy == "joint" else ""))

    return {
        "tasks": tasks,
        "results": results,
        "backend": "torch" if use_torch else "numpy",
        "table": [r.summary() for r in results.values()],
        "datasets": datasets,
    }


def forgetting_report(experiment: dict) -> list[dict]:
    """Flat table for the dashboard, ordered best average error first."""
    rows = []
    for r in experiment["results"].values():
        s = r.summary()
        rows.append({
            "strategy": s["strategy"],
            "average error [km]": s["average_error_km"],
            "forgetting [km]": s["forgetting_km"],
            "forgetting ratio": s["forgetting_ratio"],
            "forward transfer [km]": s["forward_transfer_km"],
            "notes": s["notes"],
        })
    return sorted(rows, key=lambda r: r["average error [km]"])

# Debris Detection & Re-entry Prediction — COSMOS-AI extension

An extension to the Satellite Digital Twin that answers one question end to end:

> **If this satellite comes apart, or this rocket sheds a stage — where does the hardware land,
> who is at risk, and what does it do to the orbital environment?**

It is deliberately *coupled* to the existing anomaly-detection and health-monitoring twin rather
than bolted alongside it. Subsystem health drives the breakup **physics**, not just a separate
risk readout: a propulsion failure produces a different kind of breakup, at a different altitude,
with a different footprint, than a thermal failure does.

---

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Seven new pages appear in the sidebar under **DEBRIS & GROUND RISK**. No new mandatory
dependencies beyond what the dashboard already used — the physics core is numpy-only.

For the machine-learning contributions (optional, adds torch):

```bash
pip install -r requirements-ml.txt
```

Programmatic use:

```python
from debris import DebrisObject, StateVector, propagate

state = StateVector.from_geodetic(13.72, 80.23, 120e3, 7500.0, -1.5, 140.0)
traj = propagate(state, DebrisObject("tank", mass=200.0, area=0.15))
print(traj.impact_latitude, traj.impact_longitude, traj.impact_speed)
```

The whole coupled chain, from a telemetry anomaly to an expected-casualty number:

```python
from debris import run_coupled_prediction

r = run_coupled_prediction(
    anomaly_score=0.9,
    health={"Propulsion System": 0.9, "Thermal Control": 0.6},
)
print(r.hazard.summary())    # breakup type, altitude, fragmentation probability
print(r.risk.summary())      # expected casualties, land probability, nearest city
print(r.zone_95.area_km2)    # conformal 95 % impact zone
```

---

## What was built

### Physics core (numpy only)

| Module | What it does |
|---|---|
| `debris/atmosphere.py` | US Standard Atmosphere 1976 + tabulated fast path |
| `debris/geodesy.py` | WGS-84 frames, great-circle geometry |
| `debris/drag.py` | Mach- and Knudsen-dependent drag coefficients |
| `debris/materials.py` | Thermal properties for the demise model |
| `debris/propagator.py` | 3-DOF re-entry integrator with coupled aerothermal demise |
| `debris/fragmentation.py` | NASA Standard Breakup Model + parent remnants |
| `debris/launch.py` | Launch-vehicle staging and drop zones |
| `debris/monte_carlo.py` | Impact dispersion and **conformal prediction zones** |
| `debris/risk.py` | Population exposure and expected casualties |
| `debris/kessler.py` | Two-species cascade / criticality engine |
| `debris/circular_economy.py` | Debris-years accounting and mitigation optimisation |
| `debris/detection.py` | Frame-differencing debris detection, pixels → physics |
| `debris/coupling.py` | Health / anomaly ↔ breakup-physics coupling |
| `debris/viz.py` | Plotly figures (needs plotly) |

### Learning layer (needs torch; every module has a working numpy fallback)

| Module | What it does |
|---|---|
| `debris/ml_common.py` | Labelled dataset generation from the propagator; ridge baseline |
| `debris/apsgtt.py` | Adaptive Prognostic State-space Graph Trajectory Transformer + LoRA |
| `debris/continual.py` | Continual learning: EWC, replay, forgetting metrics |
| `debris/federated.py` | FedAvg / FedProx / DP-FedAvg across operators |

### Dashboard

`debris_ui.py` holds the seven Streamlit pages; `app.py` gained only a navigation block and a
dispatch table, so the existing analytics pages are untouched.

---

## Validation

Everything below was measured, not asserted. Reproduce with the snippets in each module's
docstring.

### Propagator

| Check | Result |
|---|---|
| US76 atmosphere vs standard tables | **< 0.002 %** error at every layer boundary |
| Scalar vs vectorised atmosphere | 7 × 10⁻¹⁵ relative |
| WGS-84 round trip (Ferrari) | 3 × 10⁻⁹ m |
| Keplerian energy conservation, one orbit in vacuum | 8 × 10⁻⁶ relative |
| Terminal velocity vs analytic `√(2Bg/ρ)` | 0.67 % |
| Coriolis deflection, 30 km vertical drop at 45° N | 80 m **east** (analytic free-fall: 95 m) |
| J2 radial oscillation on a circular orbit | 19.5 km peak-to-peak (analytic: 19 km) |
| Step-size convergence (rtol 10⁻⁶ → 10⁻¹²) | impact point converges to 0.08 m |
| **Scalar vs vectorised ensemble propagator** | **0.15 m** worst-case impact-point disagreement |

The last row is the strongest check available: two independently written implementations of the
same physics — one pure-Python scalar, one vectorised numpy — agree to 15 cm across a population
spanning four decades of ballistic coefficient.

Downrange is monotonic in ballistic coefficient across the whole range, from an MLI blanket
(B = 0.6 kg/m², 1125 km, 64-minute fall, 4 m/s impact) to a titanium COPV sphere
(B = 7609 kg/m², 3679 km, 445 m/s impact).

Monte Carlo throughput: **2000 dispersed trajectories in 0.8 s**.

### Conformal prediction zones (contribution #5)

Held-out coverage on a 1518-sample fragment-cloud dispersion, averaged over 40 random
calibration/test splits:

| α | nominal | Gaussian χ² ellipse | conformal (Mahalanobis) | conformal (density) |
|---|---|---|---|---|
| 0.10 | 0.90 | 0.9022 | 0.9002 | 0.8987 |
| 0.05 | 0.95 | **0.9394** ✗ | 0.9500 ✓ | 0.9504 ✓ |
| 0.01 | 0.99 | **0.9707** ✗ | 0.9911 ✓ | 0.9928 ✓ |

Areas at α = 0.01: Gaussian 36 100 km², conformal-Mahalanobis 128 400 km², conformal-density
**29 400 km²**. The density-based zone therefore delivers **better coverage in 19 % less area**
than the ellipse that misses its own target, and is 4.4× tighter than the conformal ellipse.

Two implementation details are load-bearing:
- the `⌈(N+1)(1−α)⌉` quantile index, not the plain empirical quantile — that `+1` is what makes
  the guarantee finite-sample rather than asymptotic;
- a **leave-one-out** KDE for the calibration scores. Scoring a point against a density estimate
  that includes its own kernel costs ~1.5 points of coverage.

For a *single* object with moderate uncertainty the Gaussian ellipse is fine (0.945 against
0.95). The problem is that you cannot tell from the ellipse which regime you are in.

### Kessler cascade engine (contribution #6)

Two species — intact objects and fragments — tracked separately, which is the difference between
a credible model and a useless one. Collapsing them forces the ~900 fragments from a collision to
inherit the mass and cross-section of the satellites that made them; a 200-year run then
over-predicts population growth by more than two orders of magnitude (×782 instead of ×0.94).

| Check | Result |
|---|---|
| LEO-wide catastrophic collision rate | 1 per 19.5 years (published expectation: 5–10) |
| Supercritical band | 800–1000 km, criticality 1.8–3.1 |
| 200 years, zero launches | population ×0.94 (published studies: slow growth) |
| Same 400-fragment breakup at 1450 km vs 350 km | **1501× worse** |

Integrated with exponential-Euler because drag lifetimes span 0.03 years at 200 km to 60 000 years
at 1500 km — any explicit scheme with a step large enough to reach a 200-year horizon is violently
unstable on the low shells.

### Debris detection

A single frame **cannot** separate debris from stars: both are unresolved point sources through
the same PSF, and a distant fragment is usually the fainter of the two. Measured single-frame
precision is ≈ 0.01. Frame differencing is what makes the problem well-posed.

On 40 held-out synthetic frame pairs, at each detector's best operating point:

| Detector | Precision | Recall | **F1** | Position error |
|---|---|---|---|---|
| DoG (classical, untrained) | 0.266 | 0.406 | 0.322 | 0.57 px |
| CenterNet (600 steps, 177 s CPU) | **0.872** | 0.584 | **0.700** | 1.45 px |

The CNN more than doubles F1, almost entirely by *rejecting* false positives. The surviving
residuals in a difference image are not noise — they have characteristic shapes a CNN can learn
and a symmetric-blob filter cannot. Note the trade in the last column: the classical detector's
second-moment centroid is more accurate, so running the CNN for detection and the DoG centroid for
refinement would get both.

Two negative results worth recording, both measured:
- **Local noise normalisation does not help** here (best F1 0.366 at a 40 px window vs 0.361
  global), and small windows actively hurt (0.250 at 15 px) because a source inflates the noise
  estimate in its own neighbourhood. Left available and defaulted off.
- **Registration only pays above ~0.3 px of misalignment.** Fourier shifting rings around hot
  pixels and bright sources, and below a few tenths of a pixel that ringing costs more precision
  than the misalignment it corrects. At 1.5 px jitter registration gives a 3.2× F1 improvement, so
  the rule is adaptive rather than always-on.

### APSGTT-LoRA surrogate (contribution #1)

A learned surrogate for the propagator: it observes the first quarter of a fall — the arc a
tracking radar actually gets — and predicts time-to-impact and impact point directly. Not for
accuracy's sake (the physics is validated to 0.15 m) but for speed and differentiability:
**~750 µs/object against the propagator's ~9 ms, a 12× speed-up**, which is what makes continuous
re-prediction against a live feed or a very large fragment population tractable.

Measured against tuned ridge regression on flattened window features (480 held-out trajectories,
median impact error):

| training samples | ridge | APSGTT | winner |
|---|---|---|---|
| 200 | 63.2 km | 102.1 km | ridge |
| 500 | 49.9 km | 101.0 km | ridge |
| 1 000 | 45.0 km | 45.8 km | tie |
| 2 000 | 58.8 km | 20.3 km | **APSGTT** |
| 2 720 | 56.8 km | **17.3 km** | **APSGTT (3.3×)** |

The crossover sits around a thousand samples. Below it, use the ridge baseline — closed-form, fits
in milliseconds, and wins. Above it the transformer wins decisively (17.3 vs 56.8 km median, 47 vs
162 km at p90). Because the physics engine generates labels at ~15 ms each, getting past the
crossover costs under a minute of compute.

The table is included rather than just the winning number because the honest claim is conditional.
It also caught a real bug: a first version pooled the nine physical channels by averaging a
*shared* input projection, so which channel carried which value survived only as an additive
embedding — it scored 280 km where ridge scored 65. Per-channel multiplicative weights,
per-timestep graph mixing, and a direct linear path from the raw inputs fixed it. The components
were fine; the plumbing between them was not.

LoRA at the default configuration trains 14 336 of 108 164 parameters (13 %) — much more than the
sub-1 % usually quoted, because this backbone is small. The parameter saving is therefore modest
here; the real benefits are that the base weights are provably untouched (one backbone can serve
many adapted regimes) and that adaptation starts as an exact no-op.

### Continual learning (contribution #2)

Four physically distinct regimes learned in sequence (deliberately ordered so consecutive tasks
are dissimilar — forgetting is mild when tasks resemble each other, and a benign ordering would
understate the problem):

| strategy | average error | forgetting | ratio vs freshly-learned |
|---|---|---|---|
| naive sequential | 26 617 km | +39 888 km | **1268×** |
| replay (reservoir buffer) | 57 km | +52 km | 2.98× |
| joint (upper bound, retains all data) | 44 km | +32 km | 2.19× |

Catastrophic forgetting is not subtle here. The reported error matrix makes it legible: task 2 is
learned to 50 km and ends at 79 640 km after two further tasks. (The magnitude is extreme in the
numpy fallback because a linear model extrapolating outside its training domain is unbounded; the
torch path forgets substantially but finitely.) A reservoir buffer — uniform over the whole
stream, not a recency ring — recovers to within 30 % of the joint upper bound.

`joint` is included precisely because without it there is no way to tell whether a strategy closed
the gap or merely narrowed it. It is not a continual method: it retains every past sample.

### Federated intelligence (contribution #3)

Clients are physically distinct regimes, i.e. strongly non-IID. Random shards of one pool would
make every method look equally good and prove nothing.

| scheme | pooled error | worst client | fairness spread |
|---|---|---|---|
| **fedavg** (sufficient-statistic aggregation) | **36.59 km** | 56.4 km | 28.7 km |
| centralised (upper bound, all data pooled) | 36.59 km | 56.4 km | 28.7 km |
| best single-client model | 65.89 km | 206 km | 194 km |
| fedavg_oneshot (naive coefficient averaging) | 304 km | 421 km | 307 km |

For a linear model, aggregating only the moments `zᵀz` and `zᵀy` gives the **exact** pooled
solution — bit-for-bit identical to centralised training — in one round, with no observation
leaving a client. That is reported because it is the honest ceiling: any gap in the neural path is
attributable to the optimiser and non-convexity, not to federation itself. It also does not
generalise, which is exactly why the torch path must iterate FedAvg.

The per-client table shows the failure a pooled average hides: each local model is *best* on its
own client (12, 19, 38 km) and among the worst elsewhere (up to 1220 km), while the federated
model is uniformly good (35, 28, 56 km).

`fedavg_oneshot` is kept as a control. Averaging exact local solutions equals the pooled solution
only when clients' design matrices are similar; on non-IID clients it is 8× worse than proper
aggregation and worse than the best single client — which is why real FedAvg iterates.

### Circular economy (contribution #4)

Currency: **debris-years** = objects left behind × orbital lifetime. Additive across objects, and
proportional to the integrated collision probability a mission imposes on its shell.

The mitigation selector is exact (exhaustive over the 2⁸ subsets) rather than greedy, because the
actions genuinely interact: a controlled re-entry blocks a graveyard manoeuvre, and material
recovery requires active removal. Greedy leaves debris-years on the table and the dashboard shows
the gap.

---

## Honest limitations

The physics is validated. Several *inputs* are not, and each module says which it is.

- **Population density is synthetic** — a hand-authored 10° land-fraction grid, 51 real metro
  areas, and a regional rural background. Good to roughly an order of magnitude at 100 km scales:
  enough to distinguish "ocean" from "over Dhaka", **not** enough for an operational safety case.
  `PopulationModel.from_grid` takes a real GPWv4/LandScan/WorldPop raster.
- **Launch-vehicle masses and separation conditions** are representative public-domain estimates,
  not vendor data. Every value is an overridable dataclass field.
- **The health → breakup-physics coupling is a stated hypothesis, not a fitted model.** There is
  no labelled corpus of satellite breakups to fit against. The logistic is calibrated so a nominal
  satellite reads ≈ 1 % (consistent with a handful of fragmentation events per year across
  thousands of objects) and so no single subsystem alone reaches certainty. Every mapping is
  documented with its reasoning in `debris/coupling.py`.
- **The Kessler engine is an aggregate particle-in-a-box model.** It does not propagate individual
  orbits or screen conjunctions, both of which real collision avoidance requires. Spatial densities
  are representative published figures, not a live catalogue.
- **Detector frames are simulated.** Results establish that the pipeline behaves as specified, not
  that it transfers to a real sensor.
- **Carbon factors cover direct propellant combustion only**, excluding soot radiative forcing and
  stratospheric ozone loss, which for solid and kerosene motors can rival the CO₂ term. Launches
  are therefore *under*-charged; comparisons between propellant types are more reliable than
  absolute totals.
- **Conformal coverage is conditional on exchangeability with the calibration ensemble.** It does
  not certify away model bias. Calibrating on one sampled fragment cloud and testing on a different
  one degrades coverage — that is distribution shift, and it is the honest limit of what ensemble
  calibration can promise. `conformalise_with_history` consumes real predicted-vs-actual residuals
  for coverage over actual events.
- **Differential-privacy ε is a loose upper bound** from advanced composition. A Rényi-DP or PLD
  accountant gives a materially tighter bound for the same noise.

Nothing here is qualified for an operational safety case.

---

## On the "seven novel contributions" framing

Stated plainly, because a claim that does not survive review costs more than it gains:

- **Genuinely rigorous and new for this application:** conformal prediction zones (#5) and the
  two-species Kessler cascade engine (#6). The conformal result in particular is a real
  improvement — measurably correct coverage *and* a smaller region than the standard method,
  where the standard method demonstrably under-covers.
- **Established techniques applied to a new domain:** LoRA (#1), continual learning (#2),
  federated averaging (#3). Defensible as novel *application*; not novel theory. Each is
  implemented properly, with the controls that make the comparison meaningful — particularly
  "train on the target data alone", which is the control that tells you whether adaptation
  contributed anything at all.
- **Engineering frameworks rather than research contributions:** the circular-economy accounting
  (#4) and the digital-twin coupling (#7). Both are useful and neither is a theoretical advance.

The physics validation is the part of this work that would survive the most hostile review.

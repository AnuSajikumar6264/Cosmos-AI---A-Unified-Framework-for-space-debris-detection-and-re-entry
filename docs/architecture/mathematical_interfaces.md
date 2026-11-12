# COSMOS-AI mathematical interfaces

These are exchange contracts, not claims that all adapters or empirical links already
exist. Inputs must retain source/time/unit provenance. A module returning a scalar score
must identify whether it is a probability, rank score, physical quantity or decision score.

## 1. Time and state

An observation is indexed by a timezone-aware instant `t` and source-defined identity `i`.
An orbital Cartesian state is:

\[
\mathbf{x}_i(t)=(\mathbf{r}_i(t),\mathbf{v}_i(t))
\]

where `r` is in metres, `v` in metres/second, and the coordinate frame and epoch are
mandatory. This interface performs no frame conversion. A consumer requiring a different
frame must call a named transformation and record its input/output frames and transformation
version. A vector in TEME cannot be treated as GCRF or ITRF by relabeling it.

`OrbitalState` currently supports `GCRF`, `EME2000`, `TEME`, `ITRF` and `ITRS` labels.
Frame support means declared/validated name only, not a guarantee of upstream frame
accuracy or transformation correctness.

## 2. Telemetry and health

A telemetry batch contains channel values \(x_c(t_j)\), explicit missing entries, a positive
sample cadence and a start time. Resampling and channel normalization are model-specific.
Input data should be split before fitting any normalization, forecaster, calibration pool or
alarm threshold.

The health output is:

\[
H_i(t)=\{s_i(t), a_i(t), \mathcal{U}_i(t), m, \pi\}
\]

where `s` is an anomaly score, `a` an alarm, `U` the uncertainty descriptor, `m` the model
identity and `π` provenance. `s` is **not** interpreted as \(P(\text{anomaly})\) unless the
adapter names and validates that calibration. This matters because the existing fusion code
uses a score convention for some telemetry outputs.

## 3. Lifetime and re-entry

For residual lifetime \(T_i>0\), a probabilistic model may exchange a nondecreasing quantile
function \(Q_i(u)\) (days, \(0<u<1\)) and/or a cumulative horizon probability:

\[
F_i(H)=P(T_i\le H), \quad H>0,\quad 0\le F_i(H)\le1,\quad
H_1\le H_2\Rightarrow F_i(H_1)\le F_i(H_2).
\]

Quantile levels and values must be nondecreasing. If the training target is capped, censored,
or has a point mass at a cap, that fact belongs in method metadata; it must not be erased by
an adapter. Calibrated probabilities and raw ranking scores are distinct fields because
isotonic calibration can create ties.

Monte Carlo samples are one uncertainty representation; quantile intervals are another.
They must not be relabelled “conformal.” The contract does not derive a coverage guarantee.

## 4. Collision probability and decision priority

The physical collision quantity is:

\[
P_{\mathrm{coll},i}=P(\text{collision in the encounter}\mid
\text{relative state, covariance, hard-body model, assumptions}).
\]

A separate decision layer can define a priority score:

\[
R_i^{\mathrm{priority}} =
g(P_{\mathrm{coll},i},V_i,C_i,E_i),
\]

where `V` is vulnerability/operator capability, `C` consequence, and `E` evidence quality.
This project has not validated a general `g`. Health/context may affect priority, but must
not change the physical probability unless a justified physical input (such as the state or
covariance) actually changes.

## 5. Debris image interface

A detection is `(image_id, observed_at, x_px, y_px, score, detector)`. Pixel coordinates
belong to an image plane, not an inertial frame. It is not a catalog-object identification,
orbit, size or cross-section estimate. Those require separate calibrated models and
traceable transformations.

## 6. Cross-domain couplings

### C1 — family evidence

For object `i` forecast at time `t`, \(\phi_F(i,t)\) may use only family records available
strictly before `t`. Lifetime prediction becomes:

\[
\widehat{F}_i(H\mid \mathbf{x}_i(t),\phi_F(i,t)).
\]

The contribution is measured by a predeclared paired ablation against an otherwise identical
model without \(\phi_F\), with family/launch-cluster resampling. The model's existing ablation
is not consistent enough to assert universal benefit.

### C2 — cloud survival

For a catalogued breakup family `C`, the expected number of members remaining in orbit is:

\[
E[N_C(t)] = \sum_{i\in C:\ t_{0i}\le t} P(T_i>t-t_{0i}).
\]

Linearity of expectation does not require independent fragment lifetimes. Confidence
intervals for observed cloud-level error do require respecting dependence (for example,
resampling whole clouds). This expectation is not itself a predictive distribution for
`N_C(t)`; a variance model would need joint dependence.

### C3 — operational-status policy

The current policy is a mapping from object class and catalogue status to a forecast regime:

\[
\rho_i=\pi(\text{class}_i,\text{status}_i), \qquad
\widehat{F}_i(H)=
\begin{cases}
\text{previous-window base rate}, & \rho_i=\text{operator-controlled}\\
\text{natural-decay model}, & \rho_i=\text{natural-decay}\\
\text{explicit unknown policy}, & \rho_i=\text{unknown}.
\end{cases}
\]

This encodes a decision about when drag-only dynamics are unsuitable; status does not
alter the physical drag law. Evidence is one previously analysed follow-up window.

### C4 — operational escalation

If paired data become available, retain a tuple `(P_coll, vulnerability, consequence,
evidence_quality, priority)` and evaluate priority quality separately from probability
calibration. With present anonymised sources, C4 is a demonstration only.

## 7. Uncertainty and provenance transport

For every estimate, transport:

- representation (`interval`, `quantiles`, `samples`, calibrated probability, or score);
- method and nominal level where meaningful;
- assumptions/guarantee class (for example, marginal conformal under exchangeability);
- calibration and domain status;
- source hashes, code/config/model identifiers when actually available.

Do not combine differently calibrated scores as probabilities. Do not average a physical
probability with an operational priority. If a module cannot preserve a required meaning,
return an explicit abstention or failure.

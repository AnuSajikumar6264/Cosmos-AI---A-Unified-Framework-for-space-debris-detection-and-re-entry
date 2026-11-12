# D3.1 — Additional Q1-level validation requirements: assessment and plan

Date 2026-11-04 · **No experiment in §A–§E has been started. §6 is the plan requiring your
approval.**

Governing fact for all of §A–§E: **the OPS-SAT task is supervised binary classification of
telemetry fragments**, not unsupervised anomaly detection. From `cosmos/ai/telemetry/opssat.py`:
official split 1,594 train / 529 test from the dataset's own `train` flag; validation is a
stratified 20 % of official train (seed 2137, the dataset's official seed); supervised models
decide at `P ≥ 0.5`; nothing is tuned on test; 5 seeds per stochastic model; protocol fixed before
any test number was seen. This determines which baselines are *fair* and which metrics are
*meaningful*.

---

## A. Recent state-of-the-art comparisons

### A.1 What is already implemented — five of your six families are covered

| Your family | Implemented arms | Time-blocked AUC-PR | Status |
|---|---|---|---|
| **Classical statistical** | `cosmos_robust_z` (robust z-score / MAD monitor); `logreg`; on ESA-ADB also `global_std3`, `global_std5`, `out_of_limits` | 0.6732 | **Covered** |
| **Isolation-based** | `iforest` | 0.3313 | **Covered** |
| **Lightweight neural time-series** | `fcnn` (13,249 params), `cnn` (67,713), `transformer` (71,297) | 0.9666 / 0.9712 / 0.9418 | **Covered** |
| **Reconstruction-based** | — | — | **NOT COVERED — the one real gap** |
| **Foundation-model** | `chronos:amazon/chronos-bolt-small` | 0.9191 | **Covered** |
| **Satellite-specific** | `cosmos_monitor`, `ar8`, `patchtst` — **on ESA-ADB only, not OPS-SAT** | — | **Partially covered** |

Plus tree ensembles outside your list: `xgboost` 0.9639, `lightgbm`, `catboost`, `random_forest`,
`adaboost`.

**This is already a strong baseline set for a Q1 venue — eleven arms across five families on one
fixed protocol with five seeds.** The honest finding is that the baseline requirement is largely
*already met*, and only two gaps are worth closing.

### A.2 Gap 1 — no reconstruction-based baseline on OPS-SAT

A reconstruction arm (autoencoder-style: encode, reconstruct, score by reconstruction error) is the
standard family the project lacks. **But fairness requires care**, and this is where your
instruction about comparing models trained on different information binds hardest:

- The supervised arms use **fragment labels** in training.
- A classical reconstruction detector trains on nominal data only and uses **no anomaly labels**.
- `iforest` and `cosmos_robust_z` are already in this position, and they score 0.33 and 0.67
  against the supervised arms' 0.94–0.97. **That gap is an information gap, not a method gap**, and
  adding more unsupervised arms would largely reproduce it.

**Fair implementations, in order of preference:**

1. **Supervised reconstruction-residual classifier** — train an autoencoder on nominal fragments,
   then train a small supervised head on the reconstruction residuals using the *same* labels,
   *same* split, *same* seeds as the other supervised arms. This is a genuine reconstruction-based
   method evaluated on equal information, and it is the comparison worth making.
2. **Unsupervised autoencoder with a threshold set on the validation split** (never on test) —
   reported in a clearly separated block alongside `iforest` and `cosmos_robust_z`, labelled
   *"no anomaly labels used in training"*.

**Both should be reported, in separate blocks, with the information difference stated in the table
caption.** Reporting only (2) would understate reconstruction methods; reporting only (1) would
hide that reconstruction methods are usually deployed without labels.

### A.3 Gap 2 — no satellite-specific published method on OPS-SAT

`patchtst` is evaluated on ESA-ADB and reaches EW-F0.5 0.496 there, against `cosmos_monitor`'s
0.202. Running it on the OPS-SAT protocol would give a published, satellite-telemetry-specific
comparator on the benchmark where the project's positive claim lives. **Relevance:** it is the
strongest published arm the project has already implemented. **Limitation:** PatchTST is a
forecasting architecture adapted to detection; the adaptation must be documented, and its ESA-ADB
configuration may not transfer.

### A.4 Literature verification — an honest failure to report

You asked for a review of 2023–2026 anomaly-detection methods. **I could not complete it in this
session.** Crossref and OpenAlex both returned sustained HTTP 429 rate-limiting after the earlier
JIRS retrieval, across repeated attempts with backoff.

**I have therefore named no 2023–2026 method I could not verify.** The families above are grounded
in what the project has already implemented and in references verified in earlier phases
(`docs/research/FINAL_REFERENCE_VERIFICATION_MATRIX.md`): Ruszczak et al. 2025 (the OPS-SAT
benchmark itself, `10.1038/s41597-025-05035-3`), Herrmann et al. 2024
(`10.1007/s12567-023-00529-5`, the overestimation-correction genre), Hundman et al. 2018
(`10.1145/3219819.3219845`, the LSTM telemetry-AD precedent), and the Chronos family already
pinned in `requirements-ai.txt` as `chronos-forecasting==2.3.2`.

**Action required:** a verified 2023–2026 baseline-literature review remains outstanding and must
be completed before the related-work section is written. It is listed as task **L1** in §6. I will
not populate it from memory.

## B. Operational anomaly-detection evaluation

### B.1 What exists

Already recorded per arm, per protocol, per seed: accuracy, **precision**, **recall**, **F1**,
MCC, **false-alarm rate**, AUC-PR, AUC-ROC, Brier, ECE, train time, latency, throughput, params,
size. On ESA-ADB additionally the official event-wise metrics: EW-precision/recall/F0.5, alarming
precision, channel and subsystem F0.5, **ADTQC**, AFF-F0.5, alarm fraction, and **false alarms per
year**.

So of your eight requested metrics, **five are already present on OPS-SAT** (precision, recall, F1,
FPR, threshold-free AUC-PR/ROC) and **false-alarms-per-unit-time exists on ESA-ADB**.

### B.2 What is missing, and which of it is appropriate

| Metric | Status | Appropriate for OPS-SAT? |
|---|---|---|
| Precision, recall, F1 | ✓ present | **Yes** |
| False positive rate | ✓ present (`false_alarm_rate`) | **Yes** |
| **False alarms per unit time** | ✗ on OPS-SAT; ✓ on ESA-ADB | **Partially.** OPS-SAT is scored per *fragment*, not per continuous channel-hour, so "per year" requires a stated fragment-to-time mapping. Report as **false alarms per 1,000 fragments** instead, which needs no assumption, and give the time conversion only if the dataset documents fragment duration |
| **Detection delay** | ✗ | **NOT APPROPRIATE as currently framed.** Detection delay requires an anomaly *onset time* and a streaming decision. OPS-SAT fragments are classified as whole units — there is no within-fragment onset to be early or late about. Reporting a delay would require redefining the task. **I recommend against it** unless the task is reformulated to streaming, which is a different paper |
| **Missed anomaly rate** | ✓ implicitly (= 1 − recall) | **Yes** — report explicitly, it is the operationally legible form |
| **Threshold sensitivity** | ✗ | **Yes, and this is the most valuable addition.** All supervised arms decide at the fixed `P ≥ 0.5`. An operator would choose a threshold against a false-alarm budget. A precision-recall-versus-threshold sweep, and performance at matched false-alarm rates, is directly operational and **computable from saved scores with no refitting** |

### B.3 Operational context — what I will not invent

You said not to invent operational requirements or thresholds, and I will not. **I have found no
document in this repository or in the OPS-SAT dataset manifest that states an operator's
false-alarm budget, review capacity or cost ratio.**

Therefore: report performance **across a range of thresholds and at matched false-alarm rates**,
and let the reader locate their own operating point. Do **not** assert that any particular
threshold is operationally correct. The ESA-ADB track already demonstrates why this matters —
`cosmos_monitor` produces 14.7 false alarms/year against `patchtst`'s 0.29, a 51× difference that
AUC-PR alone does not surface.

## C. Cross-period and cross-satellite validation

### C.1 What the data supports — checked against the manifests

| Requirement | Supported? | Evidence |
|---|---|---|
| **Independent temporal evaluation periods** | **Yes** | Two protocols already exist: official (interleaved in time) and **time-blocked** (train before the 75th time percentile). This is the project's existing temporal control |
| **Different operational phases** | **Unclear — requires dataset inspection** | Not established from the manifest. OPS-SAT is a single CubeSat mission; whether fragments are labelled by operational phase is not recorded |
| **Different anomaly categories** | **Partially** | ESA-ADB distinguishes `anomaly` from `anomaly_and_rare` and reports channel- and subsystem-level metrics, so category structure exists **there**. For OPS-SAT, per-category labels are not established |
| **Satellite-independent testing** | **NO — and this is a hard limitation** | OPS-SAT is **one spacecraft**. ESA-ADB mission 1 is used. SMAP/MSL are two spacecraft but a different instrument domain and label convention. **No held-out-satellite experiment is possible within any single benchmark** |

### C.2 Is the time-blocked split sufficient?

**It is necessary and not sufficient.** It controls for temporal interleaving within one mission,
which is the defect it was built to address — and the hybrid's advantage survives it (AUC-PR 0.9719
vs 0.9191 for the foundation model), which is the result worth having.

What it does **not** establish: that the detector transfers to a different spacecraft, a different
instrument suite, or a different labelling convention. Those are different distribution shifts
from temporal displacement.

### C.3 Explicit limitation statement — to appear verbatim in the manuscript

> The anomaly-detection experiments use a single spacecraft (OPS-SAT) for the primary benchmark and
> a single mission from ESA-ADB. **We therefore make no claim of generalisation to unseen
> satellites.** Our temporal controls — an official split and a time-blocked split that trains only
> on fragments preceding the 75th time percentile — address temporal interleaving within a mission.
> They do not address cross-platform transfer. A cross-satellite experiment would require a
> benchmark with multiple spacecraft under a common labelling convention, which the datasets
> available to us do not provide. The one cross-corpus signal we do have is unfavourable: the
> project's own monitor attains EW-F0.5 0.202 on ESA-ADB, equal to a trivial out-of-limits rule and
> less than half of PatchTST's 0.496, which argues against assuming transfer.

**A cross-satellite claim is not available and will not be made.** The most that can be done with
existing data is a **cross-corpus** evaluation (train on OPS-SAT, test on SMAP/MSL or ESA-ADB),
which confounds satellite, instrument and labelling convention and would have to be reported as
such. That is experiment **E8** and remains optional.

## D. Efficiency evaluation

### D.1 What exists

| Your requirement | Status |
|---|---|
| Parameter count | ✓ `params` (hybrid 74,371; cnn 67,713; fcnn 13,249; transformer 71,297) |
| Checkpoint size | ✓ `size_mb` |
| Peak inference memory | ✓ `peak_memory_mb` |
| Throughput | ✓ `throughput_fragments_s` |
| Batch-1 latency | ⚠️ `latency_ms_per_fragment` recorded, but **batch size not documented** — `predict_deep` defaults to `bs=512`, so the figure is almost certainly amortised batch latency, **not** batch-1 |
| Batch-level latency | ⚠️ as above, implicit and undocumented |
| CPU inference | ✗ **not measured** — runs used `torch 2.14.0+xpu` (Intel GPU) |
| Accelerator inference | ✓ measured, on one device |
| Model-only vs end-to-end | ✗ **not separated** |
| Identical hardware for comparisons | ⚠️ presumed but **not recorded** |

### D.2 The defect worth fixing

**The single reported latency figure conflates batch-1 and batched inference, and no hardware,
thread count or batch size is recorded.** For an intelligent-systems venue where deployability is
part of the argument, this is the weakest part of an otherwise strong efficiency story.

A clean re-measurement is cheap — inference only, no retraining — and should report: batch-1
latency, batched latency at a stated batch size, CPU and accelerator separately, model-only versus
end-to-end (including feature construction), with device, thread count, batch size and warm-up
policy documented. This is experiment **E9**.

### D.3 What must not be claimed

**No energy-efficiency claim.** Power draw was never measured, and parameter count is not a proxy
for energy. **No real-time or deployment claim** — latency on one configuration does not establish
operation within a spacecraft's duty cycle.

## E. Scientific contribution of the late-fusion architecture

### E.1 Current evidence

| Comparison | Official protocol | Time-blocked | Significance |
|---|---|---|---|
| `hybrid` AUC-PR | 0.9855 | **0.9719** | — |
| vs `cnn` (CNN branch alone) | 0.9870 — **cnn is better** | 0.9712 — hybrid +0.0007 | **not tested; within noise** |
| vs `fcnn` (MLP branch alone) | 0.9800 | 0.9666 | +0.0059, CI [0.0004, 0.0127], p = 0.036 — **official only** |
| vs `xgboost` | 0.9607 | 0.9639 | +0.0254, CI [0.0078, 0.0460], p = 0.002 — **official only** |
| vs `chronos-bolt-small` | 0.9553 | 0.9191 | +0.0316, CI [0.0134, 0.0558], p < 0.001 — **official only** |

### E.2 Honest assessment: the fusion advantage over its own branches is NOT established

This is the finding you asked for, and it is unfavourable.

- **Against `cnn`, the hybrid's own convolutional branch, there is no advantage.** `cnn` is
  *better* on the official protocol (0.9870 vs 0.9855) and the hybrid's time-blocked margin is
  **+0.0007** — far inside noise, and untested.
- Against `fcnn`, the margin is +0.0059 with a CI whose lower bound is 0.0004 — statistically
  significant but **marginal**, and only on the official protocol.
- The hybrid's genuine advantages are elsewhere: **calibration** (ECE 0.035 vs `cnn`'s 0.121
  time-blocked — a 3.5× difference) and **stability across seeds** (F1 std 0.0066 vs `cnn`'s
  0.0977, a 15× difference).

**Therefore the architectural claim must be restated.** The defensible claim is **not** "late
fusion improves detection accuracy". It is:

> Late fusion of a raw-signal convolutional branch and a feature branch matches the best single
> branch on accuracy while delivering substantially better calibration (ECE 0.035 vs 0.121) and
> markedly lower seed-to-seed variance (F1 std 0.0066 vs 0.0977), at comparable parameter count and
> latency.

That is a **reliability** claim, not an accuracy claim — and it fits the paper's reframing far
better than an accuracy claim would. It also needs E1 to test it under the time-blocked protocol
and E6 to attribute it to the fusion rather than to one branch.

**Your instruction that the contribution must rest on evidence rather than integration alone is
exactly right, and on the current evidence an accuracy claim for the fusion would fail it.**

---

## 6. Prioritised plan — FOR YOUR APPROVAL

Nothing below has been started. Costs assume the available `torch` + `xgboost` backends.

### Tier 1 — no fitting, archives and saved scores only

| ID | Experiment | Answers | Cost | Freeze impact |
|---|---|---|---|---|
| **B1** | **Threshold sensitivity + matched-false-alarm-rate comparison** on OPS-SAT; add explicit missed-anomaly rate and false alarms per 1,000 fragments | §B — the operational evaluation, without inventing a threshold | **hours**, needs saved scores | none |
| **E5b** | Extend selection regret to the anomaly-detection task (validation→test regret per protocol) | Links §E to the paper's lead statistic | hours | none |

**Blocker for B1:** the OPS-SAT score archive `test_scores_official.npz` is **absent from disk**
(gap R4). B1 therefore depends on E1 persisting it, or on a scores-only re-run.

### Tier 2 — essential, requires fitting

| ID | Experiment | Answers | Cost | Priority |
|---|---|---|---|---|
| **E1** | Time-blocked paired significance tests, all arms; **persist the score archive** | The positive result's temporal validity; unblocks B1 | 2–6 GPU-h | **CRITICAL** |
| **E6** | Fusion-branch ablation: CNN-only, MLP-only, late fusion — on accuracy, **calibration and seed variance** | §E — whether fusion contributes anything, and what | 2–4 GPU-h | **CRITICAL** (§E cannot be claimed without it) |
| **E2** | Pre-registered temporal-displacement ladder | The lead contribution | 6–20 GPU-h | **CRITICAL** |

### Tier 3 — recommended

| ID | Experiment | Answers | Cost | Priority |
|---|---|---|---|---|
| **A2** | Reconstruction-based baseline, **both** fair variants (supervised residual head; unsupervised with validation-set threshold) | §A gap 1 | 2–4 GPU-h | MAJOR |
| **A3** | `patchtst` on the OPS-SAT protocol | §A gap 2 — a published satellite-specific comparator | 2–4 GPU-h | MAJOR |
| **E9** | Clean efficiency re-measurement: batch-1 vs batched, CPU vs accelerator, model-only vs end-to-end, full configuration recorded | §D | **1–2 h, inference only** | MAJOR |
| **L1** | **Verified 2023–2026 baseline-literature review** (retry when APIs permit) | §A.4 — currently outstanding | hours | MAJOR |
| **E7** | Missing-data robustness; connects to JIRS [J3] | Cross-cutting JIRS relevance | low–moderate | MAJOR |

### Tier 4 — optional

| ID | Experiment | Why optional |
|---|---|---|
| E8 | Cross-corpus transfer (OPS-SAT → SMAP/MSL or ESA-ADB) | Confounds satellite, instrument and labelling; the ESA-ADB result already suggests the answer. **Cannot support a cross-satellite claim** |
| E10 | Operational-phase / anomaly-category stratification | Requires confirming the labels exist first — a dataset inspection, not an experiment |

### Explicitly rejected

| Rejected | Reason |
|---|---|
| **Detection delay** | Not meaningful for whole-fragment classification; would require reformulating the task as streaming (§B.2) |
| **Cross-satellite generalisation experiment** | **Not possible** — one spacecraft per benchmark (§C.1) |
| **Energy-efficiency measurement** | No instrumentation; and no claim will be made (§D.3) |
| More unsupervised AD arms beyond A2 | Would reproduce the known information gap (`iforest` 0.33) without new insight |
| Architecture search on OPS-SAT | Metric-chasing; the arm set already includes a foundation model |

### Recommended immediate sequence

**E1 → B1 → E6**, then E2.

E1 both tests the positive result honestly and produces the score archive that B1 needs; B1 then
delivers the operational evaluation at near-zero marginal cost; E6 settles whether the
architectural contribution exists at all — and on current evidence **it probably does not exist as
an accuracy claim**, which you should know before the manuscript is reframed around it.

**Total Tier 1 + Tier 2: roughly 10–30 GPU-hours.** No frozen artifact is touched by any item.

**Awaiting your approval. Nothing in §6 has been started.**

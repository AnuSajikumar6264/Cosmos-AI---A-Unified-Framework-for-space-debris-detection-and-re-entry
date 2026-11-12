# COSMOS-AI claim/evidence matrix

Audit snapshot: HEAD `78ee339`, 2026-11-03. The status column describes the strength of the
available repository evidence, not publication readiness or independent replication.

| Claim | Evidence in repository | Audit status and boundary |
|---|---|---|
| Telemetry alarms have benchmark skill | ESA-ADB official-protocol results; OPSSAT-AD; SMAP/MSL comparisons and null baselines; evaluation code in `cosmos/ai/telemetry/` and `docs/RESULTS_AND_ANALYSIS.md`. | **Supported, qualified.** Mission behavior differs. Some rows are single-seed, the ESA-ADB calibration subset is small, and conformal exchangeability is not guaranteed under serial dependence/drift. No operational field validation. |
| SpotGEO detector performs on real benchmark imagery | SpotGEO benchmark records and scorer outputs under `outputs/benchmarks/vision_spotgeo/`. | **Supported on benchmark only.** Limited seeds and no independent observing dataset or broad condition-shift study. Synthetic imagery evidence is separate. |
| Lifetime model generalizes across time | Two forward-origin evaluations, family-based splits, saved test predictions, pinball/MAE/coverage/ranking metrics, and cluster bootstrap comparisons. | **Supported as a two-period benchmark.** Results differ by origin; interval coverage ranges below and above nominal and is not distribution-free under temporal shift. Test outcomes were scored more than once during development. |
| Reliability-gated physics/ML fusion is superior | Gate ablations and paired launch-family bootstrap in the results. | **Not supported as a general superiority claim.** It never beat the best single expert; effects vary by origin. Existing novelty documentation withdraws this superiority claim. |
| Family features improve lifetime estimates | C1 ablation at two origins. | **Partly supported.** Improvement is model- and period-dependent, not a universal effect. |
| Survival estimates forecast debris-cloud population | C2 compares predicted and observed catalog counts by qualifying breakup cloud; cloud bootstrap and calibrated/raw variants are reported. | **Supported as a tested coupling, with uncertainty.** Evaluation is limited to qualifying recorded clouds and cannot confidently rank all readings/experts. |
| Operational status improves re-entry decisions | C3 prospective policy comparison using an as-of status snapshot and follow-up outcomes, with launch-cluster intervals. | **Preliminary, not confirmatory.** One 72-day window, prior exposure, nonsignificant policy differences, and status is only a catalogue proxy for operational control. |
| Twin current-state predictions improve re-entry forecasts | T1 compares history-conditioned physics, class-prior physics and lifetime pipeline on one as-of window. | **Promising but exploratory.** Large calibration differences are measured, but this test window was previously used/seen during diagnosis and is not blind. Later-snapshot validation of the dated forecast remains pending. |
| Collision model estimates operational prioritization | CAC module predicts final-CDM log collision probability and calibrated high-risk probability. | **Narrow the claim.** It is benchmarked against anonymised CDMs; this is not evidence of linked-object manoeuvre prioritization or of health-informed physical collision probability. |
| Re-entry trajectory/impact/casualty chain is empirically accurate | Physics code and analytic/unit checks exist; historical ESA records are used for record linkage/context, not impact-state ground truth. | **Not established.** Simulator and analytic checks verify code properties, not real impact-location, casualty, or breakup accuracy. |
| COSMOS-AI is a fully integrated health-to-breakup-to-risk twin | Legacy pipeline runs a synthetic chain; newer twin connects catalogue and lifetime outputs. The datasets are unpaired. | **Unsupported as a validated end-to-end claim.** README wording should be narrowed to distinguish simulation from real-data studies. |
| All models/checkpoints are locally reproducible | Registry lists 20 cards; checkpoint fields are null for most. Three OPSSAT checkpoint entries point outside this workspace and do not resolve. No weight files were found under `outputs/` or `data/`. | **Not supported.** Results/experiment records may be reproducible without portable learned weights; disclose the distinction and resolve stale artifact references. |
| Manuscript is submission-ready | Checklist and venue/research-gap documentation. | **Not yet.** Author declarations, journal choice/template adaptation, data deposit/DOI, public release, later-snapshot forecast scoring, and reading identified closed-access papers remain author tasks. No acceptance claim is made. |

## Required interpretation

1. A successful unit test or run is software evidence, not scientific validation.
2. Benchmark validation is not independent external validation.
3. Historical results with test exposure must be labelled exploratory/post-hoc or otherwise
   disclosed; they must not be presented as untouched confirmation.
4. Coupling results are limited to the data linkage and evaluation actually available.
5. Claims about real re-entry footprints, casualty risk, or health-to-conjunction effects
   require ground truth and linked observations that the current datasets do not provide.

## Source documents

- [Results and analysis](../RESULTS_AND_ANALYSIS.md)
- [Final implementation report](../FINAL_IMPLEMENTATION_REPORT.md)
- [Research gap and novelty](../RESEARCH_GAP_AND_NOVELTY.md)
- [Dataset audit](../DATASET_AUDIT.md)
- [Submission checklist](../../paper/journal_v3_twin/SUBMISSION_CHECKLIST.md)

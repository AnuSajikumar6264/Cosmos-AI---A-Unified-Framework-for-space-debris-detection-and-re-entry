# COSMOS-AI demonstration script — thirteen stages, 15–20 minutes (rewritten 2026-11-08, Phase C)

Written for: the presenter. Every line in quotes is verifiable on the screen it accompanies; every number comes from a
stored artifact and is also asserted by `tests/test_e2e_demo_journey.py` and `tests/test_demo_workflow.py`. The guided
page `/demo` shows the same thirteen stages with live values; keep it open in a second tab. The earlier 10–15 minute
script is preserved in git history (commit `938d514` and before).

## Before the room (3 minutes, done in advance)

```bash
cd /data2/anupa/Final_Year_Project
python scripts/verify_protected_artifacts.py --label demo       # frozen evidence intact → all_protected_ok: True
python -m pytest tests/test_demo_workflow.py tests/test_e2e_demo_journey.py -q   # 29 tests, ≈ 15 s
python scripts/check_console_prerequisites.py && python scripts/serve_console.py
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8070/api/ready          # 200
```

Open <http://127.0.0.1:8070/demo>. If the first click on Twin State is slow (≈ 1.5 s) that is the archive being streamed
once; it is cached afterwards. A rehearsal in a fresh process takes about 10 s end to end
(`python scripts/rehearse_demo.py`).

## Stage 1 · Launch (0:00–1:00)
Show the terminal and `/api/ready`. > "The console checks its own artifacts: the forecast table is present, its recorded
digest verifies, a complete run exists, the re-emitted twin state is selected as the primary source. Readiness is about files
and digests. It says nothing about any spacecraft."

## Stage 2 · System overview (1:00–2:30)
Open `/`. Point at System readiness, then the STALE finding. > "Everything here refers to the snapshot dated 2026-10-27; the
console computes its age on every load and refuses to call it current. Nine modules ran in the latest run; abstentions are
counted, not hidden; the datasets strip states which evidence is keyed by NORAD and which is anonymised."

## Stage 3 · Satellite selection (2:30–3:30)
Open `/objects`, search `37607`. > "Search by NORAD id or name. We will use four objects: ARIANE 5 R/B as the primary case,
a Titan debris fragment whose lifetime record is non-coherent, the ISS as an operator-controlled payload, and VANGUARD R/B
at the prediction cap."

## Stage 4 · Orbital intelligence (3:30–5:30)
On `/objects/37607`: identity, elements, "Orbital lifetime assessment". > "Mean elements only — no state vector is
published. The lifetime interval is a conformal interval from the archived lifetime expert: 6.9 to 95.3 days, which crosses
the 30-day horizon. The subgroup cue says design-derived area-to-mass objects were under-covered at 80 % in the 2016
evaluation: 0.5625 observed. That is a subgroup frequency, not this object's probability."
Open `/objects/23806`. > "Here the saved per-horizon probabilities are not monotone, so the console abstains instead of
substituting a value. 123 records are in that state; limitation L17."

## Stage 5 · Re-entry prediction (5:30–7:30)
Back on 37607, "Re-entry assessment". > "p(30 d) = 1.0, quantiles at 10 days, before the horizon. The variants table shows
the physics prior, the history posterior and the lifetime comparison side by side; disagreement is shown, not averaged."
Open `/objects/25544`. > "Operator-controlled: drag physics does not determine re-entry, so the twin abstains and shows
the payload base rate with no interval." Open `/objects/12`. > "Quantiles censored at 1826.25 days: 'at least this long'."

## Stage 6 · Health and telemetry (7:30–9:30)
Open `/telemetry`, expand "Methodology". > "Three anonymised ESA-ADB missions. The pre-registered study found that the
alarm layer, not the scorer, determines event-wise F0.5: 0.074 for the AR(8) arm against 0.048, 0.030 and 0.024 for
PatchTST, TCN and Chronos on Mission 1." Open a channel. > "Real samples, ground-truth intervals, no model score per
sample. No mission can be joined to a NORAD id, so no catalogued object has telemetry and no health state is inferred."

## Stage 7 · Collision and conjunction (9:30–11:00)
Open `/risk`. > "2,167 held-out Kelvins events; quantile regression of log10 collision probability; the reliability gate's
weight is near zero — a negative result anchored to the public benchmark. Nothing here is an operational warning, and
priority is never derived from a physical probability: coupling C4 abstains."

## Stage 8 · Debris and optical imagery (11:00–12:30)
Open `/debris`, then sequence 1, frame 1. > "The detections drawn are the classical front end's — F1 0.084. The learned
U-Net scores about 0.75 in the benchmark table, but only its scores are archived, so the console does not show detections
it does not have. Pixel positions without calibration, confidence or time cannot be associated with any object."

## Stage 9 · Decision support (12:30–14:00)
On `/objects/37607`, "Decision priority". > "Rank 2 of 31,396. The formula is read from the run manifest, not
reimplemented: p(30 d) times 2 when the mass is at least 500 kg. Score 2.0. It is an operational ordering, not a probability
and not a risk estimate; it uses the point probability, not the interval; its effectiveness against outcomes has not been
evaluated."

## Stage 10 · Digital twin and provenance (14:00–16:00)
Open `/twin-state`. > "The re-emitted twin state is selected under the default policy, its digest verifies, 31,396 records
are valid, and all 31,396 are value-equivalent to the catalogue chain across 452,690 shared values. The fields that are not
compared are listed with their reasons: operator-controlled objects are represented as abstentions by the twin and as
predictions under an assumption by the chain — same numbers, different meaning — and we say so." Switch to
`?policy=archived_only`. > "An explicit archived read is amber, never green: those records carry no per-output provenance.
Model version is unavailable everywhere because no fitted model is persisted."

## Stage 11 · Scenario analysis (16:00–17:30)
Open `/scenario`, choose "Fast decision subset", run. > "The real pipeline runs in a separate process over saved artifacts
into a new directory. You see module statuses, the configuration digest and the list of assumptions that changed. No
historical run is modified and nothing is retrained."

## Stage 12 · Pipeline and research evidence (17:30–19:00)
Open `/runs`, the latest run, then compare it with `run_20261108T083402Z`. > "Every module carries code, configuration,
data-artifact and model-version lineage. The comparison reports byte-identical tables by digest and differences by key; it
never merges runs." Download the report for 37607. > "Redacted for export; hashes and the run id preserved."

## Stage 13 · Final summary (19:00–20:00)
Return to `/demo`, stage 13. > "Established: a pre-registered telemetry finding, a censoring-aware lifetime benchmark, a
twin whose integration premise was tested and not supported, and a versioned twin state verified against its archive and
the runtime chain. Outside the validated scope: live data, inference on demand, health verdicts, collision warnings for
named objects, debris-to-object association, and prospective validation, which is blocked until a later snapshot exists."

## Questions you should expect

**Is this live?** No. A dated snapshot and archived evaluations; every page says so.
**Why no telemetry for that object?** The datasets are anonymised; a link would be fabricated.
**Is the re-entry forecast validated?** On the non-blind T1 window only; the blind prospective test is blocked for want of a later snapshot.
**Does the health model feed collision risk?** No, by design; C4 abstains.
**The tests pass, so the science is validated?** The software behaves as tested; scientific validation is a separate claim the project keeps apart.

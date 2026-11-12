# Final research direction recommendation

Date 2026-11-05 · Part 2 conclusion

---

## Decision

### **B. Promising but requiring specified experiments**

**No track is scientifically defensible for manuscript development today.** Track 3 (ESA-ADB) is
the strongest on the weighted assessment (80 / 105 against 65 and 63) and remains **B**, not A,
because of three specific unresolved items — one of which is externally blocked.

---

## 1. Primary paper

**Track 3 — the pre-registered ESA-ADB alarm-selection study.**

**Working framing:**

> Selection and stability of the event-level alarm layer in spacecraft telemetry anomaly
> detection: a pre-registered comparison at full channel scale, with a refuted deep-learning
> hypothesis.

**Why this and not the others:**

- **Methodology is the contribution, and it is the project's best** (5/5): hash-frozen
  pre-registration with a refuse-to-run gate, official metric code verified byte-identical to
  upstream `67194d3`, official GlobalSTD reproduced to within 0.001 across 8 configurations, gated
  test scoring, 30-day block bootstrap hierarchical over seeds, Holm correction with a
  pre-declared minimum effect, and a separate deviation log.
- **It survives the significance check.** Removing statistical strength entirely from the scoring
  leaves Track 3 ahead by 11 points. Its margin comes from methodology, dataset quality and venue
  fit — not from H6's p-value.
- **A pre-registered negative deep-learning result is under-supplied** in this literature and is
  genuinely publishable.
- **Best venue fit** (5/5) for an applied-AI venue.
- **Highest-quality data**: expert-annotated ESA Anomalies Dataset v1.0, official splits, two
  usable missions.

**What the primary paper must claim — and must not:**

| Claim | Status |
|---|---|
| A1 outperforms A0 on M1 at full channel scale, +0.353 [+0.206, +0.488], Holm p = 0.0015 | **Claim**, as a comparison of two *whole protocols* |
| A supervised deep event scorer shows no benefit over AR(8) or trees (H4, H5 refuted) | **Claim**, with the ±0.1 seed-variance and no-tuning-budget caveats stated |
| Event aggregation succeeds where point-level adaptive calibration fails, for a mechanical reason | **Claim** — the one distinction the project's own novelty note judges survives against TC-CAD |
| Mission 2 is near-saturated; the composite metric there is ~98 % rare-event driven and every learned arm scores exactly 0.0000 on anomalies | **Claim** — this is a genuine contribution about the benchmark |
| Which protocol difference causes the gain | **Do not claim** until 3b. Five differences, no attribution |
| Competitive or state-of-the-art absolute performance | **Do not claim.** Blocked on Brancato |
| Generalisation of the selection effect across missions | **Do not claim.** Reverses; 1 of 8 cells confirmatory |
| Abstention / operator-budget deferral as a contribution | **Do not claim.** Pre-empted by TC-CAD and Heydari et al. |

## 2. Secondary papers — justified, and separate

### Secondary A — Track 2, as a benchmark-and-negative-results paper

**Justified as a separate paper, not merged.** Different dataset, different task, different
venue. Merging would dilute both and reproduce the integrated-framework error the project already
withdrew.

**Framing:** a catalogue-scale forward-in-time orbital-lifetime benchmark, and what it reveals
about model-selection validity.

**Strongest content:** the artifact (no competitor located — Shorten et al. verified not to
occupy it) and **selection regret of 3.4 % → 18.7 % → 25.2 % across origins, significant at
origin 2016** with a CI excluding zero and zero-regret in 0 of 4,000 resamples. That is the
project's only *significant* statement about selection failure, and it is operationally legible.

**Venue:** a space venue, not EAAI or JIRS — neither has a space ASJC category. Acta Astronautica
(Scopus 12372) or Advances in Space Research are the natural homes.

### Secondary B — Track 1, only if E6 supports it

**Conditional.** If the branch ablation shows the late fusion contributes to **calibration**
(ECE 0.035 vs 0.121) and **seed stability** (F1 SD 0.0066 vs 0.0977) rather than accuracy, there
is a short applied paper. If E6 shows the fusion contributes nothing, **Track 1 should not be
published separately** — it would reduce to "a tuned CNN does well on 529 fragments", and `cnn`
already beats the fusion on the official protocol.

**Do not write Track 1 before E6.**

### Explicitly not a paper

**The integrated digital twin.** Refuted by the project's own experiments (C1 not reproducible
under the same-learner test; C2's deployed arm p = 0.364; C3 inconclusive; C4 zero joinable
pairs), decision support unvalidated, twin forecast unscored. The project already withdrew this
and marked two manuscript tracks superseded for asserting it. That decision was correct and
should stand.

## 3. Minimum experiments before manuscript development

**For the primary paper, in order:**

| # | Experiment | Why minimum | Cost | Blocked? |
|---|---|---|---|---|
| **3a** | **Report anomaly-only metric alongside the composite throughout** | Removes a systematic misreading; converts the M2 "reversal" into a characterised metric artifact | **zero — already in `results.csv`** | no |
| **3b** | **Fractional factorial decomposition of H6** (residual scale σ × calibration pool × selection data, 8 cells) | **Without it H6 attributes nothing.** The existing post-hoc work is one-factor-at-a-time and cannot separate interactions | moderate | no |
| **3c** | **Reconcile Brancato et al.** — their channel set, hierarchy level, metric variant, event-matching rule, out-of-limit definition | **The single largest rejection risk.** Their *parameter-free* reference scores 0.754 where COSMOS-AI's scores 0.0007 | — | **BLOCKED: paywalled** |
| 3d | Equal tuning budgets; ≥ 2 deep architectures | Closes the comparator-fairness objection the project itself records | moderate | no |

**3a and 3b are the minimum. 3c is required for any performance claim and cannot be done from
here.**

**Free work worth doing for Secondary A at the same time:** a trivial reference predictor
(marginal quantiles, constant-at-cap) from archives; per-arm bootstrap intervals on the main
leaderboard; the `am_design` Stage-1 subgroup coverage analysis; and citing Candès et al. 2023,
Gui et al. 2024 and Shorten et al. 2023.

## 4. Answers to your seven questions

**1. Which track has the strongest current evidence?**
**Track 3**, on methodology (5/5), dataset quality (5/5) and statistics (5/5). But its strongest
*claim* — H6 — attributes nothing because five protocol differences move together, and its
absolute performance is blocked.

**2. Which track best fits JIRS?**
**Track 1**, and only weakly. Anomaly/fault is **1.8 %** of JIRS's 282 records since 2023; space
is 2.1 %; **56.4 % is explicitly robotics**; JIRS has **no space ASJC category**. The honest
answer is that **no track fits JIRS well**, and Track 3 — the strongest — fits **EAAI**, which the
project's own prior venue analysis independently ranked first of eleven with JIRS absent entirely.

**3. The five largest rejection risks.**

| # | Risk | Severity | Evidence | Required action | Verification criterion |
|---|---|---|---|---|---|
| 1 | **Brancato et al. report 0.902 on M1 full channels where COSMOS-AI's best is ~0.09–0.20, and their parameter-free reference scores 0.754 vs 0.0007** | **Critical** | `NOVELTY_NOTE.md`; `results.csv` m1_target | Obtain the full text; reconcile protocol, channel set, hierarchy level, metric variant | Either the difference is attributed to a named protocol element, or no performance claim is made |
| 2 | **H6 is confounded five ways, so it attributes nothing** | **Critical** | `STAGE1_AUDIT.md` §5.1 — the project's own audit found the fifth | Fractional factorial decomposition (3b) | A named factor carries the effect with a CI, or the claim stays a protocol comparison |
| 3 | **The selection effect reverses on M2 and the lightweight subset; 1 of 8 cells is confirmatory** | **Major** | H6 M2: −0.089 [−0.143, −0.049] | Report anomaly-only metric (3a); state M2 is near-saturated | Reviewer accepts M2 cannot test generalisation (6 anomalies; all learned arms 0.0000 on anomalies) |
| 4 | **Test halves were scored in 128 configuration–layer combinations before the pre-registration was designed** | **Major** | `STAGE1_AUDIT.md` §6 risk 2; the project states the pre-registration "was motivated by a test result" | Disclose prominently; do not describe H6 as fully confirmatory | The limitation appears in the abstract or early methods, not buried |
| 5 | **Comparator fairness: ACI's γ tuned to a point rate not the event objective; neither supervised scorer had a tuning budget; one deep architecture** | **Major** | `STAGE1_AUDIT.md` §6 risk 4 | Equal budgets, ≥ 2 architectures (3d), or state the asymmetry as a bound | Either budgets are equalised or every affected claim is stated as a lower bound |

**4. Minimum work to address them.**
3a (free) + 3b (moderate) + 3d (moderate), plus prominent disclosure of risks 3 and 4. Risk 1 is
**blocked** and requires a paywalled full text — which is yours to obtain. Without it, the paper
must simply make no comparative-performance claim; that is survivable but it must be deliberate.

**5. Which claims should be removed or weakened.**
Full list in `PART2_SCIENTIFIC_NOVELTY_COMPARISON.md` §5. The nine that matter most: the
late-fusion accuracy claim; any distribution-free coverage guarantee; competitive ESA-ADB
performance; cross-mission generalisation; abstention/budgets as a contribution; "physics-informed"
of the OPS-SAT hybrid; novel conformal/censored-survival methodology; H2 and H6 as mechanism
confirmations; and all digital-twin, decision-support and cross-domain-fusion claims.

**6. What can be published independently without misrepresenting COSMOS-AI.**

| Paper | Independence |
|---|---|
| **Primary: ESA-ADB alarm selection** | Fully independent. One dataset, one protocol, no reliance on other modules |
| **Secondary A: lifetime benchmark + selection regret** | Fully independent. Different data, task and venue |
| **Secondary B: OPS-SAT detector** | Independent, **conditional on E6** |
| **Not publishable:** integrated twin, decision support, cross-domain fusion, debris detection, re-entry footprint validation | Each is refuted, unvalidated, or validated only on self-generated data |

Publishing the three separately is **more** honest than one integrated paper: it reports what each
study established on its own terms, and avoids implying a validated chain the evidence refutes.

**7. Title and central research question.**

**Primary paper title:**

> **Selection and stability of the event-level alarm layer in spacecraft telemetry anomaly
> detection: a pre-registered study on ESA-ADB at full channel scale**

**Central research question:**

> Under the official ESA-ADB protocol at full channel scale, does the data used to select an
> event-level alarm layer matter more to detection performance than the capacity of the anomaly
> scorer feeding it — and under what conditions does that effect hold?

This question is answerable with evidence the project already owns, it foregrounds the
pre-registered negative result rather than hiding it, the "under what conditions" clause builds
the M2 reversal and the lightweight-subset reversal into the question instead of treating them as
awkward limitations, and it makes **no** absolute-performance claim, so it is not hostage to the
Brancato blocker.

## 5. What I am not recommending, and why

- **Not a combined COSMOS-AI framework paper.** The integration premise is refuted by the
  project's own experiments. Two manuscript tracks were already superseded for asserting it.
- **Not JIRS for the primary paper**, on the evidence in §4.2 — though the venue is your decision
  and I have assessed against it rather than relitigating it.
- **Not writing any manuscript yet.** Per your instruction, and because 3b will change what the
  primary paper can claim.
- **Not running any experiment.** All protocols in these documents await your approval.

## 6. Recommended next action

**Approve 3a** (free: report the anomaly-only metric alongside the composite throughout) **and the
free Secondary-A items** (trivial baseline, leaderboard intervals, `am_design` Stage-1 subgroup
coverage). These cost no compute, touch no frozen artifact, and sharpen both candidate papers
immediately.

**Then decide on 3b**, the fractional factorial decomposition of H6 — the one experiment that
determines whether the primary paper can say *why* its headline effect occurs, or only *that* it
occurs.

**Separately, and in parallel:** obtain Brancato et al.'s full text. It is the only route to
risk 1, and it is outside what I can do from here.

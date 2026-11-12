# EAAI vs JIRS — venue comparison

Date 2026-11-05 · Scopus records verified from Elsevier's official source title list
(`ext_list_Sep_2026.xlsx`)

**Conclusion: on scope evidence, EAAI fits the project's strongest contribution and JIRS does not.
Neither journal's CiteScore rank could be officially verified, and both would meet your top-100
requirement by the same route if at all.**

---

## 1. Officially verified Scopus records

| Field | **EAAI** | **JIRS** |
|---|---|---|
| Official Scopus source title | Engineering Applications of Artificial Intelligence | Journal of Intelligent and Robotic Systems: Theory and Applications |
| **Scopus Source ID** | **24182** | **24360** |
| ISSN | 0952-1976 | 0921-0296 |
| eISSN | — (not listed) | 1573-0409 |
| Status | **Active** | **Active** |
| Coverage | **1988–2026** | **1988–2026** |
| Publisher | Elsevier Ltd | Springer Nature |
| Source type | Journal | Journal |
| Open access flag | not flagged | not flagged |
| **ASJC categories** | **1702** Artificial Intelligence; **2207** Control and Systems Engineering; **2208** Electrical and Electronic Engineering | **1702** AI; **2207** Control and Systems Eng.; **2208** Electrical and Electronic Eng.; **2210** Mechanical Eng.; **2209** Industrial and Manufacturing Eng.; **1712** Software |

**They share three categories exactly.** JIRS adds Mechanical, Industrial/Manufacturing and
Software. **Neither has a space, aerospace, astrodynamics or planetary category.**

## 2. Your top-100 requirement — identical route, same uncertainty

Active-journal counts per category, computed from the same official list:

| ASJC | Category | Active journals | Top-100 = | In EAAI? | In JIRS? |
|---|---|---|---|---|---|
| **2207** | **Control and Systems Engineering** | **306** | top 32.7 % | ✓ | ✓ |
| 1712 | Software | 380 | top 26.3 % | ✗ | ✓ |
| 1702 | Artificial Intelligence | 523 | top 19.1 % | ✓ | ✓ |
| 2209 | Industrial and Manufacturing Eng. | 361 | top 27.7 % | ✗ | ✓ |
| 2210 | Mechanical Engineering | 663 | top 15.1 % | ✗ | ✓ |
| 2208 | Electrical and Electronic Eng. | 820 | top 12.2 % | ✓ | ✓ |

**For both journals the easiest route to your requirement is Control and Systems Engineering —
top 100 of 306.** The requirement therefore does **not** discriminate between them, and it is a
genuine bar for both (unlike Space and Planetary Science, which has only 96 active journals and
where top-100 is automatic).

**Both journals' CiteScore, rank, percentile and quartile are UNVERIFIED.** `scopus.com/sources`
and `scopus.com/sourceid/...` both return HTTP 307 to Elsevier SSO; the public source list carries
indexing status, coverage, ASJC codes, publisher and OA flag but **no citation metrics**. Per your
instruction I have not substituted a third-party ranking as proof.

## 3. Scope evidence — this is where they differ, and the evidence is asymmetric

### 3.1 JIRS — measured

I retrieved **the complete set of JIRS records published from 2023 onward** via the Crossref
journal endpoint (Crossref reported `total-results = 282`; all 282 retrieved) and classified by
title keyword:

| Theme | Records | Share |
|---|---|---|
| **Explicit robotics** (robot, manipulator, grasp, UAV, drone, quadrotor, SLAM, legged, gripper, swarm, locomotion) | **159** | **56.4 %** |
| Learning / neural / deep / reinforcement | 38 | 13.5 % |
| Decision, planning, scheduling, assurance | 32 | 11.3 % |
| Uncertainty / calibration / probabilistic / Bayesian | 14 | 5.0 % |
| **Space / satellite / orbit / spacecraft / aerospace** | **6** | **2.1 %** |
| **Anomaly / fault / diagnosis / prognostics / health / monitoring** | **5** | **1.8 %** |
| Distribution shift / domain adaptation / robustness | 5 | 1.8 % |

OpenAlex's topic model for JIRS (non-Scopus, corroborative) lists: Robotic Path Planning; Robotic
Mechanisms and Dynamics; Control and Dynamics of Mobile Robots; Robotics and Sensor-Based
Localization; Adaptive Control of Nonlinear Systems; Aerospace Engineering and Control Systems;
Robot Manipulation and Learning; Reinforcement Learning in Robotics.

**A terminology trap, verified.** My keyword sweep returned a dozen JIRS papers containing
"calibration" — **all kinematic or geometric**: *Position-Based Robot Calibration*, *Hybrid
Calibration of Industrial Robot Considering Payload Variation*, *Hand-Eye Calibration Using
Quaternions*, *Robust Extrinsic Self-Calibration of Camera and Solid State LiDAR*. In JIRS,
"calibration" means aligning a sensor or kinematic chain, not calibrating a predictive
probability. "Uncertainty" likewise predominantly means bounded disturbance in a control law
(*Adaptive Control … with Uncertainties*; *Distributed Leaderless Consensus Control for Uncertain
Multiagent Systems*). A JIRS reviewer will not bring the standard reading of either word to a
conformal-coverage argument.

### 3.2 EAAI — NOT measured, and I will not estimate it

I attempted the same bulk Crossref retrieval for EAAI (ISSN 0952-1976) and was **rate-limited
(HTTP 429)** after the JIRS and Shorten retrievals, across repeated attempts with backoff.
**EAAI's topical distribution is therefore unmeasured in this session.** I am recording that
asymmetry rather than filling it with a plausible-sounding figure.

What *is* verified about EAAI's scope:

- Its ASJC set is **exactly** Artificial Intelligence + Control and Systems Engineering +
  Electrical and Electronic Engineering — i.e. **applied AI in engineering, with no mechanical,
  manufacturing or robotics category.** JIRS's additional three categories are the robotics-
  adjacent ones.
- Its title is a scope statement: *applications* of AI to *engineering*.
- The project's own prior analysis (`research_design/VENUES.md`, written 2026-10-24) assessed it
  as **"best fit: an applied deep-learning method with rigorous evaluation on real industrial or
  space data"** and ranked it first of eleven candidates. **JIRS does not appear anywhere on that
  list.**

### 3.3 Non-Scopus citation context — labelled, not evidence

From the project's OpenAlex pull of 2026-10-24 (`references/openalex_venues_2026-10-24.json`) and
my own OpenAlex query. **These are not Scopus metrics and must not be cited as CiteScore or
quartile.**

| Journal | OpenAlex 2-yr mean citedness | h-index | APC (unconfirmed) |
|---|---|---|---|
| EAAI | **7.87** | 187 | US$3,200 (subscription route free) |
| JIRS | **5.41** | 120 | US$3,090 |

## 4. Fit against the project's strongest contribution

The strongest contribution, on current evidence, is the **pre-registered ESA-ADB event-level alarm
selection study** — an applied-AI empirical study on real spacecraft telemetry with a frozen
protocol, official metric code, strong classical and tree baselines, block bootstrap and Holm
correction, and a negative deep-learning result.

| Requirement of that paper | EAAI | JIRS |
|---|---|---|
| Applied AI/ML method on real engineering data | **Core scope** | Peripheral (13.5 % learning-themed, mostly in robotics) |
| Anomaly detection / fault diagnosis / condition monitoring | **Core scope** | **1.8 % of output** |
| Rigorous statistical evaluation protocol as a contribution | Expected | Less typical |
| Negative / refuted deep-learning hypotheses | Publishable as applied-AI evaluation | Harder: no established negative-results precedent found in 282 records |
| Spacecraft telemetry domain | Accepted as an application domain | **2.1 % of output; no space ASJC category** |
| A robot, controller or autonomy loop | Not required | **56.4 % of output has one; this paper has none** |
| Conformal / predictive-uncertainty vocabulary | Standard | **Means something else to this readership (§3.1)** |

**Assessment:** EAAI's scope contains this paper; JIRS's does not. The project has **no robot, no
actuator, no control loop and no autonomous agent**, and its one JIRS-shaped component — the
decision-support layer — has **no outcome-scored evaluation of any kind**, so it cannot be
claimed.

## 5. Candidate JIRS bridges, and why they are insufficient

Two JIRS papers are genuinely relevant and were verified via Crossref:

- **Hawkins, Picardi, Donnell & Ireland (2023)**, *Creating a Safety Assurance Case for a Machine
  Learned Satellite-Based Wildfire Detection and Alert System*, JIRS vol. 108,
  `10.1007/s10846-023-01905-3`, 12 citations. ML assurance in a satellite system — the closest
  bridge, and a real one.
- **Spahic, Hepsø & Lundteigen (2023)**, *A Novel Warning Identification Framework for
  Risk-Informed Anomaly Detection*, JIRS vol. 108, `10.1007/s10846-023-01887-2`. Risk-informed
  anomaly detection for autonomous cyber-physical systems.

These establish that JIRS *can* publish ML-assurance and risk-informed-anomaly work. **But two
papers out of 282 is not a scope; it is an exception**, and neither matches the project's actual
deliverable — a benchmark-protocol comparison with a negative deep-learning result.

## 6. Recommendation

**Primary: Engineering Applications of Artificial Intelligence** (Scopus ID 24182). Scope contains
the contribution; the project's own prior analysis independently reached the same conclusion;
top-100 route identical to JIRS's.

**Alternatives, both with an aerospace category JIRS lacks:**

| Journal | Scopus ID | ASJC | Note |
|---|---|---|---|
| **Aerospace Science and Technology** | **12507** | **2202** Aerospace Eng. only (152 active journals → top-100 = top 66 %) | **Published Brancato et al. (2026) on ESA-ADB.** Topic fits precisely — but **that group may review the paper, and the unexplained 0.902 vs ~0.09 discrepancy would be examined first.** High risk, high relevance |
| **Acta Astronautica** | **12372** | 2202 Aerospace Eng. only | Space-operations audience; ML for spacecraft operations appears regularly |

**On JIRS specifically.** You have fixed it as the target, and that is your call. My assessment,
on the evidence above, is that submitting the project's strongest contribution there carries a
**high risk of desk rejection on scope** — 1.8 % of its output is anomaly/fault work, 2.1 % is
space, it has no space ASJC category, and 56.4 % of what it publishes contains a robot. I would
not describe that risk as avoidable by rewriting, because the mismatch is in what the paper *is*,
not how it is framed.

If JIRS remains fixed, the only honest route is to lead with the **ML-assurance** framing that
Hawkins et al. establishes — evidence required before a machine-learned component can be trusted
in a spacecraft system — and to accept that the paper will sit in the journal's minority.

## 7. What remains unverified

| Item | Status |
|---|---|
| EAAI and JIRS CiteScore, rank, percentile, quartile | **UNVERIFIED** — Scopus Sources is subscription-gated |
| Whether either is Q1 under *any* named system | **UNVERIFIED.** Scopus CiteScore quartile, Scopus absolute rank, SJR quartile and JIF quartile are four different claims and must not be conflated |
| **EAAI's 2023+ topical distribution** | **NOT MEASURED** — Crossref rate-limited. JIRS's *is* measured; the asymmetry is disclosed |
| Both journals' aims-and-scope pages, author instructions, article types, length limits, data/code policies, **AI-use disclosure requirements** | **NOT RETRIEVED** — ScienceDirect returned 403, SpringerLink redirected to SSO. **You must read both yourself**, particularly the AI-disclosure policy |
| APC amounts | OpenAlex-reported, **not** publisher-confirmed |

**How to verify the rank officially:** sign in at `scopus.com/sources`, search source ID **24182**
(EAAI) and **24360** (JIRS), and read CiteScore, CiteScore year, rank ("#X of Y"), percentile and
quartile for **2207 Control and Systems Engineering** first — the category where your top-100
requirement is most attainable for both.

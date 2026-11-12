# JIRS scope and recent publications (Phase 2)

Date 2026-11-04 · evidence retrieved live from Crossref and Elsevier's official Scopus source list

**Journal**: Journal of Intelligent & Robotic Systems: Theory and Applications
**Publisher**: Springer Nature · **ISSN** 0921-0296 · **eISSN** 1573-0409

---

## 1. What JIRS actually publishes — measured, not inferred

You asked me to prioritise the journal's own output. I retrieved **the complete set of JIRS
records published from 2023 onward via the Crossref journal endpoint**: Crossref reports
`total-results = 282`, and I retrieved all 282.

Classifying by title keyword:

| Theme | Records | Share of 282 |
|---|---|---|
| **Explicit robotics** (robot, manipulator, grasp, UAV, drone, quadrotor, SLAM, legged, gripper, swarm, locomotion…) | **159** | **56.4 %** |
| Learning / neural / deep / reinforcement | 38 | 13.5 % |
| Decision, planning, scheduling, assurance | 32 | 11.3 % |
| Uncertainty / calibration / probabilistic / Bayesian | 14 | 5.0 % |
| **Space / satellite / orbit / spacecraft / aerospace / debris / re-entry** | **6** | **2.1 %** |
| Anomaly / fault / diagnosis / prognostics / health / monitoring | **5** | **1.8 %** |
| Distribution shift / domain adaptation / robustness / generalisation | **5** | **1.8 %** |

OpenAlex's own topic model for the journal (non-Scopus, for corroboration) lists its leading
topics as: *Robotic Path Planning Algorithms; Robotic Mechanisms and Dynamics; Control and
Dynamics of Mobile Robots; Robotics and Sensor-Based Localization; Adaptive Control of Nonlinear
Systems; Aerospace Engineering and Control Systems; Robot Manipulation and Learning;
Reinforcement Learning in Robotics.*

**Reading.** JIRS is a robotics and intelligent-control journal. Over three-plus years it
published roughly **six** space-related papers and **five** anomaly/fault papers out of 282. The
COSMOS-AI topic occupies about **2 %** of its output.

### 1.1 A terminology trap worth knowing

My first keyword sweep returned a dozen JIRS papers containing "calibration" — all of them
**kinematic or geometric** calibration: *Position-Based Robot Calibration*, *Hybrid Calibration of
Industrial Robot Considering Payload Variation*, *Hand-Eye Calibration Using Quaternions*,
*Robust Extrinsic Self-Calibration of Camera and Solid State LiDAR*, *In-Flight Calibration* of a
phased-array navigation system.

**In JIRS, "calibration" means aligning a sensor or a kinematic chain, not calibrating a
predictive probability.** Likewise "uncertainty" in JIRS predominantly means bounded disturbance
in a control law (*Adaptive Control … with Uncertainties*, *Distributed Leaderless Consensus
Control for Uncertain Multiagent Systems*), not epistemic uncertainty in a forecast. A JIRS
reviewer encountering our conformal-coverage material will not have the standard reading of these
words. The manuscript must define them explicitly.

## 2. Genuinely relevant JIRS publications, 2023–2026

You asked for at least ten "if available". **They are not available.** After classifying all 282
records I find **five genuinely relevant papers and two of marginal relevance.** Forcing the count
to ten would mean including robot-calibration and consensus-control papers that bear no relation
to this work, which you explicitly prohibited.

All metadata below is Crossref-verified (DOI, exact title, author list, year, article type,
volume). Abstracts were retrieved where Crossref supplies them; Springer pages returned SSO
redirects, so for three records the abstract is marked not retrieved rather than guessed.

### [J1] Creating a Safety Assurance Case for a Machine Learned Satellite-Based Wildfire Detection and Alert System — **most relevant**

- **Authors** Richard Hawkins, Chiara Picardi, Lucy Donnell, Murray Ireland
- **2023** · *Journal of Intelligent & Robotic Systems* vol. 108 · `10.1007/s10846-023-01905-3`
- **Type** journal-article · **12 citations** · verified: Crossref, abstract retrieved
- **Problem** Establishing justified confidence that a machine-learned component deployed on
  satellites will behave acceptably in operation.
- **Method** A structured safety-assurance case for ML components, applied to a CubeSat
  constellation performing on-board wildfire detection; argues from evidence about the ML
  component to a system-level assurance claim.
- **Data** Satellite imagery for wildfire detection (CubeSat/constellation setting).
- **Design** Assurance-case construction and argumentation rather than a benchmark comparison.
- **Results** A worked assurance case showing what evidence an ML satellite component must supply.
- **Contribution** Methodology for arguing the trustworthiness of ML in a space system.
- **Limitations** Not a quantitative benchmark; single application; no competing-method comparison.
- **Relevance to COSMOS-AI** **High and directly exploitable.** This is JIRS's own precedent for
  *ML reliability in a satellite system*. Our reproducibility audit, pre-registration machinery,
  abstention semantics and selection-transfer diagnostic are precisely the *evidence* an assurance
  case of this kind requires. **This paper is the single best bridge between COSMOS-AI and JIRS**,
  and it should anchor the reframing: not "a benchmark paper", but "what evidence is needed before
  an ML component can be trusted in a satellite system, and what happens when you measure it".

### [J2] A Novel Warning Identification Framework for Risk-Informed Anomaly Detection

- **Authors** Rialda Spahic, Vidar Hepsø, Mary Ann Lundteigen
- **2023** · *JIRS* vol. 108 · `10.1007/s10846-023-01887-2`
- **Type** journal-article · **3 citations** · verified: Crossref, abstract retrieved
- **Problem** Autonomous cyber-physical systems in hazardous industrial settings (oil and gas,
  mining) need anomaly detection, but data characterising genuinely hazardous occurrences is
  absent, so detections cannot be risk-ranked.
- **Method** A warning-identification framework that makes anomaly detection *risk-informed* —
  coupling detection output to risk reasoning rather than reporting raw anomaly scores.
- **Data** Industrial cyber-physical monitoring data.
- **Design** Framework proposal with demonstration.
- **Contribution** Converts anomaly scores into risk-informed warnings under data scarcity.
- **Limitations** Not a quantitative benchmark against competing detectors; domain-specific.
- **Relevance** **High.** It is the JIRS-native version of what our decision layer attempts: turn
  module outputs into prioritised operator warnings under incomplete evidence. It also shows JIRS
  accepts *framework* contributions in this space — but note that our decision layer has **no**
  validation (audit §1.6), so we cannot currently claim what [J2] claims.

### [J3] A Semi-Supervised Federated Learning Fault Diagnosis Method Based on Adaptive Class Prototype Points for Data Suffered by High Missing Rate

- **Authors** Funa Zhou, Wei Xu, Chaoge Wang, Xiong Hu
- **2023** · *JIRS* · `10.1007/s10846-023-02025-8`
- **Type** journal-article · verified: Crossref metadata (abstract not supplied by Crossref)
- **Problem** Fault diagnosis when labels are scarce and data are heavily incomplete.
- **Method** Semi-supervised federated learning with adaptive class-prototype points.
- **Relevance** **Moderate–high.** Establishes that JIRS publishes *fault diagnosis under
  incomplete evidence* — adjacent to our abstention-under-missing-evidence design and to our
  label-efficiency sweep (train fractions 0.10–1.00 on OPS-SAT). A methodological comparator for
  how JIRS papers in this area are structured.

### [J4] Context Adaptive Fault Tolerant Multi-sensor Fusion: Towards a Fail-Safe Multi Operational Objective Vehicle Localization

- **Authors** Nesrine Harbaoui, Khoder Makkawi, Nourdine Ait-Tmazirte, Maan El Badaoui El Najjar
- **2024** · *JIRS* · `10.1007/s10846-023-01906-2`
- **Type** journal-article · verified: Crossref metadata
- **Problem** Fusing multiple sensors safely when individual sources may fail or degrade.
- **Method** Context-adaptive fault-tolerant fusion with explicit fail-safe objectives.
- **Relevance** **Moderate–high.** This is JIRS's own treatment of **evidence-aware fusion with
  degradation handling** — conceptually the closest published analogue to COSMOS-AI's coupling and
  abstention architecture. Importantly, it is also the comparator against which our **negative**
  integration result should be positioned: they demonstrate benefit from fault-tolerant fusion;
  we measured none from cross-domain fusion and must say so.

### [J5] Strategic Conflict Management using Recurrent Multi-agent Reinforcement Learning for Urban Air Mobility Operations Considering Uncertainties

- **Authors** Cheng Huang, Ivan Petrunin, Antonios Tsourdos
- **2023** · *JIRS* · `10.1007/s10846-022-01784-0`
- **Type** journal-article · verified: Crossref metadata
- **Problem** Conflict (collision) management for urban air mobility under uncertainty.
- **Method** Recurrent multi-agent reinforcement learning with uncertainty treatment.
- **Relevance** **Moderate.** The closest JIRS analogue to our conjunction/collision-risk module,
  in a different airspace. Relevant because our collision module's honest result is that a trivial
  baseline beats every learned arm (F2 0.739 vs 0.168) — a direct, publishable counterpoint to the
  learned-conflict-management literature this paper represents.

### Marginal relevance (recorded for completeness, not used as positioning)

| Ref | Record | Why marginal |
|---|---|---|
| [J6] | *UV Mission Planning Under Uncertainty in Vehicles' Availability*, Chirala, Venkatachalam & Smereka, 2023, `10.1007/s10846-023-01860-z` | Decision-making under uncertainty, but an optimisation/planning formulation unrelated to predictive-model reliability |
| [J7] | *Robust LQR-Based Architecture for Faulty Networked Control Systems*, Benevides, Inoue & Terra, 2023, `10.1007/s10846-023-02017-8` | Fault tolerance in a control-theoretic sense; no learned predictive component |

## 3. Honest assessment of scope fit

### 3.1 Verified from the official Scopus record

JIRS, Scopus source record **24360**, Active, coverage 1988–2026, Springer Nature. ASJC
categories: **2210** Mechanical Engineering, **2209** Industrial and Manufacturing Engineering,
**2207** Control and Systems Engineering, **1712** Software, **1702** Artificial Intelligence,
**2208** Electrical and Electronic Engineering.

**There is no space, aerospace, astrodynamics, planetary or earth-science category.** The nearest
is Control and Systems Engineering.

### 3.2 What this means for the submission

The manuscript as currently drafted — a catalogue-scale orbital-lifetime benchmark reporting
selection instability and a reproducibility failure — matches **none** of JIRS's six categories
and sits in the ~2 % tail of its subject output. Submitted unchanged, the most likely outcome is
desk rejection on scope, before any reviewer assesses the science.

**However, the project contains material that genuinely fits.** [J1] and [J2] establish that JIRS
publishes (a) assurance of machine-learned components in satellite systems and (b) risk-informed
anomaly detection for autonomous systems. COSMOS-AI owns:

- a **positive, significance-tested anomaly-detection result** on an official spacecraft-telemetry
  benchmark that beats a time-series foundation model, with calibration and compute metrics
  (audit §1.1) — the kind of result [J2]/[J3] readers expect;
- a **cross-task measurement of when validation-based model selection can be trusted**
  (ρ = +1.000 → +0.800 → 0.000 as temporal displacement increases; audit §1.2) — which is exactly
  the sort of *evidence about ML trustworthiness* that [J1]'s assurance-case argument needs and
  currently lacks;
- a **negative result on learned collision-risk assessment** that speaks directly to [J5];
- a **negative result on cross-domain fusion** that speaks directly to [J4].

That is a coherent intelligent-systems paper about **the reliability of machine-learned components
in spacecraft operations**, with both positive and negative evidence. It is not the paper currently
drafted.

### 3.3 What would still be missing

Even reframed, two JIRS expectations are unmet and cannot be met by rewriting:

1. **No robotics or autonomy loop.** 56 % of JIRS is robotics; our system has no actuator, no
   control loop and no autonomous agent. The paper will always be in the journal's minority.
2. **The decision-support layer is unvalidated** (audit §1.6). The component JIRS cares about most
   has no outcome-scored evaluation. [J2] validated its framework; we have not validated ours.

Both are addressed in `JIRS_Q1_EXPERIMENTAL_GAP_ANALYSIS.md` and the experiments plan.

## 4. Retrieval limitations, stated

| Item | Status |
|---|---|
| Complete 2023+ JIRS record set (282) | ✅ retrieved from Crossref journal endpoint |
| DOI, title, authors, year, type, volume for all cited records | ✅ Crossref-verified |
| Abstracts | ⚠️ retrieved for [J1], [J2]; Crossref supplies none for [J3]–[J7]; `link.springer.com` returned an SSO redirect, so these were **not** retrieved rather than inferred |
| Full texts | ❌ not retrieved — publisher access required. Methodology and results summaries above are therefore limited to what the verified metadata and abstracts support, and are marked where thinner |
| JIRS aims-and-scope page | ❌ not retrieved (SSO redirect). The scope characterisation in §1 is derived from the journal's **actual published output**, which is arguably stronger evidence, but you should read the official scope statement yourself |
| Author instructions / editorial policy | ❌ not retrieved — needed for Part 9 (AI-disclosure policy, article types, length limits) |

**No paper was invented, and no irrelevant paper was promoted to fill a quota.**

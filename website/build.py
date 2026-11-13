#!/usr/bin/env python3
"""Generate the COSMOS-AI project website into ``website/public/``.

    python website/build.py            # writes the HTML pages
    python website/build.py --check    # also report missing assets and broken internal links

One source file, no npm, no bundler, no CDN: the output is plain static HTML that Vercel
serves directly, so the site cannot fail on a missing build step. Every figure quoted here
comes from the repository artifacts named beside it; nothing is invented. Re-run after editing.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

GITHUB = "https://github.com/AnuSajikumar6264/Cosmos-AI---A-Unified-Framework-for-space-debris-detection-and-re-entry"
SNAPSHOT = "2026-10-27"
# Set at deploy time; the demonstration page degrades to screenshots when empty.
DEMO_URL = os.environ.get("COSMOS_DEMO_URL", "").strip()

NAV = [("index", "Home"), ("problem", "Problem"), ("objectives", "Objectives"),
       ("methodology", "Methodology"), ("demonstration", "Demonstration"), ("progress", "Progress"),
       ("documentation", "Documentation"), ("videos", "Videos"), ("team", "Team")]

MARK = ('<svg class="mark" viewBox="0 0 32 32" fill="none" aria-hidden="true">'
        '<circle cx="16" cy="16" r="7.5" stroke="#4da3ff" stroke-width="1.6"/>'
        '<ellipse cx="16" cy="16" rx="14.5" ry="5.5" stroke="#22d3ee" stroke-width="1.3"'
        ' transform="rotate(-28 16 16)" opacity=".85"/>'
        '<circle cx="27.2" cy="10.6" r="2.1" fill="#f0b429"/></svg>')


def ico(path: str) -> str:
    return (f'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"'
            f' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>')


I_GLOBE = ico('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/>')
I_CHART = ico('<path d="M3 20h18M6 17V9M11 17V5M16 17v-6M21 17v-9"/>')
I_SHIELD = ico('<path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6l7-3z"/><path d="M9 12l2 2 4-4"/>')
I_CPU = ico('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>')
I_DOC = ico('<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>')
I_LAYERS = ico('<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>')
I_ALERT = ico('<path d="M12 4l9 16H3l9-16z"/><path d="M12 10v4M12 17h.01"/>')
I_SAT = ico('<path d="M4 13l7-7 4 4-7 7-4-4z"/><path d="M11 6l3-3 4 4-3 3M9 15l-3 3M15 9l3-3"/><path d="M13 19a6 6 0 006-6"/>')
I_CODE = ico('<path d="M8 6l-5 6 5 6M16 6l5 6-5 6"/>')
I_CLOCK = ico('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>')


def page(slug: str, title: str, body: str, desc: str) -> str:
    links = "".join(
        f'<a href="{"index.html" if s == "index" else s + ".html"}"'
        f'{" aria-current=\"page\"" if s == slug else ""}>{html.escape(t)}</a>'
        for s, t in NAV)
    year_note = ("Archived snapshot " + SNAPSHOT + " · no live tracking")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — COSMOS-AI</title>
<meta name="description" content="{html.escape(desc)}">
<meta name="author" content="Anupa Sajikumar">
<meta property="og:title" content="{html.escape(title)} — COSMOS-AI">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="assets/css/site.css">
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<canvas id="stars" aria-hidden="true"></canvas>
<div class="page">
<div class="nav-outer"><div class="wrap"><nav class="nav">
  <a class="brand" href="index.html">{MARK}<span>COSMOS-AI<small>Space Debris &amp; Re-entry</small></span></a>
  <button class="nav-toggle" aria-label="Menu" aria-expanded="false">☰</button>
  <div class="nav-links">{links}
    <a class="nav-cta" href="{GITHUB}" target="_blank" rel="noopener">GitHub</a>
  </div>
</nav></div></div>
<main id="main">
{body}
</main>
<footer><div class="wrap">
  <div class="foot-grid">
    <div>
      <a class="brand" href="index.html">{MARK}<span>COSMOS-AI<small>Space Debris &amp; Re-entry</small></span></a>
      <p class="small mt2" style="max-width:38ch">A unified framework for space-debris detection and
      atmospheric re-entry prediction, built on catalogue-scale, forward-in-time evaluation.</p>
      <p class="small muted mb0">{year_note}</p>
    </div>
    <div>
      <h4>Project</h4>
      <ul>{"".join(f'<li><a href="{"index.html" if s == "index" else s + ".html"}">{html.escape(t)}</a></li>' for s, t in NAV)}</ul>
    </div>
    <div>
      <h4>Elsewhere</h4>
      <ul>
        <li><a href="{GITHUB}" target="_blank" rel="noopener">Source code (GitHub)</a></li>
        <li><a href="https://planet4589.org/space/gcat" target="_blank" rel="noopener">GCAT catalogue</a></li>
        <li><a href="https://celestrak.org" target="_blank" rel="noopener">CelesTrak</a></li>
        <li><a href="https://www.amrita.edu" target="_blank" rel="noopener">Amrita Vishwa Vidyapeetham</a></li>
      </ul>
    </div>
  </div>
  <p class="foot-note">© 2026 Anupa Sajikumar · M.Tech Artificial Intelligence, Amrita Vishwa
  Vidyapeetham, Coimbatore · Supervisor: Dr. Shanmuga Priya S. Research results, figures and
  source are the author's own work. The console serves an archived snapshot: nothing on this site is
  a live satellite feed, and no figure here is a forecast of a real present-day re-entry.</p>
</div></footer>
</div>
<script src="assets/js/site.js" defer></script>
</body>
</html>
"""


def hero_home() -> str:
    return f"""<section class="hero"><div class="wrap">
  <div class="hero-grid">
    <div>
      <span class="eyebrow"><span class="dot"></span>M.Tech research project · Amrita Vishwa Vidyapeetham</span>
      <h1>Knowing When<br>Orbits End</h1>
      <p class="lede">COSMOS-AI is a unified framework for space-debris detection and atmospheric
      re-entry prediction. It pairs orbit-averaged drag physics with modern tabular learning, and
      evaluates both the way an operator actually has to: forward in time, with survivors counted
      and nothing chosen on the test set.</p>
      <div class="btn-row">
        <a class="btn btn-primary" href="demonstration.html">{I_GLOBE}Open the demonstration</a>
        <a class="btn btn-ghost" href="methodology.html">Read the methodology</a>
      </div>
    </div>
    <div class="hero-art">
      <img src="assets/img/shots/01_mission_overview.png" width="1440" height="900"
           alt="COSMOS-AI mission overview console showing a WebGL globe, catalogue counters and a selected rocket body">
    </div>
  </div>
  <div class="stats">
    <div class="stat"><span class="n">64,516</span><span class="l">catalogued objects in the evaluation cohort</span></div>
    <div class="stat"><span class="n">31,396</span><span class="l">objects in the dated digital twin</span></div>
    <div class="stat"><span class="n">3</span><span class="l">forward-in-time forecast origins, one sealed</span></div>
    <div class="stat"><span class="n">7</span><span class="l">learned predictors benchmarked against physics</span></div>
    <div class="stat"><span class="n">570</span><span class="l">automated tests passing</span></div>
  </div>
</div></section>"""


HOME = hero_home() + f"""
<hr class="divider">
<section><div class="wrap">
  <div class="sec-head">
    <span class="kicker">What it does</span>
    <h2>Four capabilities, one evidence chain</h2>
    <p>Each capability is validated on its own public benchmark and carries its own limits. Nothing is
    fused across modules unless a dataset actually links the objects.</p>
  </div>
  <div class="cards">
    <div class="card card-tall">{I_CLOCK}<h3>Orbital lifetime &amp; re-entry</h3>
      <p>Quantile forecasts of how long an uncontrolled object stays in orbit, from a King-Hele drag
      expert with NRLMSIS 2.1 densities, seven learned predictors, and a reliability-gated fusion of
      the two. Intervals are conformalised.</p>
      <div class="meta">64,516-object cohort · 3 origins</div></div>
    <div class="card card-tall">{I_SAT}<h3>Debris detection</h3>
      <p>Optical detection of faint geostationary debris streaks on the SpotGEO benchmark, reported
      against both a classical baseline and the published challenge winner.</p>
      <div class="meta">F1 0.765 vs 0.948 winner</div></div>
    <div class="card card-tall">{I_SHIELD}<h3>Satellite health</h3>
      <p>Telemetry anomaly detection on ESA-ADB and OPS-SAT-AD, run as pre-registered hypotheses so
      that refuted ones stay reported.</p>
      <div class="meta">OPS-SAT 0.949 · 2 of 3 hypotheses refuted</div></div>
    <div class="card card-tall">{I_ALERT}<h3>Conjunction &amp; decision support</h3>
      <p>Collision-risk scoring on the Kelvins challenge data, and an auditable priority ordering that
      is kept strictly separate from physical probability.</p>
      <div class="meta">Trivial baseline beats the learned arm</div></div>
  </div>
</div></section>

<hr class="divider">
<section><div class="wrap">
  <div class="sec-head">
    <span class="kicker">Headline findings</span>
    <h2>Three measurements, reported as they came out</h2>
  </div>
  <div class="cards cards-2">
    <div class="card">{I_CHART}<h3>Catalogue features carry real signal</h3>
      <p>Every predictor beats a feature-free oracle that uses the test set's own marginal quantiles —
      by at least 9 % and by up to 66 % in pinball loss, at all three origins.</p>
      <div class="meta">leaderboard_with_intervals.csv</div></div>
    <div class="card">{I_LAYERS}<h3>Model selection does not transfer</h3>
      <p>Tuning-fold and test rankings are uncorrelated (Spearman 0.000). Picking the learner with the
      best tuning loss cost <strong>+18.7 % excess test loss</strong> at origin 2016.</p>
      <div class="meta">95 % CI on excess loss [+0.0040, +0.0169]</div></div>
    <div class="card">{I_ALERT}<h3>The intervals fail in one specific place</h3>
      <p>Nominal 80 % intervals cover 92.3 % at origin 2011 but only 71.7 % at 2016 — and just
      <strong>56.3 %</strong> for objects whose area-to-mass ratio comes from design data.</p>
      <div class="meta">am_design_stage1/subgroup_coverage.csv</div></div>
  </div>
  <div class="callout warn">
    <h3>A negative result we do not hide</h3>
    <p>The reliability-gated fusion that this project deploys is <strong>not consistently better than
    the strongest individual learned model</strong>. It ranks third of twelve arms at origin 2011 and
    seventh at 2016, where two pretrained tabular models beat it with paired bootstrap intervals that
    exclude zero. It is retained because the alternatives failed criteria fixed in advance, and its
    limits are exposed in the console rather than smoothed over.</p>
  </div>
</div></section>

<hr class="divider">
<section><div class="wrap">
  <div class="sec-head"><span class="kicker">Explore</span><h2>Where to go next</h2></div>
  <div class="cards">
    <a class="card" href="demonstration.html">{I_GLOBE}<h3>Live demonstration →</h3>
      <p>The mission intelligence console: 19 screens over an archived twin of 31,396 objects.</p></a>
    <a class="card" href="methodology.html">{I_CPU}<h3>Methodology →</h3>
      <p>Architecture, data pipeline, the drag physics and every model actually used.</p></a>
    <a class="card" href="documentation.html">{I_DOC}<h3>Documentation →</h3>
      <p>Reports, dataflow and metrics, diagrams and the reproducibility record.</p></a>
    <a class="card" href="{GITHUB}" target="_blank" rel="noopener">{I_CODE}<h3>Source code →</h3>
      <p>The full framework, datasets via Git LFS, and the archived result files.</p></a>
  </div>
</div></section>"""


PROBLEM = f"""<section class="hero" style="padding-bottom:1.5rem"><div class="wrap">
  <span class="eyebrow"><span class="dot"></span>Problem statement</span>
  <h1 style="max-width:22ch">Low Earth orbit is<br>crowded and opaque</h1>
  <p class="lede">Drag eventually removes every uncontrolled object from low Earth orbit. <em>When</em> it
  does governs conjunction planning, re-entry risk on the ground and the long-term evolution of the
  debris population. The mechanics have been understood for decades. The inputs have not.</p>
</div></section>
<section style="padding-top:1rem"><div class="wrap">
  <div class="grid-outline">
    <div><h3>Unknowable atmosphere</h3><p class="small">Thermospheric density depends on solar and
      geomagnetic activity that cannot be forecast years ahead. A five-year lifetime forecast must
      assume something about a driver nobody can predict.</p></div>
    <div><h3>Unknown objects</h3><p class="small">The area-to-mass ratio sets the drag. In this cohort
      mass is missing for <strong>39.8 %</strong> of objects and radar cross-section for
      <strong>60.7 %</strong>. For most debris it must be sampled, not measured.</p></div>
    <div><h3>Survivors dominate</h3><p class="small">Between <strong>56 %</strong> and
      <strong>74 %</strong> of scored objects are still in orbit when the evaluation window ends.
      A metric computed only on objects that decayed answers a different question.</p></div>
    <div><h3>The population drifts</h3><p class="small">Launch practice and the solar cycle both move.
      A random split lets a model see the future regime it is then scored on.</p></div>
    <div><h3>Missingness encodes the outcome</h3><p class="small">Whether an object's cross-section was
      ever measured depends on how long it survived — adjusted odds ratio <strong>3.59</strong>
      (95 % CI [2.09, 6.17]). Using it as a feature leaks the answer.</p></div>
    <div><h3>Nobody reports the choice</h3><p class="small">Papers report the model that scored best on
      their test set. An operator must choose <em>before</em> the forecast period. Whether that choice
      survives is rarely measured.</p></div>
  </div>

  <div class="sec-head mt3">
    <span class="kicker">The gap this project addresses</span>
    <h2>Evaluation practice, not just model accuracy</h2>
    <p>Published lifetime and re-entry predictors are usually evaluated on one historical window, with
    a single split and point losses, on objects that have element-set histories. Three properties of
    the real problem are then invisible: right-censoring, population drift, and the cost of selecting
    a model without seeing its future.</p>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Conventional practice</th><th>What it hides</th><th>What COSMOS-AI does</th></tr></thead>
      <tbody>
        <tr><td>Evaluation window ends before, or overlaps, training</td><td>Drift; the model may see its own future</td><td>Three strictly ordered forward-in-time origins, one sealed and pre-registered</td></tr>
        <tr><td>Survivors dropped, or scored by point error</td><td>Most of the population</td><td>Capped log-lifetime target scored by pinball loss on every object with a known five-year outcome</td></tr>
        <tr><td>Objects from one launch treated as independent</td><td>Shared dynamics and bookkeeping</td><td>Launch-family cluster bootstrap for every interval; tuning folds split by family hash</td></tr>
        <tr><td>The reported model is chosen on the test set</td><td>Selection cost</td><td>Regret of tuning-fold selection measured in the published loss</td></tr>
        <tr><td>Coverage reported in aggregate</td><td>Where the intervals actually fail</td><td>Coverage decomposed by the provenance of the area-to-mass ratio</td></tr>
        <tr><td>Methods need two-line elements or tracking data</td><td>Most of the catalogue</td><td>Catalogue elements only, so every object is in scope</td></tr>
      </tbody>
    </table>
  </div>
  <p class="small muted mt2">Sources: <code>docs/DATAFLOW_AND_METRICS.md</code>,
  <code>outputs/benchmarks/reentry_lifetime/leak_check.json</code>,
  <code>data/feature3_reentry/processed/lifetime_cohort_{SNAPSHOT}_build_log.json</code>.</p>
</div></section>"""


OBJECTIVES = f"""<section class="hero" style="padding-bottom:1.5rem"><div class="wrap">
  <span class="eyebrow"><span class="dot"></span>Objectives</span>
  <h1 style="max-width:24ch">What the project set<br>out to establish</h1>
  <p class="lede">Five objectives, each with the artifact that settles whether it was met. Three were
  met as stated, one produced a negative answer that is reported as such, and one is still open
  because it needs a future catalogue snapshot.</p>
</div></section>
<section style="padding-top:1rem"><div class="wrap">
  <ol class="steps">
    <li><strong>O1 — Build a catalogue-scale, censoring-aware evaluation protocol.</strong>
      A cohort of 64,516 objects with three forward-in-time origins (2006 sealed, 2011, 2016),
      launch-family clustering, and feature-free reference predictors that bound trivial performance.
      <span class="tag-row"><span class="pill pill-done">Met</span>
      <span class="pill">64,516 objects</span><span class="pill">3 origins</span></span></li>
    <li><strong>O2 — Compare drag physics, learned models and their fusion like for like.</strong>
      A physics expert, seven learned quantile regressors and three fusion rules on identical splits
      with identical metrics.
      <span class="tag-row"><span class="pill pill-done">Met</span>
      <span class="pill pill-neg">Fusion not superior</span></span></li>
    <li><strong>O3 — Measure what the standard model-selection rule costs.</strong>
      Regret of &ldquo;pick the lowest tuning loss&rdquo; expressed in the published loss, with a rank
      inversion reproduced at all three origins.
      <span class="tag-row"><span class="pill pill-done">Met</span>
      <span class="pill">+18.7 % at 2016</span></span></li>
    <li><strong>O4 — Quantify the uncertainty, and locate where it breaks.</strong>
      Mondrian conformalised quantile intervals, with coverage decomposed by subgroup until the
      failure was localised.
      <span class="tag-row"><span class="pill pill-done">Met, descriptively</span>
      <span class="pill">56.3 % subgroup coverage</span></span></li>
    <li><strong>O5 — Deliver a usable, auditable artefact.</strong>
      A dated digital twin of 31,396 objects and a read-only console in which every number traces to a
      hashed file, incoherent probabilities trigger abstention, and staleness is stated on every screen.
      <span class="tag-row"><span class="pill pill-done">Met</span>
      <span class="pill pill-prog">Blind validation pending</span></span></li>
  </ol>

  <div class="callout">
    <h3>What the project deliberately does not claim</h3>
    <p>No constituent algorithm is new: King-Hele drag theory, NRLMSIS 2.1, the NASA breakup-model
    area-to-mass distribution, gradient boosting, TabM, TabICL, sigmoid-gated combination, split
    conformal prediction and Mondrian calibration are all existing methods used as published. No arm
    is claimed to be state of the art against external published methods, because none could be
    re-implemented on this cohort without element-set data. The twin performs no live monitoring and
    no request-time inference.</p>
  </div>
</div></section>"""


METHODOLOGY = f"""<section class="hero" style="padding-bottom:1.5rem"><div class="wrap">
  <span class="eyebrow"><span class="dot"></span>Methodology</span>
  <h1 style="max-width:26ch">Physics, learning,<br>and an honest referee</h1>
  <p class="lede">Two layers share one codebase. The benchmark layer fits and scores predictors at
  historical origins. The runtime layer applies the validated configuration once, at a dated
  catalogue snapshot, and archives the result; the console only reads that archive.</p>
</div></section>
<section style="padding-top:1rem"><div class="wrap">
  <figure>
    <img src="assets/img/fig/architecture.png" alt="COSMOS-AI system architecture: data sources, feature pipelines, physics and learned experts, fusion, calibration and the runtime twin">
    <figcaption>System architecture and data flow. Source: <code>paper/figures/architecture/</code>,
    generated from the implementation.</figcaption>
  </figure>

  <div class="sec-head mt3"><span class="kicker">Step 1 · Data pipeline</span>
    <h2>From catalogue rows to an ordered cohort</h2></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Stage</th><th>What happens</th><th>Result</th></tr></thead>
      <tbody>
        <tr><td>Ingest</td><td>GCAT 1.8.8 catalogue, CelesTrak SATCAT and SW-All space weather, all dated local snapshots</td><td class="num">69,999 rows</td></tr>
        <tr><td>Filter</td><td>Drop non-Earth or untyped objects, uncertain status codes, orbits without a day-precise epoch, perigee &ge; 2000 km, imprecise or impossible end dates</td><td class="num">− 5,483</td></tr>
        <tr><td>Cohort</td><td>One row per object with a LEO-crossing canonical orbit and a known or censored outcome</td><td class="num">64,516</td></tr>
        <tr><td>Outcomes</td><td>32,970 natural decays, 29,562 still in orbit, 1,984 controlled or other endings</td><td class="num">—</td></tr>
        <tr><td>Features</td><td>Orbit, age, design, trailing space weather, causal launch- and breakup-family statistics, physics summaries, class</td><td class="num">53 columns</td></tr>
        <tr><td>Split</td><td>Train &rarr; tune-A / tune-B (by family hash) &rarr; test, strictly ordered in time; development outcomes censored at the origin</td><td class="num">4 folds × 3 origins</td></tr>
      </tbody>
    </table>
  </div>
  <p class="small muted mt2">The object's own radar cross-section is excluded by design: its
  availability depends on how long the object survived.</p>

  <div class="sec-head mt3"><span class="kicker">Step 2 · Physics</span>
    <h2>Orbit-averaged drag, with the unknowns sampled</h2></div>
  <div class="cards cards-2">
    <div class="card"><h3>King-Hele decay integration</h3>
      <p class="small">Per-revolution change of semi-major axis and eccentricity for an exponential
      atmosphere about perigee, to third order in eccentricity; above e = 0.05 the exact orbit
      averages are evaluated by quadrature on 257 nodes. Integration stops at a 120 km perigee or a
      five-year cap.</p></div>
    <div class="card"><h3>NRLMSIS 2.1 densities</h3>
      <p class="small">Density and scale height interpolated from a table of 185 altitudes × 13 F10.7
      × 7 Ap values, averaged over latitude, local time and season. Solar and geomagnetic indices are
      held at their trailing 81-day means at the forecast epoch — the honest assumption, since the
      future is unknown.</p></div>
    <div class="card"><h3>Area-to-mass as a distribution</h3>
      <p class="small">32 Monte Carlo draws per object from one of three sources, recorded per object:
      design dimensions where the catalogue has them, a class prior for intact objects without them,
      or the NASA standard breakup model for fragments. This provenance later turns out to predict
      where the intervals fail.</p></div>
    <div class="card"><h3>History-conditioned posterior</h3>
      <p class="small">In the runtime twin only, an object still in orbit has survived since its
      canonical epoch, which selects low drag. Prior draws are propagated with the realised space
      weather and reweighted by survival and by agreement with the current orbit.</p></div>
  </div>

  <div class="sec-head mt3"><span class="kicker">Step 3 · Learning</span>
    <h2>The models actually used</h2></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Model</th><th>Family</th><th>Role in the framework</th></tr></thead>
      <tbody>
        <tr><td>XGBoost</td><td>Gradient-boosted trees</td><td>Lifetime quantile regression; one model per quantile</td></tr>
        <tr><td>LightGBM</td><td>Gradient-boosted trees</td><td>Lifetime quantile regression</td></tr>
        <tr><td>CatBoost</td><td>Gradient-boosted trees</td><td>Lifetime quantile regression; multi-quantile objective</td></tr>
        <tr><td>MLP</td><td>Neural network</td><td>Lifetime quantiles via a non-crossing head</td></tr>
        <tr><td>TabM</td><td>Parameter-efficient deep ensemble</td><td>Lifetime quantiles, 32 ensemble members</td></tr>
        <tr><td>TabICLv2</td><td>Pretrained in-context tabular model</td><td>Lifetime quantiles, no hyperparameter search</td></tr>
        <tr><td>Kumo-Tabular</td><td>Pretrained tabular model (vendor software)</td><td>Lifetime quantiles, 16,000-row context</td></tr>
        <tr><td>XGBoost-AFT</td><td>Accelerated failure time</td><td>Survival-style comparison arm</td></tr>
        <tr><td>U-Net / classical frontend</td><td>Convolutional segmentation</td><td>Optical debris streak detection (SpotGEO)</td></tr>
        <tr><td>Isotonic regression</td><td>Calibration</td><td>Per-horizon re-entry probability calibration</td></tr>
      </tbody>
    </table>
  </div>
  <p class="small muted mt2">Each learner gets the same budget: 12 random configurations scored on
  tune-A, then a five-seed ensemble. The two pretrained in-context models get no search.</p>

  <div class="sec-head mt3"><span class="kicker">Step 4 · Fusion and calibration</span>
    <h2>Combining the two, then admitting the result</h2></div>
  <div class="cards cards-2">
    <div class="card"><h3>Reliability-gated fusion</h3>
      <p class="small">The fused quantiles are a convex combination of the physics and learned
      quantiles, with an object-dependent weight from a logistic gate over ten reliability
      descriptors — area-to-mass provenance, physics spread, eccentricity, perigee band, object
      class, probability of reaching the cap. Fitted on out-of-fold training predictions.</p>
      <div class="meta">Mean weight on physics: 0.11</div></div>
    <div class="card"><h3>Mondrian conformal intervals</h3>
      <p class="small">Split conformalised quantile regression, calibrated on tune-B within groups of
      object class × perigee band, with a hierarchical fallback when a group is too small. The
      coverage guarantee needs exchangeability, which a forward-in-time split does not provide — so
      coverage is reported as a measurement, never as a guarantee.</p></div>
  </div>
  <figure class="mt2">
    <img src="assets/img/fig/calibration.png" alt="Interval coverage by area-to-mass provenance and by calendar year, showing the design-derived subgroup far below nominal">
    <figcaption>Where the intervals fail: coverage by area-to-mass provenance (left) and by calendar
    year at origin 2016 (right). Generated from the archived subgroup coverage tables.</figcaption>
  </figure>

  <div class="sec-head mt3"><span class="kicker">Step 5 · Runtime</span>
    <h2>Nine modules, one archived run</h2></div>
  <p>The twin engine builds one record per object in orbit at the snapshot with perigee below
  2000 km. Three regimes are distinguished and treated differently rather than averaged:
  <strong>13,787</strong> natural-decay objects receive the physics forecast with a history-conditioned
  area-to-mass posterior; <strong>16,386</strong> operator-controlled payloads get no drag forecast at
  all, because a station-keeping satellite does not decay on a drag schedule; <strong>1,223</strong>
  objects without a status form a separate unknown regime. Health, collision and debris are
  independent roots, so a missing telemetry artefact cannot block the catalogue chain.</p>
  <div class="callout">
    <p><strong>Abstention is a first-class output.</strong> Where the saved per-horizon probabilities are
    not monotone across horizons — 123 objects, a known defect of calibrating each horizon
    independently — the adapter abstains and logs them instead of quietly taking a running maximum
    over a published number. The priority ordering is the 30-day re-entry probability times two for
    objects of 500 kg or more; it is an ordering with no probabilistic reading, and it never modifies
    a physical probability.</p>
  </div>
</div></section>"""


def demonstration() -> str:
    if DEMO_URL:
        live = f"""<div class="demo-shell">
    <div class="demo-bar"><span class="lamp"></span>COSMOS-AI Mission Intelligence Console
      <span class="url">{html.escape(DEMO_URL)}</span></div>
    <iframe src="{html.escape(DEMO_URL)}" title="COSMOS-AI Mission Intelligence Console" loading="lazy"></iframe>
  </div>
  <div class="btn-row"><a class="btn btn-primary" href="{html.escape(DEMO_URL)}" target="_blank"
      rel="noopener">{I_GLOBE}Open full screen</a>
    <a class="btn btn-ghost" href="{GITHUB}" target="_blank" rel="noopener">Run it locally</a></div>"""
    else:
        live = f"""<div class="callout warn">
    <h3>The hosted console is not published yet</h3>
    <p>This page embeds the live console once it is deployed and <code>COSMOS_DEMO_URL</code> is set at
    build time. Until then, the captures below are unedited screenshots of the running console, taken
    on 2026-11-09 at 1440×900, and the console can be run locally in two commands.</p>
  </div>
  <div class="btn-row"><a class="btn btn-primary" href="{GITHUB}" target="_blank" rel="noopener">{I_CODE}Run it locally</a></div>"""
    shots = [
        ("01_mission_overview", "Mission overview",
         "Population summary, schematic WebGL globe, the selected object's lifetime interval and its "
         "cross-horizon coherence status. The banner states the snapshot date and that nothing is live."),
        ("03_twin_37607", "Object digital twin",
         "One object (NORAD 37607, an Ariane 5 rocket body): archived orbit elements, re-entry and "
         "lifetime probability by horizon, and both interval types side by side."),
        ("07_orbital_intelligence", "Lifetime &amp; re-entry analysis",
         "The benchmark behind the forecast: arms, losses, intervals and the origins they were "
         "measured at."),
        ("10_conjunction_analysis", "Conjunction &amp; collision",
         "Collision-risk screening on the held-out Kelvins benchmark, with the trivial baseline shown "
         "alongside the learned arm."),
        ("11_debris_monitoring", "Debris detection",
         "Optical detection of geostationary debris streaks, with the classical frontend and the "
         "published winner as reference points."),
        ("13_decision_intelligence", "Decision intelligence",
         "The priority rule read from the run manifest, the ranked queue, and the health-escalation "
         "module in an explicit abstain state because no dataset links telemetry to catalogued objects."),
        ("14_evidence_validation", "Evidence &amp; provenance",
         "Snapshot digest recomputed on read, readiness checks, schema versions and the twin-state "
         "equivalence result: 31,396 of 31,396 records valid."),
        ("16_guided_demo", "Guided demonstration",
         "A scripted walkthrough of the console for a first-time visitor."),
    ]
    cards = "".join(f"""<figure>
      <img class="shot" src="assets/img/shots/{s}.png" width="1440" height="900" loading="lazy"
           alt="{html.escape(re.sub('&amp;', 'and', t))} screen of the COSMOS-AI console">
      <figcaption><strong>{t}.</strong> {d}</figcaption></figure>""" for s, t, d in shots)
    return f"""<section class="hero" style="padding-bottom:1.5rem"><div class="wrap">
  <span class="eyebrow"><span class="dot"></span>Demonstration</span>
  <h1 style="max-width:26ch">The mission<br>intelligence console</h1>
  <p class="lede">Nineteen screens over an archived digital twin of 31,396 objects. Server-rendered
  pages, charts drawn as inline SVG from the real arrays, and a WebGL globe. No model runs when you
  open a page: every number is read from a hashed file produced by a dated pipeline run.</p>
</div></section>
<section style="padding-top:1rem"><div class="wrap">
  {live}
  <div class="stats">
    <div class="stat"><span class="n">19</span><span class="l">screens</span></div>
    <div class="stat"><span class="n">24</span><span class="l">JSON endpoints</span></div>
    <div class="stat"><span class="n">31,396</span><span class="l">objects in the twin</span></div>
    <div class="stat"><span class="n">{SNAPSHOT}</span><span class="l">catalogue snapshot</span></div>
    <div class="stat"><span class="n">0</span><span class="l">models run at request time</span></div>
  </div>

  <div class="sec-head mt3"><span class="kicker">What you are looking at</span>
    <h2>Read it the way it is built</h2></div>
  <div class="cards cards-2">
    <div class="card"><h3>Archived, not live</h3><p class="small">Every screen states the snapshot date
      and its age. There is no telemetry feed, no tracking, and no request-time inference. The console
      is an evidence browser over a dated forecast, which is why it can be audited.</p></div>
    <div class="card"><h3>Geometry is schematic</h3><p class="small">Orbit size, shape and inclination are
      the object's real archived values. Orientation and the marker's place on the ellipse are a screen
      layout: the catalogue publishes no ascending node, argument of perigee or epoch anomaly, so no
      position in time and no ground track can honestly be drawn.</p></div>
    <div class="card"><h3>Intervals can be degenerate</h3><p class="small">Of 15,010 re-entry intervals,
      13,765 have zero width and 14,028 medians sit at the five-year cap — consistent with all 32
      draws agreeing the object outlives the horizon. The console shows that rather than implying a
      precision it does not have.</p></div>
    <div class="card"><h3>Variants are shown disagreeing</h3><p class="small">The two forecast variants
      differ by a factor of 10.6 in the expected number of re-entries within 30 days. Both are
      displayed, because silently picking one would be the more misleading choice.</p></div>
  </div>

  <div class="sec-head mt3"><span class="kicker">Screens</span><h2>Captured from the running console</h2>
    <p>Unedited captures, 2026-11-09, 1440×900, taken by the project's own browser driver together
    with 27 scripted interaction checks.</p></div>
  {cards}
</div></section>"""


PROGRESS = f"""<section class="hero" style="padding-bottom:1.5rem"><div class="wrap">
  <span class="eyebrow"><span class="dot"></span>Project progress</span>
  <h1 style="max-width:24ch">What is done,<br>and what is not</h1>
  <p class="lede">Status against repository evidence. Work is marked complete only where an archived
  artifact settles it, in progress where it is partially done, and planned where nothing has been run.
  A blocked item says what blocks it.</p>
</div></section>
<section style="padding-top:1rem"><div class="wrap">
  <div class="table-wrap">
    <table>
      <thead><tr><th>Workstream</th><th>Status</th><th>Evidence</th></tr></thead>
      <tbody>
        <tr><td><strong>Lifetime benchmark</strong><br><span class="small muted">Cohort, three origins, 12 arms, intervals</span></td>
            <td><span class="pill pill-done">Complete</span></td>
            <td class="small"><code>outputs/benchmarks/reentry_lifetime/</code>, <code>outputs/g5d_origin2006/</code>, <code>outputs/lifetime_reference_predictors/</code></td></tr>
        <tr><td><strong>Physics expert</strong><br><span class="small muted">King-Hele, NRLMSIS 2.1, Monte Carlo A/m</span></td>
            <td><span class="pill pill-done">Complete</span></td>
            <td class="small"><code>cosmos/ai/lifetime/physics.py</code></td></tr>
        <tr><td><strong>Selection-transfer study</strong><br><span class="small muted">Regret, rank inversion, sealed origin</span></td>
            <td><span class="pill pill-done">Complete</span></td>
            <td class="small"><code>outputs/e3_e5/</code>, <code>docs/research/SELECTION_TRANSFER_ANALYSIS.md</code></td></tr>
        <tr><td><strong>Uncertainty &amp; calibration audit</strong><br><span class="small muted">Mondrian CQR, subgroup coverage</span></td>
            <td><span class="pill pill-done">Complete</span><br><span class="small muted">descriptive</span></td>
            <td class="small"><code>outputs/am_design_stage1/</code>, <code>outputs/phase3_uncertainty/</code></td></tr>
        <tr><td><strong>Feature-group ablations</strong><br><span class="small muted">Same-learner, BH-adjusted</span></td>
            <td><span class="pill pill-done">Complete</span></td>
            <td class="small"><code>outputs/e12_same_learner/e12_ablation_table.csv</code></td></tr>
        <tr><td><strong>Telemetry health benchmarks</strong><br><span class="small muted">ESA-ADB, OPS-SAT-AD, pre-registered</span></td>
            <td><span class="pill pill-done">Complete</span><br><span class="small muted">2 of 3 refuted</span></td>
            <td class="small"><code>outputs/benchmarks/telemetry_esa_adb/</code>, <code>telemetry_opssat*/</code></td></tr>
        <tr><td><strong>Optical debris detection</strong><br><span class="small muted">SpotGEO</span></td>
            <td><span class="pill pill-done">Complete</span><br><span class="small muted">below the winner</span></td>
            <td class="small"><code>outputs/benchmarks/vision_spotgeo/</code></td></tr>
        <tr><td><strong>Conjunction risk</strong><br><span class="small muted">Kelvins collision avoidance</span></td>
            <td><span class="pill pill-done">Complete</span><br><span class="small muted">trivial baseline wins</span></td>
            <td class="small"><code>outputs/benchmarks/conjunction_kelvins_cac/</code></td></tr>
        <tr><td><strong>Digital twin and console</strong><br><span class="small muted">31,396 objects, 19 screens</span></td>
            <td><span class="pill pill-done">Complete</span></td>
            <td class="small"><code>outputs/twin/as_of_{SNAPSHOT}/</code>, <code>cosmos/product/</code></td></tr>
        <tr><td><strong>Test and acceptance suite</strong><br><span class="small muted">570 passed, 3 skipped, 27 interactions</span></td>
            <td><span class="pill pill-done">Complete</span></td>
            <td class="small"><code>tests/</code>, <code>outputs/product/screenshots/report.json</code></td></tr>
        <tr><td><strong>M.Tech thesis</strong><br><span class="small muted">257 pages, Amrita format</span></td>
            <td><span class="pill pill-done">Complete</span><br><span class="small muted">supervisor review pending</span></td>
            <td class="small">built from <code>docs/thesis/final/</code> (not published here)</td></tr>
        <tr><td><strong>Journal manuscript</strong><br><span class="small muted">Springer format, JINT target</span></td>
            <td><span class="pill pill-prog">Draft</span><br><span class="small muted">not submitted</span></td>
            <td class="small">prepared locally; not in this repository</td></tr>
        <tr><td><strong>Public code release</strong><br><span class="small muted">Framework, datasets via LFS, results</span></td>
            <td><span class="pill pill-done">Published</span></td>
            <td class="small"><a href="{GITHUB}" target="_blank" rel="noopener">GitHub repository</a></td></tr>
        <tr><td><strong>Blind prospective validation</strong><br><span class="small muted">Released forecast vs reality</span></td>
            <td><span class="pill pill-plan">Blocked</span></td>
            <td class="small">needs a catalogue snapshot dated 2026-11-26 or later</td></tr>
        <tr><td><strong>Calibration stratified by A/m source</strong><br><span class="small muted">The remedy the audit suggests</span></td>
            <td><span class="pill pill-plan">Not run</span></td>
            <td class="small">needs refits of archived learners whose backends are unavailable</td></tr>
        <tr><td><strong>Element-set comparison</strong><br><span class="small muted">Against published methods</span></td>
            <td><span class="pill pill-plan">Not possible</span></td>
            <td class="small">requires two-line element or ephemeris data this cohort does not have</td></tr>
      </tbody>
    </table>
  </div>

  <div class="sec-head mt3"><span class="kicker">Benchmark record</span>
    <h2>Measured results, including the ones that went the wrong way</h2></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Benchmark</th><th>Metric</th><th>Result</th><th>Reference point</th></tr></thead>
      <tbody>
        <tr><td>Lifetime, origin 2011</td><td>Pinball loss</td><td class="num">0.0527</td><td class="small">best arm (physics expert); feature-free oracle 0.1332</td></tr>
        <tr><td>Lifetime, origin 2016</td><td>Pinball loss</td><td class="num">0.0499</td><td class="small">best arm (TabICLv2); feature-free oracle 0.1469</td></tr>
        <tr><td>Lifetime, origin 2006 (sealed)</td><td>Pinball loss</td><td class="num">0.0568</td><td class="small">best arm (physics expert); oracle 0.1322</td></tr>
        <tr><td>Selection regret, 2016</td><td>Excess test loss</td><td class="num">+18.7 %</td><td class="small">95 % CI [+0.0040, +0.0169]; Spearman(tune, test) = 0.000</td></tr>
        <tr><td>Interval coverage, 2016</td><td>Nominal 80 %</td><td class="num">71.7 %</td><td class="small">56.3 % in the design-derived A/m subgroup</td></tr>
        <tr><td>ESA-ADB telemetry (H6)</td><td>Event-wise F1 gain</td><td class="num">+0.353</td><td class="small">0.074 &rarr; 0.428; CI [+0.206, +0.488]; Holm p = 0.0015</td></tr>
        <tr><td>ESA-ADB telemetry (H4, H5)</td><td>Pre-registered hypotheses</td><td class="num">Refuted</td><td class="small">−0.222 and −0.338; reported, not dropped</td></tr>
        <tr><td>OPS-SAT-AD</td><td>Accuracy</td><td class="num">0.949 ± 0.009</td><td class="small">the one model with persisted weights</td></tr>
        <tr><td>SpotGEO debris detection</td><td>F1</td><td class="num">0.765 ± 0.034</td><td class="small">classical frontend 0.084; published challenge winner 0.948</td></tr>
        <tr><td>Kelvins collision avoidance</td><td>F2</td><td class="num">0.739</td><td class="small">a trivial baseline; the learned arm scored 0.168</td></tr>
      </tbody>
    </table>
  </div>
  <p class="small muted mt2">Two of these are deliberately unflattering. The optical detector is well
  behind the published winner, and on the conjunction benchmark a trivial rule beats the learned
  model. Both are reported because an evaluation framework that only publishes its wins is not an
  evaluation framework.</p>
</div></section>"""


DOCUMENTATION = f"""<section class="hero" style="padding-bottom:1.5rem"><div class="wrap">
  <span class="eyebrow"><span class="dot"></span>Documentation</span>
  <h1 style="max-width:24ch">Reports, diagrams<br>and the audit trail</h1>
  <p class="lede">Everything below lives in the public repository. Paths are relative to the repository
  root; follow a card to read the file on GitHub.</p>
</div></section>
<section style="padding-top:1rem"><div class="wrap">
  <div class="sec-head"><span class="kicker">Core technical documents</span><h2>Start here</h2></div>
  <div class="cards">
    <a class="card" href="{GITHUB}/blob/main/README.md" target="_blank" rel="noopener">{I_DOC}
      <h3>Project README</h3><p>What the framework is, how to install it, the dataset inventory and
      what is deliberately not redistributed.</p><div class="meta">README.md</div></a>
    <a class="card" href="{GITHUB}/blob/main/docs/DATAFLOW_AND_METRICS.md" target="_blank" rel="noopener">{I_LAYERS}
      <h3>Dataflow and metrics</h3><p>Every pipeline stage and the metric definitions behind each
      reported number.</p><div class="meta">docs/DATAFLOW_AND_METRICS.md</div></a>
    <a class="card" href="{GITHUB}/blob/main/docs/ARCHITECTURE_AND_NOVELTY.md" target="_blank" rel="noopener">{I_CPU}
      <h3>Architecture and novelty</h3><p>The module graph, and a careful statement of which parts are
      new and which are existing methods used as published.</p><div class="meta">docs/ARCHITECTURE_AND_NOVELTY.md</div></a>
    <a class="card" href="{GITHUB}/blob/main/docs/RESULTS_AND_ANALYSIS.md" target="_blank" rel="noopener">{I_CHART}
      <h3>Results and analysis</h3><p>The full result set with intervals, subgroup breakdowns and the
      negative findings.</p><div class="meta">docs/RESULTS_AND_ANALYSIS.md</div></a>
    <a class="card" href="{GITHUB}/blob/main/docs/research/limitations_register.md" target="_blank" rel="noopener">{I_ALERT}
      <h3>Limitations register</h3><p>Nineteen known limitations, each with its cause, its effect and
      how the system handles it downstream.</p><div class="meta">docs/research/limitations_register.md</div></a>
    <a class="card" href="{GITHUB}/blob/main/docs/research/FINAL_REPRODUCIBILITY_REPORT.md" target="_blank" rel="noopener">{I_SHIELD}
      <h3>Reproducibility report</h3><p>What reproduces at the prediction level, what does not
      reproduce at the training level, and exactly why.</p><div class="meta">docs/research/FINAL_REPRODUCIBILITY_REPORT.md</div></a>
    <a class="card" href="{GITHUB}/blob/main/docs/research/dataset_provenance.md" target="_blank" rel="noopener">{I_GLOBE}
      <h3>Dataset provenance</h3><p>Source, licence, snapshot date and status for every dataset,
      including the ones that are absent.</p><div class="meta">docs/research/dataset_provenance.md</div></a>
    <a class="card" href="{GITHUB}/blob/main/docs/DATA_HOSTING.md" target="_blank" rel="noopener">{I_CODE}
      <h3>Data hosting &amp; Git LFS</h3><p>Which datasets travel with the repository, which must be
      downloaded, and the commands to fetch them.</p><div class="meta">docs/DATA_HOSTING.md</div></a>
  </div>

  <div class="sec-head mt3"><span class="kicker">Diagrams</span><h2>Figures generated from the code</h2></div>
  <figure>
    <img src="assets/img/fig/architecture.png" alt="Full COSMOS-AI architecture diagram">
    <figcaption>System architecture and evidence flow across all four capabilities.</figcaption>
  </figure>
  <div class="cards cards-2">
    <figure><img src="assets/img/fig/benchmarks.png" alt="Learned predictors against feature-free reference predictors at each origin">
      <figcaption>Learned and physical predictors against the feature-free references, per origin.</figcaption></figure>
    <figure><img src="assets/img/fig/rank_instability.png" alt="Rank instability of predictors between tuning and test folds">
      <figcaption>Rank instability between the tuning and test folds — the selection result.</figcaption></figure>
    <figure><img src="assets/img/fig/calibration.png" alt="Interval coverage by subgroup and by year">
      <figcaption>Interval coverage by area-to-mass provenance and by calendar year.</figcaption></figure>
    <figure><img src="assets/img/fig/datasets.png" alt="Inventory of datasets used by the project">
      <figcaption>Dataset inventory: what is used, what is present and what is absent.</figcaption></figure>
  </div>

  <div class="sec-head mt3"><span class="kicker">Thesis and publication</span><h2>Written outputs</h2></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Output</th><th>State</th><th>Availability</th></tr></thead>
      <tbody>
        <tr><td>M.Tech thesis, 257 pages, Amrita <code>ugthesis</code> format</td>
            <td><span class="pill pill-done">Written</span></td>
            <td class="small">Held with the author and the department; the source is not published in this repository</td></tr>
        <tr><td>Journal manuscript, Springer format, targeted at the <em>Journal of Intelligent &amp; Robotic Systems</em></td>
            <td><span class="pill pill-prog">Draft</span></td>
            <td class="small">Not submitted. Not published in this repository</td></tr>
        <tr><td>Benchmark release plan and claims matrix</td>
            <td><span class="pill pill-done">In repository</span></td>
            <td class="small"><a href="{GITHUB}/tree/main/docs/jirs" target="_blank" rel="noopener">docs/jirs/</a></td></tr>
        <tr><td>Audit and acceptance reports</td>
            <td><span class="pill pill-done">In repository</span></td>
            <td class="small"><a href="{GITHUB}/tree/main/docs/research" target="_blank" rel="noopener">docs/research/</a></td></tr>
      </tbody>
    </table>
  </div>
</div></section>"""


VIDEOS = f"""<section class="hero" style="padding-bottom:1.5rem"><div class="wrap">
  <span class="eyebrow"><span class="dot"></span>Demonstration videos</span>
  <h1 style="max-width:24ch">No recordings<br>exist yet</h1>
  <p class="lede">To be straightforward about it: the repository contains no video or screen recording
  of any kind. The slots below are labelled placeholders, not hidden or broken embeds. Until they are
  filled, the still captures on the demonstration page and the guided walkthrough inside the console
  are the closest thing available.</p>
  <div class="btn-row">
    <a class="btn btn-primary" href="demonstration.html">{I_GLOBE}See the screen captures</a>
    <a class="btn btn-ghost" href="{GITHUB}" target="_blank" rel="noopener">Run the console yourself</a>
  </div>
</div></section>
<section style="padding-top:1rem"><div class="wrap">
  <div class="cards cards-2">
    <div class="card card-tall">{I_CLOCK}<h3>Console walkthrough</h3>
      <p>A guided tour of the 19 screens: mission overview, an object twin, the benchmark pages and the
      evidence trail.</p>
      <div class="tag-row"><span class="pill pill-plan">Placeholder · not recorded</span></div>
      <div class="meta">Suggested length 4–6 min</div></div>
    <div class="card card-tall">{I_CHART}<h3>Methodology explainer</h3>
      <p>How the drag physics, the learned quantile models and the reliability gate fit together, and
      why the evaluation is ordered in time.</p>
      <div class="tag-row"><span class="pill pill-plan">Placeholder · not recorded</span></div>
      <div class="meta">Suggested length 6–8 min</div></div>
    <div class="card card-tall">{I_LAYERS}<h3>Results and negative findings</h3>
      <p>The three headline measurements, and an honest account of where the fusion loses and the
      intervals fail.</p>
      <div class="tag-row"><span class="pill pill-plan">Placeholder · not recorded</span></div>
      <div class="meta">Suggested length 5–7 min</div></div>
    <div class="card card-tall">{I_CODE}<h3>Reproduction from a clean checkout</h3>
      <p>Clone, fetch the datasets, run the prerequisite check and start the console.</p>
      <div class="tag-row"><span class="pill pill-plan">Placeholder · not recorded</span></div>
      <div class="meta">Suggested length 3–5 min</div></div>
  </div>
  <div class="callout">
    <p>When a recording exists, drop the file or its link into <code>website/build.py</code> and re-run
    the build: the placeholder becomes a player. Nothing else needs to change.</p>
  </div>
</div></section>"""


TEAM = f"""<section class="hero" style="padding-bottom:1.5rem"><div class="wrap">
  <span class="eyebrow"><span class="dot"></span>Team</span>
  <h1 style="max-width:22ch">Who built this</h1>
  <p class="lede">A single-author M.Tech research project, carried out under supervision at Amrita
  Vishwa Vidyapeetham. Only verified people and roles are listed here.</p>
</div></section>
<section style="padding-top:1rem"><div class="wrap">
  <div class="cards cards-2">
    <div class="card">
      <h3>Anupa Sajikumar</h3>
      <p class="small muted mb0 mono">CB.SC.P2AIE25003</p>
      <p class="small mt2">M.Tech, Artificial Intelligence. Author of the framework: the evaluation
      protocol, the physics expert, the learned and fused lifetime predictors, the benchmark studies,
      the digital twin, the console and all written outputs.</p>
      <div class="tag-row"><span class="pill">Author</span><span class="pill">Research &amp; implementation</span></div>
    </div>
    <div class="card">
      <h3>Dr. Shanmuga Priya S</h3>
      <p class="small muted mb0">Supervisor</p>
      <p class="small mt2">Project supervisor, Amrita Vishwa Vidyapeetham. Guidance and review of the
      research direction, methodology and written outputs.</p>
      <div class="tag-row"><span class="pill">Supervisor</span></div>
    </div>
  </div>

  <div class="sec-head mt3"><span class="kicker">Institution</span><h2>Amrita Vishwa Vidyapeetham</h2></div>
  <div class="grid-outline">
    <div><h3>Department</h3><p class="small">Computer Science and Engineering · M.Tech programme in
      Artificial Intelligence.</p></div>
    <div><h3>Campus</h3><p class="small">Coimbatore – 641 112, Tamil Nadu, India.</p></div>
    <div><h3>Programme</h3><p class="small">M.Tech research project, submitted November 2026.</p></div>
  </div>

  <div class="callout mt3">
    <h3>Authorship statement</h3>
    <p>The research design, implementation, experiments, analysis and written outputs are the author's
    own work, carried out under the supervision named above. No AI tool is an author or contributor to
    this project. Third-party datasets, libraries and published methods are credited to their authors
    wherever they are used, in the repository documentation and in the written outputs.</p>
  </div>
</div></section>"""


PAGES = {
    "index": ("Home", HOME,
              "COSMOS-AI: a unified framework for space-debris detection and atmospheric re-entry "
              "prediction, with forward-in-time, censoring-aware evaluation over 64,516 catalogued objects."),
    "problem": ("Problem Statement", PROBLEM,
                "Why orbital lifetime prediction is hard: unknowable atmosphere, unknown objects, "
                "right-censoring, population drift and outcome-dependent missing data."),
    "objectives": ("Objectives", OBJECTIVES,
                   "The five objectives of the COSMOS-AI project and the artifact that settles each."),
    "methodology": ("Methodology", METHODOLOGY,
                    "Architecture, data pipeline, King-Hele drag physics with NRLMSIS 2.1, the learned "
                    "quantile models, reliability-gated fusion and conformal calibration."),
    "demonstration": ("Demonstration", demonstration(),
                      "The COSMOS-AI mission intelligence console: 19 screens over an archived digital "
                      "twin of 31,396 catalogued objects."),
    "progress": ("Project Progress", PROGRESS,
                 "Completed, in-progress and planned work across the COSMOS-AI project, with the "
                 "repository evidence for each and the full benchmark record."),
    "documentation": ("Documentation", DOCUMENTATION,
                      "Technical reports, architecture diagrams, dataset provenance, the limitations "
                      "register and the reproducibility record."),
    "videos": ("Demonstration Videos", VIDEOS,
               "Planned demonstration videos for COSMOS-AI. No recordings exist yet; these are "
               "labelled placeholders."),
    "team": ("Team", TEAM,
             "Anupa Sajikumar, author, supervised by Dr. Shanmuga Priya S at Amrita Vishwa "
             "Vidyapeetham, Coimbatore."),
}

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="7" fill="#05080f"/>
<circle cx="16" cy="16" r="7" stroke="#4da3ff" stroke-width="1.8" fill="none"/>
<ellipse cx="16" cy="16" rx="13.5" ry="5" stroke="#22d3ee" stroke-width="1.5" fill="none"
 transform="rotate(-28 16 16)"/><circle cx="26" cy="11" r="2.2" fill="#f0b429"/></svg>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report missing assets and broken internal links")
    args = ap.parse_args()

    os.makedirs(os.path.join(OUT, "assets", "img"), exist_ok=True)
    written = []
    for slug, (title, body, desc) in PAGES.items():
        path = os.path.join(OUT, f"{slug}.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(page(slug, title, body, desc))
        written.append(f"{slug}.html")
    with open(os.path.join(OUT, "assets", "img", "favicon.svg"), "w", encoding="utf-8") as fh:
        fh.write(FAVICON)
    print(f"wrote {len(written)} pages to {OUT}: {', '.join(written)}")
    print(f"demo embed: {DEMO_URL or '(none - set COSMOS_DEMO_URL and re-run to embed the live console)'}")

    if args.check:
        bad = 0
        pages = {p for p in os.listdir(OUT) if p.endswith(".html")}
        for p in sorted(pages):
            text = open(os.path.join(OUT, p), encoding="utf-8").read()
            for m in re.finditer(r'(?:href|src)="(?!https?:|#|mailto:)([^"]+)"', text):
                target = m.group(1).split("#")[0]
                if not target:
                    continue
                if not os.path.exists(os.path.join(OUT, target)):
                    print(f"  MISSING  {p} -> {target}")
                    bad += 1
        print(f"check: {bad} missing local target(s)")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

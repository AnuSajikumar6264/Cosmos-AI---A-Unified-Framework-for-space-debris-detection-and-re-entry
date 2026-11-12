# Kelvins Spacecraft Collision Avoidance Challenge — metric and baselines, verbatim

Source: Uriot, Izzo, Simões et al., *Spacecraft collision avoidance challenge: Design and results of a
machine learning competition*, Astrodynamics 2021, DOI 10.1007/s42064-021-0101-5 (hybrid open access,
Unpaywall-verified 2026-11-06); text extracted with pypdf from the arXiv copy
https://arxiv.org/pdf/2008.03069 (4,836,697 bytes) into an isolated directory, nothing executed.
Ligatures (ﬁ) and spacing are as extracted.

## Metric (verbatim)
> Denoting the ﬁnal risk byr and the corresponding prediction by ˆr, the metric is deﬁned as: L(ˆr) = 1F2 MSEHR(r, ˆr), (1) whereF2 is computed over the whole test set, using two classes, (high ﬁnal risk:r≥− 6, low ﬁnal risk:r< −6) and the MSEHR(r,·) is only computed for the high risk events. More formally, we have MSEHR(r, ˆr) = 1N ∗ N∑ i=1 1i(ri− ˆri)2, whereN is the total number of events,N ∗ = N∑ i=1 1i is the number of high risk events,ri and ˆri are the true risk and predicted risk for theith event and 6 A PREPRINT - OCTOBER 13, 2020 1i = {1 if ri≥− 6, 0 otherwise. Finally, theF score is deﬁned as Fβ = (1 +β2

## Constant Risk Prediction baseline (verbatim)
> CRP baseline) is then deﬁned as: ˆri =−5 and has an overall score ofL = 2.5. It constantly predicts the same value for the risk and was highlighted during the competition as a persistent entry in the leaderboard. Out of the 97 teams 38 managed to produce a better model. One of the simplest approaches in time series prediction is the naive forecast [22], i.e. forecast with the l

## Latest Risk Prediction baseline (verbatim)
> a second baseline solution, called Latest Risk Prediction baseline (LRP baseline) is deﬁned as the clipped naive forecast: ˆri = {r−2i if r−2i≥− 6, −6.001 otherwise. and has a score ofL = 0.694 when evaluated on the complete test set. Out of the 97 teams 12 managed to submit better solutions. Quite a few different teams found and made use of this baseline (or equivalent variants) in their submissions. The score achieved by the LRP is also reported in Table 3 and is plotted as an horizontal line in Figure 9, alongsi

## On F2 (verbatim)
> All the teams managed to improve upon the LRP baseline score by obtaining a better MSEHR. Interestingly, however, many of the teams fail to obtain a better F2 value than the LRP baseline. In order to investigate further the differences between theF2 score achieved by the teams and the LRP baseline solution, it is helpful to look into the false positives and 

## Relevance to COSMOS-AI (not from the paper)
* The archived `latest_risk_point` row in `outputs/benchmarks/conjunction_kelvins_cac/test_results.csv`
  has `L_clip = 0.693961` on the same complete test set — it reproduces the paper's LRP baseline
  (L = 0.694) to three decimals, an external check on the metric implementation and test inputs.
* The paper reports that only 12 of 97 teams beat LRP and that many failed to beat its F2; the
  project's finding that its learned arms do not beat the latest-risk rule on F2 is therefore the
  expected outcome on this benchmark, not an anomaly of the implementation.

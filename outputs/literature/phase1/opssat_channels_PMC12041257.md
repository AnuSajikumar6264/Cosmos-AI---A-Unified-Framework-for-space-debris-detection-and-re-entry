# OPS-SAT-AD channel semantics — verbatim from the benchmark paper

Source: Ruszczak, Kotowski, Evans et al., *The OPS-SAT benchmark for detecting anomalies in satellite
telemetry*, Scientific Data 2025, DOI 10.1038/s41597-025-05035-3, open access, Europe PMC
**PMC12041257** (full-text XML fetched 2026-11-06 from
https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12041257/fullTextXML).

## Channels (verbatim)

> It is built of 9 source telemetry channels that were selected by the space operations engineers. They include 3 magnetometer telemetry channels: I_B_FB_MM_0 (CADC0872), I_B_FB_MM_1 (CADC0873), I_B_FB_MM_2 (CADC0874), and 6 photo diode (PD) channels: I_PD1_THETA (CADC0884), I_PD2_THETA (CADC0886), I_PD3_THETA (CADC0888), I_PD4_THETA (CADC0890), I_PD5_THETA (CADC0892), I_PD6_THETA (CADC0894). Here, the names correspond to the source names from the WebMUST repository and the OPS-SAT telemetry channel names (in brackets). The layout of the dataset is summarized in Fig. 5 —it includes both the raw files, as well as the extracted features in a tabular form. Fig. 5 The layout of the OPS-SAT benchma

## Dataset composition (verbatim)

> ting data-driven anomaly detection techniques. It includes a selection and the corresponding ground-truth annotation of 2123 short single-channel satellite telemetry fragments (univariate time series) captured within 9 telemetry channels. Due to the underlying nature of the OPS-SAT mission, anomalous fragments account for 20% of the dataset. Such fragments contain raw data with many aforementioned real-life challenges, and they differ in their le

## What this does and does not establish for COSMOS-AI

* The nine channels are **three magnetometer** and **six photodiode** telemetry channels chosen by the
  operations engineers. The paper does not use the terms "ADCS", "attitude" or "sun sensor"
  (0 hits each in the full text); COSMOS-AI therefore describes OPS-SAT-AD as *magnetometer and
  photodiode channel monitoring*, not as named-subsystem monitoring.
* Fragments are single-channel; anomaly labels are per fragment, not per subsystem.
* No power, thermal or propulsion telemetry is present in any real dataset used by the project.

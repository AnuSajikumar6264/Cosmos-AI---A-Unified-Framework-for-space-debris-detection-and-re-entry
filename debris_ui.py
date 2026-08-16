"""
Streamlit pages for the debris stack, kept out of ``app.py`` so that file stays readable.

Every expensive computation is wrapped in ``st.cache_data`` keyed on primitive arguments, so
moving a slider re-runs only what actually depends on it.  The physics is in :mod:`debris`;
nothing here does arithmetic that matters.

Each page states the provenance of what it shows.  Some of the inputs are validated physics
and some are coarse stand-ins (population density, launch-vehicle masses), and a dashboard
that renders both in the same confident typeface is misleading.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from debris import (
    LAUNCH_SITES,
    LAUNCH_VEHICLES,
    BreakupType,
    Camera,
    DebrisObject,
    DispersionConfig,
    DoGDetector,
    DragModel,
    MissionProfile,
    ParentType,
    StateVector,
    SubsystemHealth,
    SyntheticFrameConfig,
    SyntheticPopulationModel,
    ascent_profile,
    assess_breakup_hazard,
    assess_footprint,
    assess_sustainability,
    breakup_contribution,
    build_action_catalogue,
    compare_altitudes,
    debris_evidence_to_health,
    default_leo_shells,
    density_zone,
    detection_metrics,
    detections_to_objects,
    estimate_time_to_breakup,
    generate_debris_cloud,
    generate_frame_pair,
    greedy_mitigation,
    mahalanobis_zone,
    optimise_mitigation,
    propagate,
    run_cloud_dispersion,
    run_coupled_prediction,
    run_dispersion,
    separation_states,
    simulate_cascade,
    zone_comparison,
    zone_population,
)
from debris import viz

SUBSYSTEM_ORDER = (
    "Attitude Control", "Power System", "Thermal Control", "Communication",
    "Payload Sensors", "On-board Computer", "Propulsion System", "Data Storage Unit",
)


# --------------------------------------------------------------------------- helpers
def _header(text: str):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def _note(text: str):
    st.markdown(f"<div class='info-box'>{text}</div>", unsafe_allow_html=True)


def _metrics(pairs, columns: int | None = None):
    cols = st.columns(columns or len(pairs))
    for col, (label, value, *rest) in zip(cols, pairs):
        col.metric(label, value, *(rest[:1]))


def _df(rows) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _kv(mapping, name: str = "value") -> pd.DataFrame:
    """
    Render a summary dict as a two-column field/value table.

    Transposing a one-row DataFrame instead produces an object column holding a mix of floats,
    strings, bools and lists, which Arrow cannot assign a type to - Streamlit then falls back
    with a logged traceback. Formatting to strings up front keeps the display identical and the
    log clean, and it also lets numbers be shown to a sensible precision rather than full
    float repr.
    """
    def fmt(v):
        if isinstance(v, bool) or v is None:
            return str(v)
        if isinstance(v, (int,)):
            return f"{v:,}"
        if isinstance(v, float):
            if v != v:
                return "n/a"
            if v == 0:
                return "0"
            av = abs(v)
            return f"{v:,.4g}" if 1e-4 <= av < 1e7 else f"{v:.4e}"
        if isinstance(v, (list, tuple)):
            return ", ".join(str(x) for x in v) or "-"
        return str(v)

    items = list(mapping.items()) if isinstance(mapping, dict) else list(mapping)
    return pd.DataFrame({"field": [k.replace("_", " ") for k, _ in items],
                         name: [fmt(v) for _, v in items]})


def _provenance(text: str):
    st.caption(f"Provenance: {text}")


# =========================================================================== detection
@st.cache_data(show_spinner=False)
def _detect_scene(seed: int, n_fragments: int, faintness: float, limb: float,
                  jitter: float, streak: float, n_stars: int, threshold: float):
    cfg = SyntheticFrameConfig(
        n_fragments=int(n_fragments),
        fragment_flux=(0.03 + 0.05 * (1 - faintness), 0.12 + 0.5 * (1 - faintness)),
        limb_brightness=float(limb),
        streak_length_px=(0.0, float(streak)),
        n_stars=int(n_stars),
    )
    frame_a, frame_b, truth = generate_frame_pair(int(seed), cfg, jitter_px=float(jitter))
    det = DoGDetector(threshold=float(threshold), max_detections=120)
    single = det.detect(frame_b)
    paired = det.detect_pair(frame_a, frame_b)
    return (frame_a, frame_b, truth, single, paired,
            detection_metrics(single, truth).summary(),
            detection_metrics(paired, truth).summary(),
            det.last_shift)


def page_detection():
    _header("Debris Detection - frame differencing")
    _note(
        "A <strong>single frame cannot separate debris from stars</strong>: both are unresolved "
        "point sources through the same PSF, and a distant fragment is usually the fainter of "
        "the two. What separates them is motion. Differencing two frames a few seconds apart "
        "cancels the static star field and leaves whatever moved - which is how real optical "
        "debris surveys work. The two panels below are the same detector on the same scene, "
        "run on one frame and on the difference."
    )

    c = st.columns([1, 3])
    with c[0]:
        seed = st.slider("Scene seed", 0, 200, 7)
        n_frag = st.slider("Fragments in scene", 1, 25, 8)
        faint = st.slider("Fragment faintness", 0.0, 1.0, 0.5,
                          help="1.0 = as faint as the model allows; the hard case.")
        limb = st.slider("Earth limb brightness", 0.0, 1.0, 0.35)
        streak = st.slider("Max motion streak [px]", 0.0, 12.0, 6.0)
        stars = st.slider("Star count", 20, 300, 140)
        jitter = st.slider("Boresight jitter [px]", 0.0, 4.0, 1.0)
        thr = st.slider("Detection threshold [sigma]", 3.0, 45.0, 22.0)
        rng_m = st.number_input("Range to target [m]", 100.0, 2_000_000.0, 1000.0, step=100.0)
        sizing = st.radio("Sizing method", ["angular (resolved)", "photometric (unresolved)"],
                          help="Angular sizing is only valid when the fragment spans several "
                               "pixels. At surveillance range it just measures the PSF.")

    (fa, fb, truth, single, paired, m_single, m_pair, shift) = _detect_scene(
        seed, n_frag, faint, limb, jitter, streak, stars, thr)

    with c[1]:
        _metrics([
            ("Frame-pair F1", f"{m_pair['f1']:.3f}", f"{m_pair['f1'] - m_single['f1']:+.3f} vs single"),
            ("Precision", f"{m_pair['precision']:.3f}"),
            ("Recall", f"{m_pair['recall']:.3f}"),
            ("Registration shift", f"{np.hypot(*shift):.2f} px"),
        ])
        tabs = st.tabs(["Difference detections", "Single-frame detections", "Raw frames"])
        with tabs[0]:
            from debris.detection import difference_frames
            diff, _ = difference_frames(fa, fb)
            st.plotly_chart(viz.plot_frame_detections(diff, paired, truth,
                                                     title="Registered difference b - a"),
                            width="stretch")
        with tabs[1]:
            st.plotly_chart(viz.plot_frame_detections(fb, single, truth,
                                                      title="Frame B only - stars dominate"),
                            width="stretch")
        with tabs[2]:
            cc = st.columns(2)
            cc[0].plotly_chart(viz.plot_frame_detections(fa, None, None, height=340,
                                                         title="Frame A"),
                               width="stretch")
            cc[1].plotly_chart(viz.plot_frame_detections(fb, None, None, height=340,
                                                         title="Frame B"),
                               width="stretch")

    st.divider()
    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### Detector scoring")
        st.dataframe(_df([{"input": "single frame", **m_single},
                          {"input": "frame difference", **m_pair}]),
                     width="stretch", hide_index=True)
    with right:
        st.markdown("#### Pixels to physics")
        _note(
            "What the propagator needs from a detection is a <strong>ballistic coefficient</strong>, "
            "not a bounding box. Size gives area through the NASA breakup model's area-length "
            "law; mass comes from <em>sampling</em> the model's empirical A/M distribution, "
            "because a single image cannot determine mass - so the uncertainty is carried "
            "forward honestly rather than replaced by a point value."
        )
        objs = detections_to_objects(
            paired, range_m=float(rng_m), camera=Camera(),
            rng=int(seed), size_from="angular" if sizing.startswith("angular") else "photometric")
        if objs:
            st.dataframe(_df([{
                "name": o.name, "Lc [cm]": 100 * o.characteristic_length,
                "area [m2]": o.area, "mass [kg]": o.mass,
                "A/M [m2/kg]": o.area_to_mass,
                "B [kg/m2]": o.ballistic_coefficient(), "shape": o.drag.shape,
            } for o in objs[:20]]), width="stretch", hide_index=True)
        else:
            st.info("No detections at this threshold.")
    _provenance(
        "Detector and difference-imaging pipeline are real algorithms. Frames are a "
        "physically-motivated simulator, not real sensor data, so scores establish that the "
        "pipeline behaves as specified - not that it transfers to a real sensor."
    )


# ==================================================================== fall prediction
@st.cache_data(show_spinner=False)
def _single_object_prediction(lat, lon, alt_km, speed, fpa, az, mass, area, shape, material,
                              n_samples, bc_sigma, dens_sigma, wind_e, wind_n, seed):
    state = StateVector.from_geodetic(lat, lon, alt_km * 1000.0, speed, fpa, az)
    obj = DebrisObject("object", mass=mass, area=area,
                       drag=DragModel(shape, reference_length=float(np.sqrt(area))),
                       material=material)
    traj = propagate(state, obj, store_trajectory=True)
    cfg = DispersionConfig(n_samples=int(n_samples), bc_sigma_log10=bc_sigma,
                           density_sigma_log10=dens_sigma, wind_zonal=wind_e,
                           wind_meridional=wind_n, seed=int(seed))
    fp = run_dispersion(state, obj, cfg)
    return traj, fp, obj


@st.cache_data(show_spinner=False)
def _cloud_prediction(lat, lon, alt_km, speed, fpa, az, parent_mass, breakup, parent,
                      max_frag, per_frag, bc_sigma, wind_e, wind_n, seed):
    state = StateVector.from_geodetic(lat, lon, alt_km * 1000.0, speed, fpa, az)
    cloud = generate_debris_cloud(
        state, parent_mass=parent_mass, breakup=BreakupType(breakup),
        parent=ParentType(parent), max_fragments=int(max_frag), rng=int(seed))
    cfg = DispersionConfig(bc_sigma_log10=bc_sigma, wind_zonal=wind_e,
                           wind_meridional=wind_n, seed=int(seed))
    fp = run_cloud_dispersion(cloud, cfg, samples_per_fragment=int(per_frag))
    return cloud, fp


def page_fall_prediction():
    _header("Debris Fall Prediction")
    _note(
        "3-DOF re-entry propagation in the rotating ECEF frame with J2 gravity, Mach- and "
        "Knudsen-dependent drag, winds, and a coupled aerothermal demise model so objects that "
        "burn up simply never produce an impact point. Two independently written "
        "implementations of this physics agree to <strong>0.15 m</strong> on impact position."
    )
    mode = st.radio("Scenario", ["Single object", "Fragment cloud (breakup)"], horizontal=True)

    c = st.columns([1, 3])
    with c[0]:
        st.markdown("**Entry state**")
        lat = st.number_input("Latitude [deg]", -85.0, 85.0, 13.72)
        lon = st.number_input("Longitude [deg]", -180.0, 180.0, 80.23)
        alt_km = st.slider("Breakup / entry altitude [km]", 40.0, 140.0, 78.0)
        speed = st.slider("Earth-relative speed [m/s]", 500, 8200, 7300, step=50)
        fpa = st.slider("Flight-path angle [deg]", -20.0, 0.0, -1.5, step=0.1)
        az = st.slider("Azimuth [deg]", 0.0, 360.0, 140.0)
        st.markdown("**Uncertainty**")
        bc_sigma = st.slider("B spread [decades]", 0.0, 0.5, 0.15, step=0.01)
        wind_e = st.slider("Peak zonal wind [m/s]", -60.0, 60.0, 20.0)
        wind_n = st.slider("Peak meridional wind [m/s]", -60.0, 60.0, -5.0)
        seed = st.slider("Seed", 0, 100, 42)

    if mode == "Single object":
        with c[0]:
            st.markdown("**Object**")
            mass = st.number_input("Mass [kg]", 0.1, 40_000.0, 200.0)
            area = st.number_input("Avg cross-section [m2]", 0.001, 80.0, 0.15, format="%.4f")
            shape = st.selectbox("Shape", ["tumbling", "sphere", "cylinder", "box", "flat_plate"])
            material = st.selectbox("Material",
                                    ["stainless_steel", "titanium", "aluminium_oxidised",
                                     "inconel", "cfrp", "silica", "mli", "copper"])
            n_samples = st.slider("Monte Carlo samples", 100, 2000, 600, step=100)
        traj, fp, obj = _single_object_prediction(
            lat, lon, alt_km, float(speed), fpa, az, mass, area, shape, material,
            n_samples, bc_sigma, 0.06, wind_e, wind_n, seed)
        cloud = None
    else:
        with c[0]:
            st.markdown("**Breakup**")
            parent_mass = st.number_input("Parent mass [kg]", 10.0, 20_000.0, 1800.0)
            breakup = st.selectbox("Breakup type", [b.value for b in BreakupType], index=2)
            parent = st.selectbox("Parent type", [p.value for p in ParentType])
            max_frag = st.slider("Max fragments", 20, 400, 150, step=10)
            per_frag = st.slider("MC samples per fragment", 1, 8, 3)
        cloud, fp = _cloud_prediction(lat, lon, alt_km, float(speed), fpa, az, parent_mass,
                                      breakup, parent, max_frag, per_frag, bc_sigma,
                                      wind_e, wind_n, seed)
        traj, obj = None, None

    stats = fp.statistics()
    z95 = density_zone(fp, 0.05)
    z99 = mahalanobis_zone(fp, 0.01)
    pop = SyntheticPopulationModel()
    risk = assess_footprint(fp, pop)

    with c[1]:
        _metrics([
            ("Impacts", f"{fp.n_impacted} / {fp.n_requested}",
             f"{fp.n_demised} demised"),
            ("Mean downrange", f"{stats['downrange_mean_km']:.0f} km",
             f"±{stats['downrange_std_km']:.0f} km"),
            ("95% zone area", f"{z95.area_km2:,.0f} km²"),
            ("Expected casualties", f"{risk.expected_casualties:.2e}", risk.risk_band),
        ])
        st.plotly_chart(viz.plot_impact_map(fp, [z95, z99]), width="stretch")

    tabs = st.tabs(["Dispersion", "Footprint vs B", "Trajectory profiles", "3-D re-entry",
                    "Ground risk", "Fragment cloud"])
    with tabs[0]:
        st.plotly_chart(viz.plot_dispersion(fp, [z95, z99], density_zone=z95),
                        width="stretch")
        _note(
            "Downrange spread is driven by the ballistic coefficient; crossrange spread by wind "
            "and azimuth error. Separating them on orthogonal axes shows immediately which "
            "uncertainty dominates."
        )
    with tabs[1]:
        st.plotly_chart(viz.plot_footprint_by_bc(fp), width="stretch")
    with tabs[2]:
        if traj is not None and traj.t.size > 1:
            st.plotly_chart(viz.plot_trajectory_profiles(traj), width="stretch")
            s = traj.summary()
            _metrics([("Peak deceleration", f"{s['peak_decel_g']:.1f} g"),
                      ("Peak heat flux", f"{s['peak_heat_flux_kW_m2']:.0f} kW/m²"),
                      ("Peak dynamic pressure", f"{s['peak_q_kPa']:.1f} kPa"),
                      ("Mass remaining", f"{s['mass_remaining_frac']*100:.1f} %"),
                      ("Fall time", f"{s['fall_time_s']:.0f} s")])
        else:
            st.info("Nominal trajectory profiles are shown for the single-object scenario.")
    with tabs[3]:
        if traj is not None and traj.t.size > 1:
            st.plotly_chart(viz.plot_reentry_3d([traj]), width="stretch")
        else:
            st.info("3-D view is shown for the single-object scenario.")
    with tabs[4]:
        zp = zone_population(z95, fp, pop)
        _metrics([
            ("Land impact probability", f"{risk.land_impact_probability:.1%}"),
            ("Casualty-capable fragments", f"{risk.n_casualty_capable}"),
            ("Population in 95% zone", f"{zp['population']/1e6:.3f} M"),
            ("Nearest city", f"{risk.nearest_city}", f"{risk.nearest_city_km:.0f} km"),
        ])
        st.dataframe(_kv(risk.summary()), width="stretch", hide_index=True)
        _provenance(risk.provenance)
    with tabs[5]:
        if cloud is not None:
            _metrics([("Fragments", f"{len(cloud)}"),
                      ("Mass closure", f"{cloud.mass_closure*100:.0f} %"),
                      ("Remnant bodies", f"{cloud.metadata['n_remnants']}"),
                      ("B range", f"{cloud.ballistic_coefficients.min():.1f} – "
                                  f"{cloud.ballistic_coefficients.max():.0f}")])
            cc = st.columns(2)
            cc[0].plotly_chart(viz.plot_size_distribution(cloud), width="stretch")
            cc[1].plotly_chart(viz.plot_cloud_properties(cloud), width="stretch")
            _note(
                "The NASA model's size distribution accounts for only 10-20 % of a satellite's "
                "mass over a metre-scale band. The balance is assigned to a few compact "
                "<strong>remnant</strong> bodies, because in reality that mass sits in a "
                "handful of large pieces - a propulsion module, a tank - and those are exactly "
                "the objects that survive re-entry and arrive with megajoules of energy."
            )
        else:
            st.info("Select the fragment-cloud scenario to see breakup statistics.")


# ======================================================================= conformal zones
@st.cache_data(show_spinner=False)
def _conformal_experiment(alt_km, parent_mass, max_frag, per_frag, alpha, seed, n_splits):
    from debris import Footprint

    state = StateVector.from_geodetic(13.72, 80.23, alt_km * 1000.0, 7300.0, -2.0, 140.0)
    cloud = generate_debris_cloud(state, parent_mass=parent_mass,
                                 breakup=BreakupType.AERODYNAMIC,
                                 max_fragments=int(max_frag), rng=int(seed))
    fp = run_cloud_dispersion(cloud, DispersionConfig(seed=int(seed), wind_zonal=20.0),
                              samples_per_fragment=int(per_frag))
    comparison = zone_comparison(fp, alpha)

    def sub(idx):
        return Footprint(
            latitude=fp.latitude[idx], longitude=fp.longitude[idx],
            impact_time=fp.impact_time[idx], impact_speed=fp.impact_speed[idx],
            impact_mass=fp.impact_mass[idx], impact_energy=fp.impact_energy[idx],
            ballistic_coefficient=fp.ballistic_coefficient[idx],
            downrange=fp.downrange[idx], crossrange=fp.crossrange[idx],
            origin_latitude=fp.origin_latitude, origin_longitude=fp.origin_longitude,
            reference_azimuth=fp.reference_azimuth, n_requested=len(idx),
            n_impacted=len(idx), n_demised=0, n_other=0)

    from debris import chi2_quantile_2dof

    rng = np.random.default_rng(0)
    rows = []
    for _ in range(int(n_splits)):
        perm = rng.permutation(fp.n_impacted)
        half = fp.n_impacted // 2
        cal, test = sub(perm[:half]), sub(perm[half:])
        mz, dz = mahalanobis_zone(cal, alpha), density_zone(cal, alpha)
        x = np.stack([cal.downrange, cal.crossrange])
        centre, cov = np.mean(x, axis=1), np.cov(x)
        dev = np.stack([test.downrange, test.crossrange]) - centre[:, None]
        chi2 = chi2_quantile_2dof(1 - alpha)
        vals = np.maximum(np.linalg.eigvalsh(cov), 0.0)
        rows.append({
            "gauss_cov": float(np.mean(np.einsum("ij,jk,ik->i", dev.T,
                                                 np.linalg.pinv(cov), dev.T) <= chi2)),
            "gauss_area": float(np.pi * chi2 * np.sqrt(vals[0] * vals[1]) / 1e6),
            "maha_cov": float(np.mean(mz.contains(test.downrange, test.crossrange))),
            "maha_area": mz.area_km2,
            "dens_cov": float(np.mean(dz.contains(test.downrange, test.crossrange))),
            "dens_area": dz.area_km2,
        })
    return fp, comparison, _df(rows).mean().to_dict(), cloud


def page_conformal():
    _header("Conformal Prediction Zones")
    _note(
        "The usual impact region is a mean point plus a Gaussian ellipse sized by the "
        "chi-squared quantile. For a <em>single</em> object with moderate uncertainty that is "
        "fine. For a <strong>fragment cloud</strong> it is not: ballistic coefficients spanning "
        "two decades produce a skewed, long-tailed, effectively multi-modal footprint, and the "
        "chi-squared ellipse then under-covers - it claims 99 % and delivers about 97 %. "
        "A conformal zone sizes the region from the empirical quantile of a nonconformity "
        "score instead, which holds coverage with no distributional assumption at all."
    )
    c = st.columns([1, 3])
    with c[0]:
        alt_km = st.slider("Breakup altitude [km]", 60.0, 100.0, 78.0)
        parent_mass = st.number_input("Parent mass [kg]", 100.0, 8000.0, 1800.0)
        max_frag = st.slider("Fragments", 50, 300, 200, step=10)
        per_frag = st.slider("MC per fragment", 2, 8, 5)
        alpha = st.select_slider("alpha (miss rate)", [0.20, 0.10, 0.05, 0.01], 0.05)
        n_splits = st.slider("Validation splits", 5, 60, 25, step=5)
        seed = st.slider("Seed", 0, 50, 7)

    fp, comparison, avg, cloud = _conformal_experiment(
        alt_km, parent_mass, max_frag, per_frag, alpha, seed, n_splits)
    nominal = 1.0 - alpha

    with c[1]:
        under = avg["gauss_cov"] < nominal - 0.005
        _metrics([
            ("Nominal coverage", f"{nominal:.0%}"),
            ("Gaussian χ²", f"{avg['gauss_cov']:.4f}",
             "UNDER-COVERS" if under else "ok"),
            ("Conformal (Mahalanobis)", f"{avg['maha_cov']:.4f}"),
            ("Conformal (density)", f"{avg['dens_cov']:.4f}"),
        ])
        st.plotly_chart(viz.plot_coverage_comparison(comparison), width="stretch")

    st.markdown(f"#### Held-out coverage, averaged over {n_splits} calibration/test splits")
    st.dataframe(_df([{
        "region": "Gaussian chi-squared ellipse", "coverage": avg["gauss_cov"],
        "area [km2]": avg["gauss_area"], "meets nominal": avg["gauss_cov"] >= nominal - 0.005},
        {"region": "Conformal - Mahalanobis score", "coverage": avg["maha_cov"],
         "area [km2]": avg["maha_area"], "meets nominal": avg["maha_cov"] >= nominal - 0.005},
        {"region": "Conformal - KDE highest-density", "coverage": avg["dens_cov"],
         "area [km2]": avg["dens_area"], "meets nominal": avg["dens_cov"] >= nominal - 0.005},
    ]), width="stretch", hide_index=True)

    ratio = avg["dens_area"] / max(avg["gauss_area"], 1e-9)
    st.success(
        f"The density-based conformal zone holds {avg['dens_cov']:.4f} "
        f"coverage against a nominal {nominal:.0%} in {avg['dens_area']:,.0f} km² - "
        f"{ratio:.2f}x the area of the chi-squared ellipse, which itself only reaches "
        f"{avg['gauss_cov']:.4f}. Better coverage and a smaller region at the same time."
    )
    _note(
        "Scope of the guarantee: coverage is exact under <em>exchangeability with the "
        "calibration ensemble</em>. It does not certify away model bias (a wrong drag law, a "
        "wrong breakup altitude), and calibrating on one sampled fragment cloud then testing on "
        "a different one degrades it - that is distribution shift, and it is the honest limit of "
        "what ensemble calibration can promise. For coverage over real events you need "
        "historical predicted-versus-actual residuals, which "
        "<code>conformalise_with_history</code> consumes."
    )
    cc = st.columns(2)
    cc[0].plotly_chart(viz.plot_dispersion(fp, [comparison["zones"]["mahalanobis"],
                                                comparison["zones"]["density"]],
                                           density_zone=comparison["zones"]["density"]),
                       width="stretch")
    cc[1].plotly_chart(viz.plot_impact_map(fp, [comparison["zones"]["density"],
                                                comparison["zones"]["mahalanobis"]]),
                       width="stretch")


# ========================================================================= launch pages
@st.cache_data(show_spinner=False)
def _launch_drop_zones(vehicle_key, site_key, azimuth, n_samples, wind_e, wind_n, seed,
                       speed_factor):
    from debris.launch import with_scaled_performance

    vehicle = LAUNCH_VEHICLES[vehicle_key]
    if abs(speed_factor - 1.0) > 1e-6:
        vehicle = with_scaled_performance(vehicle, speed_factor=speed_factor)
    site = LAUNCH_SITES[site_key]
    profile = ascent_profile(vehicle, site, azimuth)
    seps = separation_states(vehicle, site, azimuth)

    results, rows = [], []
    for ev, state, objs in seps:
        obj = objs[0]
        cfg = DispersionConfig(n_samples=int(n_samples), bc_sigma_log10=0.12,
                               wind_zonal=wind_e, wind_meridional=wind_n, seed=int(seed))
        fp = run_dispersion(state, obj, cfg)
        if fp.n_impacted == 0:
            continue
        zone = mahalanobis_zone(fp, 0.05)
        results.append((ev.name, fp, zone))
        s = fp.statistics()
        mlat, mlon = fp.mean_point
        rows.append({
            "event": ev.name, "count": ev.count, "t_sep [s]": ev.time,
            "sep alt [km]": ev.altitude / 1000, "sep speed [m/s]": ev.speed,
            "mass each [kg]": ev.dry_mass, "B [kg/m2]": obj.ballistic_coefficient(),
            "impact lat": mlat, "impact lon": mlon,
            "downrange [km]": s["downrange_mean_km"],
            "fall time [s]": s["fall_time_median_s"],
            "95% zone [km2]": zone.area_km2,
            "impact speed [m/s]": s["impact_speed_median_ms"],
        })
    return profile, seps, results, _df(rows)


def page_launch():
    _header("Launch Drop Zones - scheduled debris")
    _note(
        "Most falling launch debris is not a failure, it is scheduled. Every orbital launch "
        "drops strap-on boosters, a first stage, a payload fairing and usually an interstage, "
        "each on its own suborbital arc. The ascent here is <strong>kinematic</strong>: it "
        "interpolates through the vehicle's published separation conditions rather than "
        "integrating thrust and mass flow, so it cannot drift away from the quoted numbers, "
        "but it also does not model dog-legs or throttle-down."
    )
    c = st.columns([1, 3])
    with c[0]:
        vkey = st.selectbox("Launch vehicle", list(LAUNCH_VEHICLES),
                            format_func=lambda k: LAUNCH_VEHICLES[k].name)
        skey = st.selectbox("Launch site", list(LAUNCH_SITES),
                            format_func=lambda k: LAUNCH_SITES[k].name)
        site = LAUNCH_SITES[skey]
        az = st.slider("Launch azimuth [deg]", 0.0, 360.0, float(site.default_azimuth))
        n_samples = st.slider("MC samples per item", 100, 1200, 400, step=100)
        wind_e = st.slider("Peak zonal wind [m/s]", -60.0, 60.0, 15.0)
        wind_n = st.slider("Peak meridional wind [m/s]", -60.0, 60.0, 0.0)
        under = st.slider("First-stage performance factor", 0.85, 1.05, 1.00, step=0.01,
                          help="Under-performance is a classic way scheduled debris ends up "
                               "outside its cleared drop zone.")
        seed = st.slider("Seed", 0, 60, 42)

    vehicle = LAUNCH_VEHICLES[vkey]
    profile, seps, results, table = _launch_drop_zones(
        vkey, skey, az, n_samples, wind_e, wind_n, seed, under)

    with c[1]:
        _metrics([
            ("Jettisoned items", f"{vehicle.total_falling_items}"),
            ("Falling mass", f"{vehicle.total_falling_mass/1000:.1f} t"),
            ("Drop zones", f"{len(results)}"),
            ("Site", site.country),
        ])
        st.plotly_chart(viz.plot_drop_zones(results), width="stretch")

    tabs = st.tabs(["Drop-zone table", "Ascent profile", "Vehicle definition"])
    with tabs[0]:
        st.dataframe(table, width="stretch", hide_index=True)
        _note(
            "Note the ordering: the payload fairing has a low ballistic coefficient and lands "
            "<em>closer</em> than the much heavier first stage despite separating later and "
            "faster. Ballistic coefficient, not separation energy, sets downrange distance."
        )
    with tabs[1]:
        st.plotly_chart(viz.plot_ascent_profile(profile, seps), width="stretch")
    with tabs[2]:
        st.dataframe(_df([{
            "event": e.name, "count": e.count, "t [s]": e.time,
            "alt [km]": e.altitude / 1000, "speed [m/s]": e.speed,
            "fpa [deg]": e.flight_path_angle, "dry mass [kg]": e.dry_mass,
            "area [m2]": e.area, "shape": e.shape, "material": e.material,
            "reaches orbit": e.reaches_orbit,
        } for e in vehicle.events]), width="stretch", hide_index=True)
        st.caption(vehicle.notes)
    _provenance(
        "Vehicle masses, separation conditions and tumbling cross-sections are representative "
        "public-domain estimates assembled for demonstration, not vendor data. Every value is "
        "an overridable field on the StageEvent dataclass."
    )


# ============================================================== anomaly -> debris fusion
@st.cache_data(show_spinner=False)
def _coupled(anomaly, severities_tuple, lat, lon, speed, fpa, az, parent_mass,
             max_frag, per_frag, wind_e, wind_n, seed):
    health = SubsystemHealth(dict(severities_tuple))
    return run_coupled_prediction(
        anomaly, health, latitude=lat, longitude=lon, entry_speed=speed,
        flight_path_angle=fpa, azimuth=az, parent_mass=parent_mass,
        max_fragments=int(max_frag), n_samples_per_fragment=int(per_frag),
        wind_zonal=wind_e, wind_meridional=wind_n, seed=int(seed))


def page_fusion(dashboard_health: dict | None = None):
    _header("Anomaly → Debris Fusion")
    _note(
        "This is the link that makes the twin one system rather than two dashboards. "
        "<strong>Which</strong> subsystem is failing changes the physics of the breakup, not "
        "only its probability: propulsion drives an energetic rupture with hundreds of m/s of "
        "ejection velocity, thermal loss reduces structural margin so the vehicle comes apart "
        "higher, and attitude loss means tumbling - which raises the breakup altitude and makes "
        "the ballistic coefficient far less predictable. Communication and data-storage failures "
        "change none of the physics; they degrade <em>observability</em>, which enters as "
        "inflated state uncertainty. That distinction is the difference between 'more dangerous' "
        "and 'less well known'."
    )

    c = st.columns([1, 3])
    with c[0]:
        anomaly = st.slider("Telemetry anomaly score", 0.0, 1.0, 0.85, step=0.01,
                            help="The twin's detector output: autoencoder reconstruction error, "
                                 "CNN class probability, or LSTM forecast residual.")
        use_dash = st.checkbox("Use health from the live twin", value=bool(dashboard_health))
        st.markdown("**Subsystem severity** (0 nominal → 1 failed)")
        sev = {}
        for name in SUBSYSTEM_ORDER:
            default = 0.05
            if use_dash and dashboard_health and name in dashboard_health:
                v = dashboard_health[name]
                default = float(v[0] if isinstance(v, (tuple, list)) else v)
            sev[name] = st.slider(name, 0.0, 1.0, float(np.clip(default, 0.0, 1.0)),
                                  step=0.01, key=f"sev_{name}")
        st.markdown("**Scenario**")
        lat = st.number_input("Latitude [deg]", -85.0, 85.0, 13.72, key="fuse_lat")
        lon = st.number_input("Longitude [deg]", -180.0, 180.0, 80.23, key="fuse_lon")
        speed = st.slider("Entry speed [m/s]", 1000, 8000, 7400, step=100)
        fpa = st.slider("Flight-path angle [deg]", -15.0, 0.0, -1.5, step=0.1, key="fuse_fpa")
        az = st.slider("Azimuth [deg]", 0.0, 360.0, 140.0, key="fuse_az")
        parent_mass = st.number_input("Satellite mass [kg]", 50.0, 12000.0, 1800.0)
        max_frag = st.slider("Max fragments", 20, 250, 100, step=10, key="fuse_frag")
        per_frag = st.slider("MC per fragment", 1, 6, 3, key="fuse_mc")
        wind_e = st.slider("Zonal wind [m/s]", -60.0, 60.0, 15.0, key="fuse_we")
        wind_n = st.slider("Meridional wind [m/s]", -60.0, 60.0, 0.0, key="fuse_wn")

    result = _coupled(anomaly, tuple(sorted(sev.items())), lat, lon, float(speed), fpa, az,
                      parent_mass, max_frag, per_frag, wind_e, wind_n, 42)
    hz, fp, risk = result.hazard, result.footprint, result.risk
    z95 = result.zone_95

    with c[1]:
        _metrics([
            ("P(fragmentation)", f"{hz.fragmentation_probability:.3f}", hz.hazard_band),
            ("Breakup altitude", f"{hz.breakup_altitude/1000:.1f} km", hz.breakup_type.value),
            ("E_c conditional", f"{risk.expected_casualties:.2e}", risk.risk_band),
            ("E_c risk-weighted", f"{result.risk_weighted_casualties:.2e}",
             "vs 1e-4 gate"),
        ])
        st.plotly_chart(viz.plot_impact_map(fp, [z95, result.zone_99]),
                        width="stretch")

    tabs = st.tabs(["Why this hazard", "Dispersion", "Reverse: detections → health",
                    "Predictive fault", "Full summary"])
    with tabs[0]:
        st.markdown("#### Reasoning trace")
        for line in hz.rationale:
            st.markdown(f"- {line}")
        st.dataframe(_kv(hz.summary()), width="stretch", hide_index=True)
        _note(
            "These mappings are <strong>stated hypotheses, not fitted models</strong>. There is "
            "no labelled corpus of satellite breakups to fit against, and presenting a guess as "
            "a learned relationship would be worse than being explicit about it. The logistic "
            "is calibrated so a nominal satellite reads about 1 % - consistent with a handful of "
            "fragmentation events per year across thousands of orbiting objects - and so no "
            "single subsystem alone reaches certainty, because fragmentation needs both an "
            "energy source and a trigger."
        )
    with tabs[1]:
        st.plotly_chart(viz.plot_dispersion(fp, [z95], density_zone=z95),
                        width="stretch")
        st.plotly_chart(viz.plot_footprint_by_bc(fp), width="stretch")
    with tabs[2]:
        st.markdown("#### Debris observation updates health")
        _note(
            "The loop also closes the other way. A satellite can shed insulation while reporting "
            "nominal on every telemetry channel, so a visual detection of separated material is "
            "physical evidence that should move the assessment on its own. Attribution is by "
            "fragment size: centimetre flecks read as blanket or paint loss, decimetre pieces as "
            "structural or array failure."
        )
        cc = st.columns([1, 2])
        with cc[0]:
            n_det = st.slider("Fragments detected", 0, 30, 6)
            conf = st.slider("Mean detector confidence", 0.0, 1.0, 0.85)
            largest = st.slider("Largest fragment [cm]", 1.0, 80.0, 15.0)
            frames = st.slider("Frames observed", 1, 40, 5)
        ev = debris_evidence_to_health(n_det, conf, largest / 100.0, frame_count=frames)
        with cc[1]:
            st.metric("Anomaly score boost", f"+{ev.anomaly_boost:.3f}",
                      f"{anomaly:.2f} → {min(anomaly + ev.anomaly_boost, 1.0):.2f}")
            st.info(ev.interpretation)
            if ev.health_penalties:
                st.dataframe(_df([{"subsystem": k, "severity penalty": v}
                                  for k, v in ev.health_penalties.items()]),
                             width="stretch", hide_index=True)
                updated = ev.apply(SubsystemHealth(dict(sev)))
                new_hz = assess_breakup_hazard(min(anomaly + ev.anomaly_boost, 1.0), updated)
                st.metric("Revised P(fragmentation)",
                          f"{new_hz.fragmentation_probability:.3f}",
                          f"{new_hz.fragmentation_probability - hz.fragmentation_probability:+.3f}")
    with tabs[3]:
        st.markdown("#### Extrapolating a degradation trend")
        cc = st.columns([1, 2])
        with cc[0]:
            growth = st.slider("Trend growth rate [per sample]", -0.02, 0.06, 0.02, step=0.002)
            noise = st.slider("Noise level", 0.01, 0.5, 0.15, step=0.01)
            n_pts = st.slider("History length [samples]", 20, 400, 120, step=10)
            dt_s = st.number_input("Sample interval [s]", 1.0, 600.0, 60.0)
        rng = np.random.default_rng(0)
        t = np.arange(int(n_pts))
        series = np.abs(0.02 * np.exp(growth * t) * (1 + noise * rng.normal(size=int(n_pts))))
        f = estimate_time_to_breakup(series, dt=float(dt_s))
        with cc[1]:
            st.metric("Trend", f.trend,
                      "credible" if f.credible else "not credible (poor fit)")
            if np.isfinite(f.time_to_threshold):
                st.metric("Time to threshold", f"{f.time_to_threshold/3600:.2f} h",
                          f"95% CI {f.confidence_low/3600:.2f} – {f.confidence_high/3600:.2f} h")
            st.dataframe(_kv(f.summary()), width="stretch", hide_index=True)
            _note(
                "Fitted in <strong>log space</strong>: degradation processes - crack growth, "
                "capacity fade, thermal-runaway onset - are multiplicative, so a linear fit "
                "systematically under-predicts how soon a threshold is reached. A weak fit is "
                "reported as 'no significant trend' rather than dressed up as a countdown."
            )
    with tabs[4]:
        st.dataframe(_kv(result.summary()), width="stretch", hide_index=True)


# =============================================================================== kessler
@st.cache_data(show_spinner=False)
def _kessler(bin_width, intact_fraction, years, launch_rate, breakup_alt, breakup_frags,
             ref_area):
    shells = default_leo_shells(bin_width=bin_width, intact_fraction=intact_fraction)
    cascade = simulate_cascade(shells, years=years, launch_rate=launch_rate)
    contrib = breakup_contribution(breakup_alt, breakup_frags, reference_area_m2=ref_area)
    rows = [s.summary() for s in shells]
    alt_scan = [breakup_contribution(a, breakup_frags, reference_area_m2=ref_area).summary()
                for a in (350, 450, 550, 650, 750, 850, 950, 1050, 1250, 1450)]
    return shells, cascade, contrib, _df(rows), _df(alt_scan)


def page_kessler():
    _header("Kessler Cascade Risk Engine")
    _note(
        "A breakup has two consequences, and the dramatic one is not the ground risk. Fragments "
        "that stay in orbit raise the collision rate for everything at that altitude, and if "
        "collisions produce debris faster than drag removes it, the population runs away. "
        "The model tracks <strong>two species</strong> - intact objects and fragments - "
        "separately. Collapsing them would force the ~900 fragments from a collision to inherit "
        "the mass and cross-section of the satellites that made them, and a 200-year run then "
        "over-predicts growth by more than two orders of magnitude."
    )
    c = st.columns([1, 3])
    with c[0]:
        bin_width = st.select_slider("Shell width [km]", [50.0, 100.0, 200.0], 100.0)
        intact_frac = st.slider("Intact fraction of catalogue", 0.05, 0.6, 0.20, step=0.05)
        years = st.slider("Simulation horizon [years]", 25, 500, 200, step=25)
        launch_rate = st.slider("Launch rate [objects/year]", 0, 400, 0, step=10)
        st.markdown("**Breakup contribution**")
        breakup_alt = st.slider("Breakup altitude [km]", 300, 1500, 850, step=50)
        breakup_frags = st.slider("Fragments created", 50, 2000, 400, step=50)
        ref_area = st.number_input("Reference satellite area [m2]", 0.5, 100.0, 10.0)

    shells, cascade, contrib, table, alt_scan = _kessler(
        bin_width, intact_frac, float(years), float(launch_rate), float(breakup_alt),
        int(breakup_frags), float(ref_area))
    worst = max(shells, key=lambda s: s.criticality())

    with c[1]:
        cs = cascade.summary()
        _metrics([
            ("Worst shell", f"{worst.alt_mid:.0f} km", worst.stability()),
            ("Max criticality", f"{cs['max_criticality_initial']:.2f}"),
            (f"Population in {years} yr", f"{cs['final_population']:,}",
             f"×{cs['growth_factor']:.2f}"),
            ("Catastrophic collisions", f"{cs['total_collisions']:.1f}"),
        ])
        st.plotly_chart(viz.plot_kessler_shells(shells), width="stretch")

    tabs = st.tabs(["Cascade simulation", "Breakup contribution", "Shell table"])
    with tabs[0]:
        st.plotly_chart(viz.plot_cascade(cascade), width="stretch")
        _metrics([("Intact objects", f"{cs['initial_intact']:,} → {cs['final_intact']:,}"),
                  ("Cascade onset", f"{cs['cascade_onset_year']:.0f} yr"
                   if cascade.cascading else "not triggered"),
                  ("Worst final shell", f"{cs['worst_shell_alt_km']:.0f} km")])
        _note(
            "Integrated with an exponential-Euler scheme because drag lifetimes span 0.03 years "
            "at 200 km to 60 000 years at 1500 km - any explicit scheme with a step large enough "
            "to reach a 200-year horizon is violently unstable on the low shells. Fragment counts "
            "are bounded by mass conservation, since collisions redistribute mass rather than "
            "creating it."
        )
    with tabs[1]:
        d = contrib.summary()
        _metrics([
            ("Added collision probability", f"{d['added_collision_probability']:.3e}",
             "per reference satellite, over the debris lifetime"),
            ("Fragment lifetime", f"{d['fragment_lifetime_years']:.0f} yr"),
            ("Debris-years added", f"{d['debris_years_added']:.2e}"),
            ("Collision-rate increase", f"{d['rate_increase_pct']:.1f} %"),
        ])
        st.plotly_chart(
            viz.plot_hazard_sensitivity(
                alt_scan.to_dict("records"), x_key="altitude_km",
                series=("added_collision_probability",)),
            width="stretch")
        ratio = (alt_scan["added_collision_probability"].iloc[-1]
                 / max(alt_scan["added_collision_probability"].iloc[0], 1e-30))
        st.success(
            f"The same {breakup_frags}-fragment breakup is **{ratio:,.0f}x worse** at 1450 km "
            f"than at 350 km, because drag clears the low-altitude debris in months and the "
            f"high-altitude debris in millennia. Any metric that counts only *how much* debris "
            f"was created gets this trade backwards."
        )
        st.dataframe(_kv(d), width="stretch", hide_index=True)
        _note(
            "<code>delta_criticality</code> is shown for completeness but is a poor headline "
            "number and can even be negative: criticality is a ratio of production to removal, "
            "and injected fragments have high area-to-mass, so they raise drag removal faster "
            "than production. <strong>Added collision probability</strong> is the number to "
            "quote - absolute, monotone in fragments added, and correctly altitude-weighted."
        )
    with tabs[2]:
        st.dataframe(table, width="stretch", hide_index=True)
    _provenance(
        "Spatial densities and orbital lifetimes are representative published ORDEM/MASTER-class "
        "figures, not a live catalogue. This is an aggregate particle-in-a-box model: it does not "
        "propagate individual orbits or screen conjunctions, both of which real collision "
        "avoidance requires."
    )


# ====================================================================== circular economy
@st.cache_data(show_spinner=False)
def _sustainability(dry_mass, altitude, propellant, demisable, passivated, isp,
                    prop_type, launch_mass, frag_prob, exp_frags, budget, objective):
    profile = MissionProfile(
        name="mission", dry_mass=dry_mass, altitude=altitude,
        propellant_remaining=propellant, demisable_fraction=demisable,
        passivated=passivated, isp=isp, propellant_type=prop_type, launch_mass=launch_mass)
    assessment = assess_sustainability(profile, frag_prob, int(exp_frags))
    optimal = optimise_mitigation(assessment, budget=budget, objective=objective)
    greedy = greedy_mitigation(assessment, budget=budget)
    catalogue = build_action_catalogue(profile)
    alt_rows = compare_altitudes(profile)
    return profile, assessment, optimal, greedy, catalogue, _df(alt_rows)


def page_circular_economy():
    _header("Circular Economy - debris-years and mitigation")
    _note(
        "Orbital sustainability is usually discussed qualitatively. It does not have to be. "
        "<strong>Debris-years</strong> = objects left behind × their orbital lifetime captures "
        "both halves in one additive number, and it is proportional to the integrated collision "
        "probability a mission imposes on its shell. A hundred fragments at 400 km clear in "
        "about a year; the same hundred at 1400 km are in the way for five millennia."
    )
    c = st.columns([1, 3])
    with c[0]:
        dry_mass = st.number_input("Dry mass at EOL [kg]", 10.0, 12000.0, 1200.0)
        altitude = st.slider("Operational altitude [km]", 300, 1500, 800, step=25)
        propellant = st.number_input("Propellant remaining [kg]", 0.0, 500.0, 20.0)
        demisable = st.slider("Demisable mass fraction", 0.0, 1.0, 0.55, step=0.05)
        passivated = st.checkbox("Already passivated", value=False)
        isp = st.slider("Thruster Isp [s]", 150, 340, 220, step=10)
        prop_type = st.selectbox("Launch propellant",
                                 ["kerolox", "methalox", "hydrolox", "solid", "hypergolic"])
        launch_mass = st.number_input("Launch (wet) mass [kg]", 20.0, 20000.0, 1800.0)
        frag_prob = st.slider("P(fragmentation) if abandoned", 0.0, 1.0, 0.05, step=0.01)
        exp_frags = st.slider("Fragments if it fragments", 50, 2000, 300, step=50)
        budget = st.slider("Mitigation budget [cost units]", 1.0, 60.0, 10.0, step=1.0)
        objective = st.selectbox("Optimiser objective",
                                 ["debris_years", "efficiency", "carbon"])

    profile, assessment, optimal, greedy, catalogue, alt_rows = _sustainability(
        dry_mass, float(altitude), propellant, demisable, passivated, float(isp),
        prop_type, launch_mass, frag_prob, exp_frags, budget, objective)
    a = assessment.summary()
    o = optimal.summary()

    with c[1]:
        _metrics([
            ("Debris-years", f"{a['debris_years']:.2e}"),
            ("Natural lifetime", f"{a['natural_lifetime_years']:.0f} yr",
             "25-yr compliant" if a["compliant_25_year"] else "NOT compliant"),
            ("Δv available", f"{a['available_delta_v_ms']:.0f} m/s",
             f"need {a['delta_v_for_controlled_reentry_ms']:.0f} to re-enter"),
            ("Circularity index", f"{a['circularity_index']:.3f}"),
        ])
        _metrics([
            ("Best plan reduction", f"{o['reduction_pct']:.1f} %"),
            ("Plan cost", f"{o['total_cost_units']:.1f} units"),
            ("Propellant needed", f"{o['total_propellant_kg']:.1f} kg"),
            ("Carbon delta", f"{o['carbon_delta_tonnes']:+.1f} t"),
        ])
        st.markdown("**Selected actions:** " +
                    (", ".join(f"`{k}`" for k in o["actions"]) or "_none affordable_"))
        for n in optimal.notes:
            st.caption(n)

    tabs = st.tabs(["Optimiser vs greedy", "Action catalogue", "Altitude trade",
                    "Baseline assessment"])
    with tabs[0]:
        g = greedy.summary()
        st.dataframe(_df([
            {"selector": "exact (exhaustive over subsets)", **{k: o[k] for k in
             ("actions", "total_cost_units", "debris_years_avoided", "reduction_pct",
              "casualty_risk_multiplier")}},
            {"selector": "greedy (benefit per cost)", **{k: g[k] for k in
             ("actions", "total_cost_units", "debris_years_avoided", "reduction_pct",
              "casualty_risk_multiplier")}},
        ]), width="stretch", hide_index=True)
        gap = o["debris_years_avoided"] - g["debris_years_avoided"]
        if gap > 0:
            st.success(
                f"The exact optimiser avoids **{gap:.2e} more debris-years** than greedy at the "
                f"same budget. Greedy fails here because the actions interact: it takes a "
                f"controlled re-entry early, which then blocks the graveyard manoeuvre, and it "
                f"will select material recovery without the active removal it depends on.")
        else:
            st.info("At this budget greedy happens to match the exact optimum. Raise the budget "
                    "or add propellant to make the interactions bite.")
    with tabs[1]:
        st.dataframe(_df([{
            "key": x.key, "action": x.name, "cost units": x.cost_units,
            "propellant [kg]": x.propellant_kg, "carbon [kg]": x.carbon_kg,
            "debris-year reduction": x.debris_year_reduction,
            "casualty multiplier": x.casualty_risk_multiplier,
            "requires": ", ".join(x.requires) or "-",
            "conflicts": ", ".join(x.conflicts) or "-",
        } for x in catalogue]), width="stretch", hide_index=True)
        with st.expander("What each action actually does"):
            for x in catalogue:
                st.markdown(f"**{x.name}** — {x.description}")
    with tabs[2]:
        st.dataframe(alt_rows, width="stretch", hide_index=True)
        st.plotly_chart(
            viz.plot_hazard_sensitivity(alt_rows.to_dict("records"), x_key="altitude_km",
                                       series=("debris_years",)),
            width="stretch")
        st.success(
            "Debris-years span several orders of magnitude across LEO, so **where** a "
            "constellation flies dominates every other design decision about it.")
    with tabs[3]:
        st.dataframe(_kv(a), width="stretch", hide_index=True)
    _provenance(
        "Carbon factors cover direct propellant combustion only and exclude soot radiative "
        "forcing and stratospheric ozone loss, which for solid and kerosene motors can rival the "
        "CO2 term - so launches are under-charged here and comparisons between propellant types "
        "are more reliable than absolute totals. Cost units are an arbitrary common scale for the "
        "optimiser to trade against. Recyclability is potential, not existing practice."
    )


# ============================================================================== learning
@st.cache_data(show_spinner=False)
def _ml_dataset(regime: str, n: int, seed: int):
    from debris.ml_common import build_trajectory_dataset

    ds = build_trajectory_dataset(int(n), regime, seed=int(seed))
    return ds.split(0.8, seed=1)


@st.cache_resource(show_spinner=False)
def _ml_benchmark(regime: str, n: int, epochs: int, seed: int):
    from debris.apsgtt import benchmark_against_ridge

    tr, te = _ml_dataset(regime, n, seed)
    return benchmark_against_ridge(tr, te, epochs=int(epochs), seed=int(seed))


@st.cache_resource(show_spinner=False)
def _ml_continual(order: tuple, n: int, epochs: int, seed: int):
    from debris.continual import forgetting_report, run_continual_experiment

    exp = run_continual_experiment(list(order), n_samples=int(n), epochs=int(epochs),
                                   seed=int(seed))
    return exp, forgetting_report(exp)


@st.cache_resource(show_spinner=False)
def _ml_federated(clients: tuple, n: int, rounds: int, local_epochs: int, mu: float,
                  noise: float, seed: int):
    from debris.federated import (federated_report, heterogeneity_report,
                                  run_federated_experiment)

    exp = run_federated_experiment(list(clients), n_samples_per_client=int(n),
                                   rounds=int(rounds), local_epochs=int(local_epochs),
                                   fedprox_mu=float(mu), dp_noise=float(noise), seed=int(seed))
    return exp, federated_report(exp), heterogeneity_report(exp)


def page_learning():
    from debris.ml_common import REGIMES, RidgeSurrogate, torch_available

    _header("APSGTT-LoRA & the Learning Layer")
    have_torch = torch_available()
    _note(
        "A learned <strong>surrogate</strong> for the re-entry propagator. Given the short arc a "
        "tracking radar actually gets - the first quarter of the fall - it predicts time to "
        "impact and the impact point directly. The point is not accuracy for its own sake: the "
        "physics engine is already validated to 0.15 m. It is that a surrogate runs in "
        "microseconds instead of milliseconds and is differentiable, which is what makes "
        "continuous re-prediction against a live feed, or a very large fragment population, "
        "tractable. Because the physics engine generates the labels, training data is unlimited "
        "and there is nothing to overfit to."
    )
    if not have_torch:
        st.warning(
            "**torch is not installed**, so the neural models are unavailable. The numpy "
            "fallback — a tuned closed-form ridge surrogate — still runs, and it is also the "
            "baseline the neural models are measured against. Install with "
            "`pip install -r requirements-ml.txt`."
        )

    tabs = st.tabs(["Surrogate vs baseline", "LoRA adaptation", "Continual learning",
                    "Federated intelligence", "Architecture"])

    # ------------------------------------------------------------------ surrogate
    with tabs[0]:
        c = st.columns([1, 3])
        with c[0]:
            regime = st.selectbox("Regime", list(REGIMES),
                                  format_func=lambda k: REGIMES[k].name, key="ml_regime")
            n = st.select_slider("Dataset size", [200, 400, 800, 1600, 3200], 800, key="ml_n")
            epochs = st.slider("Epochs", 20, 200, 80, step=20, key="ml_ep")
            seed = st.slider("Seed", 0, 20, 0, key="ml_seed")
            go = st.button("Train and evaluate", key="ml_go")
        with c[1]:
            st.caption(REGIMES[regime].description)
            if not go:
                _note(
                    "Training runs on demand because it takes tens of seconds to a few minutes. "
                    "A <strong>predict-the-mean</strong> floor is always shown alongside: on a "
                    "narrow regime the mean is already a fair predictor, and a model that only "
                    "just beats it has learned very little however good its absolute error looks."
                )
            else:
                with st.spinner(f"Building {n} trajectories and training…"):
                    if have_torch:
                        r = _ml_benchmark(regime, n, epochs, seed)
                        rows = [
                            {"model": "predict the mean", "params": 0, **r["predict_mean"]},
                            {"model": f"ridge (alpha={r['ridge_alpha']:g})",
                             "params": r["ridge_parameters"], **r["ridge"]},
                            {"model": "APSGTT-LoRA", "params": r["apsgtt_parameters"],
                             **r["apsgtt"]},
                        ]
                    else:
                        tr, te = _ml_dataset(regime, n, seed)
                        ridge = RidgeSurrogate.tune(tr, seed=seed)
                        from debris.ml_common import surrogate_metrics
                        mean_pred = np.tile(tr.y.mean(axis=0), (len(te), 1))
                        rows = [
                            {"model": "predict the mean", "params": 0,
                             **surrogate_metrics(te.y, mean_pred)},
                            {"model": f"ridge (alpha={ridge.alpha:g})",
                             "params": ridge.n_parameters, **ridge.evaluate(te)},
                        ]
                keep = ["model", "params", "impact_median_error_km", "impact_p90_error_km",
                        "time_mae_s", "downrange_mae_km", "r2_downrange"]
                st.dataframe(_df([{k: row[k] for k in keep if k in row} for row in rows]),
                             width="stretch", hide_index=True)
                best = min(rows[1:], key=lambda r: r["impact_median_error_km"])
                st.success(f"Best model: **{best['model']}** at "
                           f"{best['impact_median_error_km']:.1f} km median impact error, "
                           f"against {rows[0]['impact_median_error_km']:.1f} km for the "
                           f"predict-the-mean floor.")
                if have_torch:
                    from debris.apsgtt import surrogate_speedup
                    tr, te = _ml_dataset(regime, n, seed)
                    sp = surrogate_speedup(r["model"], te)
                    _metrics([("Surrogate", f"{sp['surrogate_us_per_object']:.0f} µs/object"),
                              ("Physics propagator", f"{sp['physics_ms_per_object']:.2f} ms/object"),
                              ("Speed-up", f"{sp['speedup']:.0f}×")])

    # ---------------------------------------------------------------- LoRA adaptation
    with tabs[1]:
        _note(
            "The operational case for LoRA: adapt a model trained on one population to a new one "
            "- a new satellite class, a new launcher, a different solar-activity epoch - from few "
            "examples and without touching the base weights. Four conditions are compared, and "
            "the important one is <strong>target-only</strong>: adaptation is worth something only "
            "if it beats training from scratch on the same few target samples. Otherwise the base "
            "model contributed nothing and the honest recommendation is to skip it."
        )
        if not have_torch:
            st.info("Requires torch.")
        else:
            c = st.columns([1, 3])
            with c[0]:
                base_reg = st.selectbox("Base regime", list(REGIMES), index=0,
                                        format_func=lambda k: REGIMES[k].name, key="lora_base")
                tgt_reg = st.selectbox("Target regime", list(REGIMES), index=4,
                                       format_func=lambda k: REGIMES[k].name, key="lora_tgt")
                n_shot = st.select_slider("Target samples", [20, 50, 100, 200], 50, key="lora_shot")
                go_l = st.button("Run adaptation study", key="lora_go")
            with c[1]:
                if go_l:
                    if base_reg == tgt_reg:
                        st.warning("Pick different base and target regimes — adapting a model to "
                                   "its own training distribution measures nothing.")
                    else:
                        from debris.apsgtt import compare_adaptation
                        with st.spinner("Training base model, then three adaptation conditions…"):
                            btr, _bte = _ml_dataset(base_reg, 800, 0)
                            ttr, tte = _ml_dataset(tgt_reg, 400, 1)
                            out = compare_adaptation(btr, ttr, tte, epochs=60, adapt_epochs=50,
                                                     n_shot=int(n_shot), seed=0)
                        st.dataframe(_df([
                            {"condition": k.replace("_", " "),
                             "median error [km]": out[k]["impact_median_error_km"],
                             "p90 [km]": out[k]["impact_p90_error_km"],
                             "time MAE [s]": out[k]["time_mae_s"]}
                            for k in ("zero_shot", "lora", "full_finetune", "target_only")
                        ]), width="stretch", hide_index=True)
                        _metrics([
                            ("LoRA trainable params",
                             f"{out['lora_trainable_parameters']:,}",
                             f"{out['lora_trainable_fraction']*100:.1f}% of "
                             f"{out['total_parameters']:,}"),
                            ("Target samples", f"{out['n_target_samples']}"),
                        ])
                        lora_e = out["lora"]["impact_median_error_km"]
                        scratch_e = out["target_only"]["impact_median_error_km"]
                        if lora_e < scratch_e:
                            st.success(f"LoRA adaptation beats training on the target data alone "
                                       f"({lora_e:.1f} vs {scratch_e:.1f} km), so the base model "
                                       f"genuinely transferred.")
                        else:
                            st.warning(f"LoRA ({lora_e:.1f} km) does **not** beat training on the "
                                       f"target alone ({scratch_e:.1f} km) at this sample count. "
                                       f"The base model transferred nothing useful here — with "
                                       f"this much target data, train from scratch.")

    # ---------------------------------------------------------------- continual learning
    with tabs[2]:
        _note(
            "A deployed surrogate meets new populations over its life. Fine-tuning on only the "
            "new one is fast and destroys the old capability — <strong>catastrophic "
            "forgetting</strong>. Three strategies are compared against a <em>joint</em> upper "
            "bound that retains all past data (and so is not a continual method at all, but "
            "without it there is no way to tell whether a strategy closed the gap or merely "
            "narrowed it). The task order is chosen so consecutive tasks are dissimilar: "
            "forgetting is mild when tasks resemble each other, and a benign ordering would "
            "understate the problem."
        )
        c = st.columns([1, 3])
        with c[0]:
            n_c = st.select_slider("Samples per task", [150, 300, 600], 300, key="cl_n")
            ep_c = st.slider("Epochs per task", 10, 80, 30, step=10, key="cl_ep")
            go_c = st.button("Run continual experiment", key="cl_go")
        with c[1]:
            if go_c:
                from debris.continual import DEFAULT_TASK_ORDER
                with st.spinner("Training through the task sequence under each strategy…"):
                    exp, report = _ml_continual(tuple(DEFAULT_TASK_ORDER), n_c, ep_c, 0)
                st.dataframe(_df(report), width="stretch", hide_index=True)
                naive = exp["results"].get("naive")
                if naive is not None:
                    st.error(
                        f"Naive sequential fine-tuning ends with earlier tasks "
                        f"**{naive.forgetting_ratio:.1f}× worse** than when they were freshly "
                        f"learned ({naive.forgetting:+.0f} km of forgetting).")
                cols = st.columns(min(len(exp["results"]), 2))
                for i, r in enumerate(exp["results"].values()):
                    cols[i % len(cols)].plotly_chart(viz.plot_error_matrix(r),
                                                     width="stretch")
                st.caption(f"Backend: {exp['backend']}")

    # ------------------------------------------------------------------ federated
    with tabs[3]:
        _note(
            "The data needed to predict where debris lands sits with parties who will not pool "
            "it. Each party's slice is narrow — one vehicle family, one orbital regime — so a "
            "locally-trained model is good at its own regime and poor everywhere else, which is "
            "the wrong shape for a problem where the object falling on you was launched by "
            "someone else. Clients here are physically distinct regimes, i.e. strongly "
            "<strong>non-IID</strong>; random shards of one pool would make every method look "
            "equally good and prove nothing."
        )
        c = st.columns([1, 3])
        with c[0]:
            n_f = st.select_slider("Samples per client", [150, 300, 600], 300, key="fl_n")
            rounds = st.slider("Federated rounds", 2, 20, 8, key="fl_rounds")
            local_ep = st.slider("Local epochs / round", 1, 10, 4, key="fl_le")
            mu = st.slider("FedProx mu", 0.0, 0.5, 0.05, step=0.01, key="fl_mu")
            noise = st.slider("DP noise multiplier", 0.0, 1.5, 0.35, step=0.05, key="fl_dp")
            go_f = st.button("Run federated experiment", key="fl_go")
        with c[1]:
            if go_f:
                from debris.federated import DEFAULT_CLIENTS
                with st.spinner("Training local, centralised and three federated schemes…"):
                    exp, report, hetero = _ml_federated(tuple(DEFAULT_CLIENTS), n_f, rounds,
                                                        local_ep, mu, noise, 0)
                st.plotly_chart(viz.plot_federated_comparison(report), width="stretch")
                st.dataframe(_df(report), width="stretch", hide_index=True)
                fed = exp["results"].get("fedavg")
                central = exp["results"].get("centralised")
                locals_ = [r for k, r in exp["results"].items() if k.startswith("local:")]
                if fed and central and locals_:
                    best_local = min(r.global_error for r in locals_)
                    st.success(
                        f"FedAvg reaches **{fed.global_error:.1f} km** on the pooled test set "
                        f"against **{best_local:.1f} km** for the best single-client model and "
                        f"**{central.global_error:.1f} km** for the centralised upper bound — "
                        f"without any raw observation crossing an organisational boundary.")
                st.markdown("#### Per-client error of each scheme's global model")
                st.dataframe(_df(hetero), width="stretch", hide_index=True)
                _note(
                    "The failure this table exposes: a local model can be the <em>best</em> on its "
                    "own client and among the worst everywhere else, which a pooled average hides "
                    "entirely. Differential-privacy epsilon is a <strong>loose upper bound</strong> "
                    "from advanced composition; a Renyi-DP accountant gives a materially tighter "
                    "bound for the same noise."
                )
                st.caption(f"Backend: {exp['backend']}")

    # ------------------------------------------------------------------ architecture
    with tabs[4]:
        st.markdown("#### APSGTT-LoRA: what each component is for")
        st.markdown(
            "- **Graph** — the nine input channels are not an unordered bag. Altitude sets "
            "density, density scales drag, drag decelerates speed, ballistic coefficient "
            "multiplies every drag term. That coupling is *known* from the equations of motion, "
            "so it is supplied as a fixed adjacency rather than left for attention to rediscover "
            "from a few thousand trajectories.\n"
            "- **State-space** — a re-entry has a genuinely long-range dependency: the ballistic "
            "coefficient implied by the early deceleration determines the impact point minutes "
            "later. A diagonal state-space layer (S4D) gives each channel a learned exponential "
            "memory kernel over the whole window at O(L log L) cost. Its poles are "
            "parameterised as `-exp(·)`, so the layer cannot become unstable for any parameter "
            "value.\n"
            "- **Transformer** — self-attention over time for the content-dependent comparisons "
            "fixed kernels cannot make.\n"
            "- **Prognostic** — joint time-to-impact and impact-offset heads; one object's "
            "ballistic coefficient determines both.\n"
            "- **LoRA** — rank-*r* updates with the backbone frozen. Adapters start as an exact "
            "no-op (`B` initialised to zero), so adaptation begins from the base model's "
            "behaviour rather than a random perturbation of it."
        )
        st.markdown("#### Physics-derived channel adjacency")
        from debris.ml_common import FEATURES, physics_adjacency
        adj = physics_adjacency()
        st.dataframe(pd.DataFrame(adj, index=list(FEATURES), columns=list(FEATURES)).round(3),
                     width="stretch")
        _note(
            "Rows are row-normalised so the mixer averages neighbours rather than summing them — "
            "otherwise a channel's scale would depend on how many neighbours it happens to have. "
            "A learned gate lets the model down-weight the prior if the data disagrees, so the "
            "graph biases the model without hard-constraining it."
        )

"""
Plotly figures for the debris stack, styled to match the existing digital-twin dashboard.

Plotly is imported lazily inside each function, so the physics modules stay importable in an
environment without it (and so a headless batch run does not pay the import cost).

Design rules followed throughout, for consistency with the rest of the dashboard:

* Backgrounds are transparent; the page's own starfield shows through.
* One accent colour (cyan) carries the primary series; status uses green/amber/red only for
  genuine nominal/warning/critical semantics, never for decoration.
* Ballistic coefficient is encoded on a *sequential* scale, because it is a magnitude spanning
  decades - a categorical palette would imply unordered classes.
* Every axis is labelled with units.  A debris footprint plotted without units is unreadable.
"""

from __future__ import annotations

import math

import numpy as np

# ------------------------------------------------------------------------------- theme
BG = "#0a0e1a"
PANEL = "#0d1117"
GRID = "#1e3050"
MUTED = "#607090"
TEXT = "#c9d8f0"
ACCENT = "#00d4ff"
NOMINAL = "#2ECC71"
WARNING = "#F39C12"
CRITICAL = "#E74C3C"
SEQUENTIAL = "Viridis"

#: Colours by object provenance, so a mixed footprint stays readable.
ORIGIN_COLOURS = {
    "stage": "#F39C12",
    "fragment": ACCENT,
    "remnant": CRITICAL,
    "detected": "#A78BFA",
}


def _go():
    import plotly.graph_objects as go

    return go


def _layout(fig, title=None, height=420, legend=True):
    """Apply the shared dark theme."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=11),
        margin=dict(l=60, r=20, t=40 if title else 12, b=48),
        height=height,
        showlegend=legend,
        legend=dict(bgcolor="rgba(13,17,23,0.75)", bordercolor=GRID, borderwidth=1),
        hoverlabel=dict(bgcolor=PANEL, bordercolor=GRID, font=dict(color=TEXT)),
    )
    if title:
        fig.update_layout(title=dict(text=title, font=dict(color=ACCENT, size=14)))
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID,
                     tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID,
                     tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    return fig


# =========================================================================== trajectories
def plot_trajectory_profiles(trajectory, height: int = 460):
    """
    Altitude, speed, Mach, dynamic pressure, deceleration and heat flux against time.

    Six aligned panels rather than one busy axis: these quantities span many decades and peak
    at different moments, and the *ordering* of those peaks is the physically interesting part
    (peak heating precedes peak deceleration, which precedes peak dynamic pressure).
    """
    from plotly.subplots import make_subplots

    go = _go()
    t = trajectory.t
    if t.size < 2:
        return _layout(go.Figure(), "No trajectory samples stored", height)

    panels = [
        ("Altitude", trajectory.altitude / 1000.0, "km", ACCENT),
        ("Earth-relative speed", trajectory.speed / 1000.0, "km/s", "#5D9CEC"),
        ("Mach number", trajectory.mach, "-", "#A78BFA"),
        ("Dynamic pressure", trajectory.dynamic_pressure / 1000.0, "kPa", WARNING),
        ("Deceleration", trajectory.deceleration_g, "g", CRITICAL),
        ("Stagnation heat flux", trajectory.heat_flux / 1000.0, "kW/m^2", "#E8C547"),
    ]
    fig = make_subplots(rows=3, cols=2, subplot_titles=[p[0] for p in panels],
                        vertical_spacing=0.12, horizontal_spacing=0.10)
    for i, (name, y, unit, colour) in enumerate(panels):
        r, c = i // 2 + 1, i % 2 + 1
        fig.add_trace(go.Scatter(x=t, y=y, mode="lines", line=dict(color=colour, width=2),
                                 name=name, hovertemplate=f"%{{x:.1f}} s<br>%{{y:.3f}} {unit}<extra></extra>"),
                      row=r, col=c)
        fig.update_yaxes(title_text=unit, row=r, col=c)
        fig.update_xaxes(title_text="Time [s]" if r == 3 else None, row=r, col=c)
    for ann in fig.layout.annotations:
        ann.font.color = ACCENT
        ann.font.size = 11
    return _layout(fig, None, height, legend=False)


def plot_reentry_3d(trajectories, height: int = 480, globe_resolution: int = 48):
    """
    Trajectories over a globe, coloured by ballistic coefficient.

    The 3-D view earns its place here specifically because the eastward Coriolis curvature and
    the enormous spread between high- and low-B objects are both geometric facts that a 2-D
    ground track hides.
    """
    go = _go()
    fig = go.Figure()

    u = np.linspace(0, 2 * np.pi, globe_resolution)
    v = np.linspace(0, np.pi, globe_resolution)
    r_e = 6371.0
    fig.add_surface(
        x=r_e * np.outer(np.cos(u), np.sin(v)),
        y=r_e * np.outer(np.sin(u), np.sin(v)),
        z=r_e * np.outer(np.ones_like(u), np.cos(v)),
        colorscale=[[0, "#0d1f3a"], [1, "#1a3a6b"]], showscale=False, opacity=0.85,
        hoverinfo="skip",
    )

    trajectories = [tr for tr in (trajectories or []) if getattr(tr, "t", np.zeros(0)).size > 1]
    if trajectories:
        bcs = np.array([tr.obj.ballistic_coefficient() for tr in trajectories])
        lo, hi = float(np.log10(max(bcs.min(), 1e-3))), float(np.log10(max(bcs.max(), 1e-2)))
        span = max(hi - lo, 1e-6)
        for tr in trajectories:
            frac = (math.log10(max(tr.obj.ballistic_coefficient(), 1e-3)) - lo) / span
            fig.add_scatter3d(
                x=tr.r[:, 0] / 1000.0, y=tr.r[:, 1] / 1000.0, z=tr.r[:, 2] / 1000.0,
                mode="lines", line=dict(width=3, color=_viridis(frac)),
                name=f"{tr.obj.name} (B={tr.obj.ballistic_coefficient():.0f})",
                hovertemplate=f"{tr.obj.name}<extra></extra>",
            )
            if tr.impacted:
                fig.add_scatter3d(
                    x=[tr.r[-1, 0] / 1000.0], y=[tr.r[-1, 1] / 1000.0], z=[tr.r[-1, 2] / 1000.0],
                    mode="markers", marker=dict(size=5, color=CRITICAL, symbol="x"),
                    name=f"{tr.obj.name} impact", showlegend=False,
                )

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            bgcolor="rgba(0,0,0,0)", aspectmode="data",
            camera=dict(eye=dict(x=1.4, y=1.4, z=0.7)),
        ),
    )
    return _layout(fig, None, height)


def _viridis(frac: float) -> str:
    """Sample a viridis-like ramp without importing matplotlib."""
    stops = [(0.0, (68, 1, 84)), (0.25, (59, 82, 139)), (0.5, (33, 145, 140)),
             (0.75, (94, 201, 98)), (1.0, (253, 231, 37))]
    f = float(np.clip(frac, 0.0, 1.0))
    for (f0, c0), (f1, c1) in zip(stops[:-1], stops[1:]):
        if f <= f1:
            w = (f - f0) / max(f1 - f0, 1e-9)
            rgb = [int(round(a + w * (b - a))) for a, b in zip(c0, c1)]
            return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
    return "rgb(253,231,37)"


# ============================================================================== footprint
def plot_impact_map(footprint, zones=None, height: int = 520, show_hull: bool = True,
                    label: str = "impacts"):
    """
    World map of impact points with conformal zone overlays.

    Uses plotly's built-in ``scattergeo`` coastlines, so it renders offline with no map tile
    service and no access token.
    """
    go = _go()
    fig = go.Figure()
    if footprint is None or footprint.n_impacted == 0:
        return _layout(go.Figure(), "No impacts to plot", height)

    if show_hull:
        hlat, hlon = footprint.convex_hull()
        if len(hlat) > 2:
            fig.add_trace(go.Scattergeo(
                lat=hlat, lon=hlon, mode="lines", line=dict(color=MUTED, width=1, dash="dot"),
                name="convex hull", hoverinfo="skip"))

    for z, colour, dash in zip(zones or [], (WARNING, CRITICAL, "#A78BFA"),
                               ("solid", "dash", "dot")):
        if z is None or len(z.boundary_lat) < 3:
            continue
        fig.add_trace(go.Scattergeo(
            lat=z.boundary_lat, lon=z.boundary_lon, mode="lines",
            line=dict(color=colour, width=2, dash=dash),
            fill="toself", fillcolor=_rgba(colour, 0.10),
            name=f"{z.nominal_coverage:.0%} {z.score} zone ({z.area_km2:,.0f} km^2)",
            hoverinfo="skip"))

    bc = np.maximum(footprint.ballistic_coefficient, 1e-3)
    fig.add_trace(go.Scattergeo(
        lat=footprint.latitude, lon=footprint.longitude, mode="markers",
        marker=dict(size=4, color=np.log10(bc), colorscale=SEQUENTIAL, opacity=0.75,
                    colorbar=dict(title="log10 B<br>[kg/m^2]", tickfont=dict(color=MUTED),
                                  title_font=dict(color=MUTED), len=0.7)),
        name=label,
        customdata=np.stack([footprint.impact_speed, footprint.impact_mass, bc], axis=1),
        hovertemplate=("%{lat:.3f}, %{lon:.3f}<br>%{customdata[0]:.0f} m/s"
                       "<br>%{customdata[1]:.2f} kg<br>B=%{customdata[2]:.1f}<extra></extra>")))

    mlat, mlon = footprint.mean_point
    fig.add_trace(go.Scattergeo(
        lat=[footprint.origin_latitude], lon=[footprint.origin_longitude], mode="markers+text",
        marker=dict(size=11, color=ACCENT, symbol="diamond"),
        text=["breakup"], textposition="top center", textfont=dict(color=ACCENT, size=10),
        name="breakup subpoint"))
    fig.add_trace(go.Scattergeo(
        lat=[mlat], lon=[mlon], mode="markers",
        marker=dict(size=12, color=CRITICAL, symbol="x"), name="mean impact"))

    fig.update_geos(
        projection_type="natural earth", showland=True, landcolor="#12203a",
        showocean=True, oceancolor="#070c18", showcountries=True, countrycolor=GRID,
        coastlinecolor="#2a4a72", showlakes=False, bgcolor="rgba(0,0,0,0)",
    )
    return _layout(fig, None, height)


def _rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def plot_dispersion(footprint, zones=None, height: int = 460, density_zone=None):
    """
    Downrange/crossrange scatter in the range-safety frame, with zone boundaries.

    This is the diagnostic view: downrange spread is ballistic-coefficient driven and
    crossrange spread is wind and azimuth driven, so seeing them on separate orthogonal axes
    tells you immediately which uncertainty dominates.  Aspect ratio is *not* locked to 1:1 -
    real footprints are 30:1 elongated and forcing equal axes makes them an unreadable line.
    """
    go = _go()
    if footprint is None or footprint.n_impacted == 0:
        return _layout(go.Figure(), "No impacts to plot", height)
    fig = go.Figure()

    if density_zone is not None and density_zone.grid is not None:
        g = density_zone.grid
        fig.add_trace(go.Contour(
            x=g["crossrange"] / 1000.0, y=g["downrange"] / 1000.0,
            z=g["density"].T, showscale=False, contours=dict(coloring="heatmap"),
            colorscale=[[0, "rgba(0,0,0,0)"], [1, _rgba(ACCENT, 0.45)]],
            hoverinfo="skip", name="KDE"))

    bc = np.maximum(footprint.ballistic_coefficient, 1e-3)
    fig.add_trace(go.Scatter(
        x=footprint.crossrange / 1000.0, y=footprint.downrange / 1000.0, mode="markers",
        marker=dict(size=5, color=np.log10(bc), colorscale=SEQUENTIAL, opacity=0.8,
                    colorbar=dict(title="log10 B", tickfont=dict(color=MUTED),
                                  title_font=dict(color=MUTED), len=0.7)),
        name="impacts", hovertemplate="cross %{x:.1f} km<br>down %{y:.1f} km<extra></extra>"))

    for z, colour, dash in zip(zones or [], (WARNING, CRITICAL, "#A78BFA"),
                               ("solid", "dash", "dot")):
        if z is None or not np.isfinite(z.threshold):
            continue
        d, c = _zone_local_boundary(z, footprint)
        if d is None:
            continue
        fig.add_trace(go.Scatter(
            x=c / 1000.0, y=d / 1000.0, mode="lines",
            line=dict(color=colour, width=2, dash=dash),
            name=f"{z.nominal_coverage:.0%} {z.score}"))

    fig.update_xaxes(title_text="Crossrange [km]")
    fig.update_yaxes(title_text="Downrange [km]")
    return _layout(fig, None, height)


def _zone_local_boundary(zone, footprint, n: int = 181):
    """Zone boundary back in the local frame, for the dispersion plot."""
    if zone.score == "mahalanobis" and zone.centre is not None and zone.cov_inv is not None:
        cov = np.linalg.pinv(zone.cov_inv)
        vals, vecs = np.linalg.eigh(cov)
        vals = np.maximum(vals, 0.0)
        th = np.linspace(0, 2 * np.pi, n)
        pts = vecs @ (np.sqrt(vals * (zone.threshold * zone.inflation) ** 2)[:, None]
                      * np.stack([np.cos(th), np.sin(th)]))
        return pts[0] + zone.centre[0], pts[1] + zone.centre[1]
    if zone.score == "density" and zone.grid is not None:
        dg, cg, mask = zone.grid["downrange"], zone.grid["crossrange"], zone.grid["mask"]
        up, down = [], []
        for i, row in enumerate(mask):
            idx = np.flatnonzero(row)
            if idx.size:
                up.append((dg[i], cg[idx[-1]]))
                down.append((dg[i], cg[idx[0]]))
        if len(up) < 2:
            return None, None
        ring = np.array(up + down[::-1] + up[:1])
        return ring[:, 0], ring[:, 1]
    return None, None


def plot_footprint_by_bc(footprint, height: int = 380):
    """
    Downrange against ballistic coefficient - the single clearest debris-footprint diagram.

    A near-straight line on a log-x axis is the physics: higher B penetrates deeper before
    decelerating, so it lands further downrange, and the relationship spans hundreds of
    kilometres over a couple of decades of B.
    """
    go = _go()
    if footprint is None or footprint.n_impacted == 0:
        return _layout(go.Figure(), "No impacts", height)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=np.maximum(footprint.ballistic_coefficient, 1e-3),
        y=footprint.downrange / 1000.0, mode="markers",
        marker=dict(size=5, color=footprint.impact_speed, colorscale="Inferno", opacity=0.8,
                    colorbar=dict(title="impact<br>speed [m/s]", tickfont=dict(color=MUTED),
                                  title_font=dict(color=MUTED), len=0.7)),
        name="impacts",
        hovertemplate="B=%{x:.1f}<br>downrange %{y:.0f} km<extra></extra>"))
    fig.update_xaxes(title_text="Ballistic coefficient B = m / (Cd A) [kg/m^2]", type="log")
    fig.update_yaxes(title_text="Downrange [km]")
    return _layout(fig, None, height, legend=False)


# ============================================================================== breakup
def plot_size_distribution(cloud, height: int = 380):
    """
    Sampled fragment sizes against the analytic NASA breakup-model power law.

    A validation plot, not decoration: the sampled population should track the analytic slope,
    and any offset should be explainable by the mass budget and the fragment cap rather than
    being a sampling bug.
    """
    from .fragmentation import size_distribution_check

    go = _go()
    edges, sampled, analytic = size_distribution_check(cloud)
    fig = go.Figure()
    if edges.size:
        fig.add_trace(go.Scatter(x=edges * 100.0, y=np.maximum(analytic, 1e-3), mode="lines",
                                 line=dict(color=WARNING, width=2, dash="dash"),
                                 name="NASA SBM analytic N(>Lc)"))
        fig.add_trace(go.Scatter(x=edges * 100.0, y=np.maximum(sampled, 1e-3), mode="lines+markers",
                                 line=dict(color=ACCENT, width=2), marker=dict(size=5),
                                 name="sampled population"))
    fig.update_xaxes(title_text="Characteristic length Lc [cm]", type="log")
    fig.update_yaxes(title_text="Cumulative count N(> Lc)", type="log")
    return _layout(fig, None, height)


def plot_cloud_properties(cloud, height: int = 380):
    """Area-to-mass against characteristic length, coloured by ejection delta-v."""
    go = _go()
    fig = go.Figure()
    origins = np.array([o.origin for o in cloud.objects])
    lc = cloud.characteristic_lengths * 100.0
    for origin in np.unique(origins):
        m = origins == origin
        fig.add_trace(go.Scatter(
            x=lc[m], y=cloud.area_to_mass[m], mode="markers",
            marker=dict(size=np.clip(4 + 3 * np.log10(np.maximum(cloud.masses[m], 1e-3) + 1), 4, 16),
                        color=ORIGIN_COLOURS.get(origin, ACCENT), opacity=0.8,
                        line=dict(width=0)),
            name=origin,
            customdata=np.stack([cloud.masses[m], cloud.delta_v_magnitude[m],
                                 cloud.ballistic_coefficients[m]], axis=1),
            hovertemplate=("Lc %{x:.1f} cm<br>A/M %{y:.3f} m^2/kg<br>"
                           "%{customdata[0]:.2f} kg<br>dv %{customdata[1]:.1f} m/s"
                           "<br>B=%{customdata[2]:.1f}<extra></extra>")))
    fig.update_xaxes(title_text="Characteristic length Lc [cm]", type="log")
    fig.update_yaxes(title_text="Area-to-mass A/M [m^2/kg]", type="log")
    return _layout(fig, None, height)


# =============================================================================== launch
def plot_ascent_profile(profile, separations=None, height: int = 420):
    """Ascent altitude and speed against time, with separation events marked."""
    from plotly.subplots import make_subplots

    go = _go()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=profile.time, y=profile.altitude / 1000.0, mode="lines",
                             line=dict(color=ACCENT, width=2.5), name="Altitude"),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=profile.time, y=profile.speed / 1000.0, mode="lines",
                             line=dict(color=WARNING, width=2, dash="dash"), name="Speed"),
                  secondary_y=True)
    for ev, _state, _objs in (separations or []):
        fig.add_vline(x=ev.time, line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_annotation(x=ev.time, y=ev.altitude / 1000.0, text=ev.name,
                           showarrow=True, arrowhead=2, arrowcolor=MUTED,
                           font=dict(color=TEXT, size=9), bgcolor="rgba(13,17,23,0.85)",
                           bordercolor=GRID, ax=18, ay=-28)
    fig.update_xaxes(title_text="Time from lift-off [s]")
    fig.update_yaxes(title_text="Altitude [km]", secondary_y=False)
    fig.update_yaxes(title_text="Earth-relative speed [km/s]", secondary_y=True,
                     gridcolor="rgba(0,0,0,0)")
    return _layout(fig, None, height)


def plot_drop_zones(results, height: int = 520):
    """
    Map of predicted drop zones for every jettisoned item on one launch.

    ``results`` is a list of ``(label, footprint, zone)`` triples.  Plotting them together is
    the point: the whole hazard area of a launch is the union of several well-separated
    ellipses, not one region.
    """
    go = _go()
    fig = go.Figure()
    palette = [ACCENT, WARNING, "#A78BFA", NOMINAL, "#5D9CEC", CRITICAL, "#E8C547"]
    for i, (label, fp, zone) in enumerate(results or []):
        if fp is None or fp.n_impacted == 0:
            continue
        colour = palette[i % len(palette)]
        if zone is not None and len(zone.boundary_lat) > 2:
            fig.add_trace(go.Scattergeo(
                lat=zone.boundary_lat, lon=zone.boundary_lon, mode="lines",
                line=dict(color=colour, width=2), fill="toself",
                fillcolor=_rgba(colour, 0.14),
                name=f"{label} {zone.nominal_coverage:.0%} zone", hoverinfo="skip"))
        mlat, mlon = fp.mean_point
        fig.add_trace(go.Scattergeo(
            lat=fp.latitude, lon=fp.longitude, mode="markers",
            marker=dict(size=3, color=colour, opacity=0.5), name=label, showlegend=False))
        fig.add_trace(go.Scattergeo(
            lat=[mlat], lon=[mlon], mode="markers+text",
            marker=dict(size=10, color=colour, symbol="x"),
            text=[label], textposition="top right", textfont=dict(color=colour, size=9),
            name=label))
    fig.update_geos(projection_type="natural earth", showland=True, landcolor="#12203a",
                    showocean=True, oceancolor="#070c18", showcountries=True,
                    countrycolor=GRID, coastlinecolor="#2a4a72", bgcolor="rgba(0,0,0,0)")
    return _layout(fig, None, height)


# ============================================================================== kessler
def plot_kessler_shells(shells, height: int = 420):
    """
    Criticality by altitude shell, with the criticality-1 line marked.

    Bars are coloured by stability class and the threshold is drawn explicitly, because the
    only question this chart needs to answer is which shells are above 1.
    """
    go = _go()
    alts = [s.alt_mid for s in shells]
    crit = [s.criticality() for s in shells]
    colours = [NOMINAL if c < 0.75 else (WARNING if c < 1.0 else CRITICAL) for c in crit]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=alts, y=crit, marker=dict(color=colours),
        customdata=np.stack([[s.n_objects for s in shells],
                             [s.collisional_growth_time() for s in shells],
                             [s.lifetime(s.fragment) for s in shells]], axis=1),
        name="criticality",
        hovertemplate=("%{x:.0f} km<br>criticality %{y:.2f}<br>%{customdata[0]} objects"
                       "<br>growth time %{customdata[1]:.0f} yr"
                       "<br>fragment lifetime %{customdata[2]:.0f} yr<extra></extra>")))
    fig.add_hline(y=1.0, line=dict(color=CRITICAL, width=2, dash="dash"),
                  annotation_text="criticality = 1: collisions outpace drag",
                  annotation_font=dict(color=CRITICAL, size=10))
    fig.update_xaxes(title_text="Altitude [km]")
    fig.update_yaxes(title_text="Criticality  (fragment production / drag removal)", type="log")
    return _layout(fig, None, height, legend=False)


def plot_cascade(result, height: int = 400):
    """Total population against time, split into intact objects and fragments."""
    go = _go()
    fig = go.Figure()
    t = result.time_years
    fig.add_trace(go.Scatter(x=t, y=result.n_fragment.sum(axis=1), mode="lines",
                             line=dict(color=CRITICAL, width=2), name="fragments",
                             stackgroup="one"))
    fig.add_trace(go.Scatter(x=t, y=result.n_intact.sum(axis=1), mode="lines",
                             line=dict(color=ACCENT, width=2), name="intact objects",
                             stackgroup="one"))
    fig.update_xaxes(title_text="Years from now")
    fig.update_yaxes(title_text="Trackable objects in LEO")
    return _layout(fig, None, height)


# ============================================================================ detection
def plot_frame_detections(image, detections=None, truth=None, height: int = 480,
                          title: str | None = None):
    """
    Sensor frame with detections and ground truth overlaid.

    Truth is drawn as hollow circles and detections as crosses, so a match reads as a cross
    inside a circle, a miss as an empty circle and a false positive as a bare cross - all
    three legible at a glance without a legend lookup.
    """
    go = _go()
    img = np.asarray(image, dtype=float)
    if img.ndim == 3:
        img = img.mean(axis=2)
    fig = go.Figure(go.Heatmap(z=img, colorscale="Greys_r", showscale=False,
                               hoverinfo="skip"))
    for t in truth or []:
        if t.kind != "fragment":
            continue
        fig.add_trace(go.Scatter(
            x=[t.x], y=[t.y], mode="markers",
            marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color=NOMINAL, width=1.6),
                        symbol="circle"),
            name="truth", showlegend=False,
            hovertemplate=f"truth: {t.size_px:.1f} px<extra></extra>"))
    for d in detections or []:
        colour = ACCENT if d.kind == "fragment" else WARNING
        fig.add_trace(go.Scatter(
            x=[d.x], y=[d.y], mode="markers",
            marker=dict(size=11, color=colour, symbol="x", line=dict(width=1)),
            name="detection", showlegend=False,
            hovertemplate=(f"{d.kind}: {d.size_px:.1f} px<br>score {d.score:.2f}"
                           f"<br>elongation {d.elongation:.2f}<extra></extra>")))
    fig.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1,
                     title_text="pixels")
    fig.update_xaxes(title_text="pixels")
    return _layout(fig, title, height, legend=False)


# ============================================================================ conformal
def plot_coverage_comparison(comparison, height: int = 380):
    """
    Measured coverage and area for the Gaussian ellipse and both conformal zones.

    Coverage is plotted against the nominal line: the whole argument for conformal zones is
    that the chi-squared ellipse can sit *below* it, and that only shows in a chart that draws
    the target explicitly.
    """
    from plotly.subplots import make_subplots

    go = _go()
    nominal = comparison["nominal_coverage"]
    names = ["Gaussian chi^2", "Conformal (Mahalanobis)", "Conformal (density)"]
    cov = [comparison["gaussian_empirical_coverage"],
           comparison["conformal_mahalanobis"]["empirical_coverage"],
           comparison["conformal_density"]["empirical_coverage"]]
    area = [comparison["gaussian_area_km2"],
            comparison["conformal_mahalanobis"]["area_km2"],
            comparison["conformal_density"]["area_km2"]]
    colours = [CRITICAL if (c is not None and np.isfinite(c) and c < nominal - 0.005) else NOMINAL
               for c in cov]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Empirical coverage", "Zone area [km^2]"),
                        horizontal_spacing=0.16)
    fig.add_trace(go.Bar(x=names, y=cov, marker_color=colours, name="coverage",
                         hovertemplate="%{x}<br>coverage %{y:.4f}<extra></extra>"), row=1, col=1)
    fig.add_hline(y=nominal, line=dict(color=ACCENT, width=2, dash="dash"), row=1, col=1,
                  annotation_text=f"nominal {nominal:.0%}",
                  annotation_font=dict(color=ACCENT, size=10))
    fig.add_trace(go.Bar(x=names, y=area, marker_color=ACCENT, name="area",
                         hovertemplate="%{x}<br>%{y:,.0f} km^2<extra></extra>"), row=1, col=2)
    lo = min([c for c in cov if c is not None and np.isfinite(c)] + [nominal])
    fig.update_yaxes(range=[max(lo - 0.05, 0), 1.005], row=1, col=1)
    for ann in fig.layout.annotations:
        ann.font.color = ACCENT
        ann.font.size = 11
    return _layout(fig, None, height, legend=False)


def plot_error_matrix(result, height: int = 420):
    """
    Continual-learning error matrix as a heatmap: rows are training stages, columns are tasks.

    The diagonal is each task when freshly learned; everything below-left of it shows what
    happened to earlier tasks afterwards. Catastrophic forgetting is visible as a bright
    lower-left triangle, which no single averaged number conveys.
    """
    go = _go()
    e = np.asarray(result.error_matrix, dtype=float)
    labels = [t if len(t) < 18 else t[:16] + "…" for t in result.tasks]
    fig = go.Figure(go.Heatmap(
        z=e, x=labels, y=[f"after {labels[i]}" for i in range(len(labels))],
        colorscale="Inferno", reversescale=True,
        colorbar=dict(title="error<br>[km]", tickfont=dict(color=MUTED),
                      title_font=dict(color=MUTED), len=0.75),
        text=[[f"{v:.0f}" for v in row] for row in e], texttemplate="%{text}",
        textfont=dict(size=9),
        hovertemplate="task %{x}<br>%{y}<br>%{z:.1f} km<extra></extra>"))
    fig.update_xaxes(title_text="evaluated on task")
    fig.update_yaxes(title_text="training stage", autorange="reversed")
    return _layout(fig, f"{result.strategy}: error matrix", height, legend=False)


def plot_federated_comparison(rows, height: int = 420):
    """
    Pooled error per scheme, with local-only models separated from federated ones.

    Local models are drawn in a muted colour because the point of the chart is that they are the
    thing being beaten: each is good on its own client and poor on the pooled distribution.
    """
    go = _go()
    rows = sorted(rows, key=lambda r: r["pooled error [km]"])
    names = [r["scheme"] for r in rows]
    vals = [r["pooled error [km]"] for r in rows]
    colours = [MUTED if n.startswith("local:") else
               (NOMINAL if n == "centralised" else ACCENT) for n in names]
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h", marker_color=colours,
        text=[f"{v:.1f}" for v in vals], textposition="outside",
        textfont=dict(color=TEXT, size=10),
        hovertemplate="%{y}<br>%{x:.2f} km pooled error<extra></extra>"))
    fig.update_xaxes(title_text="Pooled-test impact error [km] (lower is better)")
    fig.update_yaxes(autorange="reversed")
    return _layout(fig, None, height, legend=False)


def plot_scaling_curve(rows, height: int = 400, x_key: str = "n_train",
                       series=("ridge_km", "apsgtt_km")):
    """Error against training-set size, log-log - the curve that says which model to use when."""
    go = _go()
    fig = go.Figure()
    palette = {"ridge_km": WARNING, "apsgtt_km": ACCENT}
    for key in series:
        fig.add_trace(go.Scatter(
            x=[r[x_key] for r in rows], y=[r[key] for r in rows], mode="lines+markers",
            line=dict(color=palette.get(key, ACCENT), width=2), marker=dict(size=7),
            name=key.replace("_km", "").replace("_", " ")))
    fig.update_xaxes(title_text="Training samples", type="log")
    fig.update_yaxes(title_text="Median impact error [km]", type="log")
    return _layout(fig, None, height)


def plot_hazard_sensitivity(rows, height: int = 400,
                            x_key: str = "severity", series=("fragmentation_probability",)):
    """Generic line chart for a swept-parameter table (list of dicts)."""
    go = _go()
    fig = go.Figure()
    palette = [ACCENT, WARNING, CRITICAL, NOMINAL, "#A78BFA"]
    x = [r[x_key] for r in rows]
    for i, key in enumerate(series):
        fig.add_trace(go.Scatter(x=x, y=[r[key] for r in rows], mode="lines+markers",
                                 line=dict(color=palette[i % len(palette)], width=2),
                                 name=key.replace("_", " ")))
    fig.update_xaxes(title_text=x_key.replace("_", " "))
    return _layout(fig, None, height)

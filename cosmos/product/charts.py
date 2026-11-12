"""Server-side SVG charts rendered from real arrays.

No chart in this module can be produced without data: each function takes the actual values
and returns an explicit "no data" placeholder when they are absent or non-finite. Nothing is
smoothed, interpolated, extrapolated or styled to imply precision the data lacks.

SVG is generated here rather than in the browser so that the product has no JavaScript
charting dependency and works offline during a demonstration.
"""
from __future__ import annotations

import html
import math
from datetime import datetime
from typing import Sequence

#: Palette. Deliberately restrained: status colour carries meaning, series colour does not.
INK = "#c7d2de"
MUTED = "#7d8c9e"
GRID = "#243445"
SERIES = "#4ea8de"
ANOMALY = "#d98236"
ABSTAIN = "#9a7fb8"
AXIS_FONT = 11


def _placeholder(width: int, height: int, message: str) -> str:
    return (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{html.escape(message)}">'
        f'<rect width="{width}" height="{height}" fill="none" stroke="{GRID}" '
        f'stroke-dasharray="4 3"/>'
        f'<text x="{width / 2}" y="{height / 2}" fill="{MUTED}" font-size="12" '
        f'text-anchor="middle">{html.escape(message)}</text></svg>'
    )


def _nice_ticks(low: float, high: float, count: int = 4) -> list[float]:
    """Round tick values spanning [low, high]."""
    if not math.isfinite(low) or not math.isfinite(high) or high <= low:
        return [low] if math.isfinite(low) else []
    span = high - low
    raw = span / max(count, 1)
    magnitude = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for multiple in (1, 2, 2.5, 5, 10):
        step = magnitude * multiple
        if step >= raw:
            break
    start = math.ceil(low / step) * step
    ticks = []
    value = start
    while value <= high + step * 1e-9:
        ticks.append(round(value, 10))
        value += step
    return ticks


def _fmt(value: float) -> str:
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 1000 or magnitude < 0.01:
        return f"{value:.3g}"
    if magnitude >= 10:
        return f"{value:.0f}"
    return f"{value:.2f}"


def telemetry_series(times: Sequence[str], values: Sequence[float | None],
                     intervals: Sequence[dict] | None = None,
                     width: int = 940, height: int = 280,
                     y_label: str = "value (normalised)") -> str:
    """Decimated telemetry with ground-truth anomaly intervals shaded.

    Gaps in the data are breaks in the line, not interpolated segments: a missing sample is
    visibly missing. Shaded bands are benchmark annotations, not model detections.
    """
    points = [(index, value) for index, value in enumerate(values)
              if value is not None and math.isfinite(value)]
    if len(points) < 2:
        return _placeholder(width, height, "no finite telemetry samples in this channel")

    left, right, top, bottom = 56, 14, 14, 34
    plot_w = width - left - right
    plot_h = height - top - bottom
    n = len(values)
    y_lo = min(value for _, value in points)
    y_hi = max(value for _, value in points)
    if y_hi == y_lo:
        y_hi = y_lo + 1.0

    def sx(index: float) -> float:
        return left + (index / max(n - 1, 1)) * plot_w

    def sy(value: float) -> float:
        return top + plot_h - ((value - y_lo) / (y_hi - y_lo)) * plot_h

    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="telemetry series with {len(intervals or [])} annotated intervals">']

    # anomaly/rare-event bands, mapped from timestamps onto sample index
    if intervals and times:
        try:
            t0 = datetime.fromisoformat(times[0])
            t1 = datetime.fromisoformat(times[-1])
            span = (t1 - t0).total_seconds()
        except (ValueError, TypeError):
            span = 0
        if span > 0:
            for interval in intervals:
                if not interval.get("start") or not interval.get("end"):
                    continue
                try:
                    start = datetime.fromisoformat(interval["start"])
                    end = datetime.fromisoformat(interval["end"])
                except (ValueError, TypeError):
                    continue
                a = (start - t0).total_seconds() / span * (n - 1)
                b = (end - t0).total_seconds() / span * (n - 1)
                a, b = max(0.0, min(a, n - 1)), max(0.0, min(b, n - 1))
                x0, x1 = sx(a), sx(b)
                # Guarantee a visible mark for an interval shorter than one pixel.
                band = max(x1 - x0, 1.5)
                parts.append(f'<rect x="{x0:.1f}" y="{top}" width="{band:.1f}" '
                             f'height="{plot_h}" fill="{ANOMALY}" opacity="0.28"/>')

    # grid and y axis
    for tick in _nice_ticks(y_lo, y_hi, 4):
        y = sy(tick)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
                     f'stroke="{GRID}"/>')
        parts.append(f'<text x="{left - 6}" y="{y + 3:.1f}" fill="{MUTED}" '
                     f'font-size="{AXIS_FONT}" text-anchor="end">{_fmt(tick)}</text>')

    # the series itself, broken at gaps
    segments: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    previous_index = None
    for index, value in points:
        if previous_index is not None and index != previous_index + 1:
            if len(current) > 1:
                segments.append(current)
            current = []
        current.append((sx(index), sy(value)))
        previous_index = index
    if len(current) > 1:
        segments.append(current)
    for segment in segments:
        path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}"
                        for i, (x, y) in enumerate(segment))
        parts.append(f'<path d="{path}" fill="none" stroke="{SERIES}" stroke-width="1.1"/>')

    # x axis labels: first and last real timestamps
    if times:
        parts.append(f'<text x="{left}" y="{height - 12}" fill="{MUTED}" '
                     f'font-size="{AXIS_FONT}">{html.escape(times[0][:16])}</text>')
        parts.append(f'<text x="{left + plot_w}" y="{height - 12}" fill="{MUTED}" '
                     f'font-size="{AXIS_FONT}" text-anchor="end">'
                     f'{html.escape(times[-1][:16])}</text>')
    parts.append(f'<text x="6" y="{top + 10}" fill="{MUTED}" font-size="{AXIS_FONT}">'
                 f'{html.escape(y_label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def horizon_bars(probabilities: dict[str, float | None], width: int = 420,
                 height: int = 190, incoherent: bool = False) -> str:
    """Probability per horizon. A missing horizon is drawn as an explicit gap, not as zero."""
    order = [key for key in ("30d", "90d", "1yr") if key in probabilities]
    if not order:
        return _placeholder(width, height, "no horizon probabilities available")
    usable = [probabilities[key] for key in order
              if probabilities[key] is not None and math.isfinite(probabilities[key])]
    if not usable:
        return _placeholder(width, height, "no horizon probability was produced")

    left, right, top, bottom = 46, 14, 16, 30
    plot_w = width - left - right
    plot_h = height - top - bottom
    slot = plot_w / len(order)
    bar_w = min(58.0, slot * 0.55)

    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="re-entry probability by horizon">']
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + plot_h - tick * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
                     f'stroke="{GRID}"/>')
        parts.append(f'<text x="{left - 6}" y="{y + 3:.1f}" fill="{MUTED}" '
                     f'font-size="{AXIS_FONT}" text-anchor="end">{tick:.2f}</text>')

    colour = ABSTAIN if incoherent else SERIES
    for index, key in enumerate(order):
        cx = left + slot * (index + 0.5)
        value = probabilities[key]
        if value is None or not math.isfinite(value):
            parts.append(f'<text x="{cx:.1f}" y="{top + plot_h / 2:.1f}" fill="{MUTED}" '
                         f'font-size="10" text-anchor="middle">n/a</text>')
        else:
            bar_h = max(value * plot_h, 1.0)
            parts.append(f'<rect x="{cx - bar_w / 2:.1f}" y="{top + plot_h - bar_h:.1f}" '
                         f'width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{colour}" '
                         f'opacity="0.85"/>')
            parts.append(f'<text x="{cx:.1f}" y="{top + plot_h - bar_h - 5:.1f}" fill="{INK}" '
                         f'font-size="10" text-anchor="middle">{value:.3f}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{height - 10}" fill="{MUTED}" '
                     f'font-size="{AXIS_FONT}" text-anchor="middle">{html.escape(key)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def interval_plot(low: float | None, median: float | None, high: float | None,
                  width: int = 420, height: int = 130,
                  unit: str = "days", label: str = "5-95 % Monte-Carlo spread") -> str:
    """One quantile interval on a log axis, because lifetimes span several decades."""
    values = [v for v in (low, median, high) if v is not None and math.isfinite(v) and v > 0]
    if len(values) < 2:
        return _placeholder(width, height, "no time quantiles available for this object")

    left, right, top = 20, 20, 44
    plot_w = width - left - right
    lo_log = math.log10(min(values))
    hi_log = math.log10(max(values))
    if hi_log - lo_log < 0.3:               # keep a visible span for a tight interval
        mid = (hi_log + lo_log) / 2
        lo_log, hi_log = mid - 0.15, mid + 0.15

    def sx(value: float) -> float:
        return left + (math.log10(value) - lo_log) / (hi_log - lo_log) * plot_w

    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{html.escape(label)}">']
    parts.append(f'<text x="{left}" y="18" fill="{MUTED}" font-size="{AXIS_FONT}">'
                 f'{html.escape(label)}</text>')
    if low is not None and high is not None and low > 0 and high > 0:
        x0, x1 = sx(low), sx(high)
        parts.append(f'<line x1="{x0:.1f}" y1="{top}" x2="{x1:.1f}" y2="{top}" '
                     f'stroke="{SERIES}" stroke-width="5" opacity="0.5"/>')
        for x in (x0, x1):
            parts.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{top + 8}" '
                         f'stroke="{SERIES}" stroke-width="2"/>')
        parts.append(f'<text x="{x0:.1f}" y="{top + 26}" fill="{MUTED}" font-size="10" '
                     f'text-anchor="middle">{_fmt(low)}</text>')
        parts.append(f'<text x="{x1:.1f}" y="{top + 26}" fill="{MUTED}" font-size="10" '
                     f'text-anchor="middle">{_fmt(high)}</text>')
    if median is not None and median > 0 and math.isfinite(median):
        xm = sx(median)
        parts.append(f'<circle cx="{xm:.1f}" cy="{top}" r="5" fill="{INK}"/>')
        parts.append(f'<text x="{xm:.1f}" y="{top - 14}" fill="{INK}" font-size="11" '
                     f'text-anchor="middle">{_fmt(median)} {html.escape(unit)}</text>')
    parts.append(f'<text x="{width - right}" y="{height - 8}" fill="{MUTED}" font-size="10" '
                 f'text-anchor="end">log scale</text>')
    parts.append("</svg>")
    return "".join(parts)


def log_probability_strip(values: Sequence[float], width: int = 940, height: int = 150,
                          threshold: float = -6.0,
                          floor: float = -30.0) -> str:
    """Histogram of log10 collision probability with the high-risk threshold marked."""
    usable = [v for v in values if v is not None and math.isfinite(v)]
    if not usable:
        return _placeholder(width, height, "no collision probabilities available")

    left, right, top, bottom = 46, 14, 16, 34
    plot_w = width - left - right
    plot_h = height - top - bottom
    bins = 30
    lo, hi = floor, 0.0
    counts = [0] * bins
    for value in usable:
        clamped = min(max(value, lo), hi - 1e-9)
        index = int((clamped - lo) / (hi - lo) * bins)
        counts[min(index, bins - 1)] += 1
    peak = max(counts) or 1

    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="distribution of log10 collision probability">']
    bar_w = plot_w / bins
    for index, count in enumerate(counts):
        if not count:
            continue
        bar_h = count / peak * plot_h
        x = left + index * bar_w
        centre = lo + (index + 0.5) * (hi - lo) / bins
        colour = ANOMALY if centre >= threshold else SERIES
        parts.append(f'<rect x="{x:.1f}" y="{top + plot_h - bar_h:.1f}" '
                     f'width="{max(bar_w - 1, 1):.1f}" height="{bar_h:.1f}" fill="{colour}" '
                     f'opacity="0.8"><title>{count} event(s) near 1e{centre:.0f}</title></rect>')
    xt = left + (threshold - lo) / (hi - lo) * plot_w
    parts.append(f'<line x1="{xt:.1f}" y1="{top}" x2="{xt:.1f}" y2="{top + plot_h}" '
                 f'stroke="{ANOMALY}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    parts.append(f'<text x="{xt + 4:.1f}" y="{top + 12}" fill="{ANOMALY}" font-size="10">'
                 f'high-risk threshold 1e{threshold:.0f}</text>')
    for tick in (-30, -24, -18, -12, -6, 0):
        x = left + (tick - lo) / (hi - lo) * plot_w
        parts.append(f'<text x="{x:.1f}" y="{height - 12}" fill="{MUTED}" '
                     f'font-size="{AXIS_FONT}" text-anchor="middle">1e{tick}</text>')
    parts.append(f'<text x="6" y="{top + 10}" fill="{MUTED}" font-size="{AXIS_FONT}">events</text>')
    parts.append("</svg>")
    return "".join(parts)


def detection_overlay(detections: Sequence[dict], width: int = 640, height: int = 480,
                      image_url: str | None = None) -> str:
    """Real detection markers over a real SpotGEO frame, in the image's own pixel space.

    Markers are rings, never filled blobs sized by confidence: this detector reports no
    confidence, so no visual channel may imply one.
    """
    parts = [f'<svg class="overlay" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{len(detections)} detections on a SpotGEO frame">']
    if image_url:
        parts.append(f'<image href="{html.escape(image_url)}" x="0" y="0" '
                     f'width="{width}" height="{height}" preserveAspectRatio="none"/>')
    else:
        parts.append(f'<rect width="{width}" height="{height}" fill="#0d1620"/>'
                     f'<text x="{width / 2}" y="{height / 2}" fill="{MUTED}" font-size="13" '
                     f'text-anchor="middle">frame image unavailable</text>')
    for index, detection in enumerate(detections, start=1):
        x = detection.get("x_px")
        y = detection.get("y_px")
        if x is None or y is None or not math.isfinite(x) or not math.isfinite(y):
            continue
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="none" '
                     f'stroke="{ANOMALY}" stroke-width="1.6" opacity="0.95">'
                     f'<title>detection {index}: x={x:.1f} px, y={y:.1f} px; '
                     f'confidence not reported</title></circle>')
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.5" fill="{ANOMALY}"/>')
    parts.append("</svg>")
    return "".join(parts)


def category_bars(labels: Sequence[str], values: Sequence[float | None], *,
                  width: int = 460, height: int = 210, unit: str = "",
                  value_digits: int = 0, colour: str | None = None,
                  horizontal: bool = False, note: str | None = None) -> str:
    """Counts or scores per named category, drawn from the values given and nothing else.

    A missing value is drawn as an explicit gap labelled ``n/a``, never as zero. Added 2026-11-09
    for the distribution panels of the visual dashboard; the caller supplies the numbers, so this
    function cannot invent one.
    """
    pairs = [(str(label), value) for label, value in zip(labels, values)]
    if not pairs:
        return _placeholder(width, height, "no categories to draw")
    usable = [v for _, v in pairs if v is not None and math.isfinite(float(v))]
    if not usable:
        return _placeholder(width, height, "no values were produced")
    top_value = max(usable) or 1.0
    series = colour or SERIES

    if horizontal:
        left, right, top, bottom = 150, 54, 10, 14
        plot_w = width - left - right
        plot_h = height - top - bottom
        slot = plot_h / len(pairs)
        bar_h = min(20.0, slot * 0.68)
        parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
                 f'aria-label="{html.escape(note or "category values")}">']
        for index, (label, value) in enumerate(pairs):
            cy = top + slot * (index + 0.5)
            parts.append(f'<text x="{left - 8}" y="{cy + 3.5:.1f}" fill="{MUTED}" '
                         f'font-size="{AXIS_FONT}" text-anchor="end">{html.escape(label[:26])}</text>')
            if value is None or not math.isfinite(float(value)):
                parts.append(f'<text x="{left + 4}" y="{cy + 3.5:.1f}" fill="{MUTED}" '
                             f'font-size="10">n/a</text>')
                continue
            bar_w = max(float(value) / top_value * plot_w, 1.0)
            parts.append(f'<rect x="{left}" y="{cy - bar_h / 2:.1f}" width="{bar_w:.1f}" '
                         f'height="{bar_h:.1f}" fill="{series}" opacity="0.85" rx="2"/>')
            text = f"{float(value):,.{value_digits}f}{(' ' + unit) if unit else ''}"
            parts.append(f'<text x="{left + bar_w + 6:.1f}" y="{cy + 3.5:.1f}" fill="{INK}" '
                         f'font-size="10">{html.escape(text)}</text>')
        parts.append("</svg>")
        return "".join(parts)

    left, right, top, bottom = 46, 12, 14, 34
    plot_w = width - left - right
    plot_h = height - top - bottom
    slot = plot_w / len(pairs)
    bar_w = min(54.0, slot * 0.6)
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{html.escape(note or "category values")}">']
    for tick in _nice_ticks(0.0, top_value, 4):
        y = top + plot_h - (tick / top_value) * plot_h if top_value else top + plot_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="{GRID}"/>')
        parts.append(f'<text x="{left - 6}" y="{y + 3:.1f}" fill="{MUTED}" '
                     f'font-size="{AXIS_FONT}" text-anchor="end">{_fmt(tick)}</text>')
    for index, (label, value) in enumerate(pairs):
        cx = left + slot * (index + 0.5)
        if value is None or not math.isfinite(float(value)):
            parts.append(f'<text x="{cx:.1f}" y="{top + plot_h / 2:.1f}" fill="{MUTED}" '
                         f'font-size="10" text-anchor="middle">n/a</text>')
        else:
            bar_h = max(float(value) / top_value * plot_h, 1.0)
            parts.append(f'<rect x="{cx - bar_w / 2:.1f}" y="{top + plot_h - bar_h:.1f}" '
                         f'width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{series}" opacity="0.85" rx="2"/>')
            text = f"{float(value):,.{value_digits}f}"
            parts.append(f'<text x="{cx:.1f}" y="{top + plot_h - bar_h - 5:.1f}" fill="{INK}" '
                         f'font-size="10" text-anchor="middle">{html.escape(text)}</text>')
        words = html.escape(label[:18])
        parts.append(f'<text x="{cx:.1f}" y="{height - 18}" fill="{MUTED}" '
                     f'font-size="{AXIS_FONT}" text-anchor="middle">{words}</text>')
    if unit:
        parts.append(f'<text x="{left}" y="{height - 4}" fill="{MUTED}" font-size="9">{html.escape(unit)}</text>')
    parts.append("</svg>")
    return "".join(parts)

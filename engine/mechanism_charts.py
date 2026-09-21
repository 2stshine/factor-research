"""Small dependency-free SVG views of actual diagnostic tables, no invented data."""
from __future__ import annotations

from html import escape
import math


def _plot(rows, fields, title):
    if not rows:
        return None
    values = [row.get(field) for row in rows for field in fields]
    finite = [float(x) for x in values if isinstance(x, (float, int)) and math.isfinite(x)]
    if not finite:
        return None
    lo, hi = min(min(finite), 0), max(max(finite), 0)
    pad = (hi - lo) * .1 or .01
    lo, hi = lo - pad, hi + pad
    colors = ["#2563eb", "#d97706", "#059669"]
    width, height = 900, 310
    x = lambda i: 70 + i / max(1, len(rows) - 1) * 790
    y = lambda v: 250 - (v - lo) / (hi - lo) * 185
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="20" y="24" font-family="sans-serif" font-size="17">{escape(title)}</text>',
             '<text x="20" y="45" font-family="sans-serif" font-size="11">Descriptive observations, not causal proof. Missing months break lines.</text>',
             f'<line x1="70" x2="860" y1="{y(0):.2f}" y2="{y(0):.2f}" stroke="#aaa"/>']
    for tick in (lo, (lo + hi) / 2, hi):
        parts.append(f'<text x="5" y="{y(tick):.2f}" font-family="sans-serif" font-size="11">{tick:.4g}</text>')
    for index, field in enumerate(fields):
        color = colors[index % len(colors)]
        segments, points, last_month = [], [], None
        for i, row in enumerate(rows):
            month = row["month"]
            ordinal = int(month[:4]) * 12 + int(month[5:7])
            value = row.get(field)
            valid = isinstance(value, (int, float)) and math.isfinite(value)
            if not valid or (last_month is not None and ordinal != last_month + 1):
                if points:
                    segments.append(points)
                points = []
            if valid:
                points.append(f"{x(i):.2f},{y(value):.2f}")
            last_month = ordinal
        if points:
            segments.append(points)
        for segment in segments:
            if len(segment) == 1:
                cx, cy = segment[0].split(",")
                parts.append(f'<circle cx="{cx}" cy="{cy}" r="2" fill="{color}"/>')
            else:
                parts.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<text x="{70 + index * 240}" y="300" fill="{color}" font-family="sans-serif" font-size="12">{escape(field)}</text>')
    for i in sorted({0, len(rows) // 2, len(rows) - 1}):
        parts.append(f'<text x="{x(i):.2f}" y="274" text-anchor="middle" font-family="sans-serif" font-size="11">{escape(str(rows[i]["month"]))}</text>')
    return "".join(parts) + "</svg>"


def diagnostic_charts(sections):
    charts = []
    monthly = sections.get("monthly_performance", {}).get("data", {}).get("monthly", [])
    targets = [("monthly_ic", monthly, ["rank_ic"], "Monthly rank association", "monthly_performance"),
               ("group_returns", monthly, ["top_mean", "bottom_mean"], "Monthly reformed group returns (gross)", "monthly_performance")]
    for index, outcome in enumerate(sections.get("economic_outcomes", {}).get("data", {}).get("outcomes", [])):
        targets.append((f"economic_{index}", outcome.get("monthly", []), ["top_mean", "bottom_mean"],
                        f"Forward economic observation: {outcome['name']}", "economic_outcomes"))
    for chart_id, rows, fields, title, section in targets:
        svg = _plot(rows, fields, title)
        if svg:
            charts.append({"id": chart_id, "mime_type": "image/svg+xml", "svg": svg,
                           "source_evidence_ids": [f"diagnostic.discovery.{section}"]})
    return charts

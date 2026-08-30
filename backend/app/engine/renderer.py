"""Dashboard PNG renderer — premium matplotlib dashboard from a DashboardSpec.

The renderer is deterministic: given the same spec → same PNG. All values are
read from the metric registry. The output is a high-resolution (200 DPI) PNG
suitable for presentation, review, and client sharing. No PBIX/PBIT/HTML.
"""

from __future__ import annotations

import io
from typing import Any

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from app.engine.context import DashboardPanel, DashboardSpec
from app.engine.metric_registry import MetricRegistry

# Brand-neutral premium palette.
COLORS = {
    "primary": "#1a1a2e",
    "accent": "#16213e",
    "highlight": "#0f3460",
    "accent2": "#e94560",
    "kpi_bg": "#f0f4f8",
    "text": "#1a1a2e",
    "text_light": "#6b7280",
    "white": "#ffffff",
    "positive": "#10b981",
    "negative": "#ef4444",
    "neutral": "#6b7280",
    "chart1": "#2563eb",
    "chart2": "#10b981",
    "chart3": "#f59e0b",
    "chart4": "#ef4444",
    "chart5": "#8b5cf6",
    "chart6": "#06b6d4",
    "chart7": "#f97316",
    "chart8": "#84cc16",
}

CHART_COLORS = [COLORS[f"chart{i}"] for i in range(1, 9)]


def render_dashboard(spec: DashboardSpec, registry: MetricRegistry) -> bytes:
    """Render the spec to a PNG and return the bytes.

    Statsmodels imports are deferred to this module; nothing else in the engine
    imports matplotlib.
    """
    n_panels = len(spec.panels)
    if n_panels == 0:
        return _empty_dashboard(spec.title)

    # Layout: responsive grid.
    cols = spec.columns
    rows = 1
    if n_panels <= cols:
        rows = 1
        grid_cols = n_panels
    else:
        grid_cols = cols
        rows = (n_panels + cols - 1) // cols

    # Include title row.
    total_rows = rows + 1  # +1 for title bar

    fig = plt.figure(figsize=(4 * cols, 1.0 + 2.8 * rows), dpi=200)
    fig.patch.set_facecolor(COLORS["kpi_bg"])

    # --- Title bar ---
    ax_title = fig.add_axes([0.04, 0.96, 0.92, 0.035])
    ax_title.set_facecolor(COLORS["primary"])
    ax_title.set_xticks([])
    ax_title.set_yticks([])
    ax_title.spines[:].set_visible(False)
    ax_title.text(0.02, 0.5, spec.title, fontsize=11, fontweight="bold",
                  color=COLORS["white"], verticalalignment="center", transform=ax_title.transAxes)
    if spec.note:
        ax_title.text(0.98, 0.5, spec.note, fontsize=6, fontweight="normal",
                      color=COLORS["chart3"], verticalalignment="center",
                      horizontalalignment="right", transform=ax_title.transAxes)

    # --- Panels ---
    for i, panel in enumerate(spec.panels):
        r = i // grid_cols + 1  # 1-indexed after title
        c = i % grid_cols
        ax = fig.add_axes([
            0.04 + c * (0.92 / grid_cols),
            0.92 - r * (0.85 / rows),
            (0.92 / grid_cols) * 0.88,
            (0.85 / rows) * 0.75,
        ])
        ax.set_facecolor(COLORS["white"])
        _draw_panel(ax, panel, registry)

    # --- Date stamp ---
    from datetime import datetime, timezone
    fig.text(0.98, 0.01, f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             fontsize=5, color=COLORS["text_light"], horizontalalignment="right")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", pad_inches=0.1,
                facecolor=COLORS["kpi_bg"])
    plt.close(fig)
    return buf.getvalue()


def _draw_panel(ax, panel: DashboardPanel, registry: MetricRegistry) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines[:].set_visible(False)
    ax.set_title(panel.title, fontsize=7, fontweight="bold", pad=6, color=COLORS["text"])

    if panel.panel_type == "kpi":
        _draw_kpi(ax, panel, registry)
    elif panel.panel_type == "bar":
        _draw_bar(ax, panel, registry)
    elif panel.panel_type == "line":
        _draw_line(ax, panel, registry)
    elif panel.panel_type == "pie":
        _draw_pie(ax, panel, registry)
    elif panel.panel_type == "heatmap":
        _draw_heatmap(ax, panel, registry)
    elif panel.panel_type == "insight_callout":
        _draw_callout(ax, panel)
    else:
        _draw_kpi(ax, panel, registry)


def _kpi_value(panel: DashboardPanel) -> str:
    val = panel.data.get("value", {})
    if isinstance(val, dict):
        v = val.get("value", val.get("display", ""))
        unit = val.get("unit", "")
        if v and isinstance(v, (int, float)):
            return _fmt(v, unit)
        return str(v) if v else "—"
    if isinstance(val, (int, float)):
        return _fmt(val, panel.data.get("unit", ""))
    return str(val) if val else "—"


def _fmt(v: float, unit: str = "") -> str:
    abs_v = abs(v)
    if abs_v >= 1_000_000_000:
        s = f"${v / 1_000_000_000:.2f}B" if unit else f"{v / 1_000_000_000:.2f}B"
    elif abs_v >= 1_000_000:
        s = f"${v / 1_000_000:.2f}M" if unit else f"{v / 1_000_000:.2f}M"
    elif abs_v >= 1_000:
        s = f"${v / 1_000:.1f}K" if unit else f"{v / 1_000:.1f}K"
    else:
        s = f"{v:,.2f}"
    return s


def _draw_kpi(ax, panel, registry):
    """Premium KPI card with value and optional mini trend."""
    val = _kpi_value(panel)
    ax.text(0.5, 0.55, val, fontsize=14, fontweight="bold",
            color=COLORS["primary"], ha="center", va="center",
            transform=ax.transAxes)
    subtitle = ""
    # Check for growth data in the metric.
    mid = panel.data.get("metric_id", "")
    m = registry.get(mid) if mid else None
    if m:
        v = m.value
        if isinstance(v, dict) and "growth_pct" in v:
            g = v["growth_pct"]
            color = COLORS["positive"] if g and g > 0 else (COLORS["negative"] if g and g < 0 else COLORS["neutral"])
            subtitle = f"{g:+.1f}% vs prev period" if g is not None else ""
            ax.text(0.5, 0.2, subtitle, fontsize=5, color=color, ha="center", va="center",
                    transform=ax.transAxes)
        elif isinstance(v, dict) and "direction" in v:
            d = v["direction"]
            color = COLORS["positive"] if d == "up" else (COLORS["negative"] if d == "down" else COLORS["neutral"])
            subtitle = f"Trend: {d}"
            ax.text(0.5, 0.2, subtitle, fontsize=5, color=color, ha="center", va="center",
                    transform=ax.transAxes)


def _draw_bar(ax, panel, registry):
    """Bar chart from registry metric data."""
    mid = panel.data.get("metric_id", "")
    m = registry.get(mid) if mid else None
    if not m:
        return
    data = m.value
    if isinstance(data, dict):
        data = data.get("value", data)
    if isinstance(data, list) and len(data) > 0:
        keys = [str(d.get("key", d.get("name", d.get("period", f"#{i}"))))[:20] for i, d in enumerate(data)]
        vals = [float(d.get("value", d.get("count", 0))) for d in data]
        if not vals:
            return
        colors = CHART_COLORS[:len(keys)]
        bars = ax.barh(range(len(keys)), vals, color=colors, height=0.6)
        ax.set_yticks(range(len(keys)))
        ax.set_yticklabels(keys, fontsize=5)
        ax.set_xlim(0, max(vals) * 1.15)
        ax.invert_yaxis()
        for i, (b, v) in enumerate(zip(bars, vals)):
            ax.text(b.get_width() + max(vals) * 0.01, b.get_y() + b.get_height() / 2,
                    _fmt(v), fontsize=4, va="center", color=COLORS["text_light"])


def _draw_line(ax, panel, registry):
    mid = panel.data.get("metric_id", "")
    m = registry.get(mid) if mid else None
    if not m:
        return
    data = m.value
    if isinstance(data, dict) and "history" in data:
        data = data["history"]
    if isinstance(data, dict) and "value" in data:
        data = data["value"]
    if isinstance(data, list) and len(data) > 0:
        # Try to get values.
        vals = []
        for d in data:
            v = d.get("value", d.get("count", 0))
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                pass
        if len(vals) < 2:
            return
        ax.plot(vals, color=COLORS["chart1"], linewidth=1.5, marker="o", markersize=2.5)
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels([str(d.get("period", d.get("key", f"#{i}")))[:8] for i, d in enumerate(data)], fontsize=4.5, rotation=30)
        ax.set_ylabel("", fontsize=6)
        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(COLORS["kpi_bg"])
        ax.spines["left"].set_visible(True)
        ax.spines["left"].set_color(COLORS["kpi_bg"])
        ax.tick_params(axis="both", labelsize=5)


def _draw_pie(ax, panel, registry):
    mid = panel.data.get("metric_id", "")
    m = registry.get(mid) if mid else None
    if not m:
        return
    data = m.value
    if isinstance(data, dict) and "value" in data:
        data = data["value"]
    if isinstance(data, list) and len(data) > 0:
        vals = [float(d.get("value", 0)) for d in data[:6]]
        labels = [str(d.get("key", d.get("name", f"#{i}")))[:12] for i, d in enumerate(data[:6])]
        if sum(vals) > 0:
            colors = CHART_COLORS[:len(vals)]
            wedges, texts, autotexts = ax.pie(vals, labels=labels, autopct="%1.0f%%",
                                               colors=colors, startangle=90,
                                               textprops={"fontsize": 5})
            for t in autotexts:
                t.set_fontsize(4.5)


def _draw_heatmap(ax, panel, registry):
    mid = panel.data.get("metric_id", "")
    m = registry.get(mid) if mid else None
    if not m:
        return
    data = m.value
    if not isinstance(data, dict):
        return
    # data is a nested dict {col1: {col2: r}}.
    cols = list(data.keys())
    if len(cols) < 2:
        return
    vals = []
    for c1 in cols:
        row = []
        for c2 in cols:
            v = data.get(c1, {}).get(c2)
            if v is None:
                row.append(0.0)
            else:
                row.append(float(v))
        vals.append(row)
    mat = np.array(vals)
    ax.imshow(mat, cmap="RdBu_r", aspect="auto", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels([c[:12] for c in cols], fontsize=4.5, rotation=45, ha="right")
    ax.set_yticklabels([c[:12] for c in cols], fontsize=4.5)
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                    fontsize=4, color="white" if abs(mat[i, j]) > 0.5 else "black")


def _draw_callout(ax, panel):
    text = panel.data.get("text", "")
    prompt = panel.data.get("prompt", "")
    ax.set_facecolor(COLORS["highlight"])
    ax.text(0.5, 0.6, text, fontsize=6, color=COLORS["white"],
            ha="center", va="center", transform=ax.transAxes, wrap=True)
    if prompt:
        ax.text(0.5, 0.2, f"Prompt: \"{prompt[:80]}{'...' if len(prompt) > 80 else ''}\"",
                fontsize=4.5, color=COLORS["chart3"], ha="center", va="center",
                transform=ax.transAxes, style="italic")


def _empty_dashboard(title: str) -> bytes:
    """Return a placeholder PNG when there are no panels."""
    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    ax.set_facecolor(COLORS["kpi_bg"])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines[:].set_visible(False)
    ax.text(0.5, 0.7, title, fontsize=14, fontweight="bold", color=COLORS["primary"],
            ha="center", va="center", transform=ax.transAxes)
    ax.text(0.5, 0.4, "No dashboard panels generated\n(no validated metrics available)",
            fontsize=9, color=COLORS["text_light"], ha="center", va="center",
            transform=ax.transAxes)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=COLORS["kpi_bg"])
    plt.close(fig)
    return buf.getvalue()
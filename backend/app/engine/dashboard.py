"""Dashboard spec builder — maps registry + plan + prompt into a layout spec.

The spec drives the renderer; it is not a dashboard itself. The user's prompt is
the authoritative spec for what the dashboard should contain; the registry is the
only source of values.
"""

from __future__ import annotations

from app.engine.context import AnalysisPlan, DashboardPanel, DashboardSpec, DaxMeasure, RunContext
from app.engine.metric_registry import MetricRegistry


def build_dashboard_spec(
    plan: AnalysisPlan,
    registry: MetricRegistry,
    skill_panels: list[dict],
) -> DashboardSpec:
    """Build a dashboard spec from the plan + registry + skill suggestions.

    KPIs and charts are selected based on the prompt and available metrics.
    Every panel references a metric_id; the renderer pulls the value from the
    registry at render time.
    """
    panels: list[DashboardPanel] = []
    validated = registry.validated()

    # 1. KPI cards from validated metrics (prefer totals, then important ones).
    kpi_priority = [
        "m_total_revenue", "m_revenue_growth", "m_customer_customer_count",
        "m_customer_repeat_rate_pct", "m_product_count", "m_inventory_total_stock",
        "m_inventory_turnover", "m_customer_avg_revenue_per_customer"
    ]
    kpi_panels = []
    for mid in kpi_priority:
        m = registry.get(mid)
        if m and m.validation_status == "validated":
            kpi_panels.append(DashboardPanel(
                panel_type="kpi",
                title=m.name,
                data={"metric_id": mid, "value": m.value, "unit": m.value.get("unit", "") if isinstance(m.value, dict) else ""},
                position=(0, len(kpi_panels)),
                width=1, height=1,
            ))

    # 2. Chart panels from skill suggestions + prompt.
    chart_panels: list[DashboardPanel] = []
    used_suggestions = set()
    for sp in skill_panels:
        mid = sp.get("metric_id")
        if not mid or mid in used_suggestions:
            continue
        m = registry.get(mid)
        if not m or m.validation_status != "validated":
            continue
        used_suggestions.add(mid)

        panel_type = sp.get("panel_type", "kpi")
        if panel_type not in ("kpi", "bar", "line", "pie", "heatmap", "stacked_bar"):
            panel_type = "bar"

        chart_panels.append(DashboardPanel(
            panel_type=panel_type,
            title=sp.get("title", m.name),
            data={"metric_id": mid, "value": m.value,
                  "unit": m.value.get("unit", "") if isinstance(m.value, dict) else ""},
            position=(0, 0),
            width=1 if panel_type == "kpi" else 2,  # charts span 2 cols
            height=1,
        ))

    # 3. Insight callouts (top 3 high-priority).
    if plan.prompt and registry.get("m_total_revenue"):
        chart_panels.append(DashboardPanel(
            panel_type="insight_callout",
            title="Analysis Overview",
            data={"text": "Analysis generated from the user's prompt. "
                          "See the full report for detailed insights and recommendations.",
                   "prompt": plan.prompt[:200]},
            position=(0, 0),
            width=3, height=1,
        ))

    # 4. Assemble layout.
    row = 0

    # Row 0: insight callout if present.
    callouts = [p for p in chart_panels if p.panel_type == "insight_callout"]
    non_callouts = [p for p in chart_panels if p.panel_type != "insight_callout"]
    for p in callouts:
        p.position = (row, 0)
        row += 1

    # Row 1+: KPIs in a row.
    for i, p in enumerate(kpi_panels):
        p.position = (row, i)
    if kpi_panels:
        row += 1

    # Next rows: charts.
    for i, p in enumerate(non_callouts):
        p.position = (row + i // 3, i % 3)

    total_rows = row + max(1, (len(non_callouts) + 2) // 3)

    # 5. Date range note.
    date_range_str = None
    for m in validated:
        src = m.source or {}
        if src.get("grain") == "period" and m.value:
            break

    return DashboardSpec(
        panels=kpi_panels + non_callouts,
        columns=3,
        title="Dashboard",
        note=f"Based on analysis prompt: {plan.prompt[:100]}{'...' if len(plan.prompt) > 100 else ''}",
    )
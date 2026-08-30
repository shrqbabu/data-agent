"""Dashboard PNG renderer + spec builder tests."""

import pandas as pd
import pytest

from app.engine.dashboard import build_dashboard_spec
from app.engine.metric_registry import MetricRegistry
from app.engine.renderer import render_dashboard
from app.engine.context import DashboardPanel, DashboardSpec, AnalysisPlan, SchemaModel


def _registry() -> MetricRegistry:
    reg = MetricRegistry()
    reg.add_simple("m_total_revenue", "Total Revenue", 1200000, unit="currency")
    reg.add_simple("m_revenue_growth", "Revenue Growth", {"pct": 15.0, "direction": "up"})
    reg.add_simple("m_customer_customer_count", "Customer Count", 450)
    reg.add_simple("m_customer_repeat_rate_pct", "Repeat Rate %", 62.5)
    return reg


def test_renderer_produces_png_bytes():
    reg = _registry()
    spec = DashboardSpec(
        panels=[
            DashboardPanel(panel_type="kpi", title="Total Revenue",
                           data={"metric_id": "m_total_revenue"}, position=(0, 0)),
            DashboardPanel(panel_type="kpi", title="Customer Count",
                           data={"metric_id": "m_customer_customer_count"}, position=(0, 1)),
        ],
        title="Test Dashboard",
    )
    png = render_dashboard(spec, reg)
    assert len(png) > 1000
    assert png[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


def test_renderer_handles_empty_spec():
    spec = DashboardSpec(panels=[], title="Empty")
    png = render_dashboard(spec, MetricRegistry())
    assert len(png) > 100


def test_png_displays_registry_values():
    """Verify the rendered spec contains the registry's display values."""
    reg = _registry()
    spec = build_dashboard_spec(
        AnalysisPlan(prompt="test", sections=["KPIs"], selected_skills=["sales"],
                     requested_kpis=[], dimensions=[]),
        reg,
        [{"panel_type": "kpi", "title": "Total Revenue", "metric_id": "m_total_revenue"}],
    )
    # The kpi panel should reference the metric_id.
    kpi = [p for p in spec.panels if p.panel_type == "kpi"]
    assert kpi
    assert kpi[0].data.get("metric_id") == "m_total_revenue"


def test_dashboard_builder_uses_prompt():
    reg = _registry()
    plan = AnalysisPlan(prompt="Analyze sales by region", sections=["KPIs", "Regions"],
                        selected_skills=["sales", "customer"], requested_kpis=[],
                        dimensions=[])
    spec = build_dashboard_spec(plan, reg, [])
    assert spec.note and "sales" in spec.note.lower()
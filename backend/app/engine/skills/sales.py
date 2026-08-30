"""Sales analysis skill."""

from __future__ import annotations

import pandas as pd

from app.engine.calculations import (
    aggregate, contribution, fmt_compact, fmt_num, growth, growth_between_periods,
    missing_summary, period_summary, pick_amount_column, pick_date_column, total,
)
from app.engine.context import SchemaModel
from app.engine.metric_registry import MetricRegistry
from app.engine.skills.base import Skill


class SalesSkill(Skill):
    domain = "sales"

    def detect(self, prompt: str, model: SchemaModel) -> float:
        if not model.amount_columns:
            return 0.0
        keywords = ["revenue", "sales", "sell", "order", "pipeline", "booking", "deal", "margin"]
        text = prompt.lower()
        hits = sum(1 for kw in keywords if kw in text)
        # Bonus for having both date + amount.
        has_date = bool(model.date_columns)
        base = 0.3 if (hits > 0 or has_date) else 0.1
        return min(1.0, base + hits * 0.15)

    def analyze(self, ctx, registry, tables):
        df = ctx.df
        if df is None or df.empty:
            return []
        model = ctx.schema_model
        insights = []

        amount_col = pick_amount_column(df, model)
        date_col = pick_date_column(df, model)

        if not amount_col:
            registry.not_supported("m_total_revenue", "Total Revenue",
                                   "No amount/revenue column detected in the dataset.")
            return insights

        # --- Total Revenue ---
        rev = total(df[amount_col])
        registry.add_simple("m_total_revenue", "Total Revenue", rev,
                            unit="currency", dimension="sales",
                            formula=f"SUM({amount_col})",
                            source={"table": "data", "column": amount_col})

        # --- Revenue by category (if dimensions exist) ---
        dims = [c for c in model.categorical_columns if c in df.columns][:3]
        for dim in dims:
            contrib = contribution(df, dim, amount_col)
            metric_id = f"m_revenue_by_{dim}"
            registry.add_simple(metric_id, f"Revenue by {dim}", contrib,
                                unit="", dimension="sales",
                                formula=f"SUM({amount_col}) GROUP BY {dim}",
                                source={"table": "data", "column": amount_col, "grain": dim})

            insight = {
                "title": f"Revenue by {dim}",
                "finding": f"Top {dim} concentration: top contributor = {contrib[0]['key']} ({fmt_num(contrib[0]['share_pct'])})% of revenue.",
                "evidence": [{"metric_id": metric_id, "value": contrib[:3]}],
                "confidence": "high",
                "priority": "medium",
            }
            insights.append(insight)

        # --- Revenue over time (period analysis) ---
        if date_col:
            period_data = period_summary(df, date_col, amount_col)
            registry.add_simple("m_revenue_by_period", "Revenue by Period",
                                period_data, unit="currency", dimension="sales",
                                formula=f"SUM({amount_col}) GROUP BY period",
                                source={"table": "data", "column": amount_col, "grain": "period"})

            growth_data = growth_between_periods(df, date_col, amount_col)
            if growth_data["current"] is not None:
                registry.add_simple("m_revenue_growth", "Revenue Growth (Latest Period)",
                                    growth_data, unit="", dimension="sales",
                                    formula=f"GROWTH(SUM({amount_col}), previous period)",
                                    source={"table": "data", "column": amount_col})

                direction = growth_data.get("direction", "flat")
                pct_val = growth_data["growth_pct"]
                pct_str = f"{pct_val:+.1f}%" if pct_val is not None else "N/A"
                insights.append({
                    "title": "Revenue Trend",
                    "finding": f"Revenue {direction} {pct_str} from {growth_data.get('previous_period')} to {growth_data.get('period')}.",
                    "evidence": [{"metric_id": "m_revenue_growth", "value": growth_data},
                                 {"metric_id": "m_revenue_by_period", "value": period_data[-3:]}],
                    "confidence": "high",
                    "priority": "high",
                })

                # --- Growth stability ---
                from app.engine.statistics import growth_stability
                vals = [p["value"] for p in period_data]
                stab = growth_stability(vals)
                registry.add_simple("m_revenue_growth_stability", "Revenue Growth Stability",
                                    stab, dimension="sales",
                                    source={"table": "data", "column": amount_col, "grain": "period"})
                if stab["trend"] != "flat":
                    insights.append({
                        "title": "Revenue Growth Stability",
                        "finding": f"Revenue shows a {stab['trend']} trend with {stab['up_periods']} up periods and {stab['down_periods']} down periods.",
                        "evidence": [{"metric_id": "m_revenue_growth_stability", "value": stab}],
                        "confidence": "medium",
                        "priority": "medium",
                    })

        # --- Revenue by category breakdown ---
        if dims:
            for dim in dims:
                cats = aggregate(df, dim, amount_col, "sum")[:5]
                registry.add_simple(f"m_revenue_by_{dim}_top5", f"Top 5 {dim} by Revenue",
                                    cats, dimension="sales",
                                    source={"table": "data", "column": amount_col, "grain": dim})

        # --- Missing amounts ---
        missing = missing_summary(df[[amount_col]])
        if missing and missing[0]["missing"] > 0:
            registry.add_simple("m_missing_revenue", "Missing Revenue Values",
                                {"count": missing[0]["missing"], "pct": missing[0]["pct"]},
                                dimension="sales",
                                source={"table": "data", "column": amount_col})

        return insights

    def panel_suggestions(self, registry):
        panels = []
        rev = registry.get("m_total_revenue")
        if rev:
            panels.append({"panel_type": "kpi", "title": "Total Revenue", "metric_id": "m_total_revenue"})
        growth = registry.get("m_revenue_growth")
        if growth:
            panels.append({"panel_type": "kpi", "title": "Revenue Growth", "metric_id": "m_revenue_growth"})
        periods = registry.get("m_revenue_by_period")
        if periods:
            panels.append({"panel_type": "line", "title": "Revenue Trend", "metric_id": "m_revenue_by_period"})
        return panels
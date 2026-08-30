"""Customer analysis skill."""

from __future__ import annotations

import pandas as pd

from app.engine.calculations import (
    contribution, customer_metrics, fmt_compact, fmt_num, new_vs_returning,
    pick_amount_column, pick_date_column, total,
)
from app.engine.context import SchemaModel
from app.engine.metric_registry import MetricRegistry
from app.engine.skills.base import Skill


class CustomerSkill(Skill):
    domain = "customer"

    def detect(self, prompt: str, model: SchemaModel) -> float:
        keywords = ["customer", "client", "retention", "churn", "acquisition", "cohort",
                     "repeat", "loyalty", "lifetime", "clv"]
        text = prompt.lower()
        hits = sum(1 for kw in keywords if kw in text)
        has_customer_id = any("customer" in c.lower() or "client" in c.lower() for c in model.id_columns)
        base = 0.4 if has_customer_id else 0.0
        return min(1.0, base + hits * 0.15)

    def analyze(self, ctx, registry, tables):
        df = ctx.df
        if df is None or df.empty:
            return []
        model = ctx.schema_model
        insights = []

        # Find customer ID column.
        customer_col = next(
            (c for c in model.id_columns if any(kw in c.lower() for kw in ["customer", "client", "user", "member"])),
            None
        )
        if not customer_col:
            # Fallback: any id column with high cardinality.
            for c in model.id_columns:
                if df[c].nunique(dropna=True) / max(len(df), 1) > 0.5:
                    customer_col = c
                    break
        if not customer_col:
            registry.not_supported("m_customer_metrics", "Customer Metrics",
                                   "No customer ID column detected.",
                                   alternative="Use Sales Analysis for revenue-based metrics.")
            return insights

        amount_col = pick_amount_column(df, model)
        date_col = pick_date_column(df, model)

        if not amount_col:
            registry.not_supported("m_customer_metrics", "Customer Revenue Metrics",
                                   "No amount column found for revenue-based customer analysis.")
            return insights

        # --- Customer KPIs ---
        cm = customer_metrics(df, customer_col, date_col, amount_col) if date_col else {}
        if cm:
            for k, v in cm.items():
                metric_id = f"m_customer_{k}"
                registry.add_simple(metric_id, f"Customer {k.replace('_', ' ').title()}", v,
                                    unit="", dimension="customer",
                                    formula=f"COMPUTE({k})",
                                    source={"table": "data", "column": customer_col})

            insights.append({
                "title": "Customer Overview",
                "finding": f"{cm.get('customer_count', 0):,} total customers, "
                           f"{cm.get('repeat_rate_pct', 0):.1f}% repeat purchase rate, "
                           f"avg revenue per customer: {fmt_compact(cm.get('avg_revenue_per_customer', 0), '')}.",
                "evidence": [{"metric_id": "m_customer_customer_count", "value": cm.get("customer_count")},
                             {"metric_id": "m_customer_repeat_rate_pct", "value": cm.get("repeat_rate_pct")},
                             {"metric_id": "m_customer_avg_revenue_per_customer", "value": cm.get("avg_revenue_per_customer")}],
                "confidence": "high",
                "priority": "high",
            })

            if cm.get("repeat_customers", 0) > 0:
                repeat_rate = cm.get("repeat_rate_pct", 0)
                insights.append({
                    "title": "Customer Retention",
                    "finding": f"{repeat_rate:.1f}% of customers have made repeat purchases. "
                               f"{cm.get('churned_proxy_count', 0)} inactive accounts detected (inactivity > {cm.get('inactivity_threshold_days', 90):.0f} days proxy).",
                    "evidence": [{"metric_id": "m_customer_repeat_rate_pct", "value": repeat_rate},
                                 {"metric_id": "m_customer_churned_proxy_count", "value": cm.get("churned_proxy_count")}],
                    "confidence": "medium",
                    "priority": "high",
                    "recommendation": "Implement a re-engagement campaign for inactive accounts.",
                })

        # --- New vs Returning by period ---
        if date_col and customer_col:
            nvr = new_vs_returning(df, customer_col, date_col)
            if nvr:
                registry.add_simple("m_customer_new_vs_returning", "New vs Returning Customers",
                                    nvr, dimension="customer",
                                    source={"table": "data", "column": customer_col, "grain": "period"})
                latest = list(nvr.values())[-1] if nvr else {}
                if latest:
                    new_pct = latest["new"] / max(latest["new"] + latest["returning"], 1) * 100
                    insights.append({
                        "title": "New Customer Acquisition",
                        "finding": f"New customers represent {new_pct:.1f}% of recent activity.",
                        "evidence": [{"metric_id": "m_customer_new_vs_returning", "value": latest}],
                        "confidence": "medium",
                        "priority": "medium",
                    })

        # --- Top customers ---
        cats = contribution(df, customer_col, amount_col, 5)
        if cats:
            top_share = cats[0]["share_pct"] if cats else 0
            registry.add_simple("m_customer_top5_share", "Top 5 Customer Revenue Share",
                                cats, dimension="customer",
                                source={"table": "data", "column": customer_col, "grain": "customer"})
            insights.append({
                "title": "Customer Concentration",
                "finding": f"Top customer represents {top_share:.1f}% of revenue. "
                           f"{'High concentration risk.' if top_share > 30 else 'Concentration is manageable.'}",
                "evidence": [{"metric_id": "m_customer_top5_share", "value": cats[:3]}],
                "confidence": "high",
                "priority": "medium",
            })

        return insights

    def panel_suggestions(self, registry):
        panels = []
        for mid in ["m_customer_customer_count", "m_customer_repeat_rate_pct"]:
            m = registry.get(mid)
            if m:
                panels.append({"panel_type": "kpi", "title": m.name, "metric_id": mid})
        nvr = registry.get("m_customer_new_vs_returning")
        if nvr:
            panels.append({"panel_type": "bar", "title": "New vs Returning Customers", "metric_id": "m_customer_new_vs_returning"})
        return panels
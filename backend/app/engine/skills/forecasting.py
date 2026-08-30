"""Forecasting skill — wraps the deterministic forecast engine."""

from __future__ import annotations

import pandas as pd

from app.engine.calculations import pick_amount_column, pick_date_column
from app.engine.context import SchemaModel
from app.engine.forecast import forecast_series
from app.engine.metric_registry import MetricRegistry
from app.engine.skills.base import Skill


class ForecastingSkill(Skill):
    domain = "forecasting"

    def detect(self, prompt: str, model: SchemaModel) -> float:
        keywords = ["forecast", "predict", "trend", "projection", "next month", "next year",
                     "future", "seasonality"]
        text = prompt.lower()
        hits = sum(1 for kw in keywords if kw in text)
        # Requires date + numeric.
        has_prereqs = bool(model.date_columns) and bool(model.numeric_columns)
        base = 0.5 if (has_prereqs and hits > 0) else 0.0
        return min(1.0, base + hits * 0.2)

    def analyze(self, ctx, registry, tables):
        df = ctx.df
        if df is None or df.empty:
            return []
        model = ctx.schema_model
        insights = []

        date_col = pick_date_column(df, model)
        amount_col = pick_amount_column(df, model)

        if not date_col or not amount_col:
            registry.not_supported("m_forecast", "Forecast",
                                   "Forecasting requires a date column and a numeric/amount column.")
            return insights

        # Forecast 6 periods ahead.
        result = forecast_series(df, date_col, amount_col, horizon=6)
        registry.add_simple("m_forecast_result", "Revenue Forecast", result,
                            dimension="forecasting",
                            formula=f"ETS({amount_col} BY {date_col})",
                            source={"table": "data", "column": amount_col, "grain": "period"})

        if result["forecast"] and result["confidence"]:
            insights.append({
                "title": "Forecast",
                "finding": f"Forecast generated ({result['method']}). "
                           f"Confidence: {result['confidence']:.1%}. "
                           f"Next period value: {result['forecast'][0].get('value', 0):,.2f}.",
                "evidence": [{"metric_id": "m_forecast_result", "value": result}],
                "confidence": "medium" if result["confidence"] > 0.3 else "low",
                "priority": "high",
            })

        if result.get("notes"):
            insights.append({
                "title": "Forecast Notes",
                "finding": " | ".join(result["notes"]),
                "evidence": [{"metric_id": "m_forecast_result", "value": result}],
                "confidence": "high",
                "priority": "low",
            })

        return insights

    def panel_suggestions(self, registry):
        m = registry.get("m_forecast_result")
        if m:
            return [{"panel_type": "line", "title": "Forecast", "metric_id": "m_forecast_result"}]
        return []
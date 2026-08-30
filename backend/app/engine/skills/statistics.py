"""Statistics skill — distributions, correlations, outliers, and significance tests."""

from __future__ import annotations

import pandas as pd

from app.engine.calculations import correlation_matrix, descriptive_stats, distribution, fmt_num
from app.engine.context import SchemaModel
from app.engine.metric_registry import MetricRegistry
from app.engine.skills.base import Skill
from app.engine.statistics import correlation_significance, normality_p_value, outliers_iqr


class StatisticsSkill(Skill):
    domain = "statistics"

    def detect(self, prompt: str, model: SchemaModel) -> float:
        keywords = ["statistic", "correlation", "distribution", "outlier", "significance",
                     "variance", "regression", "segment", "describe", "summary"]
        text = prompt.lower()
        hits = sum(1 for kw in keywords if kw in text)
        has_numeric = len(model.numeric_columns) >= 2
        base = 0.5 if has_numeric else 0.1
        return min(1.0, base + hits * 0.15)

    def analyze(self, ctx, registry, tables):
        df = ctx.df
        if df is None or df.empty:
            return []
        model = ctx.schema_model
        insights = []

        numeric_cols = [c for c in model.numeric_columns if c in df.columns]
        if len(numeric_cols) < 2:
            registry.not_supported("m_stats_correlations", "Correlation Analysis",
                                   "Need at least 2 numeric columns for correlation analysis.")
            return insights

        # --- Descriptive statistics for each numeric column ---
        for col in numeric_cols:
            desc = descriptive_stats(df[col])
            if desc:
                registry.add_simple(f"m_stats_desc_{col}", f"Descriptive Stats: {col}", desc,
                                    dimension="statistics",
                                    source={"table": "data", "column": col})

        # --- Correlation matrix ---
        corr = correlation_matrix(df, numeric_cols)
        if corr:
            registry.add_simple("m_stats_correlation_matrix", "Correlation Matrix", corr,
                                dimension="statistics",
                                source={"table": "data", "columns": numeric_cols})

            # Find strong correlations (|r| > 0.7).
            strong = []
            for c1, row in corr.items():
                for c2, r in row.items():
                    if c1 < c2 and r is not None and abs(r) > 0.7:
                        strong.append((c1, c2, r))
            if strong:
                registry.add_simple("m_stats_strong_correlations", "Strong Correlations", strong,
                                    dimension="statistics")
                # Top insight.
                pair = max(strong, key=lambda x: abs(x[2]))
                insights.append({
                    "title": "Key Correlation",
                    "finding": f"Strong correlation between {pair[0]} and {pair[1]} (r = {pair[2]:.3f}). "
                               f"{'This is a significant relationship worth investigating.' if abs(pair[2]) > 0.85 else ''}",
                    "evidence": [{"metric_id": "m_stats_strong_correlations", "value": pair}],
                    "confidence": "high",
                    "priority": "high",
                })

        # --- Outliers ---
        for col in numeric_cols:
            o = outliers_iqr(df[col])
            if o and o["count"] > 0:
                registry.add_simple(f"m_stats_outliers_{col}", f"Outliers: {col}", o,
                                    dimension="statistics",
                                    source={"table": "data", "column": col})
                if o["count"] > 5:
                    insights.append({
                        "title": f"Outlier Detection: {col}",
                        "finding": f"{col} has {o['count']} outlier(s) outside [{fmt_num(o['lower'])}, {fmt_num(o['upper'])}].",
                        "evidence": [{"metric_id": f"m_stats_outliers_{col}", "value": o}],
                        "confidence": "high",
                        "priority": "low",
                    })

        # --- Normality check on the first numeric column ---
        if numeric_cols:
            p = normality_p_value(df[numeric_cols[0]])
            if p is not None:
                registry.add_simple("m_stats_normality_p", f"Normality p-value: {numeric_cols[0]}",
                                    {"p_value": p, "normal_for_p_gt_0_05": p > 0.05},
                                    dimension="statistics",
                                    source={"table": "data", "column": numeric_cols[0]})

        # --- Distribution (histogram) of important columns ---
        for col in numeric_cols[:3]:
            dist = distribution(df[col], bins=10)
            if dist:
                registry.add_simple(f"m_stats_distribution_{col}", f"Distribution: {col}", dist,
                                    dimension="statistics",
                                    source={"table": "data", "column": col})

        return insights

    def panel_suggestions(self, registry):
        panels = []
        corr = registry.get("m_stats_correlation_matrix")
        if corr:
            panels.append({"panel_type": "heatmap", "title": "Correlation Matrix", "metric_id": "m_stats_correlation_matrix"})
        return panels
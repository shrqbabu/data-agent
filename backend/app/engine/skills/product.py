"""Product analysis skill."""

from __future__ import annotations

import pandas as pd

from app.engine.calculations import (
    aggregate, contribution, fmt_compact, fmt_num, pick_amount_column, total,
)
from app.engine.context import SchemaModel
from app.engine.metric_registry import MetricRegistry
from app.engine.skills.base import Skill


class ProductSkill(Skill):
    domain = "product"

    def detect(self, prompt: str, model: SchemaModel) -> float:
        keywords = ["product", "sku", "category", "item", "brand", "assortment", "portfolio"]
        text = prompt.lower()
        hits = sum(1 for kw in keywords if kw in text)
        has_product_col = any(kw in c.lower() for c in model.id_columns for kw in ["product", "sku", "item"])
        base = 0.3 if (hits > 0 or has_product_col) else 0.0
        return min(1.0, base + hits * 0.15)

    def analyze(self, ctx, registry, tables):
        df = ctx.df
        if df is None or df.empty:
            return []
        model = ctx.schema_model
        insights = []

        amount_col = pick_amount_column(df, model)
        if not amount_col:
            registry.not_supported("m_product_metrics", "Product Metrics",
                                   "No amount column found for revenue-based product analysis.")
            return insights

        # Find product ID/category columns.
        product_col = next(
            (c for c in model.id_columns if any(kw in c.lower() for kw in ["product", "sku", "item"])),
            None
        )
        category_col = next(
            (c for c in model.categorical_columns if any(kw in c.lower() for kw in ["category", "brand", "group", "line"])),
            None
        )

        if not product_col:
            product_col = category_col  # fallback

        if not product_col:
            registry.not_supported("m_product_metrics", "Product Metrics",
                                   "No product or category column detected.")
            return insights

        # --- Product count ---
        n_products = int(df[product_col].nunique(dropna=True))
        registry.add_simple("m_product_count", "Product Count", n_products,
                            dimension="product",
                            source={"table": "data", "column": product_col})

        # --- Top products by revenue ---
        top_contrib = contribution(df, product_col, amount_col, 10)
        if top_contrib:
            registry.add_simple("m_product_top10_share", "Top 10 Product Contribution",
                                top_contrib, dimension="product",
                                source={"table": "data", "column": product_col, "grain": "product"})
            if top_contrib[0]["share_pct"] > 15:
                insights.append({
                    "title": "Product Concentration",
                    "finding": f"Top product '{top_contrib[0]['key']}' represents {fmt_num(top_contrib[0]['share_pct'])}% of revenue.",
                    "evidence": [{"metric_id": "m_product_top10_share", "value": top_contrib[:3]}],
                    "confidence": "high",
                    "priority": "medium",
                })

        # --- By category ---
        if category_col and category_col != product_col:
            cat_contrib = contribution(df, category_col, amount_col, 5)
            if cat_contrib:
                registry.add_simple("m_product_category_share", "Category Revenue Share",
                                    cat_contrib, dimension="product",
                                    source={"table": "data", "column": category_col})

                insights.append({
                    "title": "Category Performance",
                    "finding": f"Top category '{cat_contrib[0]['key']}' = {fmt_num(cat_contrib[0]['share_pct'])}% of revenue.",
                    "evidence": [{"metric_id": "m_product_category_share", "value": cat_contrib}],
                    "confidence": "high",
                    "priority": "medium",
                })

        # --- Avg revenue per product ---
        if n_products > 0:
            rev = total(df[amount_col])
            avg = rev / n_products
            registry.add_simple("m_product_avg_revenue", "Avg Revenue per Product", avg,
                                unit="currency", dimension="product",
                                source={"table": "data", "column": amount_col, "grain": product_col})

        return insights

    def panel_suggestions(self, registry):
        panels = []
        mid = "m_product_top10_share"
        m = registry.get(mid)
        if m:
            panels.append({"panel_type": "bar", "title": "Products by Revenue", "metric_id": mid})
        return panels
"""Inventory analysis skill — works with stock, turnover, and supply-chain data."""

from __future__ import annotations

import pandas as pd

from app.engine.calculations import (
    aggregate, correlation_matrix, descriptive_stats, fmt_compact, fmt_num,
    pick_amount_column, total,
)
from app.engine.context import SchemaModel
from app.engine.metric_registry import MetricRegistry
from app.engine.skills.base import Skill


class InventorySkill(Skill):
    domain = "inventory"

    def detect(self, prompt: str, model: SchemaModel) -> float:
        keywords = ["inventory", "stock", "warehouse", "reorder", "turnover", "supply",
                     "out of stock", "backorder", "stockout"]
        text = prompt.lower()
        hits = sum(1 for kw in keywords if kw in text)
        # Detect stock columns in schema.
        stock_cols = [c for c in model.numeric_columns if any(kw in c.lower() for kw in ["stock", "qty", "quantity", "inventory", "on_hand", "balance"])]
        has_stock = bool(stock_cols)
        base = 0.4 if has_stock else 0.0
        return min(1.0, base + hits * 0.15)

    def analyze(self, ctx, registry, tables):
        df = ctx.df
        if df is None or df.empty:
            return []
        model = ctx.schema_model
        insights = []

        # Find stock and cost columns.
        stock_col = next(
            (c for c in model.numeric_columns if any(kw in c.lower() for kw in ["stock", "qty", "quantity", "on_hand", "balance", "inventory"])),
            None
        )
        cost_col = next(
            (c for c in model.numeric_columns if any(kw in c.lower() for kw in ["cost", "unit_cost", "cogs", "total_cost"])),
            None
        )
        amount_col = pick_amount_column(df, model)

        if not stock_col:
            registry.not_supported("m_inventory_metrics", "Inventory Metrics",
                                   "No stock/quantity column detected. "
                                   "Consider adding a column with stock-on-hand or quantity values.",
                                   alternative="Use Sales Analysis for revenue-based metrics.")
            return insights

        # --- Total stock units ---
        stock_total = total(df[stock_col])
        registry.add_simple("m_inventory_total_stock", "Total Stock Units", stock_total,
                            unit="units", dimension="inventory",
                            formula=f"SUM({stock_col})",
                            source={"table": "data", "column": stock_col})

        # --- Stock levels by product/category ---
        product_col = next(
            (c for c in model.id_columns if any(kw in c.lower() for kw in ["product", "sku", "item"])),
            None
        )
        if product_col:
            top_stock = aggregate(df, product_col, stock_col, "sum")[:10]
            registry.add_simple("m_inventory_top10_stock", "Top 10 Stock by Product",
                                top_stock, dimension="inventory",
                                source={"table": "data", "column": stock_col, "grain": product_col})

        # --- Stockout proxy (zero/min stock items) ---
        zero_stock = int((df[stock_col] <= 0).sum())
        if zero_stock > 0:
            registry.add_simple("m_inventory_zero_stock", "Zero Stock Items", zero_stock,
                                unit="items", dimension="inventory",
                                source={"table": "data", "column": stock_col})
            insights.append({
                "title": "Stockout Risk",
                "finding": f"{zero_stock:,} items have zero stock. "
                           f"{'Immediate replenishment review recommended.' if zero_stock > 10 else 'Monitor closely.'}",
                "evidence": [{"metric_id": "m_inventory_zero_stock", "value": zero_stock}],
                "confidence": "high",
                "priority": "high" if zero_stock > 10 else "medium",
            })

        # --- Stock turnover proxy (cost column == sold) ---
        if cost_col and stock_total > 0:
            cogs = total(df[cost_col])
            turnover = cogs / stock_total if stock_total > 0 else 0
            registry.add_simple("m_inventory_turnover", "Inventory Turnover (Proxy)",
                                {"turnover": round(turnover, 2), "cogs": cogs, "avg_stock": stock_total},
                                dimension="inventory",
                                formula=f"SUM({cost_col}) / SUM({stock_col})",
                                source={"table": "data"})
            insights.append({
                "title": "Inventory Turnover",
                "finding": f"Inventory turnover ratio: {turnover:.2f}x. "
                           f"{'High turnover indicates efficient stock management.' if turnover > 6 else 'Consider reviewing stock levels.'}",
                "evidence": [{"metric_id": "m_inventory_turnover", "value": {"turnover": turnover}}],
                "confidence": "medium",
                "priority": "medium",
            })

        # --- Stock value (if cost available) ---
        if cost_col and stock_col:
            stock_value = total(df[cost_col])  # using cost column as unit cost proxy
            # Better: stock qty * unit cost. Requires a clear unit_cost column.
            unit_cost_col = next((c for c in model.numeric_columns if "unit_cost" in c.lower()), None)
            if unit_cost_col:
                stock_value = float((pd.to_numeric(df[stock_col], errors="coerce") * pd.to_numeric(df[unit_cost_col], errors="coerce")).sum(skipna=True))
                registry.add_simple("m_inventory_stock_value", "Stock Value", stock_value,
                                    unit="currency", dimension="inventory",
                                    formula=f"SUM({stock_col} * {unit_cost_col})",
                                    source={"table": "data"})
                insights.append({
                    "title": "Inventory Value",
                    "finding": f"Total stock value: {fmt_compact(stock_value, '')}.",
                    "evidence": [{"metric_id": "m_inventory_stock_value", "value": stock_value}],
                    "confidence": "high",
                    "priority": "medium",
                })

        # --- Descriptive stats ---
        stats = descriptive_stats(df[stock_col])
        if stats:
            registry.add_simple("m_inventory_stock_stats", "Stock Level Statistics", stats,
                                dimension="inventory",
                                source={"table": "data", "column": stock_col})

        return insights

    def panel_suggestions(self, registry):
        panels = []
        for mid in ["m_inventory_total_stock", "m_inventory_zero_stock"]:
            m = registry.get(mid)
            if m:
                panels.append({"panel_type": "kpi", "title": m.name, "metric_id": mid})
        return panels
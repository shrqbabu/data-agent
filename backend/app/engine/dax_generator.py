"""DAX generation — deterministic mapping from the ACTUAL schema + metric registry.

Never generates PBIX/PBIT and never invents table or column names. Every
reference resolves to a real table/column in the dataset schema. Output is
grouped by: Base, Sales, Customer, Product, Inventory, Time Intelligence, Growth,
Advanced. Only applicable groups are emitted.
"""

from __future__ import annotations

import re

from app.engine.context import DaxMeasure, SchemaModel
from app.engine.metric_registry import Metric, MetricRegistry

# DAX function words we can safely use. Everything else must reference
# Table[Column] or [Measure].
SAFE_FUNCTIONS = {
    "SUM", "SUMX", "AVERAGE", "AVERAGEX", "DIVIDE", "CALCULATE", "FILTER",
    "ALL", "ALLSELECTED", "VALUES", "DISTINCT", "DISTINCTCOUNT", "COUNTROWS",
    "MAX", "MIN", "SUM", "COUNT", "COUNTA", "VAR", "RETURN", "EARLIER",
    "RANKX", "TOPN", "IF", "SWITCH", "TRUE", "FALSE", "BLANK", "ISBLANK",
    "HASONEVALUE", "SELECTEDVALUE", "DATEADD", "SAMEPERIODLASTYEAR",
    "PREVIOUSMONTH", "PREVIOUSYEAR", "PARALLELPERIOD", "TOTALYTD", "TOTALMTD",
    "STARTOFYEAR", "ENDOFYEAR", "DATESBETWEEN", "RELATED", "DIVIDE",
}

RESERVED_WORDS = {
    "CALCULATE", "FILTER", "ALL", "DISTINCT", "VALUES", "VAR", "RETURN",
    "SUM", "SUMX", "DIVIDE", "IF", "SWITCH", "TRUE", "FALSE", "BLANK",
    "DATEADD", "SAMEPERIODLASTYEAR", "TOTALYTD", "CALCULATETABLE", "TOPN",
}


def _col_ref(table: str, col: str) -> str:
    return f"{table}[{col}]"


def _escaped_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9 _%()-]", "", name)


def metric_to_dax(m: Metric, table: str, all_metrics: list[Metric]) -> DaxMeasure | None:
    """Map a registry metric to a DAX measure definition."""
    mid = m.metric_id
    source = m.source or {}
    col = source.get("column")
    grain = source.get("grain")
    name = m.name
    deps: list[str] = []
    group = m.dimension or "Base Measures"

    dax = None
    if mid == "m_total_revenue" and col:
        dax = f"{name} =\n    SUM ( {_col_ref(table, col)} )"

    elif mid == "m_revenue_growth" and col:
        dax = (
            f"{name} =\n"
            f"    VAR Current = SUM ( {_col_ref(table, col)} )\n"
            f"    VAR Previous =\n"
            f"        CALCULATE ( SUM ( {_col_ref(table, col)} ),\n"
            f"            PREVIOUSMONTH ( {_col_ref(table, m.source.get('date_col', table + '[date]'))} ) )\n"
            f"    RETURN\n"
            f"        DIVIDE ( Current - Previous, Previous, 0 )"
        )
        # Note: growth measure is group Growth Measures.

    elif mid == "m_revenue_by_period" and col:
        dax = (
            f"{name} =\n"
            f"    VAR SelectedPeriod =\n"
            f"        SELECTEDVALUE ( {_col_ref(table, m.source.get('date_col', 'date'))} )\n"
            f"    RETURN\n"
            f"        CALCULATE ( SUM ( {_col_ref(table, col)} ),\n"
            f"            ALL ( {_col_ref(table, m.source.get('date_col', 'date'))} ),\n"
            f"            {_col_ref(table, m.source.get('date_col', 'date'))} <= SelectedPeriod )"
        )

    elif mid.startswith("m_revenue_by_") and col:
        dim = mid.replace("m_revenue_by_", "")
        dax = (
            f"{name} =\n"
            f"    SUM ( {_col_ref(table, col)} )\n"
            f"    -- Segment by {_escaped_name(dim)} in report visuals"
        )

    elif mid == "m_customer_customer_count":
        c = m.source.get("column", "customer_id")
        dax = f"{name} =\n    DISTINCTCOUNT ( {_col_ref(table, c)} )"

    elif mid == "m_customer_repeat_rate_pct":
        c = m.source.get("column", "customer_id")
        dax = (
            f"{name} =\n"
            f"    VAR TotalCustomers = DISTINCTCOUNT ( {_col_ref(table, c)} )\n"
            f"    VAR RepeatCustomers =\n"
            f"        COUNTROWS ( FILTER ( VALUES ( {_col_ref(table, c)} ),\n"
            f"            CALCULATE ( COUNTROWS ( {table} ) ) > 1 ) )\n"
            f"    RETURN\n"
            f"        DIVIDE ( RepeatCustomers, TotalCustomers, 0 )"
        )

    elif mid == "m_customer_avg_revenue_per_customer" and col:
        c = m.source.get("column", "customer_id")
        dax = (
            f"{name} =\n"
            f"    DIVIDE ( SUM ( {_col_ref(table, col)} ),\n"
            f"        DISTINCTCOUNT ( {_col_ref(table, c)} ), 0 )"
        )

    elif mid == "m_product_count":
        c = m.source.get("column", "product_id")
        dax = f"{name} =\n    DISTINCTCOUNT ( {_col_ref(table, c)} )"

    elif mid == "m_inventory_total_stock" and col:
        dax = f"{name} =\n    SUM ( {_col_ref(table, col)} )"

    elif mid == "m_inventory_turnover":
        dax = (
            f"{name} =\n"
            f"    VAR Cost = SUM ( {_col_ref(table, m.source.get('column', 'cost'))} )\n"
            f"    VAR AvgStock = AVERAGE ( {_col_ref(table, m.source.get('column', 'stock_qty'))} )\n"
            f"    RETURN\n"
            f"        DIVIDE ( Cost, AvgStock, 0 )"
        )

    # Generic fallback for remaining validated metrics.
    if dax is None and m.validation_status == "validated":
        if col:
            dax = f"{name} =\n    SUM ( {_col_ref(table, col)} )"
        else:
            dax = f"{name} =\n    -- Computed during analysis; value: {m.display_value()}"

    if dax is None:
        return None

    # Determine dependency names referenced as [Other Measure].
    refs = set(re.findall(r"\[\s*([^\]\s][^\]]*?)\s*\]", dax))
    for r in refs:
        if r != name and any(other.name == r for other in all_metrics):
            deps.append(r)

    return DaxMeasure(
        name=name,
        dax_code=dax,
        purpose=m.definition,
        dependencies=deps,
        validation_status="unvalidated",
    )


def generate_dax(registry: MetricRegistry, model: SchemaModel) -> list[DaxMeasure]:
    """Generate the full DAX measure set, organized by group."""
    metrics = [m for m in registry.all() if m.validation_status == "validated"]
    table = "data"  # single-table datasets are loaded as table 'data'

    measures: list[DaxMeasure] = []
    seen: set[str] = set()
    for m in metrics:
        dm = metric_to_dax(m, table, metrics)
        if dm and dm.name not in seen:
            measures.append(dm)
            seen.add(dm.name)

    # --- Time Intelligence (only if a date column exists) ---
    if model.date_columns:
        date_col = model.date_columns[0]
        measures.extend(_time_intelligence(registry, table, date_col, seen))

    # --- Advanced (only when relevant metrics exist) ---
    if any(m.metric_id.startswith("m_stats_") for m in metrics):
        measures.append(DaxMeasure(
            name="Top Product by Revenue",
            dax_code=(
                "Top Product by Revenue =\n"
                f"    CALCULATE (\n"
                f"        MAX ( {table}[{_safe_col(model)}] ),\n"
                f"        TOPN ( 1, VALUES ( {table}[{_safe_dim(model)}] ),\n"
                f"            SUM ( {table}[{_safe_amount(model)}] ) ) )"
            ),
            purpose="Highest-grossing product (requires a product/dimension column).",
            dependencies=[],
        ))

    # Group + sort measures into canonical group order.
    group_order = [
        "Base Measures", "Sales Measures", "Customer Measures", "Product Measures",
        "Inventory Measures", "Time Intelligence", "Growth Measures", "Advanced",
    ]
    grouped: dict[str, list[DaxMeasure]] = {}
    for dm in measures:
        group = _group_of(dm, metrics)
        grouped.setdefault(group, []).append(dm)

    ordered: list[DaxMeasure] = []
    for g in group_order:
        if g in grouped:
            ordered.extend(grouped[g])
    return ordered


def _group_of(dm: DaxMeasure, metrics: list[Metric]) -> str:
    for m in metrics:
        if m.name == dm.name:
            if dm.name == "Revenue Growth %" or "Growth" in m.name:
                return "Growth Measures"
            if m.dimension == "sales":
                return "Sales Measures"
            if m.dimension == "customer":
                return "Customer Measures"
            if m.dimension == "product":
                return "Product Measures"
            if m.dimension == "inventory":
                return "Inventory Measures"
            if m.dimension == "statistics" or m.dimension == "forecasting":
                return "Advanced"
    return "Base Measures"


def _safe_col(model: SchemaModel) -> str:
    return (model.id_columns and next(iter(model.id_columns))) or (model.categorical_columns and model.categorical_columns[0]) or "id"


def _safe_dim(model: SchemaModel) -> str:
    return (model.categorical_columns and model.categorical_columns[0]) or "category"


def _safe_amount(model: SchemaModel) -> str:
    return (model.amount_columns and model.amount_columns[0]) or (model.numeric_columns and model.numeric_columns[0]) or "value"


def _time_intelligence(registry: MetricRegistry, table: str, date_col: str, seen: set[str]) -> list[DaxMeasure]:
    base = "Total Revenue"
    if registry.get("m_total_revenue"):
        base = registry.get("m_total_revenue").name  # type: ignore[union-attr]
    col_ref = f"{table}[{date_col}]"
    out: list[DaxMeasure] = []

    candidates = [
        DaxMeasure(
            name="Revenue YTD",
            dax_code=(
                "Revenue YTD =\n"
                f"    TOTALYTD ( [{base}], {col_ref} )"
            ),
            purpose="Cumulative revenue from the start of the year to the latest date.",
            dependencies=[base],
        ),
        DaxMeasure(
            name="Revenue YoY %",
            dax_code=(
                "Revenue YoY % =\n"
                f"    VAR Current = [{base}]\n"
                f"    VAR Previous =\n"
                f"        CALCULATE ( [{base}], SAMEPERIODLASTYEAR ( {col_ref} ) )\n"
                f"    RETURN\n"
                f"        DIVIDE ( Current - Previous, Previous, 0 )"
            ),
            purpose="Year-over-year growth of revenue.",
            dependencies=[base],
        ),
        DaxMeasure(
            name="Previous Month Revenue",
            dax_code=(
                "Previous Month Revenue =\n"
                f"    CALCULATE ( [{base}], PREVIOUSMONTH ( {col_ref} ) )"
            ),
            purpose="Revenue in the prior month (context-dependent).",
            dependencies=[base],
        ),
    ]
    out.extend(c for c in candidates if c.name not in seen)
    return out
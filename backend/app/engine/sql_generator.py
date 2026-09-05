"""SQL query, DDL schema, and analytical query generator.

Generates production-grade DDL schemas, Common Table Expressions (CTEs),
Window functions (ROW_NUMBER, DENSE_RANK, LAG, LEAD), Cohort retention,
and indexing recommendations across PostgreSQL, MySQL, T-SQL, and Snowflake.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.engine.context import SchemaModel
from app.engine.metric_registry import Metric, MetricRegistry


class SqlQueryItem(BaseModel):
    title: str
    query_type: str  # DDL, Window Function, CTE, Aggregation, Index
    dialect: str     # PostgreSQL, MySQL, T-SQL, Snowflake
    sql_code: str
    explanation: str
    expected_columns: List[str]
    indexing_suggestion: Optional[str] = None


def generate_sql_queries(registry: MetricRegistry, model: SchemaModel, prompt: str = "") -> List[Dict[str, Any]]:
    """Generate comprehensive SQL queries tailored to the dataset schema."""
    queries: List[SqlQueryItem] = []

    table_name = "analytics_records"
    amount_col = (model.amount_columns and model.amount_columns[0]) or (model.numeric_columns and model.numeric_columns[0]) or "revenue"
    date_col = (model.date_columns and model.date_columns[0]) or "transaction_date"
    cat_col = (model.categorical_columns and model.categorical_columns[0]) or "category"
    id_col = (model.id_columns and next(iter(model.id_columns))) or "id"

    # 1. DDL Schema Definition with Data Types and Indexes
    col_defs = []
    for col_dict in model.tables.get("data", []):
        c_name = col_dict.get("name", "col")
        c_kind = col_dict.get("kind", "categorical")
        dtype_str = "VARCHAR(255)"
        if c_kind == "numeric" or c_kind == "amount":
            dtype_str = "NUMERIC(15, 2)"
        elif c_kind == "date":
            dtype_str = "TIMESTAMP WITH TIME ZONE"
        elif c_kind == "id":
            dtype_str = "VARCHAR(100) PRIMARY KEY" if c_name == id_col else "VARCHAR(100)"
        col_defs.append(f"    {c_name:<25} {dtype_str}")

    ddl_cols = ",\n".join(col_defs) if col_defs else f"    {id_col} VARCHAR(100) PRIMARY KEY,\n    {amount_col} NUMERIC(15,2)"

    ddl_sql = f"""-- ==========================================================
-- Production DDL Table Definition (PostgreSQL / Snowflake)
-- ==========================================================
CREATE TABLE IF NOT EXISTS {table_name} (
{ddl_cols},
    created_at                TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Recommended B-Tree Indexes for Query Acceleration
CREATE INDEX IF NOT EXISTS idx_{table_name}_{cat_col} ON {table_name} ({cat_col});
CREATE INDEX IF NOT EXISTS idx_{table_name}_{date_col} ON {table_name} ({date_col} DESC);"""

    queries.append(SqlQueryItem(
        title="DDL Table Schema & Index Strategy",
        query_type="DDL",
        dialect="PostgreSQL / Snowflake / MySQL",
        sql_code=ddl_sql,
        explanation="Standard normalized table schema with high-performance composite indexes on filter and time-series columns.",
        expected_columns=["table_created", "indexes_applied"],
        indexing_suggestion=f"B-Tree index on ({cat_col}, {date_col}) to satisfy index-only scans for aggregate queries."
    ))

    # 2. Executive KPI & MoM Growth Window Function Query
    window_sql = f"""-- ==========================================================
-- Monthly Aggregate with Window Functions (MoM Growth & Running Total)
-- ==========================================================
WITH monthly_stats AS (
    SELECT
        DATE_TRUNC('month', {date_col}) AS report_month,
        COUNT(DISTINCT {id_col})       AS total_transactions,
        SUM({amount_col})              AS monthly_revenue,
        AVG({amount_col})              AS avg_order_value
    FROM {table_name}
    WHERE {amount_col} IS NOT NULL
    GROUP BY DATE_TRUNC('month', {date_col})
)
SELECT
    report_month,
    total_transactions,
    monthly_revenue,
    avg_order_value,
    -- Prior Month Revenue via LAG Window Function
    LAG(monthly_revenue, 1) OVER (ORDER BY report_month) AS prev_month_revenue,
    -- Month-over-Month Growth %
    ROUND(
        (monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY report_month))
        / NULLIF(LAG(monthly_revenue, 1) OVER (ORDER BY report_month), 0) * 100.0,
        2
    ) AS mom_growth_pct,
    -- Cumulative Running Total
    SUM(monthly_revenue) OVER (ORDER BY report_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue
FROM monthly_stats
ORDER BY report_month DESC;"""

    queries.append(SqlQueryItem(
        title="Monthly Trend, MoM Growth % & Running Total (Window CTE)",
        query_type="Window Function",
        dialect="ANSI SQL / PostgreSQL / Snowflake / BigQuery",
        sql_code=window_sql,
        explanation="Calculates monthly totals, previous month baseline with LAG(), growth rate variance, and running totals in a single pass.",
        expected_columns=["report_month", "total_transactions", "monthly_revenue", "mom_growth_pct", "cumulative_revenue"],
        indexing_suggestion=f"Ensure composite index on ({date_col}, {amount_col}) exists."
    ))

    # 3. Pareto 80/20 & Dense Rank Analysis
    pareto_sql = f"""-- ==========================================================
-- Pareto 80/20 Distribution & Category Ranking
-- ==========================================================
WITH category_totals AS (
    SELECT
        {cat_col},
        SUM({amount_col}) AS total_volume,
        COUNT(*)          AS record_count
    FROM {table_name}
    GROUP BY {cat_col}
),
ranked_distribution AS (
    SELECT
        {cat_col},
        total_volume,
        record_count,
        DENSE_RANK() OVER (ORDER BY total_volume DESC) AS rank_order,
        SUM(total_volume) OVER ()                      AS grand_total,
        SUM(total_volume) OVER (ORDER BY total_volume DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_volume
    FROM category_totals
)
SELECT
    rank_order,
    {cat_col},
    total_volume,
    ROUND((total_volume / grand_total * 100.0), 2) AS pct_of_total,
    ROUND((cumulative_volume / grand_total * 100.0), 2) AS cumulative_pct,
    CASE
        WHEN (cumulative_volume / grand_total * 100.0) <= 80.0 THEN 'Top 80% (Core Driver)'
        ELSE 'Long Tail (20%)'
    END AS pareto_tier
FROM ranked_distribution
ORDER BY rank_order ASC;"""

    queries.append(SqlQueryItem(
        title="Pareto 80/20 Rule & Dense Rank Category Breakdown",
        query_type="CTE",
        dialect="PostgreSQL / T-SQL / MySQL 8.0+",
        sql_code=pareto_sql,
        explanation="Applies Pareto 80/20 principle by computing category rankings and cumulative contribution percentage.",
        expected_columns=["rank_order", cat_col, "total_volume", "pct_of_total", "cumulative_pct", "pareto_tier"]
    ))

    return [q.model_dump() for q in queries]

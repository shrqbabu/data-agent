"""Star Schema Data Modeler for Power BI.

Classifies tables into Fact and Dimension entities, defines primary/foreign key
mappings, determines cardinality (1:N), cross-filter directions, and generates
the recommended Power BI DAX Date Table script.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from app.engine.context import SchemaModel


class StarTable(BaseModel):
    name: str
    type: str  # FACT or DIMENSION
    primary_key: Optional[str] = None
    foreign_keys: List[Dict[str, str]] = []
    columns: List[str]
    description: str


class StarRelationship(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str  # "1:N" or "N:1" or "1:1"
    cross_filter_direction: str  # "Single" or "Both"
    is_active: bool = True


class StarSchemaResult(BaseModel):
    model_name: str
    fact_tables: List[StarTable]
    dimension_tables: List[StarTable]
    relationships: List[StarRelationship]
    date_table_dax: str
    modeling_recommendations: List[str]


def generate_star_schema(model: SchemaModel) -> Dict[str, Any]:
    """Analyze the schema and construct an optimized Star Schema representation."""
    tables_meta = model.tables.get("data", [])

    amount_cols = model.amount_columns or model.numeric_columns or []
    cat_cols = model.categorical_columns or []
    date_cols = model.date_columns or []
    id_cols = list(model.id_columns.keys()) if model.id_columns else []

    primary_id = id_cols[0] if id_cols else (tables_meta[0]["name"] if tables_meta else "RecordID")
    primary_date = date_cols[0] if date_cols else "OrderDate"

    # 1. Fact Table definition
    fact_cols = [c["name"] for c in tables_meta if c["name"] in (amount_cols + id_cols + date_cols)]
    if not fact_cols:
        fact_cols = [c["name"] for c in tables_meta]

    fact_table = StarTable(
        name="Fact_Transactions",
        type="FACT",
        primary_key=primary_id,
        foreign_keys=[
            {"column": primary_date, "references_table": "Dim_Date", "references_column": "Date"},
            {"column": "CategoryID", "references_table": "Dim_Category", "references_column": "CategoryID"}
        ],
        columns=fact_cols,
        description="Central transactional table containing granular metrics, timestamps, and foreign keys."
    )

    # 2. Dimension Tables
    dimension_tables: List[StarTable] = []

    # Dim_Date
    dimension_tables.append(StarTable(
        name="Dim_Date",
        type="DIMENSION",
        primary_key="Date",
        foreign_keys=[],
        columns=["Date", "Year", "Quarter", "Month", "MonthName", "DayOfWeek", "FiscalYear", "IsWeekend"],
        description="Conformed Date dimension enabling robust time-intelligence DAX functions."
    ))

    # Dim_Category / Dim_Entity
    if cat_cols:
        dimension_tables.append(StarTable(
            name="Dim_Category",
            type="DIMENSION",
            primary_key=cat_cols[0],
            foreign_keys=[],
            columns=cat_cols[:5],
            description="Categorical attribute dimension for slicing and dicing metrics."
        ))

    # 3. Relationships
    relationships: List[StarRelationship] = []

    if date_cols:
        relationships.append(StarRelationship(
            from_table="Dim_Date",
            from_column="Date",
            to_table="Fact_Transactions",
            to_column=primary_date,
            cardinality="1:N",
            cross_filter_direction="Single",
            is_active=True
        ))

    if cat_cols:
        relationships.append(StarRelationship(
            from_table="Dim_Category",
            from_column=cat_cols[0],
            to_table="Fact_Transactions",
            to_column=cat_cols[0],
            cardinality="1:N",
            cross_filter_direction="Single",
            is_active=True
        ))

    # 4. Recommended Date Table DAX
    date_table_dax = f"""-- ==========================================================
-- Enterprise DAX Date Dimension Table
-- In Power BI: Modeling -> New Table -> Paste Formula
-- ==========================================================
Dim_Date =
VAR MinYear = YEAR ( MIN ( 'Fact_Transactions'[{primary_date}] ) )
VAR MaxYear = YEAR ( MAX ( 'Fact_Transactions'[{primary_date}] ) )
RETURN
    ADDCOLUMNS (
        CALENDAR ( DATE ( MinYear, 1, 1 ), DATE ( MaxYear, 12, 31 ) ),
        "Year", YEAR ( [Date] ),
        "YearMonth", FORMAT ( [Date], "YYYY-MM" ),
        "MonthNumber", MONTH ( [Date] ),
        "MonthName", FORMAT ( [Date], "MMMM" ),
        "MonthShort", FORMAT ( [Date], "MMM" ),
        "Quarter", "Q" & FORMAT ( [Date], "Q" ),
        "YearQuarter", YEAR ( [Date] ) & "-Q" & FORMAT ( [Date], "Q" ),
        "DayOfWeekNumber", WEEKDAY ( [Date], 2 ),
        "DayOfWeekName", FORMAT ( [Date], "dddd" ),
        "IsWeekend", IF ( WEEKDAY ( [Date], 2 ) IN {{ 6, 7 }}, TRUE (), FALSE () )
    )"""

    recommendations = [
        "Mark 'Dim_Date' as an Official Date Table in Power BI to ensure Time-Intelligence DAX functions operate properly.",
        "Maintain single-directional cross-filtering (1:N) from Dimensions to Facts to avoid ambiguous filter paths.",
        "Hide raw foreign key and amount columns in the Fact table to force users to use explicit DAX measures.",
        "Sort 'MonthName' column by 'MonthNumber' in Power BI column tools to prevent alphabetical month ordering."
    ]

    result = StarSchemaResult(
        model_name="Executive_Star_Schema",
        fact_tables=[fact_table],
        dimension_tables=dimension_tables,
        relationships=relationships,
        date_table_dax=date_table_dax,
        modeling_recommendations=recommendations
    )

    return result.model_dump()

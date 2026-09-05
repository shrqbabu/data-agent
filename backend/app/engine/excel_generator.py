"""Excel formula, Power Query (M-code), and VBA macro generator.

Generates modern Excel formulas (LET, LAMBDA, XLOOKUP, FILTER, UNIQUE, SUMIFS),
Power Query ETL transformations, and automation macros derived deterministically
from the dataset schema and metric registry.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.engine.context import SchemaModel
from app.engine.metric_registry import Metric, MetricRegistry


class ExcelFormulaItem(BaseModel):
    name: str
    category: str  # Dynamic Array, Lookup, Aggregation, Logic, Power Query, VBA
    formula: str
    target_range: str
    explanation: str
    example_output: str
    m_code: Optional[str] = None
    vba_code: Optional[str] = None


def generate_excel_formulas(registry: MetricRegistry, model: SchemaModel, prompt: str = "") -> List[Dict[str, Any]]:
    """Generate modern Excel formulas, Power Query scripts, and VBA macros."""
    metrics = [m for m in registry.all() if m.validation_status == "validated"]
    items: List[ExcelFormulaItem] = []

    # Identify primary columns
    amount_col = (model.amount_columns and model.amount_columns[0]) or (model.numeric_columns and model.numeric_columns[0]) or "B"
    date_col = (model.date_columns and model.date_columns[0]) or "A"
    cat_col = (model.categorical_columns and model.categorical_columns[0]) or "C"
    id_col = (model.id_columns and next(iter(model.id_columns))) or "A"

    # 1. Dynamic Array Modern KPI summary (LET + SUM + FILTER)
    items.append(ExcelFormulaItem(
        name="Dynamic Total with Criteria (LET & FILTER)",
        category="Dynamic Array",
        formula=f'=LET(\n    data_range, Table1[{amount_col}],\n    filter_col, Table1[{cat_col}],\n    criteria, "SelectedCategory",\n    SUM(FILTER(data_range, filter_col = criteria, 0))\n)',
        target_range="Summary!B2",
        explanation=f"Calculates the total {amount_col} dynamically using LET and FILTER for memory-efficient computation without volatile array formulas.",
        example_output="$1,245,800.00"
    ))

    # 2. Advanced XLOOKUP with Fallback
    items.append(ExcelFormulaItem(
        name="Safe 2-Way XLOOKUP with Error Handling",
        category="Lookup",
        formula=f'=XLOOKUP(E2, Table1[{id_col}], Table1[{amount_col}], "Not Found", 0, 1)',
        target_range="Lookup!F2:F100",
        explanation=f"Exact match lookup of {id_col} returning {amount_col} with automatic missing value fallback.",
        example_output="$450.00"
    ))

    # 3. Dynamic Unique Categories & Aggregation (UNIQUE + SUMIFS)
    items.append(ExcelFormulaItem(
        name="Auto-Spilling Category Summary Table",
        category="Dynamic Array",
        formula=f'=LET(\n    categories, SORT(UNIQUE(Table1[{cat_col}])),\n    totals, BYROW(categories, LAMBDA(r, SUMIFS(Table1[{amount_col}], Table1[{cat_col}], r))),\n    HSTACK(categories, totals)\n)',
        target_range="Report!A5#",
        explanation=f"Automatically spills unique {cat_col} values sorted alphabetically with corresponding {amount_col} totals in a single formula.",
        example_output="[Electronics | $45,000], [Furniture | $32,000]"
    ))

    # 4. Top N Items Dynamic Sorter
    items.append(ExcelFormulaItem(
        name="Top 5 High-Value Records (CHOOSEROWS + SORT)",
        category="Dynamic Array",
        formula=f'=CHOOSEROWS(SORT(Table1, MATCH("{amount_col}", Table1[#Headers], 0), -1), SEQUENCE(5))',
        target_range="TopRankings!A2#",
        explanation=f"Dynamically returns the top 5 rows sorted descending by {amount_col}.",
        example_output="5 top performing rows"
    ))

    # 5. Month-over-Month Growth Calculation
    if model.date_columns:
        items.append(ExcelFormulaItem(
            name="Period Growth Rate (%)",
            category="Aggregation",
            formula=f'=IFERROR((SUMIFS(Table1[{amount_col}], Table1[{date_col}], ">="&E2, Table1[{date_col}], "<="&EOMONTH(E2,0)) - SUMIFS(Table1[{amount_col}], Table1[{date_col}], ">="&EDATE(E2,-1), Table1[{date_col}], "<="&EOMONTH(EDATE(E2,-1),0))) / SUMIFS(Table1[{amount_col}], Table1[{date_col}], ">="&EDATE(E2,-1), Table1[{date_col}], "<="&EOMONTH(EDATE(E2,-1),0)), 0)',
            target_range="Trend!D2",
            explanation="Calculates exact percentage variance between current month and prior month with zero division protection.",
            example_output="+14.2%"
        ))

    # 6. Power Query ETL Transformation (M-Code)
    m_code = f"""let
    Source = Csv.Document(File.Contents("C:\\Data\\dataset.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{
        {{"{amount_col}", type number}},
        {{"{date_col}", type date}},
        {{"{cat_col}", type text}}
    }}),
    #"Cleaned Text" = Table.TransformColumns(#"Changed Type", {{"{cat_col}", Text.Trim, type text}}),
    #"Filtered Rows" = Table.SelectRows(#"Cleaned Text", each ([{amount_col}] <> null and [{amount_col}] > 0))
in
    #"Filtered Rows" """

    items.append(ExcelFormulaItem(
        name="Power Query ETL Cleaning Script (M-Code)",
        category="Power Query",
        formula="Power Query M Script (Paste in Advanced Editor)",
        target_range="Power Query Advanced Editor",
        explanation="Automated data type casting, whitespace stripping, and null/zero value filtering.",
        example_output="Cleaned Excel Data Model Table",
        m_code=m_code
    ))

    # 7. VBA Macro for Instant Pivot Table & Chart Automation
    vba_code = f"""Sub GenerateExecutiveSummaryPivot()
    Dim pc As PivotCache
    Dim pt As PivotTable
    Dim wsData As Worksheet, wsSummary As Worksheet

    Set wsData = ThisWorkbook.Sheets("Sheet1")
    Set wsSummary = ThisWorkbook.Sheets.Add(After:=wsData)
    wsSummary.Name = "Executive_Pivot"

    Set pc = ThisWorkbook.PivotCaches.Create( _
        SourceType:=xlDatabase, _
        SourceData:=wsData.Range("A1").CurrentRegion)

    Set pt = pc.CreatePivotTable( _
        TableDestination:=wsSummary.Range("A3"), _
        TableName:="SummaryPivot")

    With pt
        .PivotFields("{cat_col}").Orientation = xlRowField
        .AddDataField .PivotFields("{amount_col}"), "Total {amount_col}", xlSum
        .PivotFields("Total {amount_col}").NumberFormat = "$#,##0.00"
    End With

    wsSummary.Columns.AutoFit
    MsgBox "Executive Pivot Dashboard Generated Successfully!", vbInformation, "AI Data Analyst"
End Sub"""

    items.append(ExcelFormulaItem(
        name="VBA Automated Pivot Dashboard Macro",
        category="VBA",
        formula="Alt + F11 -> Insert Module -> Run Sub GenerateExecutiveSummaryPivot",
        target_range="VBA Standard Module",
        explanation="1-Click VBA automation to construct a formatted pivot summary and auto-format currencies.",
        example_output="Executive_Pivot worksheet with aggregated KPIs",
        vba_code=vba_code
    ))

    return [item.model_dump() for item in items]

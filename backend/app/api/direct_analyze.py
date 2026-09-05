"""Direct Analysis API endpoint.

Provides instant analysis of uploaded CSV / Excel files with prompt input
and choice of mode:
  1. Excel (Formulas, Power Query M-code, VBA)
  2. Power BI (DAX Measures, Time Intelligence, Star Schema Data Modeling)
  3. SQL (DDL, Window functions, CTEs, Indexing)
Generates high-resolution dashboard PNG visuals and executive summaries.
"""

from __future__ import annotations

import base64
import io
import os
import uuid
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, Response

from app.engine.context import DatasetRecord, RunContext
from app.engine.dax_generator import generate_dax
from app.engine.dax_validator import validate_dax
from app.engine.excel_generator import generate_excel_formulas
from app.engine.insights import generate_insights
from app.engine.llm import LLMClient
from app.engine.metric_registry import MetricRegistry
from app.engine.planner import build_plan
from app.engine.profile import profile_dataframe
from app.engine.quality import assess_quality
from app.engine.renderer import render_dashboard
from app.engine.report import build_report
from app.engine.schema import build_schema_model
from app.engine.schema_modeler import generate_star_schema
from app.engine.skills import CustomerSkill, ForecastingSkill, InventorySkill, ProductSkill, SalesSkill, StatisticsSkill
from app.engine.sql_generator import generate_sql_queries
from app.engine.dashboard import build_dashboard_spec

router = APIRouter(prefix="/api/v1/analyze", tags=["direct-analysis"])


@router.post("/direct")
async def analyze_dataset_direct(
    file: UploadFile = File(...),
    prompt: str = Form(default="Analyze dataset, generate executive summary, KPI metrics, and key measures."),
    mode: str = Form(default="powerbi"),  # excel | powerbi | sql
) -> Dict[str, Any]:
    """Instant analysis of uploaded CSV/Excel with mode selection."""
    mode_normalized = mode.lower().strip()
    if mode_normalized not in ("excel", "powerbi", "sql"):
        mode_normalized = "powerbi"

    # Read uploaded file content
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    filename = file.filename or "dataset.csv"
    filename_lower = filename.lower()

    # Parse to Pandas DataFrame
    try:
        if filename_lower.endswith((".xlsx", ".xls")):
            excel_file = pd.ExcelFile(io.BytesIO(contents))
            first_sheet = excel_file.sheet_names[0]
            df = pd.read_excel(excel_file, sheet_name=first_sheet)
        else:
            # Handle delimiter detection
            sample_text = contents[:4096].decode("utf-8", errors="ignore")
            delim = ";" if ";" in sample_text and sample_text.count(";") > sample_text.count(",") else ","
            df = pd.read_csv(io.BytesIO(contents), sep=delim, on_bad_lines="skip")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse file: {str(e)}"
        )

    if df.empty:
        raise HTTPException(status_code=400, detail="The uploaded dataset contains no rows.")

    # Clean column headers
    df.columns = [str(c).strip() for c in df.columns]

    # Initialize Engine Run Context
    run_id = str(uuid.uuid4())
    ctx = RunContext(
        project_id="direct_run",
        run_id=run_id,
        user_id="direct_user",
        prompt=prompt,
        df=df,
        tables={"data": df}
    )

    # 1. Profile & Quality
    ctx.profile = profile_dataframe(df)
    ctx.schema_model = build_schema_model(df)
    ctx.quality = assess_quality(df, ctx.schema_model)

    # 2. Plan & Registry
    llm = LLMClient()
    ctx.plan = build_plan(prompt, ctx.schema_model, llm)
    registry = MetricRegistry()
    ctx.metrics = registry

    # 3. Deterministic Domain Skills Computation
    skills = [SalesSkill(), CustomerSkill(), ProductSkill(), InventorySkill(), StatisticsSkill(), ForecastingSkill()]
    drafts: list[dict] = []
    panel_suggestions: list[dict] = []

    for s in skills:
        try:
            res = s.analyze(ctx, registry, ctx.tables)
            drafts.extend(res or [])
            panel_suggestions.extend(s.panel_suggestions(registry))
        except Exception:
            pass

    # 4. Insights & Executive Report
    ctx.insights = generate_insights(drafts, registry, llm)
    ctx.report = build_report(ctx.plan, registry, ctx.insights, None, llm)

    # 5. Render Visual Dashboard PNG
    ctx.dashboard_spec = build_dashboard_spec(ctx.plan, registry, panel_suggestions)
    dashboard_bytes = render_dashboard(ctx.dashboard_spec, registry)
    dashboard_base64 = base64.b64encode(dashboard_bytes).decode("utf-8")

    # 6. Mode-Specific Artifact Generation
    dax_measures = []
    star_schema = None
    excel_formulas = []
    sql_queries = []

    if mode_normalized == "powerbi":
        dax_measures = [dm.__dict__ for dm in generate_dax(registry, ctx.schema_model)]
        star_schema = generate_star_schema(ctx.schema_model)
    elif mode_normalized == "excel":
        excel_formulas = generate_excel_formulas(registry, ctx.schema_model, prompt)
    elif mode_normalized == "sql":
        sql_queries = generate_sql_queries(registry, ctx.schema_model, prompt)

    # Format KPI Cards for UI
    kpi_cards = []
    for p in ctx.dashboard_spec.panels:
        if p.panel_type == "kpi":
            v = p.data.get("value", {})
            disp = v.get("display", str(v.get("value", "—"))) if isinstance(v, dict) else str(v)
            kpi_cards.append({
                "title": p.title,
                "value": disp,
                "unit": p.data.get("unit", "")
            })

    return {
        "ok": True,
        "run_id": run_id,
        "mode": mode_normalized,
        "file_name": filename,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [c["name"] for c in ctx.schema_model.tables.get("data", [])],
        "quality_score": ctx.quality.score if ctx.quality else 95.0,
        "executive_summary": ctx.report.get("executive_summary", "Comprehensive analysis performed successfully."),
        "key_findings": ctx.report.get("key_findings", []),
        "kpi_cards": kpi_cards,
        "dashboard_image_base64": dashboard_base64,
        # Mode-specific outputs
        "dax_measures": dax_measures,
        "star_schema": star_schema,
        "excel_formulas": excel_formulas,
        "sql_queries": sql_queries,
        "recommendations": ctx.report.get("recommendations", [
            "Leverage the generated measures/queries in your production workflow.",
            "Verify edge cases against seasonal anomalies."
        ])
    }

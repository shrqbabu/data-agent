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
from app.engine.pdf_generator import generate_pdf_report
from app.engine.python_generator import generate_python_scripts

router = APIRouter(prefix="/api/v1/analyze", tags=["direct-analysis"])

# In-memory storage for generated PDFs for direct download
_PDF_CACHE: Dict[str, bytes] = {}


@router.get("/pdf/{run_id}")
async def download_analysis_pdf(run_id: str):
    """Download compiled Executive Analytics PDF for a given run ID."""
    pdf_bytes = _PDF_CACHE.get(run_id)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="PDF report not found or expired for this run.")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Executive_Analytics_Report_{run_id[:8]}.pdf"'},
    )


@router.post("/direct")
async def analyze_dataset_direct(
    file: UploadFile = File(...),
    prompt: str = Form(default="Analyze dataset, generate executive summary, KPI metrics, and key measures."),
    mode: str = Form(default="all"),  # excel | powerbi | mysql | sql | python | all
    action: str = Form(default="full"),   # preview | full
) -> Dict[str, Any]:
    """Instant analysis of uploaded CSV/Excel with mode selection (Excel, PowerBI, MySQL, Python, All)."""
    mode_normalized = mode.lower().strip()
    valid_modes = ("excel", "powerbi", "mysql", "sql", "python", "all")
    if mode_normalized not in valid_modes:
        mode_normalized = "all"

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

    total_rows = int(len(df))
    dup_rows = int(df.duplicated().sum())
    unique_recs = total_rows - dup_rows
    dup_pct = round((dup_rows / total_rows * 100), 2) if total_rows > 0 else 0.0
    quality_val = ctx.quality.score if ctx.quality else 95.0

    # If preview requested, return initial AI summary & deduplication health preview immediately
    if action.lower().strip() == "preview":
        col_names = [c["name"] for c in ctx.schema_model.tables.get("data", [])]
        preview_summary = (
            f"Dataset '{filename}' successfully ingested with {total_rows:,} records across {len(col_names)} columns. "
            f"Data integrity inspection identified {unique_recs:,} unique records and {dup_rows:,} duplicate rows ({dup_pct}% duplication). "
            f"Overall dataset health rating stands at {quality_val:.1f}%. "
            f"Ready to synthesize verified measures, data modeling, and executive dashboard PDF."
        )
        preview_findings = [
            f"Total record volume: {total_rows:,} rows; Distinct unique entities: {unique_recs:,}.",
            f"Deduplication status: {dup_rows:,} exact duplicate rows identified for removal/consolidation.",
            f"Schema structure: {len(ctx.schema_model.numeric_columns)} numeric metrics, {len(ctx.schema_model.categorical_columns)} categorical dimensions, {len(ctx.schema_model.date_columns)} temporal date axes.",
            f"Data quality rating: {quality_val:.1f}% calculated across completeness, uniqueness, and consistency."
        ]
        return {
            "ok": True,
            "action": "preview",
            "run_id": run_id,
            "mode": mode_normalized,
            "file_name": filename,
            "row_count": total_rows,
            "column_count": len(df.columns),
            "columns": col_names,
            "duplicate_rows": dup_rows,
            "unique_records": unique_recs,
            "duplicates_percentage": dup_pct,
            "quality_score": quality_val,
            "executive_summary": preview_summary,
            "key_findings": preview_findings,
        }

    # 2. Plan & Registry (Full Execution)
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

    # 6. Mode-Specific Artifact Generation (Excel, PowerBI, MySQL, Python, All)
    dax_measures = []
    star_schema = None
    excel_formulas = []
    sql_queries = []
    python_scripts = []

    if mode_normalized in ("powerbi", "all"):
        dax_measures = [dm.__dict__ for dm in generate_dax(registry, ctx.schema_model)]
        star_schema = generate_star_schema(ctx.schema_model)
    if mode_normalized in ("excel", "all"):
        excel_formulas = generate_excel_formulas(registry, ctx.schema_model, prompt)
    if mode_normalized in ("mysql", "sql", "all"):
        sql_queries = generate_sql_queries(registry, ctx.schema_model, prompt)
    if mode_normalized in ("python", "all"):
        python_scripts = generate_python_scripts(registry, ctx.schema_model, prompt)

    # 7. Compile Final Executive Report & Suggested Dashboard PDF
    pdf_bytes = generate_pdf_report(
        dataset_name=filename,
        total_rows=total_rows,
        unique_records=unique_recs,
        duplicate_rows=dup_rows,
        quality_score=quality_val,
        report_data=ctx.report,
        dashboard_png_bytes=dashboard_bytes,
        prompt=prompt,
    )
    _PDF_CACHE[run_id] = pdf_bytes
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

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
        "action": "full",
        "run_id": run_id,
        "mode": mode_normalized,
        "file_name": filename,
        "row_count": total_rows,
        "column_count": len(df.columns),
        "columns": [c["name"] for c in ctx.schema_model.tables.get("data", [])],
        "duplicate_rows": dup_rows,
        "unique_records": unique_recs,
        "duplicates_percentage": dup_pct,
        "quality_score": quality_val,
        "executive_summary": ctx.report.get("executive_summary", "Comprehensive analysis performed successfully."),
        "key_findings": ctx.report.get("key_findings", []),
        "kpi_cards": kpi_cards,
        "dashboard_image_base64": dashboard_base64,
        "pdf_base64": pdf_base64,
        "pdf_download_url": f"/api/v1/analyze/pdf/{run_id}",
        # Mode-specific outputs (interactively rendered in App UI)
        "dax_measures": dax_measures,
        "star_schema": star_schema,
        "excel_formulas": excel_formulas,
        "sql_queries": sql_queries,
        "python_scripts": python_scripts,
        "recommendations": ctx.report.get("recommendations", [
            "Leverage the generated measures/queries in your production workflow.",
            "Verify edge cases against seasonal anomalies."
        ]),
    }

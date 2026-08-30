"""Engine run context — the single mutable object that flows through pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

import pandas as pd

# ---- Forward references ----
MetricRegistry: type = "app.engine.metric_registry.MetricRegistry"
ProfileResult: type = "ProfileResult"
SchemaModel: type = "SchemaModel"
AnalysisPlan: type = "AnalysisPlan"
QualityReport: type = "QualityReport"
Insight: type = "Insight"
ReportResult: type = "ReportResult"
DaxMeasure: type = "DaxMeasure"
DashboardSpec: type = "DashboardSpec"
ValidationResult: type = "ValidationResult"


@dataclass
class DatasetRecord:
    id: str
    project_id: str
    name: str
    source_type: str  # csv, excel, sql
    storage_path: str | None
    file_size: int
    mime_type: str | None
    row_count: int
    column_count: int
    schema: dict  # list of column definitions
    profile: dict  # profiling summary
    created_at: str


@dataclass
class ProfileResult:
    row_count: int
    column_count: int
    columns: list[dict]  # name, type, missing%, unique%, sample
    date_columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    duplicate_rows: int
    date_range: dict | None  # {min, max} for date columns
    tables: int = 1


@dataclass
class SchemaModel:
    tables: dict[str, list[dict]]  # table_name -> [column_def]
    relationships: list[dict]  # [{from_table, from_col, to_table, to_col, confidence}]
    grain: str | None = None
    date_columns: list[str] = field(default_factory=list)
    numeric_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    id_columns: dict[str, str] = field(default_factory=dict)  # col_name -> role
    amount_columns: list[str] = field(default_factory=list)
    time_series_columns: list[str] = field(default_factory=list)


@dataclass
class AnalysisPlan:
    prompt: str
    sections: list[str]  # report sections
    selected_skills: list[str]  # domain names
    requested_kpis: list[str]
    dimensions: list[str]
    filters: list[dict] | None
    visual_requirements: list[str]
    comparisons: list[str] | None
    special_instructions: list[str] | None


@dataclass
class QualityReport:
    score: float  # 0-100
    completeness: dict
    validity: dict
    consistency: dict
    uniqueness: dict
    relationships: dict
    issues: list[dict]  # {severity, category, message, column?}


@dataclass
class Insight:
    title: str
    finding: str
    evidence: list[dict]  # [{metric_id, value}]
    interpretation: str | None = None
    business_impact: str | None = None
    recommendation: str | None = None
    confidence: str = "medium"
    priority: str = "medium"
    # Persisted fields
    id: str | None = None


@dataclass
class ReportResult:
    sections: dict[str, str]  # section_title -> markdown content
    generated_at: str = ""


@dataclass
class DaxMeasure:
    name: str
    dax_code: str
    purpose: str | None = None
    dependencies: list[str] = field(default_factory=list)
    validation_status: str = "unvalidated"
    # Persisted
    id: str | None = None


@dataclass
class DashboardPanel:
    panel_type: str  # kpi, bar, line, pie, table, heatmap, stacked_bar, insight_callout
    title: str
    data: dict  # type-specific: values, labels, series, etc.
    position: tuple[int, int]  # row, col
    width: int = 1  # grid columns
    height: int = 1  # grid rows


@dataclass
class DashboardSpec:
    panels: list[DashboardPanel]
    layout: str = "grid"  # grid, freeform
    columns: int = 3
    title: str = "Dashboard"
    date_range: str | None = None
    note: str | None = None


@dataclass
class ValidationResult:
    passed: bool
    checks: dict[str, bool]  # check_name -> passed
    failures: list[dict]  # {check, detail, severity}
    warnings: list[str]


@dataclass
class RunContext:
    """Mutable context carried through the pipeline."""

    run_id: str
    project_id: str
    owner_id: str
    prompt: str
    stage: str = "queued"
    dataset: DatasetRecord | None = None
    df: pd.DataFrame | None = None
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    profile: ProfileResult | None = None
    quality: QualityReport | None = None
    schema_model: SchemaModel | None = None
    plan: AnalysisPlan | None = None
    metrics: Any = None  # MetricRegistry — set after init
    insights: list[Insight] = field(default_factory=list)
    report: ReportResult | None = None
    dax: list[DaxMeasure] = field(default_factory=list)
    dax_validation: dict | None = None  # {passed, measures: [{name, passed, errors}]}
    dashboard_spec: DashboardSpec | None = None
    dashboard_bytes: bytes | None = None  # raw PNG bytes from the renderer
    dashboard_artifact: dict | None = None  # {id, storage_path, file_name, ...}
    validation: ValidationResult | None = None
    llm: Any = None  # LLMClient
    stage_errors: list[str] = field(default_factory=list)
    progress_callback: Callable[[str, int], Coroutine] | None = None
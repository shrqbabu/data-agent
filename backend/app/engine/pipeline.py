"""Analysis pipeline — orchestrates stages in the canonical order.

VALIDATING_INPUT → PROFILING → DATA_QUALITY → SCHEMA_MODELING → ANALYSIS_PLANNING
→ DETERMINISTIC_CALCULATIONS → BUSINESS_ANALYSIS → STATISTICS
→ FORECASTING_IF_SUPPORTED → INSIGHT_GENERATION → DAX_GENERATION → DAX_VALIDATION
→ DASHBOARD_PNG_GENERATION → FINAL_VALIDATION → COMPLETED / VALIDATION_FAILED

The pipeline is compute-only: it never touches Supabase. Persistence and progress
are handled by the job worker. This keeps the engine testable offline.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import pandas as pd

from app.engine.context import AnalysisPlan, DatasetRecord, ProfileResult, QualityReport, RunContext, SchemaModel
from app.engine.dashboard import build_dashboard_spec
from app.engine.dax_generator import generate_dax
from app.engine.dax_validator import validate_dax
from app.engine.insights import generate_insights
from app.engine.llm import LLMClient
from app.engine.metric_registry import MetricRegistry
from app.engine.planner import build_plan
from app.engine.profile import profile_dataframe
from app.engine.quality import assess_quality
from app.engine.report import build_report
from app.engine.renderer import render_dashboard
from app.engine.schema import build_schema_model
from app.engine.skills import (
    CustomerSkill, ForecastingSkill, InventorySkill, ProductSkill, SalesSkill,
    StatisticsSkill,
)
from app.engine.skills.base import Skill
from app.engine.validator import validate_run

STAGE_ORDER = [
    "VALIDATING_INPUT",
    "PROFILING",
    "DATA_QUALITY",
    "SCHEMA_MODELING",
    "ANALYSIS_PLANNING",
    "DETERMINISTIC_CALCULATIONS",
    "BUSINESS_ANALYSIS",
    "STATISTICS",
    "FORECASTING_IF_SUPPORTED",
    "INSIGHT_GENERATION",
    "DAX_GENERATION",
    "DAX_VALIDATION",
    "DASHBOARD_PNG_GENERATION",
    "FINAL_VALIDATION",
    "COMPLETED",
]

ALL_SKILLS: list[Skill] = [
    SalesSkill(), CustomerSkill(), ProductSkill(), InventorySkill(),
    ForecastingSkill(), StatisticsSkill(),
]


class PipelineError(Exception):
    def __init__(self, message: str, stage: str | None = None):
        super().__init__(message)
        self.stage = stage


class AnalysisPipeline:
    def __init__(
        self,
        llm: LLMClient | None = None,
        render: bool = True,
        persist_callback: Callable[[RunContext], Awaitable[None]] | None = None,
    ):
        self.llm = llm or LLMClient()
        self.render = render
        self.persist_callback = persist_callback

    async def run(
        self,
        ctx: RunContext,
        progress: Callable[[str, int], Awaitable[None]] | None = None,
    ) -> RunContext:
        """Run the full pipeline, mutating ctx. Returns ctx on success; raises
        PipelineError on unrecoverable failure (input/loading)."""
        async def set_stage(stage: str, pct: int) -> None:
            ctx.stage = stage
            if progress:
                await progress(stage, pct)

        # --- VALIDATING_INPUT ---
        await set_stage("VALIDATING_INPUT", 2)
        await self._validate_input(ctx)

        # --- PROFILING ---
        await set_stage("PROFILING", 10)
        ctx.profile = profile_dataframe(ctx.df)

        # --- DATA_QUALITY ---
        await set_stage("DATA_QUALITY", 18)
        ctx.quality = assess_quality(ctx.df, ctx.schema_model)

        # --- SCHEMA_MODELING ---
        await set_stage("SCHEMA_MODELING", 25)
        ctx.schema_model = build_schema_model(ctx.df)
        ctx.schema_model.relationships = relate(ctx)

        # --- ANALYSIS_PLANNING ---
        await set_stage("ANALYSIS_PLANNING", 32)
        ctx.plan = build_plan(ctx.prompt, ctx.schema_model, self.llm)

        # --- DETERMINISTIC_CALCULATIONS + BUSINESS_ANALYSIS (skills) ---
        await set_stage("DETERMINISTIC_CALCULATIONS", 42)
        registry = MetricRegistry()
        ctx.metrics = registry
        drafts: list[dict] = []
        panel_suggestions: list[dict] = []

        selected_skills = self._select_skills(ctx.plan, ctx.schema_model)
        for skill in ALL_SKILLS:
            if skill.domain in selected_skills:
                # Run deterministic computation in a thread (avoids blocking loop).
                result = await asyncio.to_thread(skill.analyze, ctx, registry, ctx.tables)
                drafts.extend(result or [])
                panel_suggestions.extend(skill.panel_suggestions(registry))

        # --- STATISTICS (always when numeric data present) ---
        await set_stage("STATISTICS", 55)
        stats_skill = StatisticsSkill()
        if stats_skill.detect(ctx.prompt, ctx.schema_model) > 0:
            stats_drafts = await asyncio.to_thread(stats_skill.analyze, ctx, registry, ctx.tables)
            drafts.extend(stats_drafts or [])
            panel_suggestions.extend(stats_skill.panel_suggestions(registry))

        # --- FORECASTING_IF_SUPPORTED ---
        await set_stage("FORECASTING_IF_SUPPORTED", 62)
        f_skill = ForecastingSkill()
        if f_skill.domain in selected_skills or "forecast" in ctx.prompt.lower():
            forecast_drafts = await asyncio.to_thread(f_skill.analyze, ctx, registry, ctx.tables)
            drafts.extend(forecast_drafts or [])
            panel_suggestions.extend(f_skill.panel_suggestions(registry))

        # --- INSIGHT_GENERATION ---
        await set_stage("INSIGHT_GENERATION", 70)
        ctx.insights = generate_insights(drafts, registry, self.llm)

        # --- DAX_GENERATION ---
        await set_stage("DAX_GENERATION", 78)
        ctx.dax = generate_dax(registry, ctx.schema_model)

        # --- DAX_VALIDATION ---
        await set_stage("DAX_VALIDATION", 84)
        ctx.dax_validation = validate_dax(ctx.dax, ctx.schema_model)

        # --- DASHBOARD_PNG_GENERATION ---
        await set_stage("DASHBOARD_PNG_GENERATION", 90)
        ctx.dashboard_spec = build_dashboard_spec(ctx.plan, registry, panel_suggestions)
        if self.render:
            ctx.dashboard_bytes = render_dashboard(ctx.dashboard_spec, registry)

        # --- Report (built alongside, from the same registry) ---
        ctx.report = build_report(ctx.plan, registry, ctx.insights,
                                  quality_to_dict(ctx.quality), self.llm)

        # --- FINAL_VALIDATION ---
        await set_stage("FINAL_VALIDATION", 96)
        ctx.validation = validate_run(ctx)

        if self.persist_callback:
            await self.persist_callback(ctx)

        if ctx.validation.passed:
            await set_stage("COMPLETED", 100)
        else:
            await set_stage("VALIDATION_FAILED", 100)
        return ctx

    # ------------------------------------------------------------------
    async def _validate_input(self, ctx: RunContext) -> None:
        if not ctx.prompt or not ctx.prompt.strip():
            raise PipelineError("Report prompt must not be empty.", "VALIDATING_INPUT")
        if len(ctx.prompt) > 8000:
            raise PipelineError("Report prompt exceeds 8000 characters.", "VALIDATING_INPUT")
        if ctx.df is None:
            raise PipelineError("No data frame loaded for the dataset.", "VALIDATING_INPUT")
        if ctx.df.empty:
            raise PipelineError("Dataset is empty.", "VALIDATING_INPUT")

    def _select_skills(self, plan: AnalysisPlan, model: SchemaModel) -> set[str]:
        return set(plan.selected_skills or [])


def relate(ctx: RunContext) -> list[dict]:
    from app.engine.schema import relate_tables
    if len(ctx.tables) > 1:
        return relate_tables(ctx.tables)
    return ctx.schema_model.relationships if ctx.schema_model else []


def quality_to_dict(q: QualityReport | None) -> dict | None:
    if q is None:
        return None
    return {
        "score": q.score,
        "completeness": q.completeness,
        "validity": q.validity,
        "consistency": q.consistency,
        "uniqueness": q.uniqueness,
        "relationships": q.relationships,
        "issues": q.issues,
    }
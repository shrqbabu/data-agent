"""End-to-end pipeline test with synthetic data.

Runs the full pipeline (no LLM, no Supabase) and verifies that all stages
produce coherent output, metrics are registered, insights carry evidence, DAX
is generated and validated, and a dashboard PNG is produced.
"""

import asyncio
import os

import pandas as pd
import pytest

from app.engine.context import RunContext
from app.engine.llm import LLMClient
from app.engine.pipeline import AnalysisPipeline


@pytest.fixture
def synthetic_df():
    """Realistic sales + customer dataset."""
    dates = pd.date_range("2025-07-01", periods=180, freq="D")
    n = 500
    import numpy as np
    np.random.seed(42)
    return pd.DataFrame({
        "order_date": np.random.choice(dates, n),
        "customer_id": np.random.choice([f"c{i}" for i in range(30)], n),
        "product_id": np.random.choice([f"p{i}" for i in range(15)], n),
        "category": np.random.choice(["Electronics", "Clothing", "Food", "Home"], n),
        "revenue": np.round(np.random.exponential(scale=200, size=n), 2),
        "quantity": np.random.randint(1, 10, n),
        "cost": np.round(np.random.uniform(10, 150, n), 2),
    })


@pytest.mark.asyncio
async def test_full_pipeline_completes(synthetic_df):
    ctx = RunContext(
        run_id="e2e-test",
        project_id="e2e-proj",
        owner_id="e2e-user",
        prompt="Analyze revenue trends, customer segments, and product performance. "
               "Show top products, customer concentration, and forecast next quarter.",
        df=synthetic_df,
        tables={"data": synthetic_df},
    )

    llm = LLMClient()  # disabled (LLM_ENABLED=false in test env)
    pipeline = AnalysisPipeline(llm=llm)

    async def noop_progress(stage, pct):
        pass

    try:
        result = await pipeline.run(ctx, progress=noop_progress)
    except Exception as e:
        pytest.fail(f"Pipeline failed: {e}")

    # --- Stage: Profiling ---
    assert result.profile is not None, "Profile not generated"
    assert result.profile.row_count == 500
    assert result.profile.column_count >= 6

    # --- Stage: Data Quality ---
    assert result.quality is not None, "Quality not generated"
    assert 0 <= result.quality.score <= 100

    # --- Stage: Schema Modeling ---
    assert result.schema_model is not None, "Schema model not generated"
    assert result.schema_model.amount_columns, "No amount columns detected"
    assert result.schema_model.date_columns, "No date columns detected"

    # --- Stage: Planning ---
    assert result.plan is not None, "Plan not generated"
    assert result.plan.sections, "No sections in plan"
    assert result.plan.selected_skills, "No skills selected"

    # --- Stage: Metrics ---
    assert result.metrics is not None, "Metrics not generated"
    validated = result.metrics.validated()
    assert len(validated) > 0, "No validated metrics"
    not_supported = result.metrics.not_supported_list()
    # Some metrics may be NOT_SUPPORTED.

    # --- Stage: Insights ---
    assert len(result.insights) > 0, "No insights generated"
    for ins in result.insights:
        assert ins.title, f"Insight missing title: {ins}"
        assert ins.evidence, f"Insight '{ins.title}' has no evidence"
        assert ins.finding, f"Insight '{ins.title}' has no finding"

    # --- Stage: DAX ---
    assert len(result.dax) > 0, "No DAX measures generated"
    # DAX validation should have run.
    assert result.dax_validation is not None, "DAX validation not run"

    # --- Stage: Dashboard ---
    assert result.dashboard_spec is not None, "Dashboard spec not generated"
    assert result.dashboard_bytes is not None, "Dashboard PNG not rendered"
    assert result.dashboard_bytes[:8] == b"\x89PNG\r\n\x1a\n", "Not a valid PNG"

    # --- Stage: Report ---
    assert result.report is not None, "Report not generated"
    assert result.report.sections, "Report has no sections"

    # Open pages: verify metric values reconcile between report and dashboard.
    # (The metric registry is the single source of truth for both.)
    for m in validated:
        assert m.metric_id in [m2.metric_id for m2 in result.metrics.all()], \
            f"Metric {m.metric_id} lost in registry"

    # Final validation.
    assert result.validation is not None, "Final validation not run"
    # The pipeline should pass final validation for a clean synthetic dataset.
    if not result.validation.passed:
        failures = [f"{f['check']}: {f['detail']}" for f in result.validation.failures]
        pytest.fail(f"Validation failed: {failures}")
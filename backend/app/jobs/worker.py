"""Job worker — async analysis job queue.

Starts an analysis run, loads the dataset, creates the engine context, runs the
pipeline, persists all results to Supabase, and updates the status/progress.
All heavy compute runs in `asyncio.to_thread` so the API stays responsive.
"""

from __future__ import annotations

import asyncio
import io
import json
import time
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from app.engine.context import DatasetRecord, RunContext
from app.engine.loader import load_dataframe
from app.engine.pipeline import AnalysisPipeline
from app.engine.llm import LLMClient
from app.services.supabase_client import SupabaseClient


class JobManager:
    """Simple in-process async job queue. Each job runs the full pipeline.

    For production scale, replace with Celery/Arq — the pipeline is stateless
    and the context is serializable.
    """

    def __init__(self, concurrency: int = 2, llm: LLMClient | None = None):
        self._semaphore = asyncio.Semaphore(concurrency)
        self._llm = llm
        self._tasks: set[asyncio.Task] = set()

    def submit(self, run_id: str, admin_id: str, project_id: str, prompt: str) -> None:
        """Schedule an analysis run job in the background."""
        task = asyncio.create_task(self._run_wrapper(run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def submit_dataset_process(self, dataset_id: str) -> str:
        """Schedule dataset processing; returns the internal job id."""
        from app.jobs.processor import process_dataset
        task = asyncio.create_task(self._dataset_wrapper(dataset_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return f"dsproc_{dataset_id[:8]}"

    async def _run_wrapper(self, run_id: str) -> None:
        await self.start_job(run_id, SupabaseClient())

    async def _dataset_wrapper(self, dataset_id: str) -> None:
        async with self._semaphore:
            try:
                from app.jobs.processor import process_dataset
                await process_dataset(dataset_id)
            except Exception as e:
                # Mark the dataset as errored so the UI can surface it.
                try:
                    db = SupabaseClient()
                    ds = await db.select_one("datasets", dataset_id)
                    if ds:
                        await db.update("datasets", dataset_id, {
                            "profile": json.dumps({"processing_error": str(e)[:500]}),
                        })
                except Exception:
                    pass

    async def start_job(self, run_id: str, supabase: SupabaseClient) -> dict:
        async with self._semaphore:
            return await self._execute(run_id, supabase)

    async def _execute(self, run_id: str, supabase: SupabaseClient) -> dict:
        t0 = time.time()
        run: dict = {}
        try:
            # --- Load run ---
            run = await supabase.select_one("analysis_runs", run_id)
            if not run:
                raise RuntimeError(f"Run {run_id} not found")

            # Mark running.
            await supabase.update("analysis_runs", run_id, {
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
            await supabase.append_audit(
                admin_id=run["owner_id"], action="ANALYSIS_STARTED",
                project_id=run["project_id"],
                metadata={"run_id": run_id, "prompt": run["user_prompt"][:200]},
            )

            # --- Load dataset ---
            project = await supabase.select_one("projects", run["project_id"])
            if not project:
                raise RuntimeError("Project not found")

            # Get the most recent dataset for this project.
            datasets = await supabase.select("datasets", {
                "project_id": f"eq.{run['project_id']}",
                "order": "created_at.desc",
                "limit": "1",
            })
            if not datasets:
                raise RuntimeError("No dataset found for this project")
            ds = datasets[0]

            # Download file from storage.
            source_type = ds.get("source_type", "csv")
            storage_path = ds.get("storage_path")
            file_name = ds.get("name", "data.csv")
            df = None
            tables = {}

            if storage_path:
                bucket = "project-inputs"
                data = await supabase.download_file(bucket, storage_path)
                df = await asyncio.to_thread(load_dataframe, data, source_type, file_name)
            else:
                # SQL-based: load from parquet snapshot.
                bucket = "project-artifacts"
                try:
                    parquet_path = f"{run['owner_id']}/{run['project_id']}/sql_snapshot.parquet"
                    data = await supabase.download_file(bucket, parquet_path)
                    df = await asyncio.to_thread(load_dataframe, data, "parquet", "sql_snapshot.parquet")
                except Exception:
                    raise RuntimeError("No stored data found for this SQL dataset.")

            tables["data"] = df

            # --- Build context ---
            ctx = RunContext(
                run_id=run_id,
                project_id=run["project_id"],
                owner_id=run["owner_id"],
                prompt=run["user_prompt"],
                dataset=DatasetRecord(
                    id=ds["id"],
                    project_id=ds["project_id"],
                    name=ds.get("name", "dataset"),
                    source_type=source_type,
                    storage_path=storage_path,
                    file_size=ds.get("file_size", 0),
                    mime_type=ds.get("mime_type"),
                    row_count=ds.get("row_count", 0),
                    column_count=ds.get("column_count", 0),
                    schema=ds.get("schema", {}),
                    profile=ds.get("profile", {}),
                    created_at=ds.get("created_at", ""),
                ),
                df=df,
                tables=tables,
            )

            # --- Progress callback ---
            async def progress(stage: str, pct: int) -> None:
                await supabase.update("analysis_runs", run_id, {
                    "stage": stage,
                    "progress": pct,
                })

            # --- Persistence callback ---
            async def persist(ctx: RunContext) -> None:
                await _persist_ctx(ctx, supabase, run_id, run["owner_id"], run["project_id"])

            # --- Run pipeline ---
            pipeline = AnalysisPipeline(
                llm=self._llm,
                render=True,
                persist_callback=persist,
            )
            ctx = await pipeline.run(ctx, progress=progress)

            # --- Handle validation failure ---
            if ctx.validation and not ctx.validation.passed:
                await supabase.update("analysis_runs", run_id, {
                    "status": "validation_failed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "stage": "VALIDATION_FAILED",
                    "progress": 100,
                })
                await supabase.append_audit(
                    admin_id=run["owner_id"], action="ANALYSIS_FAILED",
                    project_id=run["project_id"],
                    metadata={"run_id": run_id, "reason": "validation_failed",
                              "failures": ctx.validation.failures[:5]},
                )
            else:
                await supabase.update("analysis_runs", run_id, {
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "stage": "COMPLETED",
                    "progress": 100,
                })
                await supabase.append_audit(
                    admin_id=run["owner_id"], action="ANALYSIS_COMPLETED",
                    project_id=run["project_id"],
                    metadata={"run_id": run_id, "duration_s": round(time.time() - t0, 2)},
                )

            # Update project last_run_at.
            await supabase.update("projects", run["project_id"], {
                "last_run_at": datetime.now(timezone.utc).isoformat(),
            })

            return {"run_id": run_id, "status": ctx.validation.passed if ctx.validation else "unknown"}

        except Exception as e:
            # Mark failed.
            try:
                await supabase.update("analysis_runs", run_id, {
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "error": json.dumps({"code": "pipeline_error", "message": str(e)[:500]}),
                })
                await supabase.append_audit(
                    admin_id=run.get("owner_id", ""), action="ANALYSIS_FAILED",
                    project_id=run.get("project_id", ""),
                    metadata={"run_id": run_id, "error": str(e)[:300]},
                )
            except Exception:
                pass
            return {"run_id": run_id, "status": "failed", "error": str(e)}


async def _persist_ctx(ctx: RunContext, supabase: SupabaseClient, run_id: str, owner_id: str, project_id: str) -> None:
    """Persist pipeline results to Supabase tables."""
    from datetime import timezone

    # --- Metrics ---
    for m in ctx.metrics.all():
        await supabase.insert("metrics", {
            "analysis_run_id": run_id,
            "metric_id": m.metric_id,
            "name": m.name,
            "definition": m.definition,
            "formula": m.formula,
            "value": json.dumps(m.value, default=str),
            "source": json.dumps(m.source, default=str),
            "validation_status": m.validation_status,
        })

    # --- Insights ---
    for ins in ctx.insights:
        await supabase.insert("insights", {
            "analysis_run_id": run_id,
            "title": ins.title,
            "finding": ins.finding,
            "evidence": json.dumps(ins.evidence, default=str),
            "interpretation": ins.interpretation,
            "business_impact": ins.business_impact,
            "recommendation": ins.recommendation,
            "confidence": ins.confidence,
            "priority": ins.priority,
        })

    # --- DAX Measures ---
    for dm in ctx.dax:
        await supabase.insert("dax_measures", {
            "analysis_run_id": run_id,
            "name": dm.name,
            "dax_code": dm.dax_code,
            "purpose": dm.purpose,
            "dependencies": json.dumps(dm.dependencies, default=str),
            "validation_status": dm.validation_status,
        })

    # --- Data Quality ---
    if ctx.quality:
        q = ctx.quality
        await supabase.insert("data_quality", {
            "analysis_run_id": run_id,
            "score": q.score,
            "completeness": json.dumps(q.completeness, default=str),
            "validity": json.dumps(q.validity, default=str),
            "consistency": json.dumps(q.consistency, default=str),
            "uniqueness": json.dumps(q.uniqueness, default=str),
            "relationships": json.dumps(q.relationships, default=str),
            "issues": json.dumps(q.issues, default=str),
        })

    # --- Report artifact ---
    if ctx.report and ctx.report.sections:
        report_text = "\n\n".join(
            f"## {title}\n\n{content}" for title, content in ctx.report.sections.items()
        )
        report_path = f"{owner_id}/{project_id}/report_{run_id}.md"
        await supabase.upload_file(
            "reports", report_path,
            report_text.encode("utf-8"), "text/markdown",
        )
        await supabase.insert("artifacts", {
            "project_id": project_id,
            "analysis_run_id": run_id,
            "artifact_type": "report",
            "storage_path": report_path,
            "file_name": f"report_{run_id}.md",
            "mime_type": "text/markdown",
            "file_size": len(report_text),
        })

    # --- Dashboard PNG artifact ---
    if ctx.dashboard_bytes:
        dash_path = f"{owner_id}/{project_id}/dashboard_{run_id}.png"
        await supabase.upload_file(
            "dashboard-images", dash_path,
            ctx.dashboard_bytes, "image/png",
        )
        dash_artifact = await supabase.insert("artifacts", {
            "project_id": project_id,
            "analysis_run_id": run_id,
            "artifact_type": "dashboard_png",
            "storage_path": dash_path,
            "file_name": f"dashboard_{run_id}.png",
            "mime_type": "image/png",
            "file_size": len(ctx.dashboard_bytes),
        })
        if dash_artifact:
            ctx.dashboard_artifact = dash_artifact[0]

    # --- DAX file artifact ---
    if ctx.dax:
        dax_text = "\n\n\n".join(f"// {dm.name}\n{dm.dax_code}" for dm in ctx.dax)
        dax_path = f"{owner_id}/{project_id}/dax_{run_id}.txt"
        await supabase.upload_file(
            "project-artifacts", dax_path,
            dax_text.encode("utf-8"), "text/plain",
        )
        await supabase.insert("artifacts", {
            "project_id": project_id,
            "analysis_run_id": run_id,
            "artifact_type": "dax_file",
            "storage_path": dax_path,
            "file_name": f"dax_{run_id}.txt",
            "mime_type": "text/plain",
            "file_size": len(dax_text),
        })
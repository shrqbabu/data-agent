"""Analysis run endpoints — create, status, cancel, history, detail."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.deps import AdminUser, DbClient

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class RunCreate(BaseModel):
    project_id: str
    dataset_id: str | None = None
    prompt: str = Field(min_length=1, max_length=8000)


@router.post("")
async def create_run(body: RunCreate, admin: AdminUser, db: DbClient):
    """Create a run (queued) and start the job. Returns the run + job_id."""
    p = await db.select_one("projects", body.project_id)
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    # Dataset must belong to the project.
    if body.dataset_id:
        ds = await db.select_one("datasets", body.dataset_id)
        if not ds or ds["project_id"] != body.project_id:
            raise HTTPException(status_code=400, detail="Dataset does not belong to this project.")

    run_id = str(uuid.uuid4())
    created = await db.insert("analysis_runs", [{
        "id": run_id,
        "project_id": body.project_id,
        "owner_id": admin["id"],
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "user_prompt": body.prompt,
    }])

    # Start the job in the background.
    from app.jobs.manager import get_job_manager
    manager = get_job_manager()
    manager.submit(run_id, admin["id"], body.project_id, body.prompt)

    return {
        "id": created[0]["id"],
        "project_id": created[0]["project_id"],
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "user_prompt": created[0]["user_prompt"],
        "created_at": created[0]["created_at"],
        "job_started": True,
    }


@router.get("/{run_id}")
async def get_run(run_id: str, admin: AdminUser, db: DbClient):
    run = await db.select_one("analysis_runs", run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run)


@router.get("/{run_id}/detail")
async def get_run_detail(run_id: str, admin: AdminUser, db: DbClient):
    """Full run result: metrics, insights, DAX, report, quality, artifacts."""
    run = await db.select_one("analysis_runs", run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Run not found")

    metrics = await db.select("metrics", {"analysis_run_id": f"eq.{run_id}", "order": "created_at.asc"})
    insights = await db.select("insights", {"analysis_run_id": f"eq.{run_id}", "order": "created_at.asc"})
    dax = await db.select("dax_measures", {"analysis_run_id": f"eq.{run_id}", "order": "created_at.asc"})
    quality = await db.select("data_quality", {"analysis_run_id": f"eq.{run_id}"})
    artifacts = await db.select("artifacts", {"analysis_run_id": f"eq.{run_id}", "order": "created_at.asc"})

    return {
        **_serialize_run(run),
        "metrics": [_parse_jsonable(m) for m in metrics],
        "insights": [_parse_jsonable(i) for i in insights],
        "dax_measures": [_parse_jsonable(d) for d in dax],
        "data_quality": _parse_jsonable(quality[0]) if quality else None,
        "artifacts": [_parse_jsonable(a) for a in artifacts],
    }


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str, admin: AdminUser, db: DbClient):
    run = await db.select_one("analysis_runs", run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Run not found")
    if run["status"] not in ("queued", "running"):
        raise HTTPException(status_code=400, detail="Run is not cancellable in its current state")

    await db.update("analysis_runs", run_id, {"status": "cancelled",
                                              "completed_at": _now()})
    return {"ok": True, "run_id": run_id}


def _serialize_run(run: dict) -> dict:
    return {
        "id": run["id"],
        "project_id": run["project_id"],
        "status": run["status"],
        "stage": run["stage"],
        "progress": run["progress"],
        "user_prompt": run["user_prompt"],
        "started_at": run.get("started_at"),
        "completed_at": run.get("completed_at"),
        "error": _parse_jsonable(run.get("error")),
        "created_at": run["created_at"],
    }


def _parse_jsonable(v):
    if not v:
        return None
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
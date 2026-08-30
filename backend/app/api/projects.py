"""Project CRUD. Every project belongs to an authenticated admin.

The client sends its JWT; the backend resolves the admin and derives owner_id
server-side — it never trusts a client-provided role or owner.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.deps import AdminUser, DbClient
from app.services.audit import log_action

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


@router.get("")
async def list_projects(admin: AdminUser, db: DbClient):
    rows = await db.select("projects", {
        "owner_id": f"eq.{admin['id']}",
        "order": "updated_at.desc",
    })
    return [_serialize(p, admin) for p in rows]


@router.post("")
async def create_project(body: ProjectCreate, admin: AdminUser, db: DbClient):
    created = await db.insert("projects", {
        "owner_id": admin["id"],
        "name": body.name,
        "description": body.description,
    })
    await log_action(db, admin["id"], "PROJECT_CREATED", created[0]["id"],
                     {"name": body.name})
    return _serialize(created[0], admin)


@router.get("/{project_id}")
async def get_project(project_id: str, admin: AdminUser, db: DbClient):
    p = await db.select_one("projects", project_id)
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Project not found")
    return _serialize(p, admin)


@router.patch("/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate, admin: AdminUser, db: DbClient):
    p = await db.select_one("projects", project_id)
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    update = {}
    if body.name is not None:
        update["name"] = body.name
    if body.description is not None:
        update["description"] = body.description
    if update:
        await db.update("projects", project_id, update)
    fresh = await db.select_one("projects", project_id)
    return _serialize(fresh, admin)


@router.delete("/{project_id}")
async def delete_project(project_id: str, admin: AdminUser, db: DbClient):
    """Full cascade delete: storage objects + rows (FKs handle the rest)."""
    p = await db.select_one("projects", project_id)
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete storage objects for all buckets.
    prefix = f"{admin['id']}/{project_id}/"
    for bucket in ["project-inputs", "project-artifacts", "dashboard-images", "reports"]:
        await db.delete_prefix(bucket, prefix)

    await db.delete("projects", project_id)
    await log_action(db, admin["id"], "PROJECT_DELETED", project_id)
    return {"ok": True, "project_id": project_id}


@router.get("/{project_id}/runs")
async def list_project_runs(project_id: str, admin: AdminUser, db: DbClient):
    p = await db.select_one("projects", project_id)
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = await db.select("analysis_runs", {
        "project_id": f"eq.{project_id}",
        "order": "created_at.desc",
        "limit": "50",
    })
    return [_serialize_run(r) for r in rows]


@router.get("/{project_id}/artifacts")
async def list_project_artifacts(project_id: str, admin: AdminUser, db: DbClient):
    p = await db.select_one("projects", project_id)
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = await db.select("artifacts", {
        "project_id": f"eq.{project_id}",
        "order": "created_at.desc",
        "limit": "100",
    })
    return [_serialize_artifact(a) for a in rows]


def _serialize(p: dict, admin: dict) -> dict:
    return {
        "id": p["id"],
        "owner_id": p["owner_id"],
        "name": p["name"],
        "description": p["description"],
        "status": p["status"],
        "created_at": p["created_at"],
        "updated_at": p["updated_at"],
        "last_run_at": p.get("last_run_at"),
    }


def _serialize_run(r: dict) -> dict:
    return {
        "id": r["id"],
        "project_id": r["project_id"],
        "status": r["status"],
        "stage": r["stage"],
        "progress": r["progress"],
        "user_prompt": r["user_prompt"],
        "started_at": r.get("started_at"),
        "completed_at": r.get("completed_at"),
        "error": _parse_json(r.get("error")),
        "created_at": r["created_at"],
    }


def _serialize_artifact(a: dict) -> dict:
    return {
        "id": a["id"],
        "project_id": a["project_id"],
        "analysis_run_id": a.get("analysis_run_id"),
        "artifact_type": a["artifact_type"],
        "storage_path": a["storage_path"],
        "file_name": a["file_name"],
        "mime_type": a.get("mime_type"),
        "file_size": a.get("file_size", 0),
        "checksum": a.get("checksum"),
        "created_at": a["created_at"],
    }


def _parse_json(v):
    if not v:
        return None
    try:
        return json.loads(v) if isinstance(v, str) else v
    except Exception:
        return None
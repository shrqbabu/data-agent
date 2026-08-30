"""Dataset endpoints — register after upload, profile, quality, process."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.deps import AdminUser, DbClient
from app.services.audit import log_action

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


class DatasetRegister(BaseModel):
    project_id: str
    name: str = Field(min_length=1, max_length=300)
    source_type: str = Field(pattern="^(csv|excel|sql)$")
    storage_path: str | None = None
    file_size: int = 0
    mime_type: str | None = None


class DatasetProcessRequest(BaseModel):
    """Kick off the file-processing pipeline (parse → profile → schema → quality)."""


@router.post("")
async def register_dataset(body: DatasetRegister, admin: AdminUser, db: DbClient):
    """Register a dataset after the file has been uploaded to storage."""
    p = await db.select_one("projects", body.project_id)
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    # Re-validate that the storage path is owner-scoped.
    if body.storage_path:
        if not body.storage_path.startswith(f"{admin['id']}/{body.project_id}/"):
            raise HTTPException(status_code=400,
                                detail="Storage path is not owner-scoped.")

    created = await db.insert("datasets", {
        "project_id": body.project_id,
        "name": body.name,
        "source_type": body.source_type,
        "storage_path": body.storage_path,
        "file_size": body.file_size,
        "mime_type": body.mime_type,
        "row_count": 0,
        "column_count": 0,
    })
    return _serialize(created[0])


@router.get("")
async def list_datasets(admin: AdminUser, db: DbClient, project_id: str | None = None):
    """List datasets, optionally filtered by project (owner-checked)."""
    params: dict = {"order": "created_at.desc", "limit": "100"}
    if project_id:
        p = await db.select_one("projects", project_id)
        if not p or p["owner_id"] != admin["id"]:
            raise HTTPException(status_code=404, detail="Project not found")
        params["project_id"] = f"eq.{project_id}"
    rows = await db.select("datasets", params)
    return [
        _serialize(ds, await db.select("dataset_tables", {"dataset_id": f"eq.{ds['id']}"}))
        for ds in rows
    ]


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, admin: AdminUser, db: DbClient):
    ds = await db.select_one("datasets", dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    p = await db.select_one("projects", ds["project_id"])
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Attach tables.
    tables = await db.select("dataset_tables", {"dataset_id": f"eq.{dataset_id}"})
    return _serialize(ds, tables)


@router.get("/{dataset_id}/profile")
async def get_profile(dataset_id: str, admin: AdminUser, db: DbClient):
    ds = await db.select_one("datasets", dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    p = await db.select_one("projects", ds["project_id"])
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {
        "dataset_id": ds["id"],
        "profile": _parse_json(ds.get("profile")),
        "schema": _parse_json(ds.get("schema")),
        "row_count": ds.get("row_count", 0),
        "column_count": ds.get("column_count", 0),
    }


@router.post("/{dataset_id}/process")
async def process_dataset(dataset_id: str, admin: AdminUser, db: DbClient):
    """Parse → profile → schema → quality for a registered dataset.

    Runs as an async job so large files don't block the API. The job updates
    the dataset's profile/schema/row counts and writes a data-quality summary.
    """
    ds = await db.select_one("datasets", dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    p = await db.select_one("projects", ds["project_id"])
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Dataset not found")

    from app.jobs.processor import enqueue_dataset_process

    job_id = await enqueue_dataset_process(dataset_id)
    return {"ok": True, "job_id": job_id, "dataset_id": dataset_id}


def _serialize(ds: dict, tables: list | None = None) -> dict:
    return {
        "id": ds["id"],
        "project_id": ds["project_id"],
        "name": ds["name"],
        "source_type": ds["source_type"],
        "storage_path": ds.get("storage_path"),
        "file_size": ds.get("file_size", 0),
        "mime_type": ds.get("mime_type"),
        "row_count": ds.get("row_count", 0),
        "column_count": ds.get("column_count", 0),
        "schema": _parse_json(ds.get("schema")),
        "profile": _parse_json(ds.get("profile")),
        "created_at": ds["created_at"],
        "tables": tables or [],
    }


def _parse_json(v):
    if not v:
        return [] if isinstance(v, list) else {}
    try:
        return json.loads(v) if isinstance(v, str) else v
    except Exception:
        return v
"""Artifact endpoints — signed download URLs (never public reads)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.deps import AdminUser, DbClient
from app.services.audit import log_action

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str, admin: AdminUser, db: DbClient):
    a = await db.select_one("artifacts", artifact_id)
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")
    p = await db.select_one("projects", a["project_id"])
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Artifact not found")
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


@router.post("/{artifact_id}/download-url")
async def artifact_download_url(artifact_id: str, admin: AdminUser, db: DbClient):
    """Create a short-lived signed URL for the artifact (default 5 min)."""
    a = await db.select_one("artifacts", artifact_id)
    if not a:
        raise HTTPException(status_code=404, detail="Artifact not found")
    p = await db.select_one("projects", a["project_id"])
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Artifact not found")

    bucket_map = {
        "report": "reports",
        "dashboard_png": "dashboard-images",
        "dax_file": "project-artifacts",
        "data_quality": "project-artifacts",
    }
    bucket = bucket_map.get(a["artifact_type"], "project-artifacts")
    url = await db.create_signed_url(bucket, a["storage_path"], expires_in=300)

    await log_action(db, admin["id"], "ARTIFACT_DOWNLOADED", a["project_id"],
                     {"artifact_id": artifact_id, "type": a["artifact_type"]})

    return {
        "signed_url": url,
        "file_name": a["file_name"],
        "mime_type": a.get("mime_type"),
        "file_size": a.get("file_size", 0),
        "expires_in_seconds": 300,
    }
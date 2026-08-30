"""File validation endpoint — validates extension, size, and ownership before
the client uploads to storage. The storage path is server-constructed."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.deps import AdminUser, DbClient
from app.services.audit import log_action

router = APIRouter(prefix="/api/v1/files", tags=["files"])


class FileValidateRequest(BaseModel):
    project_id: str
    file_name: str
    file_size: int
    mime_type: str = ""


@router.post("/validate")
async def validate_file(body: FileValidateRequest, admin: AdminUser, db: DbClient):
    """Validate file metadata + ownership; returns a server-constructed storage path."""
    s = get_settings()

    # Ownership check.
    p = await db.select_one("projects", body.project_id)
    if not p or p["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Project not found")

    # Extension check.
    ext = body.file_name.rsplit(".", 1)[-1].lower() if "." in body.file_name else ""
    if ext not in s.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(s.allowed_extensions))}",
        )

    # Size check.
    max_bytes = s.max_upload_mb * 1024 * 1024
    if body.file_size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds the {s.max_upload_mb} MB limit ({body.file_size / 1048576:.1f} MB).",
        )
    if body.file_size <= 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    # Server-constructed path. Never trust a client-provided path.
    import uuid
    storage_path = f"{admin['id']}/{body.project_id}/{uuid.uuid4().hex}.{ext}"

    await log_action(db, admin["id"], "FILE_UPLOADED", body.project_id,
                     {"file_name": body.file_name, "file_size": body.file_size})

    return {
        "ok": True,
        "bucket": "project-inputs",
        "storage_path": storage_path,
        "file_name": body.file_name,
        "file_size": body.file_size,
        "mime_type": body.mime_type,
        "max_size_bytes": max_bytes,
        "extension": ext,
    }
"""Audit log endpoints — admin reads their own audit trail."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.deps import AdminUser, DbClient

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("")
async def list_audit(admin: AdminUser, db: DbClient, limit: int = Query(default=100, le=500)):
    rows = await db.select("audit_log", {
        "admin_id": f"eq.{admin['id']}",
        "order": "created_at.desc",
        "limit": str(limit),
    })
    return [_serialize(r) for r in rows]


def _serialize(r: dict) -> dict:
    return {
        "id": r["id"],
        "admin_id": r.get("admin_id"),
        "action": r["action"],
        "project_id": r.get("project_id"),
        "metadata": _parse(r.get("metadata")),
        "created_at": r["created_at"],
    }


def _parse(v):
    import json
    if not v:
        return {}
    try:
        return json.loads(v) if isinstance(v, str) else v
    except Exception:
        return v
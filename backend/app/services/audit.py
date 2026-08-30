"""Audit helpers. Never log secrets or raw PII."""

from __future__ import annotations

from app.services.supabase_client import SupabaseClient


async def log_action(
    db: SupabaseClient,
    admin_id: str,
    action: str,
    project_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    await db.append_audit(admin_id, action, project_id, metadata)
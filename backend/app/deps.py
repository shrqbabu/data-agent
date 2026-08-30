"""FastAPI dependencies: auth + ownership."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Header

from app.config import get_settings
from app.core.security import get_admin_user
from app.services.supabase_client import SupabaseClient


async def get_admin(
    authorization: str | None = Header(None),
) -> dict:
    """Extract and verify JWT → resolve admin user {id, email, role}.

    Use this dependency on any endpoint that requires admin auth.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:]
    try:
        return await get_admin_user(token)
    except ValueError as e:
        raise HTTPException(status_code=403 if "Forbidden" in str(e) else 401, detail=str(e))


async def get_db() -> SupabaseClient:
    return SupabaseClient()


AdminUser = Annotated[dict, Depends(get_admin)]
DbClient = Annotated[SupabaseClient, Depends(get_db)]


def verify_ownership_factory(resource: str, id_field: str = "project_id"):
    """Factory for ownership-checking dependencies.

    Example: `Depends(verify_ownership_factory('projects', 'project_id'))`
    """
    from fastapi import Request

    async def _check(
        request: Request,
        admin: AdminUser,
        db: DbClient,
    ) -> None:
        resource_id = request.path_params.get(id_field) or request.query_params.get(id_field)
        if not resource_id:
            # Try body.
            try:
                body = await request.json()
                resource_id = body.get(id_field)
            except Exception:
                pass
        if not resource_id:
            raise HTTPException(status_code=400, detail=f"{id_field} is required")

        if resource == "projects":
            ok = await db.is_project_owner(resource_id, admin["id"])
        elif resource == "datasets":
            ds = await db.select_one("datasets", resource_id)
            if not ds:
                raise HTTPException(status_code=404, detail="Dataset not found")
            ok = await db.is_project_owner(ds["project_id"], admin["id"])
        elif resource == "runs":
            run = await db.select_one("analysis_runs", resource_id)
            if not run:
                raise HTTPException(status_code=404, detail="Run not found")
            ok = run.get("owner_id") == admin["id"]
        else:
            ok = False

        if not ok:
            raise HTTPException(status_code=403, detail="Forbidden: you do not own this resource")

    return _check
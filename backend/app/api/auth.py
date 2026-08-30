"""Auth endpoints — profile for the signed-in admin."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import AdminUser, DbClient

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me")
async def me(admin: AdminUser, db: DbClient):
    """Return the authenticated admin profile."""
    return {
        "id": admin["id"],
        "email": admin["email"],
        "role": admin["role"],
    }
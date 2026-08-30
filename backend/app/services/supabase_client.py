"""Thin HTTP client for Supabase (PostgREST + Auth + Storage + RPC).

Uses httpx directly so we don't depend on supabase-py. The service-role client
can bypass RLS; any caller must have already verified ownership before calling
write methods on this client.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import httpx

from app.config import get_settings


class SupabaseClient:
    """Service-role Supabase client (bypasses RLS – use only after ownership checks)."""

    def __init__(self) -> None:
        s = get_settings()
        self._url = s.supabase_url.rstrip("/")
        self._service_role = s.supabase_service_role_key
        self._anon_key = s.supabase_publishable_key
        self._headers = {
            "Authorization": f"Bearer {self._service_role}",
            "apikey": self._anon_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # ---- PostgREST ----

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        async with httpx.AsyncClient(timeout=60) as c:
            resp = await c.request(
                method,
                f"{self._url}/rest/v1/{path.lstrip('/')}",
                headers=self._headers | kwargs.pop("headers", {}),
                **kwargs,
            )
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Supabase error {resp.status_code} on {method} {path}: {resp.text}"
                )
            return resp

    async def select(self, table: str, params: dict | None = None) -> list[dict]:
        resp = await self._request("GET", table, params=params)
        return resp.json()

    async def select_one(self, table: str, id_: str) -> dict | None:
        rows = await self.select(table, {"id": "eq." + id_, "limit": "1"})
        return rows[0] if rows else None

    async def insert(self, table: str, data: dict | list[dict]) -> list[dict]:
        if isinstance(data, dict):
            data = [data]
        resp = await self._request("POST", table, json=data)
        return resp.json()

    async def update(self, table: str, id_: str, data: dict) -> dict | None:
        rows = await self.update_where(table, {"id": "eq." + id_}, data)
        return rows[0] if rows else None

    async def update_where(self, table: str, filters: dict[str, str], data: dict) -> list[dict]:
        qs = "&".join(f"{k}={v}" for k, v in filters.items())
        resp = await self._request("PATCH", f"{table}?{qs}", json=data)
        return resp.json()

    async def delete(self, table: str, id_: str) -> None:
        await self._request("DELETE", f"{table}?id=eq.{id_}")

    # ---- RPC (calling Supabase functions / stored procedures) ----

    async def rpc(self, fn: str, params: dict | None = None) -> Any:
        resp = await self._request("POST", f"rpc/{fn}", json=params or {})
        # RPC may return nothing, a JSON value, or a row set.
        text = resp.text.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    # ---- Storage ----

    async def upload_file(self, bucket: str, path: str, data: bytes, mime: str = "application/octet-stream") -> dict:
        async with httpx.AsyncClient(timeout=300) as c:
            resp = await c.post(
                f"{self._url}/storage/v1/object/{bucket}/{path}",
                headers={
                    "Authorization": f"Bearer {self._service_role}",
                    "apikey": self._anon_key,
                    "Content-Type": mime,
                },
                content=data,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Storage upload error {resp.status_code}: {resp.text}")
            return resp.json()

    async def download_file(self, bucket: str, path: str) -> bytes:
        async with httpx.AsyncClient(timeout=300) as c:
            resp = await c.get(
                f"{self._url}/storage/v1/object/{bucket}/{path}",
                headers={"Authorization": f"Bearer {self._service_role}"},
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Storage download error {resp.status_code}: {resp.text}")
            return resp.content

    async def create_signed_url(self, bucket: str, path: str, expires_in: int = 300) -> str:
        resp = await self._request(
            "POST", f"storage/v1/object/{bucket}/{path}",
            json={"expiresIn": expires_in},
        )
        return resp.json().get("signedURL", "")

    async def delete_prefix(self, bucket: str, prefix: str) -> None:
        """List and delete all objects under a prefix."""
        async with httpx.AsyncClient(timeout=60) as c:
            # List objects under prefix.
            list_resp = await c.post(
                f"{self._url}/storage/v1/object/list/{bucket}",
                headers=self._headers,
                json={"prefix": prefix, "limit": 1000},
            )
            if list_resp.status_code >= 400:
                return
            objects = list_resp.json()
            if not objects:
                return
            paths = [o["name"] for o in objects]
            # Delete them.
            await c.delete(
                f"{self._url}/storage/v1/object/{bucket}",
                headers=self._headers,
                json={"prefixes": paths},
            )

    # ---- Audit helper ----

    async def append_audit(
        self, admin_id: str, action: str, project_id: str | None = None, metadata: dict | None = None
    ) -> None:
        await self.insert("audit_log", {
            "admin_id": admin_id,
            "action": action,
            "project_id": project_id,
            "metadata": json.dumps(metadata or {}),
        })

    # ---- Profile / ownership helpers ----

    async def get_owner_id(self, project_id: str) -> str | None:
        p = await self.select_one("projects", project_id)
        return p.get("owner_id") if p else None

    async def is_project_owner(self, project_id: str, user_id: str) -> bool:
        owner = await self.get_owner_id(project_id)
        return owner == user_id

    async def append_audit_sync(self, admin_id: str, action: str, project_id: str | None = None, metadata: dict | None = None):
        """Synchronous wrapper for use in non-async contexts (e.g. job completion)."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.ensure_future(self.append_audit(admin_id, action, project_id, metadata))
                return
        except RuntimeError:
            pass
        # Fallback: run in a new event loop.
        asyncio.run(self.append_audit(admin_id, action, project_id, metadata))
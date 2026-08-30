"""Security primitives: JWT verification, Fernet encryption, no-op patterns."""

from __future__ import annotations

import json
from typing import Any

import httpx
import jwt
from cryptography.fernet import Fernet

from app.config import get_settings


def verify_supabase_jwt(token: str) -> dict[str, Any]:
    """Verify a Supabase JWT and return its payload.

    Tries the JWKS (RS256) endpoint first, then falls back to HS256 with the
    shared JWT secret. Returns the decoded payload or raises ValueError.
    """
    settings = get_settings()
    # Try JWKS path (default for newer Supabase projects).
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
        return payload
    except Exception:
        pass

    # Fallback to HS256 with the shared JWT secret.
    secret = settings.supabase_jwt_secret
    if not secret:
        raise ValueError("No JWT secret configured and JWKS verification failed")

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
        return payload
    except jwt.PyJWTError as e:
        raise ValueError(f"JWT verification failed: {e}")


# ---- Fernet encryption for SQL connector secrets ----

def get_fernet() -> Fernet | None:
    key = get_settings().sql_secrets_key
    if not key:
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        return None


def encrypt_secrets(plaintext: str) -> str:
    """Encrypt a JSON string of SQL connection secrets. Returns the encrypted token."""
    f = get_fernet()
    if f is None:
        raise RuntimeError("SQL secrets encryption not configured (SQL_SECRETS_KEY)")
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secrets(token: str) -> dict[str, Any]:
    """Decrypt and return the SQL connection secrets dict."""
    f = get_fernet()
    if f is None:
        raise RuntimeError("SQL secrets encryption not configured (SQL_SECRETS_KEY)")
    raw = f.decrypt(token.encode()).decode()
    return json.loads(raw)


# ---- Supabase admin user from JWT ----

async def get_admin_user(token: str) -> dict[str, Any]:
    """Resolve a Supabase JWT to a verified admin user dict {id, email, role}.

    Hits the Supabase Auth REST API to validate the token, then checks the
    profiles table for admin role. Raises ValueError on any failure.
    """
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise ValueError("Invalid or expired token")

        user_data = resp.json()
        user_id = user_data.get("id")
        if not user_id:
            raise ValueError("Invalid token payload")

        # Fetch profile via service-role client (bypass RLS for admin check).
        profile_resp = await client.get(
            f"{settings.supabase_url}/rest/v1/profiles",
            params={"id": "eq." + user_id, "select": "role,email"},
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_publishable_key,
            },
        )
        if profile_resp.status_code != 200:
            raise ValueError("Failed to fetch profile")

        profiles = profile_resp.json()
        if not profiles:
            raise ValueError("Profile not found")
        profile = profiles[0]

        if profile.get("role") != "admin":
            raise ValueError("Forbidden: admin role required")

        return {"id": user_id, "email": profile.get("email", ""), "role": "admin"}
"""SQL connector endpoints.

The Android app never connects to company databases directly. Connectors are
registered server-side; credentials are encrypted at rest. All queries run
READ ONLY (statement guard + read-only transaction).
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.security import encrypt_secrets
from app.deps import AdminUser, DbClient
from app.services.audit import log_action
from app.sql_connector.guard import ReadOnlyViolation

router = APIRouter(prefix="/api/v1/sql-connectors", tags=["sql-connectors"])


class SqlConnectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    engine: str = Field(default="postgres", pattern="^(postgres|postgresql)$")
    host: str = Field(min_length=1)
    port: int = 5432
    database: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    sslmode: str = "require"


class SqlQueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=20000)


@router.post("")
async def create_connector(body: SqlConnectorCreate, admin: AdminUser, db: DbClient):
    """Store a connector. Credentials are encrypted at rest; only the owner can
    use it. Host allowlist is enforced when configured."""
    s = get_settings()
    if s.allowed_hosts is not None:
        host = body.host.lower()
        if host not in s.allowed_hosts:
            raise HTTPException(status_code=400,
                                detail=f"Host '{body.host}' is not in the SQL allowlist.")

    secrets = encrypt_secrets(json.dumps({
        "host": body.host, "port": body.port, "database": body.database,
        "username": body.username, "password": body.password, "sslmode": body.sslmode,
    }))

    # Store encrypted secrets in a dedicated table (created by the backend on
    # first use if it doesn't exist — use a Supabase table `sql_connectors`).
    connector = await db.insert("sql_connectors", {
        "id": str(uuid.uuid4()),
        "owner_id": admin["id"],
        "name": body.name,
        "engine": "postgres",
        "host": body.host,
        "database": body.database,
        "secrets_token": secrets,
        "status": "ready",
        "created_at": None,
    })

    await log_action(db, admin["id"], "SQL_CONNECTOR_CREATED", None,
                     {"connector_name": body.name})

    return {
        "id": connector[0]["id"],
        "name": body.name,
        "engine": "postgres",
        "status": "ready",
    }


@router.get("")
async def list_connectors(admin: AdminUser, db: DbClient):
    rows = await db.select("sql_connectors", {"owner_id": f"eq.{admin['id']}"})
    return [{"id": r["id"], "name": r["name"], "engine": r["engine"],
             "status": r["status"]} for r in rows]


@router.delete("/{connector_id}")
async def delete_connector(connector_id: str, admin: AdminUser, db: DbClient):
    row = await db.select_one("sql_connectors", connector_id)
    if not row or row["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Connector not found")
    await db.delete("sql_connectors", connector_id)
    await log_action(db, admin["id"], "SQL_CONNECTOR_DELETED", None,
                     {"connector_id": connector_id})
    return {"ok": True}


@router.post("/{connector_id}/introspect")
async def introspect(connector_id: str, admin: AdminUser, db: DbClient):
    """Read-only introspection: schemas, tables, columns, indexes."""
    connector = await _get_owned(connector_id, admin, db)
    pg = _connector_pg(connector)
    try:
        result = pg.introspect()
    except ReadOnlyViolation:
        raise HTTPException(status_code=400, detail="Read-only violation.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connection failed: {e}")

    await log_action(db, admin["id"], "SQL_INTROSPECTED", None,
                     {"connector_id": connector_id})
    return result


@router.post("/{connector_id}/query")
async def run_query(connector_id: str, body: SqlQueryRequest, admin: AdminUser, db: DbClient):
    """Run a read-only SELECT against the connector."""
    connector = await _get_owned(connector_id, admin, db)
    pg = _connector_pg(connector)
    try:
        result = pg.run_read_only_query(body.sql, limit=2000)
    except ReadOnlyViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Query failed: {e}")

    return result


async def _get_owned(connector_id: str, admin: AdminUser, db: DbClient) -> dict:
    row = await db.select_one("sql_connectors", connector_id)
    if not row or row["owner_id"] != admin["id"]:
        raise HTTPException(status_code=404, detail="Connector not found")
    return row


def _connector_pg(row: dict):
    from app.core.security import decrypt_secrets
    try:
        secrets = decrypt_secrets(row["secrets_token"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decrypt connector secrets: {e}")

    from app.sql_connector.postgres import PostgresConnector
    return PostgresConnector(
        host=secrets["host"],
        port=int(secrets.get("port", 5432)),
        database=secrets["database"],
        user=secrets["username"],
        password=secrets["password"],
        sslmode=secrets.get("sslmode", "require"),
    )
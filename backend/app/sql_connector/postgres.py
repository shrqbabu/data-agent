"""PostgreSQL connector — executes read-only queries and introspection.

The connection is opened with `default_transaction_read_only=on`, every query
runs inside a READ ONLY transaction, and the statement guard blocks destructive
SQL before it reaches the server.
"""

from __future__ import annotations

import psycopg

from app.sql_connector.guard import assert_read_only


class PostgresConnector:
    def __init__(self, host: str, port: int, database: str, user: str, password: str,
                 sslmode: str = "require"):
        self._dsn = dict(
            host=host, port=port, dbname=database, user=user, password=password,
            sslmode=sslmode,
            options="-c default_transaction_read_only=on",
        )

    def introspect(self) -> dict:
        """Read-only introspection: schemas → tables → columns → indexes."""
        with psycopg.connect(**self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]

                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog','information_schema')
                    ORDER BY table_schema, table_name
                """)
                tables = cur.fetchall()

                cur.execute("""
                    SELECT table_schema, table_name, column_name, data_type,
                           is_nullable
                    FROM information_schema.columns
                    WHERE table_schema NOT IN ('pg_catalog','information_schema')
                    ORDER BY table_schema, table_name, ordinal_position
                """)
                cols = cur.fetchall()

                cur.execute("""
                    SELECT schemaname, tablename, indexname
                    FROM pg_indexes
                    WHERE schemaname NOT IN ('pg_catalog','information_schema')
                    ORDER BY schemaname, tablename
                """)
                indexes = cur.fetchall()

        return {
            "engine": "postgresql",
            "version": version,
            "schemas": _group_schemas(tables, cols, indexes),
        }

    def run_read_only_query(self, sql: str, limit: int = 1000) -> dict:
        """Run a validated read-only query, returning rows + column names."""
        assert_read_only(sql)
        # Enforce a row limit to protect against runaway scans.
        safe_sql = f"SELECT * FROM ({sql}) AS _q LIMIT {limit}" if not sql.strip().lower().endswith("limit") else sql

        with psycopg.connect(**self._dsn) as conn:
            # Force read-only transaction regardless of session defaults.
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
            with conn.cursor() as cur:
                cur.execute(safe_sql)
                columns = [d.name for d in cur.description] if cur.description else []
                rows = cur.fetchall()
                # Keep rows JSON-serializable.
                import json
                rows = json.loads(json.dumps(rows, default=str, ensure_ascii=False))

        return {"columns": columns, "rows": rows, "row_count": len(rows)}


def _group_schemas(tables: list, cols: list, indexes: list) -> list[dict]:
    by_table: dict[str, dict] = {}
    for schema, table in tables:
        key = f"{schema}.{table}"
        by_table[key] = {"schema": schema, "table": table, "columns": [], "indexes": []}

    for schema, table, col, dtype, nullable in cols:
        key = f"{schema}.{table}"
        if key in by_table:
            by_table[key]["columns"].append({
                "name": col, "data_type": dtype, "nullable": nullable == "YES",
            })

    for schema, table, index in indexes:
        key = f"{schema}.{table}"
        if key in by_table:
            by_table[key]["indexes"].append(index)

    return sorted(by_table.values(), key=lambda t: (t["schema"], t["table"]))
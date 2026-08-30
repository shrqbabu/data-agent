"""Read-only enforcement for SQL connectors.

Three independent layers:
  1. Statement guard — rejects destructive statements before execution.
  2. Read-only transaction — every connection runs `SET TRANSACTION READ ONLY`.
  3. Read-only role/user — connectors should use a Postgres user with SELECT-only
     grants (documented; the backend enforces 1 & 2 unconditionally).
"""

from __future__ import annotations

import re

BLOCKED_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE",
    "GRANT", "REVOKE", "MERGE", "UPSERT", "COPY", "VACUUM", "REINDEX",
    "CLUSTER", "SECURITY LABEL", "DO", "CALL", "EXECUTE", "SET", "RESET",
]

# Strip comments and string literals before keyword scanning, to defeat
# trivial obfuscation like "D/*x*/ROP" or "drop 'table'".
_COMMENT_RE = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)
_STRING_RE = re.compile(r"'([^']|'')*'")


def strip_sql_noise(sql: str) -> str:
    s = _COMMENT_RE.sub(" ", sql)
    s = _STRING_RE.sub(" ", s)
    return s


def check_read_only(sql: str) -> list[str]:
    """Return a list of violations. Empty list = safe read-only statement."""
    clean = strip_sql_noise(sql)
    upper = clean.upper()
    violations = []
    # Only allow a SELECT as the first meaningful token.
    stripped = upper.strip()
    if not stripped.startswith("SELECT") and not stripped.startswith("WITH"):
        violations.append("Only SELECT (or WITH) statements are allowed.")

    for kw in BLOCKED_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", upper):
            violations.append(f"Blocked keyword: {kw}")
    return violations


def assert_read_only(sql: str) -> None:
    violations = check_read_only(sql)
    if violations:
        raise ReadOnlyViolation(violations)


class ReadOnlyViolation(Exception):
    def __init__(self, violations: list[str]):
        super().__init__("; ".join(violations))
        self.violations = violations
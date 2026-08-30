"""SQL read-only guard tests."""

import pytest

from app.sql_connector.guard import (
    ReadOnlyViolation, assert_read_only, check_read_only,
)


def test_select_allowed():
    assert check_read_only("SELECT * FROM orders WHERE amount > 100") == []


def test_with_allowed():
    assert check_read_only("WITH t AS (SELECT 1) SELECT * FROM t") == []


@pytest.mark.parametrize("sql", [
    "DROP TABLE orders",
    "DELETE FROM orders WHERE id = 1",
    "UPDATE orders SET amount = 0",
    "INSERT INTO orders VALUES (1)",
    "TRUNCATE orders",
    "ALTER TABLE orders ADD COLUMN x int",
    "CREATE TABLE t (id int)",
    "CREATE INDEX idx ON orders(id)",
    "GRANT ALL ON orders TO public",
    "DROP/*x*/ TABLE orders",
    "SELECT * FROM orders; DROP TABLE orders",
])
def test_destructive_sql_blocked(sql):
    violations = check_read_only(sql)
    assert violations, f"Expected '{sql}' to be blocked"


def test_string_literal_not_confused_with_keyword():
    # A string literal containing a blocked word must NOT trigger a violation.
    sql = "SELECT * FROM logs WHERE message = 'drop table'"
    assert check_read_only(sql) == []


def test_assert_raises():
    with pytest.raises(ReadOnlyViolation):
        assert_read_only("DROP TABLE orders")
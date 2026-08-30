"""DAX generation + validation tests."""

import pandas as pd

from app.engine.dax_generator import generate_dax, metric_to_dax
from app.engine.dax_validator import validate_dax
from app.engine.metric_registry import MetricRegistry
from app.engine.schema import build_schema_model


def _registry_and_model():
    df = pd.DataFrame({
        "order_date": pd.date_range("2026-01-01", periods=6, freq="MS"),
        "customer_id": ["c1", "c2", "c1", "c3", "c4", "c2"],
        "product_id": ["p1", "p2", "p1", "p3", "p4", "p2"],
        "category": ["A", "B", "A", "B", "A", "B"],
        "revenue": [100, 200, 150, 300, 50, 400],
    })
    model = build_schema_model(df)

    reg = MetricRegistry()
    reg.add_simple("m_total_revenue", "Total Revenue", 1200, unit="currency",
                   dimension="sales", formula="SUM(revenue)",
                   source={"table": "data", "column": "revenue"})
    reg.add_simple("m_customer_customer_count", "Customer Count", 4,
                   dimension="customer",
                   source={"table": "data", "column": "customer_id"})
    reg.add_simple("m_customer_repeat_rate_pct", "Repeat Rate %", 50.0,
                   dimension="customer",
                   source={"table": "data", "column": "customer_id"})
    return reg, model


def test_expected_measure_generation():
    reg, model = _registry_and_model()
    measures = generate_dax(reg, model)
    names = [m.name for m in measures]
    assert "Total Revenue" in names
    assert "Customer Count" in names
    # Time intelligence present because a date column exists.
    assert any("YTD" in n or "YoY" in n for n in names)


def test_dax_uses_actual_columns():
    reg, model = _registry_and_model()
    measures = generate_dax(reg, model)
    total = next(m for m in measures if m.name == "Total Revenue")
    assert "data[revenue]" in total.dax_code  # real column, not invented
    assert "data[fake]" not in total.dax_code


def test_dax_validation_passes_for_generated():
    reg, model = _registry_and_model()
    measures = generate_dax(reg, model)
    result = validate_dax(measures, model)
    assert result["passed"] is True, result["measures"]


def test_invalid_column_detection():
    from app.engine.context import DaxMeasure
    reg, model = _registry_and_model()
    bad = [DaxMeasure(name="Bad", dax_code="Bad =\n    SUM ( data[does_not_exist] )")]
    result = validate_dax(bad, model)
    assert result["passed"] is False
    assert any("does_not_exist" in e for m in result["measures"] for e in m["errors"])


def test_invalid_table_detection():
    from app.engine.context import DaxMeasure
    reg, model = _registry_and_model()
    bad = [DaxMeasure(name="Bad", dax_code="Bad =\n    SUM ( missing_table[col] )")]
    result = validate_dax(bad, model)
    assert result["passed"] is False
    assert any("missing_table" in e for m in result["measures"] for e in m["errors"])


def test_unbalanced_brackets_detected():
    from app.engine.context import DaxMeasure
    reg, model = _registry_and_model()
    bad = [DaxMeasure(name="Bad", dax_code="Bad =\n    CALCULATE ( [Total Revenue ]")]
    result = validate_dax(bad, model)
    assert result["passed"] is False
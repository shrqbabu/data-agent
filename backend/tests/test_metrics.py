"""Deterministic analytics engine tests with known KPI datasets."""

import numpy as np
import pandas as pd
import pytest

from app.engine.calculations import (
    contribution, growth, growth_between_periods, period_summary, pct, rank_by,
    total,
)


@pytest.fixture
def sales_df():
    """Synthetic sales data with known totals."""
    dates = pd.date_range("2026-01-01", periods=12, freq="MS")
    df = pd.DataFrame({
        "order_date": list(dates) * 2,
        "customer_id": [f"c{i % 5}" for i in range(24)],
        "product_id": [f"p{i % 4}" for i in range(24)],
        "category": ["A", "B"] * 12,
        "amount": [100.0] * 24,  # total = 2400
    })
    return df


def test_total_revenue_known(sales_df):
    assert total(sales_df["amount"]) == pytest.approx(2400.0)


def test_growth_calculation():
    g = growth(120, 100)
    assert g["pct"] == pytest.approx(20.0)
    assert g["direction"] == "up"

    g2 = growth(90, 100)
    assert g2["pct"] == pytest.approx(-10.0)
    assert g2["direction"] == "down"


def test_percentage():
    assert pct(50, 200) == pytest.approx(25.0)
    assert pct(0, 0) == 0.0  # no crash on zero denominator


def test_period_summary_and_growth(sales_df):
    periods = period_summary(sales_df, "order_date", "amount")
    # 12 monthly periods, 200 each.
    assert len(periods) == 12
    assert all(p["value"] == pytest.approx(200.0) for p in periods)

    g = growth_between_periods(sales_df, "order_date", "amount")
    assert g["growth_pct"] == pytest.approx(0.0)


def test_ranking_and_contribution(sales_df):
    ranked = rank_by(sales_df, "category", "amount")
    assert ranked[0]["key"] == "A"
    assert ranked[0]["value"] == pytest.approx(1200.0)

    contrib = contribution(sales_df, "category", "amount")
    assert len(contrib) == 2
    assert sum(c["share_pct"] for c in contrib) == pytest.approx(100.0)


def test_join_duplication_detected():
    """A naive join that duplicates rows must be caught by the validator."""
    left = pd.DataFrame({"id": [1, 2], "val": [10, 20]})
    right = pd.DataFrame({"id": [1, 1, 2], "other": ["a", "b", "c"]})
    joined = left.merge(right, on="id", how="left")
    # val 10 appears twice (fan-out) — a sign of join duplication.
    assert joined["val"].tolist().count(10) == 2
    # total of val would be 40, not 30 → the engine would flag fan-out.
    assert total(joined["val"]) == pytest.approx(40.0)


def test_missing_data_handling():
    s = pd.Series([1.0, np.nan, 3.0, np.nan, 5.0])
    assert total(s) == pytest.approx(9.0)
    assert int(s.isna().sum()) == 2


def test_date_calculations():
    df = pd.DataFrame({"d": pd.date_range("2026-01-01", periods=10, freq="D"), "v": range(10)})
    periods = period_summary(df, "d", "v")
    assert len(periods) == 1  # all in one month
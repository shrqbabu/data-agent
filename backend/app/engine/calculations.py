"""Deterministic analytics engine — pure pandas/NumPy/SciPy arithmetic.

The LLM is never the arithmetic engine. All totals, averages, percentages,
growth, rankings, distributions, correlations and aggregations live here and
return plain JSON-serializable values suitable for the metric registry.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Safe helpers
# ---------------------------------------------------------------------------


def _safe_div(num: Any, den: Any, default: float = 0.0) -> float:
    try:
        num = float(num)
        den = float(den)
        if den == 0 or (den != den):
            return default
        return num / den
    except (TypeError, ValueError):
        return default


def _to_float(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        if f != f:
            return default
        return f
    except (TypeError, ValueError):
        return default


def pct(part: Any, total: Any) -> float:
    """Percentage (0-100) of part/total."""
    return _safe_div(part, total) * 100


def fmt_num(value: Any, unit: str = "", decimals: int = 2) -> str:
    """Deterministic human display, e.g. 2,481,000 USD."""
    v = _to_float(value)
    if v != v:
        return "—"
    s = f"{v:,.{decimals}f}"
    if unit:
        s += f" {unit}"
    return s


def fmt_compact(value: Any, unit: str = "") -> str:
    """Compact display: 2.48M, 1.2K, 45%."""
    v = _to_float(value)
    abs_v = abs(v)
    if abs_v >= 1_000_000_000:
        s = f"{v / 1_000_000_000:.2f}B"
    elif abs_v >= 1_000_000:
        s = f"{v / 1_000_000:.2f}M"
    elif abs_v >= 1_000:
        s = f"{v / 1_000:.1f}K"
    else:
        s = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{s}{unit}"


# ---------------------------------------------------------------------------
# Column helpers
# ---------------------------------------------------------------------------


def pick_amount_column(df: pd.DataFrame, model) -> str | None:
    """Pick the best amount column from the schema model, if any."""
    if model.amount_columns:
        return model.amount_columns[0]
    if model.numeric_columns:
        return model.numeric_columns[0]
    return None


def pick_date_column(df: pd.DataFrame, model) -> str | None:
    if model.date_columns:
        return model.date_columns[0]
    return None


def ensure_datetime(series: pd.Series) -> pd.Series:
    if not pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")
    return series


# ---------------------------------------------------------------------------
# Core computations (return JSON-safe values)
# ---------------------------------------------------------------------------


def total(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce")
    return float(s.sum(skipna=True)) if s.notna().any() else 0.0


def mean(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce")
    return float(s.mean(skipna=True)) if s.notna().any() else 0.0


def median(series: pd.Series) -> float:
    s = pd.to_numeric(series, errors="coerce")
    return float(s.median(skipna=True)) if s.notna().any() else 0.0


def count_non_null(series: pd.Series) -> int:
    return int(series.notna().sum())


def growth(current: Any, previous: Any) -> dict:
    """Return {'pct': ..., 'abs': ..., 'direction': 'up'|'down'|'flat'}."""
    cur = _to_float(current)
    prev = _to_float(previous)
    if prev == 0:
        pct_change = None  # undefined growth
    else:
        pct_change = _safe_div(cur - prev, abs(prev)) * 100
    direction = "flat"
    if pct_change is not None:
        direction = "up" if pct_change > 0 else ("down" if pct_change < 0 else "flat")
    return {"pct": pct_change, "abs": cur - prev, "direction": direction}


def period_summary(df: pd.DataFrame, date_col: str, amount_col: str) -> list[dict]:
    """Aggregate amount by period (year-month). Returns chronological list.

    [{period: '2026-01', value: 1234.5}, ...]
    """
    d = df.copy()
    d["_dt"] = ensure_datetime(d[date_col])
    d["_period"] = d["_dt"].dt.to_period("M").astype(str)
    grouped = d.groupby("_period")[amount_col].apply(lambda s: float(pd.to_numeric(s, errors="coerce").sum(skipna=True)))
    return [{"period": k, "value": float(v)} for k, v in grouped.items() if not pd.isna(v)]


def growth_between_periods(df: pd.DataFrame, date_col: str, amount_col: str) -> dict:
    """Compare the most recent complete period vs the previous one.

    Returns {'period', 'previous_period', 'current', 'previous', 'growth_pct',
    'direction', 'abs'}.
    """
    series = period_summary(df, date_col, amount_col)
    if len(series) < 2:
        return {"period": None, "previous_period": None, "current": None,
                "previous": None, "growth_pct": None, "direction": "flat", "abs": None}
    cur = series[-1]["value"]
    prev = series[-2]["value"]
    g = growth(cur, prev)
    return {
        "period": series[-1]["period"],
        "previous_period": series[-2]["period"],
        "current": cur,
        "previous": prev,
        "growth_pct": g["pct"],
        "direction": g["direction"],
        "abs": g["abs"],
    }


def aggregate(df: pd.DataFrame, by: str, agg_col: str, func: str = "sum") -> list[dict]:
    """Group by column, aggregate agg_col, sorted desc.

    Returns [{key, value}].
    """
    col = pd.to_numeric(df[agg_col], errors="coerce")
    grouped = df.groupby(df[by])[col].agg(func)
    out = [{"key": str(k), "value": float(v)} for k, v in grouped.items()]
    out.sort(key=lambda x: x["value"], reverse=True)
    return out


def top_n(df: pd.DataFrame, by: str, agg_col: str, n: int = 10) -> list[dict]:
    return aggregate(df, by, agg_col, "sum")[:n]


def contribution(df: pd.DataFrame, by: str, agg_col: str, n: int = 10) -> list[dict]:
    """Top-n contributors with share % of total."""
    agg = aggregate(df, by, agg_col, "sum")
    tot = sum(x["value"] for x in agg) or 1.0
    top = agg[:n]
    out = []
    for x in top:
        out.append({**x, "share_pct": pct(x["value"], tot)})
    other = sum(x["value"] for x in agg[n:])
    if n < len(agg):
        out.append({"key": "Other", "value": float(other), "share_pct": pct(other, tot)})
    return out


def distribution(series: pd.Series, bins: int = 10) -> list[dict]:
    """Histogram of a numeric series → [{range: '0-10', count: n}]."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return []
    counts, edges = np.histogram(s, bins=bins)
    out = []
    for i in range(len(counts)):
        out.append({
            "range": f"{edges[i]:,.0f}-{edges[i + 1]:,.0f}",
            "count": int(counts[i]),
        })
    return out


def descriptive_stats(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {}
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "std": float(s.std()) if s.std() == s.std() else 0.0,
        "min": float(s.min()),
        "max": float(s.max()),
        "q25": float(s.quantile(0.25)),
        "q75": float(s.quantile(0.75)),
    }


def correlation_matrix(df: pd.DataFrame, cols: list[str]) -> dict:
    """Pairwise Pearson correlations among numeric columns → {col: {col: r}}."""
    valid = [c for c in cols if c in df.columns]
    if len(valid) < 2:
        return {}
    mat = df[valid].apply(pd.to_numeric, errors="coerce").corr(numeric_only=True)
    out = {}
    for c in valid:
        out[c] = {}
        for d in valid:
            v = mat.loc[c, d] if c in mat.index and d in mat.columns else None
            out[c][d] = None if v is None or v != v else round(float(v), 4)
    return out


def date_range(df: pd.DataFrame, date_col: str) -> dict | None:
    s = ensure_datetime(df[date_col]).dropna()
    if s.empty:
        return None
    return {"min": s.min().isoformat(), "max": s.max().isoformat(),
            "days": int((s.max() - s.min()).days)}


def duplicate_count(df: pd.DataFrame) -> int:
    return int(df.duplicated().sum())


def missing_summary(df: pd.DataFrame) -> list[dict]:
    out = []
    for col in df.columns:
        n = int(df[col].isna().sum())
        out.append({"column": str(col), "missing": n, "pct": pct(n, len(df))})
    return out


def moving_average(series: pd.Series, window: int = 3) -> list[dict]:
    s = pd.to_numeric(series, errors="coerce")
    ma = s.rolling(window=window, min_periods=1).mean()
    return [{"index": i, "value": None if v != v else float(v)} for i, v in enumerate(ma.tolist())]


def rank_by(df: pd.DataFrame, by: str, agg_col: str) -> list[dict]:
    """Ranks of a group-by aggregate, 1 = highest."""
    agg = aggregate(df, by, agg_col, "sum")
    for i, x in enumerate(agg):
        x["rank"] = i + 1
    return agg


def customer_metrics(df: pd.DataFrame, customer_col: str, date_col: str, amount_col: str) -> dict:
    """Deterministic customer KPIs: count, new/returning, repeat, avg per customer."""
    d = df.dropna(subset=[customer_col])
    if d.empty:
        return {}
    n_customers = int(d[customer_col].nunique())
    total_rev = total(d[amount_col])
    orders = int(len(d))
    # Repeat buyers: customers with > 1 transaction.
    counts = d.groupby(d[customer_col]).size()
    repeat = int((counts > 1).sum())
    repeat_rate = pct(repeat, n_customers)
    # Avg revenue per customer.
    rev_per_customer = _safe_div(total_rev, n_customers)
    # Avg order value.
    avg_order_value = _safe_div(total_rev, orders)
    # Recency-based churn proxy: customers whose last purchase is > 2x the
    # median inter-order gap.
    dates = ensure_datetime(d[date_col])
    d2 = d.copy()
    d2["_dt"] = dates
    d2["_dt"] = d2["_dt"].dt.normalize()
    last = d2.groupby(d2[customer_col])["_dt"].max()
    today = d2["_dt"].max()
    days_since = (today - last).dt.days
    # Use the p90 of inter-purchase gaps as the inactivity threshold proxy.
    ordered = d2.sort_values([customer_col, "_dt"])
    gaps = ordered.groupby(ordered[customer_col])["_dt"].diff().dt.days.dropna()
    threshold = float(gaps.quantile(0.75)) if not gaps.empty else 90.0
    if threshold <= 0:
        threshold = 90.0
    churned_proxy = int((days_since > threshold).sum())
    return {
        "customer_count": n_customers,
        "total_revenue": total_rev,
        "order_count": orders,
        "repeat_customers": repeat,
        "repeat_rate_pct": repeat_rate,
        "avg_revenue_per_customer": rev_per_customer,
        "avg_order_value": avg_order_value,
        "churned_proxy_count": churned_proxy,
        "churned_proxy_rate_pct": pct(churned_proxy, n_customers),
        "inactivity_threshold_days": threshold,
        "new_customers_period": None,  # filled when a period dimension is present
    }


def new_vs_returning(df: pd.DataFrame, customer_col: str, date_col: str) -> dict:
    """First-purchase vs returning per period.

    Returns {'period': {new: n, returning: n}} — deterministic cohort logic.
    """
    d = df.dropna(subset=[customer_col, date_col]).copy()
    d["_dt"] = ensure_datetime(d[date_col])
    d["_period"] = d["_dt"].dt.to_period("M").astype(str)
    first = d.groupby(d[customer_col])["_period"].min().rename("_first")
    d = d.merge(first, left_on=customer_col, right_index=True, how="left")
    d["_is_new"] = d["_period"] == d["_first"]
    result = {}
    for period, grp in d.groupby("_period"):
        result[period] = {
            "new": int(grp["_is_new"].sum()),
            "returning": int((~grp["_is_new"]).sum()),
        }
    return result


def forecast_naive(df: pd.DataFrame, date_col: str, value_col: str, horizon: int = 3) -> dict:
    """Simple deterministic trend forecast (no ML).

    Uses a linear least-squares fit on the period-summed series. Returns
    historical + forecast points. The full forecasting skill may upgrade to
    statsmodels when enough history exists.
    """
    series = period_summary(df, date_col, value_col)
    if len(series) < 3:
        return {"method": "naive", "history": series, "forecast": [],
                "confidence": None}
    xs = np.arange(len(series), dtype=float)
    ys = np.array([x["value"] for x in series], dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    forecast = []
    for h in range(1, horizon + 1):
        x = len(series) - 1 + h
        forecast.append({"period": None, "step": h, "value": float(slope * x + intercept)})
    # Confidence: R^2 of the fit.
    yhat = slope * xs + intercept
    ss_res = float(np.sum((ys - yhat) ** 2))
    ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"method": "linear_trend", "history": series, "forecast": forecast,
            "confidence": round(max(0.0, min(r2, 1.0)), 4)}
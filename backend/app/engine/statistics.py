"""Statistical analysis stage — deterministic stats beyond basic arithmetic."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from app.engine.calculations import correlation_matrix, descriptive_stats


def normality_p_value(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 8 or s.nunique() < 3:
        return None
    _, p = stats.shapiro(s)
    return float(p)


def outliers_iqr(series: pd.Series) -> dict:
    """IQR-based outlier detection → {count, lower, upper, values_sample}."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"count": 0, "lower": None, "upper": None, "values_sample": []}
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = s[(s < lower) | (s > upper)]
    return {
        "count": int(len(outliers)),
        "lower": float(lower),
        "upper": float(upper),
        "values_sample": [float(v) for v in outliers.head(5).tolist()],
    }


def correlation_significance(x: pd.Series, y: pd.Series) -> dict:
    """Pearson r with p-value. Deterministic."""
    a = pd.to_numeric(x, errors="coerce").dropna()
    b = pd.to_numeric(y, errors="coerce").dropna()
    idx = a.index.intersection(b.index)
    a, b = a.loc[idx], b.loc[idx]
    if len(a) < 3:
        return {"r": None, "p": None, "n": len(a)}
    r, p = stats.pearsonr(a, b)
    return {"r": float(r), "p": float(p), "n": int(len(a))}


def growth_stability(series: list[float]) -> dict:
    """Coefficient of variation + direction consistency of a value series."""
    arr = np.array([float(v) for v in series if v is not None], dtype=float)
    if len(arr) < 2:
        return {"cv": None, "up_periods": 0, "down_periods": 0, "trend": "flat"}
    changes = np.diff(arr)
    up = int((changes > 0).sum())
    down = int((changes < 0).sum())
    mean_abs = float(np.mean(np.abs(changes))) if len(changes) else 0.0
    cv = float(np.std(arr) / np.mean(arr)) if np.mean(arr) else 0.0
    trend = "up" if up > down else ("down" if down > up else "flat")
    return {"cv": round(cv, 4), "up_periods": up, "down_periods": down,
            "avg_abs_change": mean_abs, "trend": trend}


def seasonality_strength(series: list[float], period: int = 12) -> float | None:
    """Autocorrelation at the candidate seasonal lag as a seasonality proxy."""
    arr = np.array([float(v) for v in series if v is not None], dtype=float)
    if len(arr) < period + 2:
        return None
    detrended = arr - np.convolve(arr, np.ones(3) / 3, mode="same")
    r = np.corrcoef(detrended[:-period], detrended[period:])
    if np.isnan(r[0, 1]):
        return None
    return round(float(r[0, 1]), 4)


def stats_report(df: pd.DataFrame, numeric_cols: list[str]) -> dict:
    """Overall statistics stage result for a run."""
    result = {"descriptives": {}, "outliers": {}, "correlations": {}}
    for col in numeric_cols:
        if col not in df.columns:
            continue
        s = df[col]
        result["descriptives"][col] = descriptive_stats(s)
        result["outliers"][col] = outliers_iqr(s)
    if len(numeric_cols) >= 2:
        result["correlations"] = correlation_matrix(df, numeric_cols)
    return result
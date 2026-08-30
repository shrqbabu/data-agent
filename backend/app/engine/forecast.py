"""Forecasting — deterministic time-series forecasting.

Upgrades the naive linear fit to statsmodels ETS when the dataset has enough
history. All outputs carry the method name + confidence so the validator can
judge whether a forecast is trustworthy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.engine.calculations import forecast_naive, period_summary

MIN_HISTORY_FOR_ETS = 8


def forecast_series(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    horizon: int = 6,
) -> dict:
    """Forecast a period-summed series. Returns {'method', 'history',
    'forecast', 'confidence', 'notes'}."""
    series = period_summary(df, date_col, value_col)
    if len(series) < 3:
        return {
            "method": "insufficient_data",
            "history": series,
            "forecast": [],
            "confidence": None,
            "notes": ["Not enough history to produce a reliable forecast."],
        }

    try:
        if len(series) >= MIN_HISTORY_FOR_ETS:
            return _ets_forecast(series, horizon)
    except Exception:
        pass  # fall back to linear

    naive = forecast_naive(df, date_col, value_col, horizon)
    naive["notes"] = ["Linear trend used because history is short."]
    return naive


def _ets_forecast(series: list[dict], horizon: int) -> dict:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    idx = pd.PeriodIndex([s["period"] for s in series], freq="M")
    values = pd.Series([s["value"] for s in series], index=idx, dtype=float)
    # Use additive ETS with trend (no seasonality unless 2+ full cycles).
    seasonal_periods = None
    model_kwargs: dict = {"trend": "add", "damped_trend": True, "seasonal": None}
    if len(values) >= 24:
        model_kwargs = {"trend": "add", "seasonal": "add", "seasonal_periods": 12,
                        "damped_trend": True}

    fit = ExponentialSmoothing(values, **model_kwargs).fit()
    fcast = fit.forecast(horizon)

    last_period = idx[-1]
    forecast_points = []
    for h, v in enumerate(fcast.tolist(), start=1):
        forecast_points.append({
            "period": (last_period + h).strftime("%Y-%m"),
            "step": h,
            "value": float(v),
        })

    # Confidence proxy: in-sample error (sMAPE-like).
    fitted = fit.fittedvalues
    errors = np.abs((values - fitted).tolist())
    base = np.abs(values.tolist())
    denom = (np.array(base) + np.array(errors))
    smape = np.mean(2 * np.array(errors) / np.where(denom == 0, 1, denom)) * 100 if len(denom) else None
    confidence = max(0.0, min(1.0, 1 - (smape or 0) / 100))

    return {
        "method": "ets",
        "history": series,
        "forecast": forecast_points,
        "confidence": round(float(confidence), 4),
        "smape_pct": round(float(smape), 2) if smape is not None else None,
        "notes": ["Holt-Winters ETS (additive)."],
    }
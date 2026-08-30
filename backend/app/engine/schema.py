"""Schema inference: classify columns and build a SchemaModel for a DataFrame."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from app.engine.context import SchemaModel

_ID_PATTERN = re.compile(r"(^|_)(id|code|key)(_|$)|^.*_id$", re.IGNORECASE)
_AMOUNT_PATTERN = re.compile(
    r"(revenue|sales|amount|value|price|cost|profit|gross|net|spend|total|qty|quantity|units?|invoice|revenue_amt)",
    re.IGNORECASE,
)
_DATE_PATTERN = re.compile(r"(date|time|timestamp|day|month|year|period|week)", re.IGNORECASE)


def infer_column_kind(name: str, series: pd.Series) -> str:
    """Classify a column: date | numeric | amount | id | categorical | unknown."""
    if series is None:
        return "unknown"

    non_null = series.dropna()
    if non_null.empty:
        return "categorical"

    # ID-like names or high cardinality strings.
    if _ID_PATTERN.search(name) and series.nunique(dropna=True) / max(len(series), 1) > 0.8:
        return "id"

    # Date detection.
    if _DATE_PATTERN.search(name) or series.dtype.kind in "Mm":
        converted = pd.to_datetime(non_null.astype(str), errors="coerce")
        rate = converted.notna().mean()
        if rate > 0.9:
            return "date"

    # Numeric detection.
    if pd.api.types.is_numeric_dtype(series):
        if _AMOUNT_PATTERN.search(name):
            return "amount"
        return "numeric"

    # String that parses as numeric (e.g. "1,234.56" or "12%").
    sample = non_null.head(200).astype(str)
    cleaned = sample.str.replace(r"[, ]", "", regex=True).str.replace("%", "", regex=False)
    parsed = pd.to_numeric(cleaned, errors="coerce")
    if parsed.notna().mean() > 0.9:
        if _AMOUNT_PATTERN.search(name):
            return "amount"
        return "numeric"

    # Low-cardinality string → categorical.
    if series.nunique(dropna=True) <= 50:
        return "categorical"

    return "categorical"  # high-cardinality text, treat as categorical for now


def parse_numeric(series: pd.Series) -> pd.Series:
    """Best-effort numeric parse of a column (handles commas, currency, %)."""
    cleaned = series.astype(str).str.replace(r"[, ]", "", regex=True)
    cleaned = cleaned.str.replace(r"[$,€£]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def build_schema_model(df: pd.DataFrame) -> SchemaModel:
    """Build a SchemaModel from a DataFrame (single-table case)."""
    model = SchemaModel(tables={"data": []})

    for col in df.columns:
        col_name = str(col)
        series = df[col]
        kind = infer_column_kind(col_name, series)
        nunique = int(series.nunique(dropna=True)) if not series.empty else 0
        nulls = int(series.isna().sum())
        sample = [None if pd.isna(v) else v for v in series.dropna().head(3).tolist()]

        model.tables["data"].append({
            "name": col_name,
            "kind": kind,
            "dtype": str(series.dtype),
            "nulls": nulls,
            "null_pct": round(nulls / max(len(series), 1) * 100, 1),
            "unique": nunique,
            "sample": sample,
        })

        if kind == "date":
            model.date_columns.append(col_name)
        elif kind == "amount":
            model.amount_columns.append(col_name)
            model.numeric_columns.append(col_name)
        elif kind == "numeric":
            model.numeric_columns.append(col_name)
        elif kind == "id":
            model.id_columns[col_name] = col_name
        elif kind == "categorical":
            model.categorical_columns.append(col_name)

    # Multi-table relationship inference (single df = star-ish detection on keys).
    model.relationships = detect_relationships(model)
    return model


def detect_relationships(model: SchemaModel) -> list[dict]:
    """Heuristic relationship detection for multi-table datasets.

    Given only a single table, this returns []. For multi-table runs the
    pipeline builds one df per table and calls relate_tables.
    """
    return []


def relate_tables(tables: dict[str, pd.DataFrame]) -> list[dict]:
    """Detect join keys between tables by column-name overlap.

    Returns [{from_table, from_col, to_table, to_col, confidence}].
    """
    relationships: list[dict] = []
    table_names = list(tables.keys())
    for i, t1 in enumerate(table_names):
        df1 = tables[t1]
        for t2 in table_names[i + 1:]:
            df2 = tables[t2]
            shared = set(df1.columns) & set(df2.columns)
            for col in shared:
                # Prefer id/key-named shared columns.
                score = 1.0 if _ID_PATTERN.search(col) else 0.7
                relationships.append({
                    "from_table": t1,
                    "from_col": col,
                    "to_table": t2,
                    "to_col": col,
                    "confidence": score,
                })
    return relationships
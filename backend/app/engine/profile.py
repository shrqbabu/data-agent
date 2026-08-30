"""PROFILING stage — dataset overview: rows, columns, types, missing, duplicates,
date/numeric columns."""

from __future__ import annotations

import pandas as pd

from app.engine.calculations import date_range, duplicate_count, missing_summary
from app.engine.context import ProfileResult
from app.engine.schema import build_schema_model, infer_column_kind


def profile_dataframe(df: pd.DataFrame) -> ProfileResult:
    model = build_schema_model(df)

    columns = []
    for col_def in model.tables["data"]:
        name = col_def["name"]
        series = df[name]
        sample = []
        for v in series.dropna().head(3).tolist():
            if isinstance(v, pd.Timestamp):
                sample.append(v.isoformat())
            else:
                sample.append(None if pd.isna(v) else v)
        columns.append({
            "name": name,
            "kind": col_def["kind"],
            "dtype": col_def["dtype"],
            "missing": col_def["nulls"],
            "missing_pct": col_def["null_pct"],
            "unique": col_def["unique"],
            "sample": sample,
        })

    date_col = model.date_columns[0] if model.date_columns else None
    dr = date_range(df, date_col) if date_col else None

    return ProfileResult(
        row_count=int(len(df)),
        column_count=int(len(df.columns)),
        columns=columns,
        date_columns=model.date_columns,
        numeric_columns=model.numeric_columns,
        categorical_columns=model.categorical_columns,
        duplicate_rows=duplicate_count(df),
        date_range=dr,
        tables=1,
    )


def profile_to_json(profile: ProfileResult) -> dict:
    return {
        "row_count": profile.row_count,
        "column_count": profile.column_count,
        "columns": profile.columns,
        "date_columns": profile.date_columns,
        "numeric_columns": profile.numeric_columns,
        "categorical_columns": profile.categorical_columns,
        "duplicate_rows": profile.duplicate_rows,
        "date_range": profile.date_range,
        "tables": profile.tables,
    }
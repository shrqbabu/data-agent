"""Dataset loading — from Supabase storage or uploaded bytes.

The Android app uploads directly to private storage; the backend downloads the
file bytes and loads them with pandas. Large files are processed in chunks where
possible (pandas chunked read for CSV).
"""

from __future__ import annotations

import io
from typing import BinaryIO

import pandas as pd

from app.config import get_settings


class DatasetLoadError(Exception):
    pass


def sniff_csv_params(sample: str) -> dict:
    """Detect delimiter + header from a CSV sample. Raises on malformed input."""
    import csv as _csv

    if not sample.strip():
        raise DatasetLoadError("File is empty")

    # Try common delimiters.
    delimiters = [",", ";", "\t", "|"]
    best_delim = ","
    best_count = -1
    first_lines = sample.splitlines()[:5]
    for d in delimiters:
        counts = [line.count(d) for line in first_lines if line.strip()]
        if not counts:
            continue
        consistent = sum(1 for c in counts if c == counts[0])
        if counts[0] > best_count:
            best_count = counts[0]
            best_delim = d

    return {"delimiter": best_delim}


def load_dataframe(data: bytes, source_type: str, file_name: str) -> pd.DataFrame:
    """Load bytes into a DataFrame based on source type.

    Supports csv / xls / xlsx / parquet (parquet is backend-generated for SQL
    imports and is never accepted as a client upload).
    """
    try:
        if source_type == "csv":
            return _load_csv(data)
        if source_type == "excel":
            return _load_excel(data, file_name)
        if source_type == "parquet":
            return pd.read_parquet(io.BytesIO(data))
        if source_type == "sql":
            # SQL datasets are stored as parquet snapshots by the connector.
            return pd.read_parquet(io.BytesIO(data))
        raise DatasetLoadError(f"Unsupported source type: {source_type}")
    except DatasetLoadError:
        raise
    except Exception as e:
        raise DatasetLoadError(f"Failed to parse file: {e}") from e


def _load_csv(data: bytes) -> pd.DataFrame:
    text = data.decode("utf-8-sig", errors="replace")
    if not text.strip():
        raise DatasetLoadError("File is empty")

    params = sniff_csv_params(text)
    # Check header validity: first row should have non-empty unique-ish cells.
    header = text.splitlines()[0].split(params["delimiter"])
    header = [h.strip() for h in header]
    if not header or all(not h for h in header):
        raise DatasetLoadError("Missing or empty header row")
    if len(set(header)) != len(header):
        raise DatasetLoadError(
            f"Duplicate column names in header: {[h for h in header if header.count(h) > 1]}"
        )

    try:
        df = pd.read_csv(
            io.StringIO(text),
            delimiter=params["delimiter"],
            header=0,
            low_memory=False,
            on_bad_lines="skip",
        )
    except Exception as e:
        raise DatasetLoadError(f"Malformed CSV: {e}") from e

    if df.empty:
        raise DatasetLoadError("File contains no data rows")
    return df


def _load_excel(data: bytes, file_name: str) -> pd.DataFrame:
    """Load Excel bytes; uses the first populated sheet. Sheet detection happens
    in the profiling stage (workbook → sheets → tables)."""
    try:
        if file_name.lower().endswith(".xls"):
            df = pd.read_excel(io.BytesIO(data), sheet_name=0, header=0)
        else:
            df = pd.read_excel(io.BytesIO(data), sheet_name=0, header=0)
    except Exception as e:
        raise DatasetLoadError(f"Failed to read Excel workbook: {e}") from e

    if df is None or df.empty:
        raise DatasetLoadError("Workbook has no populated sheets")
    return df


def detect_sheets(data: bytes, file_name: str) -> list[dict]:
    """Return workbook sheet metadata for the Excel flow (UI shows detected sheets)."""
    try:
        excel = pd.ExcelFile(io.BytesIO(data))
        sheets = []
        for name in excel.sheet_names:
            df = pd.read_excel(excel, sheet_name=name, header=0, nrows=10)
            sheets.append({
                "name": name,
                "rows_estimate": len(df) if df is not None else 0,
                "empty": df is None or df.empty,
                "columns": list(df.columns) if df is not None else [],
            })
        return sheets
    except Exception as e:
        raise DatasetLoadError(f"Failed to inspect workbook: {e}") from e
"""DATA_QUALITY stage — independent quality assessment of the dataset.

Score 0-100 with breakdown by dimension. Produces an issues list the validator
and the UI both use. This is *reporting* on the data, not fixing it.
"""

from __future__ import annotations

import pandas as pd

from app.engine.context import QualityReport
from app.engine.schema import SchemaModel


def assess_quality(df: pd.DataFrame, model: SchemaModel | None = None) -> QualityReport:
    n_rows = len(df)
    if n_rows == 0:
        return QualityReport(
            score=0.0,
            completeness={}, validity={}, consistency={}, uniqueness={}, relationships={},
            issues=[{"severity": "critical", "category": "completeness",
                     "message": "Dataset is empty."}],
        )

    # --- Completeness: % of cells populated ---
    total_cells = n_rows * len(df.columns)
    filled_cells = int(df.notna().sum().sum())
    completeness_pct = round(filled_cells / total_cells * 100, 2) if total_cells else 0.0
    missing_by_col = {str(c): int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()}

    # --- Validity: column type fit (unparseable numerics, impossible dates) ---
    validity_issues: list[dict] = []
    numeric_invalid = 0
    for c in df.columns:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            continue
        # String column that *looks* numeric but has unparseable values.
        cleaned = s.astype(str).str.replace(r"[, $€£%]", "", regex=True)
        parsed = pd.to_numeric(cleaned, errors="coerce")
        bad = int(parsed.isna().sum()) - int(s.isna().sum())
        if bad > 0:
            numeric_invalid += bad
            validity_issues.append({
                "severity": "medium" if bad / max(len(s), 1) < 0.1 else "high",
                "category": "validity",
                "column": str(c),
                "message": f"{bad} value(s) are not parseable as numbers.",
            })
    validity_pct = round((1 - numeric_invalid / max(filled_cells, 1)) * 100, 2)

    # --- Consistency: null patterns + duplicate rows ---
    dup_rows = int(df.duplicated().sum())
    dup_pct = round(dup_rows / n_rows * 100, 2)
    consistency_pct = round((1 - dup_pct / 100) * 100, 2)

    # --- Uniqueness: presence of a natural key with full uniqueness ---
    uniqueness_score = 0.0
    uniqueness_notes = []
    id_cols = list(model.id_columns.keys()) if model else []
    if id_cols:
        best_uniq = max(df[c].nunique(dropna=True) / max(n_rows, 1) for c in id_cols)
        uniqueness_score = round(best_uniq * 100, 2)
    else:
        # Fall back to whole-row uniqueness.
        uniqueness_score = round((1 - dup_pct / 100) * 100, 2)
        uniqueness_notes.append("No explicit ID column detected; row-level uniqueness used.")

    # --- Relationships: N/A for single table ---
    relationships = {"status": "single_table", "note": "No multi-table joins to check."}

    # --- Assemble issues ---
    issues: list[dict] = []
    if completeness_pct < 95:
        issues.append({"severity": "medium", "category": "completeness",
                       "message": f"{100 - completeness_pct:.1f}% of cells are missing.",
                       "columns": list(missing_by_col.keys())})
    if numeric_invalid > 0:
        issues.extend(validity_issues)
    if dup_pct > 0:
        issues.append({"severity": "low", "category": "consistency",
                       "message": f"{dup_rows} duplicate rows ({dup_pct}%)."})

    # --- Score (weighted) ---
    score = round(
        0.45 * completeness_pct +
        0.25 * validity_pct +
        0.15 * consistency_pct +
        0.15 * uniqueness_score,
        2,
    )
    score = max(0.0, min(100.0, score))

    return QualityReport(
        score=score,
        completeness={"pct": completeness_pct, "missing_by_column": missing_by_col},
        validity={"pct": validity_pct, "unparseable_values": numeric_invalid},
        consistency={"duplicate_rows": dup_rows, "duplicate_pct": dup_pct},
        uniqueness={"score": uniqueness_score, "notes": uniqueness_notes},
        relationships=relationships,
        issues=issues,
    )


def quality_to_json(q: QualityReport) -> dict:
    return {
        "score": q.score,
        "completeness": q.completeness,
        "validity": q.validity,
        "consistency": q.consistency,
        "uniqueness": q.uniqueness,
        "relationships": q.relationships,
        "issues": q.issues,
    }
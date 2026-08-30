"""Dataset processor — parse → profile → schema → quality, in a background job.

Writes profiling + quality results back to the datasets row (profile jsonb) and
populates dataset_tables. This runs before any analysis run so the user can
inspect the dataset and its quality score."""

from __future__ import annotations

import json

from app.engine.loader import load_dataframe
from app.engine.profile import profile_dataframe, profile_to_json
from app.engine.quality import assess_quality, quality_to_json
from app.engine.schema import build_schema_model
from app.services.supabase_client import SupabaseClient


async def process_dataset(dataset_id: str) -> dict:
    """Load + profile + quality a dataset. Returns the dataset row updated."""
    db = SupabaseClient()
    ds = await db.select_one("datasets", dataset_id)
    if not ds:
        raise RuntimeError(f"Dataset {dataset_id} not found")

    storage_path = ds.get("storage_path")
    if not storage_path:
        raise RuntimeError("Dataset has no storage path to process.")

    data = await db.download_file("project-inputs", storage_path)
    source_type = ds.get("source_type", "csv")
    file_name = ds.get("name", "data.csv")

    df = load_dataframe(data, source_type, file_name)
    profile = profile_dataframe(df)
    model = build_schema_model(df)
    quality = assess_quality(df, model)

    profile_json = profile_to_json(profile)
    profile_json["quality"] = quality_to_json(quality)
    schema_json = model.tables.get("data", [])

    await db.update("datasets", dataset_id, {
        "row_count": profile.row_count,
        "column_count": profile.column_count,
        "profile": json.dumps(profile_json, default=str),
        "schema": json.dumps(schema_json, default=str),
    })

    # dataset_tables row (single-table snapshot for file sources).
    await db.insert("dataset_tables", {
        "dataset_id": dataset_id,
        "table_name": "data",
        "grain": None,
        "row_count": profile.row_count,
        "schema": json.dumps(schema_json, default=str),
    })

    return {"dataset_id": dataset_id, "row_count": profile.row_count,
            "quality_score": quality.score, "column_count": profile.column_count}
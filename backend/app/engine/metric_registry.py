"""Metric registry — the single source of truth for every numeric fact.

Every important metric gets an id, definition, formula, source, grain, filters,
period, value and validation status. Report, DAX and dashboard PNG all read from
this registry, so $2.48M in the report == $2.48M on the PNG == the DAX value.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class Metric:
    metric_id: str
    name: str
    definition: str
    formula: str
    value: Any  # JSON-serializable {value, unit, display}
    source: dict  # {table, column, grain, filters, period}
    validation_status: str = "unvalidated"
    dimension: str | None = None  # registry group: sales, customer, product, ...

    def to_dict(self) -> dict:
        d = asdict(self)
        # Normalize numpy types.
        d["value"] = _jsonable(self.value)
        d["source"] = _jsonable(self.source)
        return d

    def display_value(self) -> str:
        v = self.value
        if isinstance(v, dict) and "display" in v:
            return str(v["display"])
        return str(v)


class MetricRegistry:
    def __init__(self) -> None:
        self._metrics: dict[str, Metric] = {}

    def add(self, metric: Metric) -> Metric:
        self._metrics[metric.metric_id] = metric
        return metric

    def add_simple(
        self,
        metric_id: str,
        name: str,
        value: Any,
        unit: str = "",
        formula: str = "",
        definition: str = "",
        source: dict | None = None,
        dimension: str | None = None,
    ) -> Metric:
        return self.add(Metric(
            metric_id=metric_id,
            name=name,
            definition=definition or name,
            formula=formula,
            value={"value": _jsonable(value), "unit": unit},
            source=source or {},
            dimension=dimension,
            validation_status="validated",
        ))

    def not_supported(
        self,
        metric_id: str,
        name: str,
        reason: str,
        alternative: str | None = None,
        source: dict | None = None,
    ) -> Metric:
        """Register a metric the dataset cannot support (NOT_SUPPORTED)."""
        return self.add(Metric(
            metric_id=metric_id,
            name=name,
            definition=reason,
            formula="NOT_SUPPORTED",
            value={"value": None, "unit": "", "reason": reason, "alternative": alternative},
            source=source or {},
            validation_status="NOT_SUPPORTED",
        ))

    def mark_failed(self, metric_id: str, reason: str) -> None:
        m = self._metrics.get(metric_id)
        if m:
            m.validation_status = "failed"
            m.value = {"value": None, "reason": reason}

    def get(self, metric_id: str) -> Metric | None:
        return self._metrics.get(metric_id)

    def all(self) -> list[Metric]:
        return list(self._metrics.values())

    def validated(self) -> list[Metric]:
        return [m for m in self._metrics.values() if m.validation_status == "validated"]

    def by_dimension(self, dimension: str) -> list[Metric]:
        return [m for m in self._metrics.values() if m.dimension == dimension]

    def not_supported_list(self) -> list[Metric]:
        return [m for m in self._metrics.values() if m.validation_status == "NOT_SUPPORTED"]

    def to_dicts(self) -> list[dict]:
        return [m.to_dict() for m in self._metrics.values()]

    def to_serde(self) -> list[dict]:
        return self.to_dicts()


def _jsonable(obj: Any) -> Any:
    """Recursively convert numpy/pandas values to JSON-safe primitives."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.ndarray,)):
        return [_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, (pd.Series,)):
        return [_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, (pd.DataFrame,)):
        return obj.to_dict(orient="records")
    if isinstance(obj, (np.datetime64,)):
        return pd.Timestamp(obj).isoformat()
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        return obj
    return obj
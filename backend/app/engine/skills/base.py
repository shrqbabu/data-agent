"""Base skill class. Every skill can detect relevance, compute metrics, and
produce insight drafts. All arithmetic is deterministic."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from app.engine.context import RunContext, SchemaModel
from app.engine.metric_registry import MetricRegistry


class Skill(ABC):
    """Analytics skill — domain-specific analysis capability."""

    domain: str = "base"

    @abstractmethod
    def detect(self, prompt: str, model: SchemaModel) -> float:
        """Score 0..1 for how relevant this domain is to the prompt + schema."""
        ...

    @abstractmethod
    def analyze(self, ctx: RunContext, registry: MetricRegistry, tables: dict[str, pd.DataFrame]) -> list[dict]:
        """Compute metrics and return insight drafts.

        Every insight draft must have:
          - title: str
          - finding: str
          - evidence: list[dict]  # metric_ids this insight is based on
          - confidence: str
          - priority: str
        """
        ...

    def panel_suggestions(self, registry: MetricRegistry) -> list[dict]:
        """Return suggested dashboard panel types for the dashboard stage."""
        return []
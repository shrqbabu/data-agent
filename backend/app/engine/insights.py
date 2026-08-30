"""INSIGHT_GENERATION — turns skill drafts into validated Insight objects.

Every insight is required to carry evidence: metric_ids that exist in the
registry. Any draft whose evidence cannot be verified is dropped. The LLM may
polish prose, but it can never add evidence.
"""

from __future__ import annotations

from app.engine.context import Insight
from app.engine.metric_registry import MetricRegistry

SUPPORTED_FIELDS = {"title", "finding", "evidence", "interpretation",
                    "business_impact", "recommendation", "confidence", "priority"}


def _validate_draft(draft: dict, registry: MetricRegistry) -> tuple[bool, str]:
    if not isinstance(draft, dict):
        return False, "not a dict"
    if not draft.get("title") or not draft.get("finding"):
        return False, "missing title/finding"
    evidence = draft.get("evidence", [])
    if not evidence:
        return False, "insight has no evidence"
    for e in evidence:
        mid = e.get("metric_id") if isinstance(e, dict) else None
        if not mid or registry.get(mid) is None:
            return False, f"evidence references unknown metric {mid}"
    return True, ""


def generate_insights(drafts: list[dict], registry: MetricRegistry, llm=None) -> list[Insight]:
    """Validate + (optionally) polish insight drafts."""
    insights: list[Insight] = []
    for draft in drafts:
        ok, reason = _validate_draft(draft, registry)
        if not ok:
            # Never deliver an un-evidenced insight.
            continue

        # Only keep known fields.
        clean = {k: v for k, v in draft.items() if k in SUPPORTED_FIELDS}
        if llm is not None and llm.enabled:
            # Polish prose (evidence untouched). Run defensively.
            try:
                import asyncio
                cleaned = asyncio.run(llm.write_insight_prose(clean, registry.to_dicts()))
                if isinstance(cleaned, dict):
                    clean = {k: v for k, v in cleaned.items() if k in SUPPORTED_FIELDS}
            except Exception:
                pass

        insights.append(Insight(
            title=str(clean.get("title", "")),
            finding=str(clean.get("finding", "")),
            evidence=clean.get("evidence", []),
            interpretation=clean.get("interpretation"),
            business_impact=clean.get("business_impact"),
            recommendation=clean.get("recommendation"),
            confidence=str(clean.get("confidence", "medium")) if clean.get("confidence") in {"high", "medium", "low"} else "medium",
            priority=str(clean.get("priority", "medium")) if clean.get("priority") in {"high", "medium", "low"} else "medium",
        ))
    return insights
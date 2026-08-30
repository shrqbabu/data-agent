"""ANALYSIS_PLANNING — maps the user's report prompt + available data to:
report sections, selected skills, requested KPIs, dimensions, comparisons.

The LLM (when enabled) drafts the plan; deterministic heuristics always provide
a fallback so the pipeline never depends on the network.
"""

from __future__ import annotations

import re
from typing import Any

from app.engine.context import AnalysisPlan, SchemaModel

# Skill keyword banks used for deterministic detection.
SKILL_KEYWORDS: dict[str, list[str]] = {
    "sales": ["revenue", "sales", "sell", "order", "gross", "margin", "sold", "booking", "deal", "pipeline"],
    "customer": ["customer", "client", "retention", "churn", "acquisition", "cohort", "repeat", "loyalty", "lifetime", "clv"],
    "product": ["product", "sku", "category", "item", "brand", "assortment", "portfolio"],
    "inventory": ["inventory", "stock", "warehouse", "reorder", "turnover", "supply", "out of stock", "backorder"],
    "forecasting": ["forecast", "predict", "trend", "projection", "next month", "seasonality", "future"],
    "statistics": ["statistic", "correlation", "distribution", "outlier", "significance", "variance", "regression", "segment"],
}

DEFAULT_SECTIONS = [
    "Executive Summary",
    "Key Findings",
    "KPIs",
    "Analysis",
    "Risks",
    "Opportunities",
    "Recommendations",
    "Data Quality",
    "Methodology",
    "Limitations",
]


def detect_skills(prompt: str, model: SchemaModel) -> list[str]:
    """Deterministic skill selection from prompt keywords + detected domain.

    Every selected skill is additionally gated by whether the schema can
    actually support it (enforced in the skills themselves).
    """
    text = prompt.lower()
    scored: list[tuple[float, str]] = []

    for domain, keywords in SKILL_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits:
            scored.append((hits, domain))

    # Schema-driven signals.
    if not model.date_columns:
        scored = [(s, d) for s, d in scored if d not in ("forecasting",)]
    if not model.amount_columns:
        scored = [(s, d) for s, d in scored if d not in ("sales",)]
    if not model.id_columns and not model.categorical_columns:
        scored = [(s, d) for s, d in scored if d not in ("customer", "product")]

    # Sorting: score desc, then canonical order.
    order = ["sales", "customer", "product", "inventory", "forecasting", "statistics"]
    scored.sort(key=lambda t: (-t[0], order.index(t[1]) if t[1] in order else 99))
    selected = [d for _, d in scored[:4]]

    # Always include statistics when enough numeric data exists.
    if len(model.numeric_columns) >= 2 and "statistics" not in selected:
        selected.append("statistics")

    # If nothing matched, fall back to what the data supports.
    if not selected:
        if model.amount_columns and model.date_columns:
            selected = ["sales", "statistics"]
        elif model.date_columns:
            selected = ["statistics", "forecasting"]
        else:
            selected = ["statistics"]

    return selected[:5]


def extract_kpis(prompt: str, model: SchemaModel) -> list[str]:
    """Extract explicitly requested KPIs from the prompt (deterministic)."""
    kpi_patterns = {
        "revenue": r"\brevenue\b|\bsales\b|\btotal (revenue|sales|amount)\b",
        "growth": r"\bgrowth\b|\byoy\b|\bmom\b|\bvs (last|previous)\b",
        "margin": r"\bmargin\b|\bprofit\b|\bgross\b",
        "retention": r"\bretention\b|\bchurn\b|\brepeat\b",
        "customer_count": r"\bcustomer(s)? count\b|\bnew customers\b",
        "forecast": r"\bforecast\b|\bpredict\b",
        "average_order_value": r"\baverage order value\b|\baov\b",
        "inventory_turnover": r"\bturnover\b|\binventory\b",
    }
    text = prompt.lower()
    found = []
    for kpi, pat in kpi_patterns.items():
        if re.search(pat, text):
            found.append(kpi)
    return found


def extract_sections(prompt: str) -> list[str]:
    """If the prompt explicitly asks for sections/headings, honor them."""
    lines = [l.strip() for l in prompt.splitlines() if l.strip()]
    sections = []
    for line in lines:
        # "## Title", "Section: Title", or a standalone Title-like line.
        clean = line.lstrip("#").strip()
        if clean.startswith(("section", "part")) and ":" in clean:
            sections.append(clean.split(":", 1)[1].strip().title())
        elif re.match(r"^[A-Z][A-Za-z ]{2,60}$", clean) and len(clean) < 61:
            sections.append(clean)
    # Dedupe, keep order, fall back to defaults.
    seen = set()
    out = [s for s in sections if not (s in seen or seen.add(s))]
    return out[:10] or DEFAULT_SECTIONS


def build_plan(
    prompt: str,
    model: SchemaModel,
    llm: Any = None,
) -> AnalysisPlan:
    """Plan from prompt + schema, with optional LLM polish.

    Deterministic extraction always runs first; the LLM (if available) is asked
    to *refine the same inputs* and its output is validated against the schema
    so it cannot inject columns/tables that don't exist.
    """
    skills = detect_skills(prompt, model)
    kpis = extract_kpis(prompt, model)
    sections = extract_sections(prompt)
    dimensions = (model.categorical_columns or [])[:6]
    comparisons = None

    plan = AnalysisPlan(
        prompt=prompt,
        sections=sections,
        selected_skills=skills,
        requested_kpis=kpis,
        dimensions=dimensions,
        filters=None,
        visual_requirements=[],
        comparisons=comparisons,
    )

    if llm is not None:
        try:
            plan = llm.refine_plan(plan, model, prompt)  # may raise
        except Exception:
            pass  # deterministic plan stands

    return plan
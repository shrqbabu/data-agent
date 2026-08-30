"""Report generation — follows the user's prompt (plan.sections).

The user's report prompt is the authoritative specification for report sections,
KPIs, comparisons and visual requirements. Skills provide analytical capability;
they never replace the requested structure. Every number in the report is read
from the metric registry — the same source the PNG and DAX read from.
"""

from __future__ import annotations

from app.engine.context import ReportResult
from app.engine.metric_registry import MetricRegistry


def _metric_row(m) -> str:
    value = m.value
    if isinstance(value, dict) and value.get("value") is not None:
        return f"- **{m.name}** (`{m.metric_id}`): {value.get('value')} {value.get('unit', '')}"
    return f"- **{m.name}** (`{m.metric_id}`): {m.display_value()}"


def _insight_block(i) -> str:
    ev = ", ".join(
        f"{e.get('metric_id')}" for e in (i.evidence or [])
    )
    return (
        f"### {i.title}\n"
        f"- Finding: {i.finding}\n"
        f"- Evidence: {ev}\n"
        + (f"- Interpretation: {i.interpretation}\n" if i.interpretation else "")
        + (f"- Business impact: {i.business_impact}\n" if i.business_impact else "")
        + (f"- Recommendation: {i.recommendation}\n" if i.recommendation else "")
        + f"- Confidence: {i.confidence} · Priority: {i.priority}"
    )


def build_report(plan, registry: MetricRegistry, insights: list, quality, llm=None) -> ReportResult:
    """Build the markdown report. Deterministic assembly; LLM prose optional."""
    from datetime import datetime, timezone

    sections: dict[str, str] = {}

    # --- Assemble the "sources" that the prose sections draw on ---
    validated = registry.validated()
    not_supported = registry.not_supported_list()

    kpis_section = "\n".join(_metric_row(m) for m in validated) or "_No validated KPIs._"
    if not_supported:
        kpis_section += "\n\n**Unsupported metrics:**\n" + "\n".join(
            f"- **{m.name}** (`{m.metric_id}`): {m.definition}"
            + (f"\n  - Alternative: {m.value.get('alternative')}" if isinstance(m.value, dict) and m.value.get("alternative") else "")
            for m in not_supported
        )

    insights_section = "\n\n".join(_insight_block(i) for i in insights) or "_No insights generated._"

    quality_section = "**Overall data quality score:** "
    if quality:
        quality_section += f"**{quality['score']} / 100**\n"
        if quality.get("issues"):
            quality_section += "\n**Issues:**\n" + "\n".join(
                f"- [{i.get('severity')}] {i.get('message')}" for i in quality["issues"]
            )
    else:
        quality_section += "not evaluated."

    methodology_section = (
        "- Pipeline: VALIDATING_INPUT → PROFILING → DATA_QUALITY → SCHEMA_MODELING → "
        "ANALYSIS_PLANNING → DETERMINISTIC_CALCULATIONS → BUSINESS_ANALYSIS → STATISTICS → "
        "FORECASTING → INSIGHT_GENERATION → DAX_GENERATION → DAX_VALIDATION → "
        "DASHBOARD_PNG_GENERATION → FINAL_VALIDATION.\n"
        "- All arithmetic is deterministic (pandas/NumPy/SciPy); the LLM writes prose only.\n"
        f"- Skills selected for this run: {', '.join(plan.selected_skills or [])}."
    )

    limitations_section = (
        "- Numbers are computed from the provided dataset only; no external benchmarks.\n"
        "- Forecasts carry a confidence value and are indicative, not guarantees.\n"
        "- Metrics marked NOT_SUPPORTED could not be computed from the available schema."
    )

    # Default section map used when the plan doesn't supply a section.
    default_map = {
        "Executive Summary": lambda: _executive_summary(plan, validated, insights),
        "Key Findings": lambda: _key_findings(insights),
        "KPIs": lambda: kpis_section,
        "Analysis": lambda: insights_section,
        "Risks": lambda: _risks(insights),
        "Opportunities": lambda: _opportunities(insights),
        "Recommendations": lambda: _recommendations(insights),
        "Data Quality": lambda: quality_section,
        "Methodology": lambda: methodology_section,
        "Limitations": lambda: limitations_section,
    }

    for section in plan.sections:
        if section in default_map:
            sections[section] = default_map[section]()
        else:
            # A user-requested custom section. Fill from LLM prose if available,
            # else from the KPIs/insights so it's never empty.
            sections[section] = _custom_section(section, validated, insights)

    # LLM polish pass (optional): fill/improve prose for sections, evidence-bound.
    if llm is not None and llm.enabled:
        try:
            import asyncio
            llm_sections = asyncio.run(llm.write_report_sections(
                plan, registry.to_dicts(),
                [{"title": i.title, "finding": i.finding, "evidence": i.evidence,
                  "recommendation": i.recommendation} for i in insights],
                quality,
            ))
            for k, v in llm_sections.items():
                if k in sections and len(v) > len(sections[k]):
                    sections[k] = v
        except Exception:
            pass

    return ReportResult(
        sections=sections,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _executive_summary(plan, metrics, insights) -> str:
    lines = []
    top = metrics[:5]
    if top:
        lines.append("Key metrics from this analysis:")
        lines.extend(_metric_row(m) for m in top)
    if insights:
        lines.append("\nTop insight:")
        lines.append(f"- {insights[0].title}: {insights[0].finding}")
    if not lines:
        lines.append("Analysis completed but produced no validated metrics.")
    return "\n".join(lines)


def _key_findings(insights) -> str:
    if not insights:
        return "_No key findings._"
    return "\n".join(f"{i + 1}. **{ins.title}** — {ins.finding}" for i, ins in enumerate(insights[:5]))


def _risks(insights) -> str:
    high = [i for i in insights if i.priority == "high"][:5]
    if not high:
        return "_No high-priority risks identified from the data._"
    return "\n".join(f"- **{i.title}**: {i.finding}" for i in high)


def _opportunities(insights) -> str:
    opportunities = [i for i in insights if i.priority == "high" and i.recommendation][:5]
    if not opportunities:
        return "_No distinct opportunities surfaced (see insights)."
    return "\n".join(f"- **{i.title}**: {i.recommendation}" for i in opportunities)


def _recommendations(insights) -> str:
    recs = [i.recommendation for i in insights if i.recommendation]
    if not recs:
        return "_No explicit recommendations generated._"
    return "\n".join(f"{i + 1}. {r}" for i, r in enumerate(dict.fromkeys(recs)[:6]))


def _custom_section(section, metrics, insights) -> str:
    parts = [f"_Section requested by report prompt._\n"]
    if metrics:
        parts.append("\n".join(_metric_row(m) for m in metrics[:8]))
    if insights:
        parts.append("\n\n".join(f"- {i.title}: {i.finding}" for i in insights[:5]))
    return "\n".join(parts)


def report_to_markdown(report: ReportResult) -> str:
    header = "# Analytics Report\n\n"
    body = "\n\n---\n\n".join(f"## {title}\n\n{content}" for title, content in report.sections.items())
    return header + body
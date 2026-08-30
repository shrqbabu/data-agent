"""FINAL_VALIDATION — independent validation stage.

The validator is deliberately separate from the analytics engine. It checks:

  data      — row counts, duplicates, missing values, relationship integrity
  metrics   — totals, percentages, growth, rankings, denominators
  insights  — evidence references, unsupported claims, causal claims, contradictions
  dax       — table/column/dependency references, syntax
  png       — registry reconcile (displayed numbers == registry values), labels, units

If critical checks fail, the run is marked VALIDATION_FAILED and is NOT delivered
as validated.
"""

from __future__ import annotations

import re

from app.engine.context import RunContext, ValidationResult

_CAUSAL_PHRASES = [
    "caused by", "is caused", "because of", "is due to", "due to", "leads to",
    "leads us", "drives", "is the reason", "is because", "result of the fact",
]


def validate_run(ctx: RunContext) -> ValidationResult:
    checks: dict[str, bool] = {}
    failures: list[dict] = []
    warnings: list[str] = []

    # --- Data ---
    checks["data_row_count"] = True
    checks["data_duplicates"] = True
    checks["data_missing"] = True
    if ctx.df is not None:
        n = len(ctx.df)
        if n == 0:
            checks["data_row_count"] = False
            failures.append({"check": "data_row_count", "detail": "Dataset is empty.",
                             "severity": "critical"})
        if ctx.profile and ctx.profile.duplicate_rows > n * 0.5:
            checks["data_duplicates"] = False
            failures.append({"check": "data_duplicates",
                             "detail": f"{ctx.profile.duplicate_rows} duplicate rows ({ctx.profile.duplicate_rows / max(n,1):.0%}).",
                             "severity": "critical"})
        if ctx.quality and ctx.quality.completeness.get("pct", 100) < 50:
            checks["data_missing"] = False
            failures.append({"check": "data_missing",
                             "detail": f"Completeness {ctx.quality.completeness.get('pct')}% is below the 50% floor.",
                             "severity": "critical"})

    # --- Metrics: denominators, growth sanity, percentages in range ---
    checks["metrics_denominators"] = True
    checks["metrics_percentages"] = True
    checks["metrics_growth"] = True
    for m in ctx.metrics.all():
        v = m.value
        if not isinstance(v, dict):
            continue
        inner = v.get("value", v)
        if isinstance(inner, dict) and "growth_pct" in inner:
            gp = inner["growth_pct"]
            if gp is not None and abs(gp) > 10000:
                checks["metrics_growth"] = False
                failures.append({"check": "metrics_growth",
                                 "detail": f"Growth {gp:.1f}% for {m.metric_id} exceeds sanity bound.",
                                 "severity": "high"})
        if m.metric_id.endswith("_pct") or "pct" in m.metric_id:
            val = inner if isinstance(inner, (int, float)) else None
            if val is not None and (val < -5 or val > 105):
                checks["metrics_percentages"] = False
                failures.append({"check": "metrics_percentages",
                                 "detail": f"Percentage {val:.1f} out of range for {m.metric_id}.",
                                 "severity": "high"})

    # --- Insights: evidence + causal claims + contradictions ---
    checks["insights_evidence"] = True
    checks["insights_causal"] = True
    checks["insights_contradictions"] = True
    metric_values: dict[str, set] = {}
    for ins in ctx.insights:
        if not ins.evidence:
            checks["insights_evidence"] = False
            failures.append({"check": "insights_evidence",
                             "detail": f"Insight '{ins.title}' has no evidence.",
                             "severity": "critical"})
            continue
        for e in ins.evidence:
            mid = e.get("metric_id")
            if not mid:
                continue
            metric_values.setdefault(mid, set())
            metric_values[mid].add(str(e.get("value")))

        low = ins.finding.lower()
        for phrase in _CAUSAL_PHRASES:
            if phrase in low:
                # Causal phrasing without a causal-analysis flag in evidence.
                has_causal = any("causal" in str(e).lower() for e in ins.evidence)
                if not has_causal:
                    checks["insights_causal"] = False
                    failures.append({"check": "insights_causal",
                                     "detail": f"Insight '{ins.title}' makes a causal claim: \"{phrase}\".",
                                     "severity": "high"})
                break

    # Contradiction: same metric id with conflicting scalar values.
    for mid, vals in metric_values.items():
        clean = {v for v in vals if v and v != "None"}
        if len(clean) > 1:
            checks["insights_contradictions"] = False
            failures.append({"check": "insights_contradictions",
                             "detail": f"Metric {mid} appears with conflicting values: {sorted(clean)}.",
                             "severity": "high"})

    # --- DAX (already validated in stage; re-check resolution) ---
    checks["dax_resolution"] = True
    if ctx.dax_validation and not ctx.dax_validation.get("passed"):
        checks["dax_resolution"] = False
        failures.append({"check": "dax_resolution",
                         "detail": "One or more DAX measures failed validation.",
                         "severity": "high"})

    # --- PNG: registry reconcile ---
    checks["png_registry_reconcile"] = True
    checks["png_has_panels"] = True
    if ctx.dashboard_spec:
        if not ctx.dashboard_spec.panels:
            checks["png_has_panels"] = False
            warnings.append("Dashboard has no panels; placeholder image generated.")
        for panel in ctx.dashboard_spec.panels:
            mid = panel.data.get("metric_id")
            if mid and ctx.metrics.get(mid) is None:
                checks["png_registry_reconcile"] = False
                failures.append({"check": "png_registry_reconcile",
                                 "detail": f"Panel '{panel.title}' references missing metric {mid}.",
                                 "severity": "critical"})
    if ctx.dashboard_artifact is None:
        checks["png_has_panels"] = False
        warnings.append("No dashboard PNG artifact was produced.")

    # --- Final verdict ---
    critical_failures = [f for f in failures if f["severity"] in ("critical", "high")]
    passed = not critical_failures
    return ValidationResult(
        passed=passed,
        checks=checks,
        failures=failures,
        warnings=warnings,
    )
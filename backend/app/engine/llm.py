"""LLM client — used ONLY for prose and planning, never for arithmetic.

Hard constraints enforced here:
  * The model is given the *actual* schema and the *actual* metric registry.
  * The system prompt forbids inventing data, metrics, columns, benchmarks,
    competitors, or causation.
  * Outputs are validated against the schema before they can affect a report.
  * If the LLM is disabled or fails, deterministic fallbacks take over and the
    pipeline still completes.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import get_settings

NO_HALLUCINATION_SYSTEM = """\
You are the analysis-prose module of an enterprise data analytics product. You
write clear, professional analytical prose. You are NOT an arithmetic engine and
you are NOT a general chatbot.

ABSOLUTE RULES:
1. Never invent data, metrics, numbers, benchmarks, or external facts.
2. Never invent table names or column names. You may only reference tables and
   columns provided to you.
3. Never claim causation. You may only describe correlations or changes present
   in the provided evidence.
4. Never mention competitors, industry averages, or market conditions unless they
   are already present in the input.
5. If evidence is insufficient, say so explicitly and mark it NOT_SUPPORTED.
6. Only use the metric_ids and values given in the evidence.

Your output must be valid JSON matching the requested schema exactly. Respond with
JSON only — no markdown fences."""


class LLMClient:
    def __init__(self) -> None:
        s = get_settings()
        self.enabled = s.llm_enabled and bool(s.openai_api_key)
        self.base_url = s.openai_base_url.rstrip("/")
        self.api_key = s.openai_api_key
        self.model = s.openai_model
        self.timeout = s.llm_timeout_seconds
        if not self.enabled:
            self.enabled = False

    async def _complete(self, messages: list[dict], json_schema: bool = True) -> str | None:
        if not self.enabled:
            return None
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                resp = await c.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"} if json_schema else None,
                        "messages": messages,
                    },
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception:
            return None

    def _parse_json(self, text: str | None) -> dict | None:
        if not text:
            return None
        # Strip markdown fences if the model ignored instructions.
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text.strip())
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    async def refine_plan(self, plan, model, prompt: str):
        """Ask the LLM to refine the deterministic plan. Output is re-validated."""
        if not self.enabled:
            return plan

        tables = {name: [c["name"] for c in cols] for name, cols in model.tables.items()}
        messages = [
            {"role": "system", "content": NO_HALLUCINATION_SYSTEM},
            {"role": "user", "content": json.dumps({
                "task": "refine_analysis_plan",
                "user_prompt": prompt,
                "available_tables": tables,
                "available_columns": model.tables.get("data", []),
                "constraints": "You may only use the available tables and columns. "
                               "Return sections (max 10), selected_skills (from: sales, customer, product, inventory, forecasting, statistics), requested_kpis, dimensions, comparisons.",
            })},
        ]
        content = await self._complete(messages)
        parsed = self._parse_json(content)
        if not parsed:
            return plan

        # Validate against schema: drop any column references that don't exist.
        known_cols = {str(c["name"]) for c in model.tables.get("data", [])}
        dims = [d for d in parsed.get("dimensions", []) if d in known_cols]
        skills = [s for s in parsed.get("selected_skills", [])
                  if s in {"sales", "customer", "product", "inventory", "forecasting", "statistics"}]

        if parsed.get("sections"):
            plan.sections = [str(s)[:100] for s in parsed["sections"]][:10]
        if skills:
            plan.selected_skills = skills
        if parsed.get("requested_kpis"):
            plan.requested_kpis = [str(k)[:100] for k in parsed["requested_kpis"]][:20]
        if dims:
            plan.dimensions = dims[:6]
        if parsed.get("comparisons"):
            plan.comparisons = [str(c)[:100] for c in parsed["comparisons"]][:6]
        if parsed.get("visual_requirements"):
            plan.visual_requirements = [str(v)[:100] for v in parsed["visual_requirements"]][:8]
        return plan

    # ------------------------------------------------------------------
    async def write_insight_prose(self, insight_draft: dict, registry_values: list[dict]) -> dict:
        """Polish an insight's finding/interpretation/impact from evidence only."""
        if not self.enabled:
            return insight_draft

        messages = [
            {"role": "system", "content": NO_HALLUCINATION_SYSTEM},
            {"role": "user", "content": json.dumps({
                "task": "write_insight_prose",
                "title": insight_draft["title"],
                "evidence": insight_draft["evidence"],
                "available_metrics": registry_values,
                "output_schema": {"finding": "str", "interpretation": "str", "business_impact": "str", "recommendation": "str", "confidence": "high|medium|low"},
            })},
        ]
        content = await self._complete(messages)
        parsed = self._parse_json(content)
        if not parsed:
            return insight_draft

        out = dict(insight_draft)
        for field in ("finding", "interpretation", "business_impact", "recommendation"):
            if isinstance(parsed.get(field), str) and parsed[field].strip():
                out[field] = parsed[field].strip()
        if parsed.get("confidence") in {"high", "medium", "low"}:
            out["confidence"] = parsed["confidence"]
        return out

    # ------------------------------------------------------------------
    async def write_report_sections(self, plan, registry_values: list[dict], insights: list[dict],
                                    quality: dict | None) -> dict[str, str]:
        """Write report section prose from plan + evidence. Returns section -> markdown."""
        if not self.enabled:
            return {}

        messages = [
            {"role": "system", "content": NO_HALLUCINATION_SYSTEM},
            {"role": "user", "content": json.dumps({
                "task": "write_report",
                "user_prompt": plan.prompt,
                "sections": plan.sections,
                "metrics": [{"metric_id": m["metric_id"], "name": m["name"], "value": m.get("value")} for m in registry_values],
                "insights": [{k: v for k, v in i.items() if k in ("title", "finding", "evidence", "recommendation")} for i in insights],
                "data_quality": quality,
                "output_schema": {"sections": {section_title: "markdown_prose"}},
                "rules": "Never invent numbers. If a requested KPI is not supported by the metrics, state so explicitly under that section and mark it NOT_SUPPORTED.",
            })},
        ]
        content = await self._complete(messages)
        parsed = self._parse_json(content)
        if not parsed or "sections" not in parsed or not isinstance(parsed["sections"], dict):
            return {}
        out: dict[str, str] = {}
        for section, prose in parsed["sections"].items():
            if isinstance(prose, str):
                out[str(section)[:200]] = prose.strip()
        return out
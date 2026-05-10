"""Agent 4: Dispatcher — generates stakeholder-specific response plans
(WFP, WHO, UNHCR, government) based on cascade predictions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from models.gemma_client import GemmaClient
from models.function_schemas import DISPATCHER_TOOLS

SYSTEM_PROMPT = """You are CascadeAI's Dispatcher agent. Given cascade impact predictions
for a country, you generate concrete, actionable response plans for different stakeholders.

Generate a response plan for EACH of these stakeholders:
1. WFP (World Food Programme) — food aid, logistics, pre-positioning
2. WHO (World Health Organization) — health surge, disease prevention, nutrition
3. UNHCR — displacement planning, camp setup, corridor logistics
4. National Government — policy, budget, trade, social protection

For each stakeholder, provide:
- "stakeholder": name
- "priority": "immediate" (0-30 days), "short_term" (30-90 days), "medium_term" (90-180 days)
- "actions": list of 3-5 specific, concrete actions
- "resources_needed": estimated resources
- "coordination_notes": how this links to other stakeholders

Return a JSON object with:
- "country": country name
- "response_plans": list of stakeholder plans
- "coordination_summary": one paragraph on cross-stakeholder coordination

Respond ONLY with valid JSON."""


@dataclass
class ResponsePlan:
    country: str
    response_plans: list[dict] = field(default_factory=list)
    coordination_summary: str = ""


class Dispatcher:
    def __init__(self, client: Optional[GemmaClient] = None):
        self.client = client or GemmaClient()

    def dispatch(
        self,
        country: str,
        predictions: list[dict],
        cascade_impacts: list[dict],
        event_summary: str = "",
    ) -> ResponsePlan:
        """Generate stakeholder response plans for a country."""
        user_prompt = self._build_prompt(country, predictions, cascade_impacts, event_summary)
        resp = self.client.complete(system=SYSTEM_PROMPT, user=user_prompt)
        parsed = self._parse_response(resp, country)

        return ResponsePlan(
            country=parsed.get("country", country),
            response_plans=parsed.get("response_plans", []),
            coordination_summary=parsed.get("coordination_summary", ""),
        )

    def _build_prompt(
        self, country: str, predictions: list[dict],
        cascade_impacts: list[dict], event_summary: str,
    ) -> str:
        return f"""Event: {event_summary}

Country: {country}

Impact predictions:
{json.dumps(predictions, indent=2)}

Cascade path:
{json.dumps(cascade_impacts, indent=2)}

Generate concrete, actionable response plans for WFP, WHO, UNHCR, and the
national government of {country}. Be specific — include quantities, timelines,
and logistics."""

    def _parse_response(self, text: str, country: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "country": country,
                "response_plans": [],
                "coordination_summary": f"Failed to parse response plans for {country}",
            }

    def _execute_tools(self, tool_calls: list[dict]) -> list[dict]:
        results = []
        for tc in tool_calls:
            results.append({
                "tool_call_id": tc["id"],
                "name": tc["name"],
                "result": f"[Stub] No live data for {tc['name']}({tc['arguments']})",
            })
        return results

"""Agent 3: Impact Predictor — generates specific numerical predictions
per country using cascade results + Gemma 4 reasoning."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from models.gemma_client import GemmaClient
from models.function_schemas import IMPACT_PREDICTOR_TOOLS

SYSTEM_PROMPT = """You are CascadeAI's Impact Predictor agent. Given a cascade analysis
showing which nodes are affected and their severity scores, you generate specific
numerical predictions for a target country.

You have access to tools to fetch real data. Use them to ground your predictions.

For each affected node in the cascade, produce a prediction with:
- "node": the graph node ID
- "indicator": the specific metric being predicted (e.g., "wheat_price_change_pct")
- "prediction": the predicted value (e.g., "+43%")
- "confidence": "high", "medium", or "low"
- "timeline_days": when this impact is expected (from the cascade delay)
- "affected_population": estimated number of people affected (if applicable)
- "reasoning": one sentence explaining the prediction

Return a JSON object with:
- "country": country name
- "predictions": list of prediction objects as described above
- "overall_severity": "critical" / "severe" / "moderate" / "mild"
- "headline": one-sentence summary for this country

Respond ONLY with valid JSON."""


@dataclass
class CountryPrediction:
    country: str
    predictions: list[dict] = field(default_factory=list)
    overall_severity: str = "moderate"
    headline: str = ""


class ImpactPredictor:
    def __init__(self, client: Optional[GemmaClient] = None):
        self.client = client or GemmaClient()

    def predict(
        self,
        country: str,
        cascade_impacts: list[dict],
        country_profile: dict,
        event_summary: str = "",
    ) -> CountryPrediction:
        """Generate numerical predictions for a country given cascade impacts."""
        user_prompt = self._build_prompt(country, cascade_impacts, country_profile, event_summary)

        resp = self.client.complete(system=SYSTEM_PROMPT, user=user_prompt)
        parsed = self._parse_response(resp, country)

        return CountryPrediction(
            country=parsed.get("country", country),
            predictions=parsed.get("predictions", []),
            overall_severity=parsed.get("overall_severity", "moderate"),
            headline=parsed.get("headline", ""),
        )

    def predict_with_tools(
        self,
        country: str,
        cascade_impacts: list[dict],
        country_profile: dict,
        event_summary: str = "",
    ) -> CountryPrediction:
        """Predict using function calling for live data grounding."""
        user_prompt = self._build_prompt(country, cascade_impacts, country_profile, event_summary)

        msg = self.client.complete_with_tools(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            tools=IMPACT_PREDICTOR_TOOLS,
        )

        tool_calls = self.client.extract_tool_calls(msg)
        if tool_calls:
            tool_results = self._execute_tools(tool_calls)
            follow_up = self.client.chat_sync(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                    msg,
                    {"role": "tool", "content": json.dumps(tool_results)},
                ]
            )
            resp = follow_up["choices"][0]["message"]["content"]
        else:
            resp = msg.get("content", "{}")

        parsed = self._parse_response(resp, country)
        return CountryPrediction(
            country=parsed.get("country", country),
            predictions=parsed.get("predictions", []),
            overall_severity=parsed.get("overall_severity", "moderate"),
            headline=parsed.get("headline", ""),
        )

    def _build_prompt(
        self, country: str, cascade_impacts: list[dict],
        country_profile: dict, event_summary: str,
    ) -> str:
        impacts_text = json.dumps(cascade_impacts, indent=2)
        profile_text = json.dumps(country_profile, indent=2)

        return f"""Event: {event_summary}

Target country: {country}

Cascade impacts (from BFS engine):
{impacts_text}

Country profile:
{profile_text}

Generate specific numerical predictions for {country} based on these cascade impacts
and the country's vulnerability profile. Be concrete — predict specific percentage
changes, population numbers, and timelines."""

    def _parse_response(self, text: str, country: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "country": country,
                "predictions": [],
                "overall_severity": "unknown",
                "headline": f"Failed to parse prediction for {country}",
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

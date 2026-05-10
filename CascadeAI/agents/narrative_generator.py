"""Agent 6: Narrative Generator — transforms cascade data into audience-specific
narratives in 6 formats and 8 native languages using Gemma 4 multilingual."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from models.gemma_client import GemmaClient

AUDIENCE_CONFIGS = {
    "who_briefing": {
        "label": "WHO Technical Briefing",
        "system": """You are writing a WHO-style technical briefing on a humanitarian crisis.
Use clinical language, IPC phase classifications, disease burden projections,
and epidemiological framing. Include specific health indicators and thresholds.
Structure: Situation Overview, Health Impact Assessment, Risk Factors, Recommendations.
Write in English.""",
        "language": "en",
    },
    "field_worker": {
        "label": "Field Worker Alert",
        "system": """You are writing an urgent field alert for a humanitarian aid worker
on the ground. Use simple, direct language. Focus on what they need to do
in the next 48 hours. Include specific action steps, locations, and priorities.
Avoid jargon. Write in {language_name} ({language_code}).
Structure: SITUATION (2 sentences), ACTIONS (numbered list, max 5), CONTACTS.""",
        "language": "local",
    },
    "policy_brief": {
        "label": "Policy Brief",
        "system": """You are writing a policy brief for a government minister or senior
official. Focus on GDP impact, trade implications, budget requirements, and
diplomatic considerations. Include specific dollar amounts and percentages.
Structure: Executive Summary, Economic Impact, Policy Options, Budget Implications.
Write in English.""",
        "language": "en",
    },
    "media_summary": {
        "label": "Media Summary",
        "system": """You are writing a factual, neutral press briefing on a developing
humanitarian crisis. Include quotable statistics, a clear timeline, and
data-driven framing. No blame, no opinion — just facts that tell the story.
Structure: Headline, Key Facts (bullet points), Timeline, Context.
Write in English.""",
        "language": "en",
    },
    "community_alert": {
        "label": "Community Preparedness Alert",
        "system": """You are writing a community preparedness alert for ordinary citizens
in an affected area — a mother, a farmer, a shopkeeper. Use plain, simple
language in {language_name}. Give household-level actionable advice they can
act on TODAY. Be warm, respectful, and empowering — not alarming.

Examples of advice: "Prices of [staple] may rise [X]% in [timeframe].
Consider buying extra now." or "Water supplies in [area] may be affected.
Store clean water."

Write the ENTIRE alert in {language_name} ({language_code}).
Keep it under 150 words. Use short sentences.""",
        "language": "local",
    },
    "public_brief": {
        "label": "Public Awareness Brief",
        "system": """You are writing a public awareness brief for journalists, civil society
organizations, and community leaders. Factual, neutral, no blame — designed
to close the information gap between institutions and the communities they serve.
Include data sources and links to official information where possible.
Structure: Situation Summary, Key Data Points, What This Means for Communities,
Where to Find Help. Write in English.""",
        "language": "en",
    },
}

LANGUAGE_MAP = {
    "kenya": ("Swahili", "sw"),
    "ethiopia": ("Amharic", "am"),
    "bangladesh": ("Bengali", "bn"),
    "egypt": ("Arabic", "ar"),
    "india": ("Hindi", "hi"),
    "turkey": ("Turkish", "tr"),
    "somalia": ("Somali", "so"),
    "pakistan": ("Urdu", "ur"),
    "congo_drc": ("French", "fr"),
    "chile": ("Spanish", "es"),
    "indonesia": ("Indonesian", "id"),
}


@dataclass
class Narrative:
    audience: str
    label: str
    language: str
    content: str


@dataclass
class NarrativeSet:
    country: str
    event_summary: str
    narratives: list[Narrative] = field(default_factory=list)


class NarrativeGenerator:
    def __init__(self, client: Optional[GemmaClient] = None):
        self.client = client or GemmaClient()

    def generate(
        self,
        country: str,
        cascade_impacts: list[dict],
        predictions: list[dict],
        event_summary: str = "",
        audiences: Optional[list[str]] = None,
    ) -> NarrativeSet:
        """Generate narratives for all (or selected) audiences."""
        if audiences is None:
            audiences = list(AUDIENCE_CONFIGS.keys())

        lang_name, lang_code = LANGUAGE_MAP.get(country.lower(), ("English", "en"))
        result = NarrativeSet(country=country, event_summary=event_summary)

        context = self._build_context(country, cascade_impacts, predictions, event_summary)

        for audience_key in audiences:
            cfg = AUDIENCE_CONFIGS.get(audience_key)
            if not cfg:
                continue

            system = cfg["system"].format(
                language_name=lang_name,
                language_code=lang_code,
            )

            narrative_text = self.client.complete(
                system=system,
                user=context,
            )

            actual_lang = lang_code if cfg["language"] == "local" else "en"

            result.narratives.append(Narrative(
                audience=audience_key,
                label=cfg["label"],
                language=actual_lang,
                content=narrative_text.strip(),
            ))

        return result

    def generate_single(
        self,
        audience_key: str,
        country: str,
        cascade_impacts: list[dict],
        predictions: list[dict],
        event_summary: str = "",
    ) -> Narrative:
        """Generate a narrative for a single audience."""
        result = self.generate(
            country=country,
            cascade_impacts=cascade_impacts,
            predictions=predictions,
            event_summary=event_summary,
            audiences=[audience_key],
        )
        return result.narratives[0] if result.narratives else Narrative(
            audience=audience_key, label="", language="en", content="Generation failed.",
        )

    def _build_context(
        self, country: str, cascade_impacts: list[dict],
        predictions: list[dict], event_summary: str,
    ) -> str:
        return f"""Crisis event: {event_summary}
Country: {country}

Cascade impacts (from dependency graph BFS):
{json.dumps(cascade_impacts, indent=2)}

Country-specific predictions:
{json.dumps(predictions, indent=2)}

Generate the appropriate narrative based on this data."""

    @staticmethod
    def available_audiences() -> dict[str, str]:
        return {k: v["label"] for k, v in AUDIENCE_CONFIGS.items()}

    @staticmethod
    def get_language_for_country(country: str) -> tuple[str, str]:
        return LANGUAGE_MAP.get(country.lower(), ("English", "en"))

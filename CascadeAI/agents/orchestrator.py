"""Agent 7: Orchestrator — coordinates all agents in the CascadeAI pipeline.

Flow: Event Detector -> Cascade Analyzer (BFS) -> Impact Predictor ->
      Dispatcher -> Narrative Generator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cascade.graph import CascadeGraph
from cascade.traversal import run_cascade, run_compound_cascade, CascadeImpact
from data.profiles import load_profile, get_profile_raw
from models.gemma_client import GemmaClient
from agents.event_detector import EventDetector, DetectedEvent
from agents.impact_predictor import ImpactPredictor, CountryPrediction
from agents.dispatcher import Dispatcher, ResponsePlan
from agents.narrative_generator import NarrativeGenerator, NarrativeSet


@dataclass
class PipelineResult:
    """Full output of the CascadeAI pipeline for one event + one country."""
    event: DetectedEvent
    cascade_impacts: list[CascadeImpact]
    prediction: CountryPrediction
    response_plan: ResponsePlan
    narratives: Optional[NarrativeSet] = None


@dataclass
class MultiCountryResult:
    """Full output across multiple countries."""
    event: DetectedEvent
    results: dict[str, PipelineResult] = field(default_factory=dict)


class Orchestrator:
    def __init__(self, client: Optional[GemmaClient] = None, use_tools: bool = False):
        self.client = client or GemmaClient()
        self.use_tools = use_tools
        self.graph = CascadeGraph.from_json()
        self.event_detector = EventDetector(self.client)
        self.impact_predictor = ImpactPredictor(self.client)
        self.dispatcher = Dispatcher(self.client)
        self.narrative_generator = NarrativeGenerator(self.client)

    def run(
        self,
        event_description: str,
        countries: Optional[list[str]] = None,
        audiences: Optional[list[str]] = None,
        skip_narratives: bool = False,
    ) -> MultiCountryResult:
        """Run the full CascadeAI pipeline for an event across countries."""
        if countries is None:
            countries = ["kenya", "ethiopia", "somalia", "egypt",
                         "bangladesh", "india", "turkey", "pakistan"]

        # Step 1: Event Detection
        if self.use_tools:
            event = self.event_detector.detect_with_tools(event_description)
        else:
            event = self.event_detector.detect(event_description)

        result = MultiCountryResult(event=event)

        for country_name in countries:
            country_result = self._run_country(
                event, country_name, event_description,
                audiences=audiences, skip_narratives=skip_narratives,
            )
            result.results[country_name] = country_result

        return result

    def run_cascade_only(
        self,
        node: str,
        severity: float,
        country: str,
    ) -> list[CascadeImpact]:
        """Run just the BFS cascade for a country (no LLM needed)."""
        profile = load_profile(country)
        return run_cascade(self.graph, node, severity, country=profile)

    def run_compound(
        self,
        events: list[dict],
        country: str,
    ) -> list[CascadeImpact]:
        """Run compound cascade for multiple simultaneous events."""
        profile = load_profile(country)
        return run_compound_cascade(self.graph, events, country=profile)

    def _run_country(
        self,
        event: DetectedEvent,
        country_name: str,
        event_description: str,
        audiences: Optional[list[str]] = None,
        skip_narratives: bool = False,
    ) -> PipelineResult:
        # Step 2: Cascade Analysis (deterministic BFS — no LLM)
        profile = load_profile(country_name)
        cascade_impacts = run_cascade(
            self.graph, event.node, event.severity, country=profile
        )

        impacts_as_dicts = [
            {
                "node": i.node,
                "severity": i.severity,
                "delay_days": i.delay_days,
                "path": i.path,
            }
            for i in cascade_impacts
        ]

        # Step 3: Impact Prediction (Gemma 4)
        country_profile_raw = get_profile_raw(country_name)
        prediction = self.impact_predictor.predict(
            country=country_name,
            cascade_impacts=impacts_as_dicts,
            country_profile=country_profile_raw,
            event_summary=event_description,
        )

        # Step 4: Dispatch (Gemma 4)
        response_plan = self.dispatcher.dispatch(
            country=country_name,
            predictions=prediction.predictions,
            cascade_impacts=impacts_as_dicts,
            event_summary=event_description,
        )

        # Step 5: Narrative Generation (Gemma 4, optional)
        narratives = None
        if not skip_narratives:
            narratives = self.narrative_generator.generate(
                country=country_name,
                cascade_impacts=impacts_as_dicts,
                predictions=prediction.predictions,
                event_summary=event_description,
                audiences=audiences,
            )

        return PipelineResult(
            event=event,
            cascade_impacts=cascade_impacts,
            prediction=prediction,
            response_plan=response_plan,
            narratives=narratives,
        )

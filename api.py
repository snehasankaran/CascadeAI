"""CascadeAI — FastAPI Backend

Run: uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import config  # noqa: F401 — loads .env

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cascade.graph import CascadeGraph
from cascade.traversal import run_cascade, run_compound_cascade
from cascade.replay import run_backtest, available_scenarios
from data.profiles import load_profile, available_countries, get_profile_raw
from models.gemma_client import GemmaClient
from agents.event_detector import EventDetector
from agents.narrative_generator import NarrativeGenerator, AUDIENCE_CONFIGS
from agents.action_verifier import ActionVerifier

app = FastAPI(
    title="CascadeAI API",
    description="Humanitarian crisis cascade prediction powered by Gemma 4",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = CascadeGraph.from_json()


# ── Request/Response Models ───────────────────────────────────────

class CascadeRequest(BaseModel):
    node: str = Field(description="Crisis type node ID (e.g., 'war', 'energy')")
    severity: float = Field(ge=0.0, le=1.0, description="Crisis severity 0.0-1.0")
    country: str = Field(description="Country name (e.g., 'kenya')")


class CompoundRequest(BaseModel):
    events: list[dict] = Field(description="List of {node, severity} dicts")
    country: str


class EventDetectRequest(BaseModel):
    description: str = Field(description="Natural language crisis description")


class NarrativeRequest(BaseModel):
    audience: str = Field(description="Audience key (e.g., 'community_alert')")
    country: str
    cascade_impacts: list[dict]
    event_summary: str = ""


class VerifyRequest(BaseModel):
    country: str = Field(description="Target country (e.g. 'Kenya')")
    response_plans: list[dict] = Field(
        description="Dispatcher response plans (each with stakeholder + actions list)",
    )
    region: str | None = Field(
        default=None,
        description="Optional ACLED region (e.g. 'East Africa') for conflict context",
    )
    event_summary: str = ""


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "CascadeAI", "version": "1.0.0", "model": "Gemma 4"}


@app.get("/graph")
def get_graph():
    return {
        "nodes": [{"id": n.id, "label": n.label} for n in graph.nodes.values()],
        "edges": [{"from": e.src, "to": e.dst, "weight": e.weight, "delay_mid": e.delay_mid} for e in graph.edges],
    }


@app.get("/countries")
def get_countries():
    return {"countries": available_countries()}


@app.get("/countries/{country}")
def get_country(country: str):
    try:
        return get_profile_raw(country)
    except FileNotFoundError:
        raise HTTPException(404, f"Country '{country}' not found")


@app.post("/cascade")
def run_cascade_endpoint(req: CascadeRequest):
    if req.node not in graph.nodes:
        raise HTTPException(400, f"Unknown node '{req.node}'")
    try:
        profile = load_profile(req.country)
    except FileNotFoundError:
        raise HTTPException(404, f"Country '{req.country}' not found")

    impacts = run_cascade(graph, req.node, req.severity, country=profile)
    return {
        "node": req.node,
        "severity": req.severity,
        "country": req.country,
        "impacts": [
            {"node": i.node, "severity": i.severity, "delay_days": i.delay_days,
             "path": i.path, "is_seed": i.is_seed}
            for i in impacts
        ],
    }


@app.post("/cascade/compound")
def run_compound_endpoint(req: CompoundRequest):
    try:
        profile = load_profile(req.country)
    except FileNotFoundError:
        raise HTTPException(404, f"Country '{req.country}' not found")

    impacts = run_compound_cascade(graph, req.events, country=profile)
    return {
        "events": req.events,
        "country": req.country,
        "impacts": [
            {"node": i.node, "severity": i.severity, "delay_days": i.delay_days,
             "path": i.path, "is_seed": i.is_seed}
            for i in impacts
        ],
    }


@app.post("/detect")
def detect_event(req: EventDetectRequest):
    client = GemmaClient()
    detector = EventDetector(client)
    event = detector.detect(req.description)
    return {
        "node": event.node,
        "severity": event.severity,
        "region": event.region,
        "summary": event.summary,
        "secondary_nodes": event.secondary_nodes,
    }


@app.post("/narrative")
def generate_narrative(req: NarrativeRequest):
    if req.audience not in AUDIENCE_CONFIGS:
        raise HTTPException(400, f"Unknown audience '{req.audience}'. Available: {list(AUDIENCE_CONFIGS.keys())}")

    client = GemmaClient()
    gen = NarrativeGenerator(client)
    narrative = gen.generate_single(
        audience_key=req.audience,
        country=req.country,
        cascade_impacts=req.cascade_impacts,
        predictions=[],
        event_summary=req.event_summary,
    )
    return {
        "audience": narrative.audience,
        "label": narrative.label,
        "language": narrative.language,
        "content": narrative.content,
    }


@app.get("/backtest/scenarios")
def list_scenarios():
    return {"scenarios": available_scenarios()}


@app.get("/backtest/{scenario}")
def run_backtest_endpoint(scenario: str):
    try:
        results = run_backtest(scenario)
    except FileNotFoundError:
        raise HTTPException(404, f"Scenario '{scenario}' not found")

    return {
        "scenario": scenario,
        "results": [
            {
                "country": r.country,
                "crisis_name": r.crisis_name,
                "trigger_date": r.trigger_date,
                "comparisons": [
                    {"indicator": c.indicator, "predicted": c.predicted,
                     "actual": c.actual, "accuracy": c.accuracy}
                    for c in r.comparisons
                ],
            }
            for r in results
        ],
    }


@app.get("/audiences")
def list_audiences():
    return {k: v["label"] for k, v in AUDIENCE_CONFIGS.items()}


@app.post("/verify")
def verify_actions(req: VerifyRequest):
    """Check Dispatcher recommendations against current-affairs reporting.

    Returns per-action status (in_progress / partial / gap), blind spots,
    and the live evidence sources used (ReliefWeb + ACLED).
    """
    client = GemmaClient()
    verifier = ActionVerifier(client)
    result = verifier.verify(
        country=req.country,
        response_plans=req.response_plans,
        region=req.region,
        event_summary=req.event_summary,
    )
    return {
        "country": result.country,
        "verifications": [
            {
                "stakeholder": v.stakeholder,
                "action": v.action,
                "status": v.status,
                "evidence": v.evidence,
                "confidence": v.confidence,
            }
            for v in result.verifications
        ],
        "blind_spots": result.blind_spots,
        "coverage_summary": result.coverage_summary,
        "evidence_sources": result.evidence_sources,
    }


from data.predictions.loader import available_predictions, load_prediction


@app.get("/predictions")
def list_predictions():
    return {"predictions": available_predictions()}


@app.get("/predictions/{name}")
def get_prediction(name: str):
    try:
        return load_prediction(name)
    except FileNotFoundError:
        raise HTTPException(404, f"Prediction '{name}' not found")

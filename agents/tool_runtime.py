"""Tool runtime — executes the function-call tools Gemma 4 emits.

This is the bridge between the model's ``tool_call`` control tokens and the
real ReliefWeb / ACLED / commodity fetchers. Both ``ActionVerifier`` and
``EventDetector`` route their tool calls through here so a single registry
governs which external data source maps to which tool name.

Every executor returns a JSON-serialisable ``dict`` so the result can be
fed straight back to Gemma 4 as a ``role: tool`` message.
"""

from __future__ import annotations

from typing import Any, Callable

from data.fetchers.acled_api import search_acled_events
from data.fetchers.reliefweb_api import fetch_response_plans, search_reports


# ---------------------------------------------------------------------------
# Action Verifier tools
# ---------------------------------------------------------------------------

def _tool_search_reliefweb_reports(args: dict) -> dict:
    country = args.get("country", "")
    query = args.get("query") or None
    limit = int(args.get("limit", 10) or 10)
    return search_reports(country=country, query=query, limit=limit)


def _tool_search_acled_recent(args: dict) -> dict:
    region = args.get("region", "")
    country = args.get("country") or None
    days = int(args.get("days", 30) or 30)
    return search_acled_events(region=region, days=days, country=country)


def _tool_lookup_active_response_plans(args: dict) -> dict:
    return fetch_response_plans(country=args.get("country", ""))


# ---------------------------------------------------------------------------
# Event Detector tools
# ---------------------------------------------------------------------------

def _tool_search_acled_events(args: dict) -> dict:
    region = args.get("region", "")
    country = args.get("country") or None
    days = int(args.get("days", 30) or 30)
    return search_acled_events(region=region, days=days, country=country)


def _tool_search_gdelt_events(args: dict) -> dict:
    # GDELT integration is out of scope for the hackathon submission;
    # we return a structured "no live data" payload so the model can still
    # reason about the absence of evidence rather than crashing.
    return {
        "source": "unavailable",
        "query": args.get("query", ""),
        "events": [],
        "note": "GDELT live fetch not wired in this build — proceed with priors.",
    }


def _tool_get_historical_severity(args: dict) -> dict:
    event_type = (args.get("event_type") or "").lower()
    region = args.get("region", "")

    # Static priors derived from CascadeAI's backtest scenarios. Keeps the
    # tool useful offline (Ollama edge mode) without needing a DB.
    priors = {
        "war": {"severity": 0.85, "examples": ["Ukraine 2022 (0.9)", "Sudan 2023 (0.85)"]},
        "conflict": {"severity": 0.75, "examples": ["Tigray 2020 (0.8)", "Yemen 2015 (0.85)"]},
        "shipping": {"severity": 0.7, "examples": ["Hormuz 2026 (0.75)", "Suez 2021 (0.5)"]},
        "energy": {"severity": 0.65, "examples": ["Hormuz 2026 (0.75)", "Russia gas 2022 (0.7)"]},
        "drought": {"severity": 0.7, "examples": ["Horn of Africa 2022 (0.8)", "Somalia 2026 (0.85)"]},
        "flood": {"severity": 0.55, "examples": ["Pakistan 2022 (0.85)", "Libya 2023 (0.75)"]},
        "earthquake": {"severity": 0.7, "examples": ["Türkiye-Syria 2023 (0.85)"]},
        "outbreak": {"severity": 0.6, "examples": ["DRC Ebola 2018 (0.75)", "Yemen cholera 2017 (0.7)"]},
    }
    match = None
    for key, val in priors.items():
        if key in event_type:
            match = val
            break
    if match is None:
        return {
            "source": "cascadeai_priors",
            "event_type": event_type,
            "region": region,
            "severity_estimate": 0.5,
            "examples": [],
            "note": "No exact prior match; default mid-severity.",
        }
    return {
        "source": "cascadeai_priors",
        "event_type": event_type,
        "region": region,
        "severity_estimate": match["severity"],
        "examples": match["examples"],
    }


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

VERIFIER_TOOL_REGISTRY: dict[str, Callable[[dict], dict]] = {
    "search_reliefweb_reports": _tool_search_reliefweb_reports,
    "search_acled_recent": _tool_search_acled_recent,
    "lookup_active_response_plans": _tool_lookup_active_response_plans,
}

EVENT_DETECTOR_TOOL_REGISTRY: dict[str, Callable[[dict], dict]] = {
    "search_acled_events": _tool_search_acled_events,
    "search_gdelt_events": _tool_search_gdelt_events,
    "get_historical_severity": _tool_get_historical_severity,
}


def execute_verifier_tool(name: str, args: Any) -> dict:
    """Execute a tool call from the Action Verifier. Returns a dict so the
    result can be fed back to Gemma 4 as a ``role: tool`` message."""
    fn = VERIFIER_TOOL_REGISTRY.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}", "available": list(VERIFIER_TOOL_REGISTRY)}
    return fn(args if isinstance(args, dict) else {})


def execute_event_detector_tool(name: str, args: Any) -> dict:
    """Execute a tool call from the Event Detector."""
    fn = EVENT_DETECTOR_TOOL_REGISTRY.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}", "available": list(EVENT_DETECTOR_TOOL_REGISTRY)}
    return fn(args if isinstance(args, dict) else {})

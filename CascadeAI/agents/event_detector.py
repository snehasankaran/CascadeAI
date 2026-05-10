"""Agent 1: Event Detector — classifies a raw crisis description into a
graph node ID, severity (0-1), and affected region using Gemma 4."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from models.gemma_client import GemmaClient
from models.function_schemas import EVENT_DETECTOR_TOOLS

SYSTEM_PROMPT = """You are CascadeAI's Event Detector agent. Your job is to classify
a raw crisis event description into a structured format for the cascade dependency graph.

The dependency graph has these nodes:
  war, energy, transport, fertilizer, crop, food, economy, jobs, health, water, displacement

For every crisis event, you MUST return a JSON object with:
- "node": the primary graph node ID that this event maps to (one of the 11 above)
- "severity": a float from 0.0 to 1.0 (0.1=minor, 0.5=significant, 0.8=severe, 1.0=catastrophic)
- "region": the geographic region primarily affected
- "summary": a one-sentence summary of why this severity was assigned
- "secondary_nodes": optional list of other nodes directly affected

Use the available tools to gather context if needed, but always return the JSON classification.

Respond ONLY with valid JSON. No markdown, no explanation outside the JSON."""


@dataclass
class DetectedEvent:
    node: str
    severity: float
    region: str
    summary: str
    secondary_nodes: list[str]


class EventDetector:
    def __init__(self, client: Optional[GemmaClient] = None):
        self.client = client or GemmaClient()

    def detect(self, event_description: str) -> DetectedEvent:
        """Classify a crisis event description into a graph node + severity."""
        resp = self.client.complete(
            system=SYSTEM_PROMPT,
            user=event_description,
        )

        parsed = self._parse_response(resp)
        return DetectedEvent(
            node=parsed["node"],
            severity=float(parsed["severity"]),
            region=parsed.get("region", "Unknown"),
            summary=parsed.get("summary", ""),
            secondary_nodes=parsed.get("secondary_nodes", []),
        )

    def detect_with_tools(self, event_description: str) -> DetectedEvent:
        """Classify using function calling for richer context."""
        msg = self.client.complete_with_tools(
            system=SYSTEM_PROMPT,
            user=event_description,
            tools=EVENT_DETECTOR_TOOLS,
        )

        tool_calls = self.client.extract_tool_calls(msg)
        if tool_calls:
            tool_results = self._execute_tools(tool_calls)
            follow_up = self.client.chat_sync(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": event_description},
                    msg,
                    {"role": "tool", "content": json.dumps(tool_results)},
                ]
            )
            resp = follow_up["choices"][0]["message"]["content"]
        else:
            resp = msg.get("content", "{}")

        parsed = self._parse_response(resp)
        return DetectedEvent(
            node=parsed["node"],
            severity=float(parsed["severity"]),
            region=parsed.get("region", "Unknown"),
            summary=parsed.get("summary", ""),
            secondary_nodes=parsed.get("secondary_nodes", []),
        )

    def _parse_response(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "node": "war",
                "severity": 0.5,
                "region": "Unknown",
                "summary": f"Failed to parse: {text[:200]}",
                "secondary_nodes": [],
            }

    def _execute_tools(self, tool_calls: list[dict]) -> list[dict]:
        """Stub tool executor — returns placeholder data.
        Replace with real API calls in data/fetchers/."""
        results = []
        for tc in tool_calls:
            results.append({
                "tool_call_id": tc["id"],
                "name": tc["name"],
                "result": f"[Stub] No live data for {tc['name']}({tc['arguments']})",
            })
        return results

"""Agent 1: Event Detector — classifies a raw crisis description into a
graph node ID, severity (0-1), and affected region using Gemma 4.

When ``detect_with_tools`` is called, Gemma 4 uses its native function-calling
protocol to decide which evidence-gathering tools to invoke (ACLED / GDELT /
historical priors) before committing to a classification. The tools are
dispatched through ``agents.tool_runtime`` so the Action Verifier and Event
Detector share the same executor registry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from agents.tool_runtime import execute_event_detector_tool
from models.function_schemas import EVENT_DETECTOR_TOOLS
from models.gemma_client import GemmaClient

MAX_TOOL_ROUNDS = 3

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
    tool_trace: list[dict] = field(default_factory=list)
    used_native_tools: bool = False


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
        """Classify using Gemma 4's native function-calling protocol.

        Runs a multi-turn agentic loop: the model emits ``tool_call`` tokens,
        we execute them via :func:`agents.tool_runtime.execute_event_detector_tool`,
        feed the results back as ``role: tool`` messages, and let Gemma 4
        commit to the final JSON classification.
        """
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": event_description},
        ]
        tool_trace: list[dict] = []
        final_content = "{}"

        for _round in range(MAX_TOOL_ROUNDS):
            resp = self.client.chat_sync(messages=messages, tools=EVENT_DETECTOR_TOOLS)
            msg = resp["choices"][0]["message"]
            tool_calls = self.client.extract_tool_calls(msg)

            if not tool_calls:
                final_content = msg.get("content", "") or "{}"
                break

            messages.append({
                "role": "assistant",
                "content": msg.get("content", "") or "",
                "tool_calls": msg.get("tool_calls", []),
            })

            for tc in tool_calls:
                result = execute_event_detector_tool(tc["name"], tc.get("arguments", {}))
                tool_trace.append({
                    "name": tc["name"],
                    "arguments": tc.get("arguments", {}),
                    "result": result,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or tc["name"],
                    "name": tc["name"],
                    "content": json.dumps(result),
                })
        else:
            # Tool budget exhausted — force a commit.
            messages.append({
                "role": "user",
                "content": (
                    "Stop calling tools. Return ONLY the JSON classification "
                    "specified in the system prompt."
                ),
            })
            resp = self.client.chat_sync(messages=messages)
            final_content = resp["choices"][0]["message"].get("content", "") or "{}"

        parsed = self._parse_response(final_content)
        return DetectedEvent(
            node=parsed["node"],
            severity=float(parsed["severity"]),
            region=parsed.get("region", "Unknown"),
            summary=parsed.get("summary", ""),
            secondary_nodes=parsed.get("secondary_nodes", []),
            tool_trace=tool_trace,
            used_native_tools=True,
        )

    def _parse_response(self, text: str) -> dict:
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        if text.lower().startswith("json"):
            text = text.split("\n", 1)[-1]
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

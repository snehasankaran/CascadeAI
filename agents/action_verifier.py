"""Agent 8: Action Verifier — closes the loop on the cascade pipeline.

Takes the Dispatcher's recommended actions for a country and compares them
against what is *already being done on the ground* by **letting Gemma 4
autonomously call live tools** to pull current-affairs evidence from
ReliefWeb situation reports and ACLED conflict feeds.

Architecture: this agent uses Gemma 4's **native function-calling protocol**
(``apply_chat_template(tools=[...])`` on Hugging Face / ``functionDeclarations``
on Google AI Studio / ``tools`` array on Ollama). It does NOT prompt-engineer
JSON tool calls — Gemma 4 emits genuine ``tool_call`` control tokens and the
``GemmaClient`` translates between the OpenAI tools format and whichever
backend is configured.

For each recommended action, Gemma 4 classifies its real-world status:
  - "in_progress"  → response is active / well covered
  - "partial"      → some activity, but gaps remain
  - "gap"          → no evidence of response → CascadeAI surfaces this to users

This is the "blind spot finder" — it tells humanitarian responders what they
have NOT yet covered, in real time, against live reporting.

If tool-call parsing fails (e.g. an older Ollama build), the agent falls back
to the legacy one-shot prompt that pre-fetches evidence and asks Gemma 4 to
classify directly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from agents.tool_runtime import execute_verifier_tool
from data.fetchers.acled_api import search_acled_events
from data.fetchers.reliefweb_api import fetch_response_plans, search_reports
from models.function_schemas import ACTION_VERIFIER_TOOLS
from models.gemma_client import GemmaClient

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

NATIVE_SYSTEM_PROMPT = """You are CascadeAI's Action Verifier — an autonomous
humanitarian-evidence agent. You will be given a list of recommended actions
(from the CascadeAI Dispatcher) for a country in crisis, and three tools you
can call to gather **real-world evidence** of what is already being done on
the ground:

  - search_reliefweb_reports(country, query=None, limit=10)
        Latest humanitarian situation reports for the country.
  - search_acled_recent(country=None, region=None, days=30)
        Recent ACLED political-violence aggregates. Pass ``country`` for a
        country-scoped summary (preferred); pass ``region`` to roll up
        across the region.
  - lookup_active_response_plans(country)
        Active humanitarian response plans on ReliefWeb.

Your job, in two phases:

PHASE 1 — Evidence gathering. Decide which tools to call. Call AT LEAST
``search_reliefweb_reports`` and ``lookup_active_response_plans`` for the
country, plus ``search_acled_recent(country=<country>)`` to ground the
security context in real ACLED political-violence aggregates. You may make
additional ``search_reliefweb_reports`` calls with focused queries (e.g.
"cholera", "food distribution", "refugee") if the initial results are
sparse.

PHASE 2 — Verification. Once you have evidence, return a SINGLE JSON object
(no markdown, no commentary) with this exact shape:

{
  "country": "<country>",
  "verifications": [
    {
      "stakeholder": "WFP|WHO|UNHCR|Government of …",
      "action": "<verbatim recommended action>",
      "status": "in_progress|partial|gap",
      "evidence": "<one sentence citing the matching ReliefWeb report / ACLED signal, or 'No matching evidence found.' if gap>",
      "confidence": "high|medium|low"
    }
  ],
  "blind_spots": ["<action description>"],
  "coverage_summary": "<one paragraph summarising overall response coverage and ending with the top blind spot>"
}

Be conservative: when there is no specific evidence, classify as "gap". The
"blind_spots" list is the critical output — these are the unaddressed cascade
risks CascadeAI surfaces to humanitarian responders."""


LEGACY_SYSTEM_PROMPT = """You are CascadeAI's Action Verifier agent. You are given:
  1. A list of recommended actions (from the Dispatcher) for a country in crisis.
  2. Real-world evidence from ReliefWeb situation reports and ACLED conflict feeds.

For EACH recommended action, decide whether it is already being executed on
the ground, based ONLY on the evidence provided. Be conservative: if there
is no specific evidence, classify as "gap".

Return a JSON object with:
- "country": country name
- "verifications": list, one entry per action, each with:
    - "stakeholder": which org owns the action (WFP, WHO, UNHCR, government)
    - "action": short description (verbatim from the input)
    - "status": one of "in_progress" | "partial" | "gap"
    - "evidence": one-sentence citation of the matching ReliefWeb report or
      ACLED signal, or "No matching evidence found." if "gap"
    - "confidence": "high" | "medium" | "low"
- "blind_spots": list of action descriptions where status == "gap"
- "coverage_summary": one-paragraph human-readable summary of overall
  response coverage, ending with the top blind spot.

Respond ONLY with valid JSON. No markdown."""


# Max agentic turns before we force the verifier to commit.
MAX_TOOL_ROUNDS = 4


@dataclass
class ActionVerification:
    stakeholder: str
    action: str
    status: str
    evidence: str
    confidence: str


@dataclass
class VerificationResult:
    country: str
    verifications: list[ActionVerification] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)
    coverage_summary: str = ""
    evidence_sources: list[dict] = field(default_factory=list)
    tool_trace: list[dict] = field(default_factory=list)
    used_native_tools: bool = False


class ActionVerifier:
    """Cross-checks Dispatcher recommendations against live humanitarian data
    using Gemma 4's native function-calling protocol."""

    def __init__(self, client: Optional[GemmaClient] = None):
        self.client = client or GemmaClient()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def verify(
        self,
        country: str,
        response_plans: list[dict],
        region: Optional[str] = None,
        event_summary: str = "",
        prefer_native_tools: bool = True,
    ) -> VerificationResult:
        """Verify Dispatcher response plans against current affairs.

        Args:
            country: target country (e.g. "Kenya")
            response_plans: list of stakeholder plans from Dispatcher
                            (each has "stakeholder", "actions", "priority", ...)
            region: optional ACLED region for conflict context
                    (e.g. "East Africa")
            event_summary: the original crisis description (for grounding)
            prefer_native_tools: when True (default) try Gemma 4 native
                function-calling first; fall back to the legacy prompt-based
                verifier if the model can't / won't emit tool_calls.
        """
        actions_flat = self._flatten_actions(response_plans)

        if prefer_native_tools:
            try:
                return self._verify_with_native_tools(
                    country=country,
                    region=region,
                    actions=actions_flat,
                    event_summary=event_summary,
                )
            except Exception as exc:  # noqa: BLE001
                # Any failure in the agentic loop → fall back to legacy.
                fallback = self._verify_legacy(country, region, actions_flat, event_summary)
                fallback.coverage_summary = (
                    f"[Native tool-call path failed: {type(exc).__name__}. "
                    f"Showing legacy one-shot verification.]\n\n"
                    + fallback.coverage_summary
                )
                return fallback

        return self._verify_legacy(country, region, actions_flat, event_summary)

    # ------------------------------------------------------------------
    # Native function-calling agentic loop
    # ------------------------------------------------------------------

    def _verify_with_native_tools(
        self,
        country: str,
        region: Optional[str],
        actions: list[dict],
        event_summary: str,
    ) -> VerificationResult:
        """Run a multi-turn agentic loop where Gemma 4 chooses which tools to
        call to gather evidence, then emits the final verification JSON."""

        user_prompt = self._native_user_prompt(country, region, actions, event_summary)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": NATIVE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        tool_trace: list[dict] = []
        all_sources: list[dict] = []
        final_content: Optional[str] = None

        for _round in range(MAX_TOOL_ROUNDS):
            resp = self.client.chat_sync(messages=messages, tools=ACTION_VERIFIER_TOOLS)
            msg = resp["choices"][0]["message"]
            tool_calls = self.client.extract_tool_calls(msg)

            if not tool_calls:
                # Model emitted text — assume it's the final verification JSON.
                final_content = msg.get("content", "")
                messages.append({
                    "role": "assistant",
                    "content": final_content,
                })
                break

            # Stash the assistant turn that *requested* the tool calls.
            messages.append({
                "role": "assistant",
                "content": msg.get("content", "") or "",
                "tool_calls": msg.get("tool_calls", []),
            })

            # Execute each tool call and feed the results back.
            for tc in tool_calls:
                result = execute_verifier_tool(tc["name"], tc.get("arguments", {}))
                tool_trace.append({
                    "name": tc["name"],
                    "arguments": tc.get("arguments", {}),
                    "result_summary": _summarise_tool_result(result),
                })
                all_sources.extend(_extract_sources(tc["name"], tc.get("arguments", {}), result))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or tc["name"],
                    "name": tc["name"],
                    "content": json.dumps(result),
                })
        else:
            # Hit MAX_TOOL_ROUNDS without a final answer — force one last turn
            # without tools so the model has to commit to a JSON answer.
            messages.append({
                "role": "user",
                "content": (
                    "Stop calling tools. You now have enough evidence. "
                    "Return ONLY the final JSON object as specified in the "
                    "system prompt."
                ),
            })
            resp = self.client.chat_sync(messages=messages)
            final_content = resp["choices"][0]["message"].get("content", "")

        parsed = self._parse_response(final_content or "", country, actions)

        verifications = [
            ActionVerification(
                stakeholder=v.get("stakeholder", ""),
                action=v.get("action", ""),
                status=v.get("status", "gap"),
                evidence=v.get("evidence", "No matching evidence found."),
                confidence=v.get("confidence", "low"),
            )
            for v in parsed.get("verifications", [])
        ]

        return VerificationResult(
            country=parsed.get("country", country),
            verifications=verifications,
            blind_spots=parsed.get("blind_spots", []),
            coverage_summary=parsed.get("coverage_summary", ""),
            evidence_sources=_dedupe_sources(all_sources),
            tool_trace=tool_trace,
            used_native_tools=True,
        )

    def _native_user_prompt(
        self,
        country: str,
        region: Optional[str],
        actions: list[dict],
        event_summary: str,
    ) -> str:
        region_clause = f"Region (for ACLED): {region}" if region else "Region: (not provided)"
        return f"""Event: {event_summary or '(no summary provided)'}
Country: {country}
{region_clause}

Recommended actions (from CascadeAI Dispatcher), one row per stakeholder action:
{json.dumps(actions, indent=2)}

Now gather evidence by calling the available tools, then emit the final
verification JSON exactly as specified in your instructions."""

    # ------------------------------------------------------------------
    # Legacy one-shot fallback (evidence pre-fetched, model classifies once)
    # ------------------------------------------------------------------

    def _verify_legacy(
        self,
        country: str,
        region: Optional[str],
        actions: list[dict],
        event_summary: str,
    ) -> VerificationResult:
        evidence = self._gather_evidence(country, region)
        prompt = self._legacy_prompt(country, actions, evidence, event_summary)
        resp = self.client.complete(system=LEGACY_SYSTEM_PROMPT, user=prompt)
        parsed = self._parse_response(resp, country, actions)

        verifications = [
            ActionVerification(
                stakeholder=v.get("stakeholder", ""),
                action=v.get("action", ""),
                status=v.get("status", "gap"),
                evidence=v.get("evidence", "No matching evidence found."),
                confidence=v.get("confidence", "low"),
            )
            for v in parsed.get("verifications", [])
        ]

        return VerificationResult(
            country=parsed.get("country", country),
            verifications=verifications,
            blind_spots=parsed.get("blind_spots", []),
            coverage_summary=parsed.get("coverage_summary", ""),
            evidence_sources=evidence.get("sources", []),
            used_native_tools=False,
        )

    def _gather_evidence(self, country: str, region: Optional[str]) -> dict:
        rw_reports = search_reports(country=country, limit=10)
        rw_plans = fetch_response_plans(country=country)

        # Prefer country-scoped ACLED via HDX; region is used as the fallback
        # aggregation key when no per-country file exists.
        acled_data: dict = search_acled_events(
            region=region or "",
            days=30,
            country=country,
        )

        sources: list[dict] = []
        for r in rw_reports.get("reports", []):
            sources.append({
                "type": "reliefweb_report",
                "title": r.get("title", ""),
                "date": r.get("date", ""),
                "org": r.get("source", ""),
                "url": r.get("url", ""),
            })
        for r in rw_plans.get("reports", []):
            sources.append({
                "type": "reliefweb_plan",
                "title": r.get("title", ""),
                "date": r.get("date", ""),
                "org": r.get("source", ""),
                "url": r.get("url", ""),
            })
        if acled_data:
            sources.append({
                "type": "acled_summary",
                "transport": acled_data.get("source", "ACLED"),
                "title": (
                    f"ACLED 30-day summary · "
                    f"{acled_data.get('country') or acled_data.get('region') or '—'}"
                ),
                "events_30d": acled_data.get("events_30d", 0),
                "fatalities_30d": acled_data.get("fatalities_30d", 0),
                "events_90d": acled_data.get("events_90d"),
                "fatalities_90d": acled_data.get("fatalities_90d"),
                "trend": acled_data.get("trend"),
                "latest_month_label": acled_data.get("latest_month_label"),
                "active_conflicts": acled_data.get("active_conflicts", []),
                "url": acled_data.get("dataset_url"),
            })

        return {
            "reliefweb_reports": rw_reports,
            "reliefweb_plans": rw_plans,
            "acled": acled_data,
            "sources": sources,
        }

    def _legacy_prompt(
        self,
        country: str,
        actions: list[dict],
        evidence: dict,
        event_summary: str,
    ) -> str:
        evidence_compact = {
            "reliefweb_reports": evidence.get("reliefweb_reports", {}).get("reports", [])[:10],
            "reliefweb_response_plans": evidence.get("reliefweb_plans", {}).get("reports", [])[:5],
            "acled_summary": evidence.get("acled", {}),
        }
        return f"""Event: {event_summary}
Country: {country}

Recommended actions (from CascadeAI Dispatcher):
{json.dumps(actions, indent=2)}

Real-world evidence pulled from live humanitarian feeds:
{json.dumps(evidence_compact, indent=2)}

For EACH recommended action above, classify its real-world status as
in_progress / partial / gap based on the evidence. Then list the blind_spots
(actions classified as "gap") and write the coverage_summary.

Return ONLY the JSON object specified in the system prompt."""

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _flatten_actions(self, response_plans: list[dict]) -> list[dict]:
        flat: list[dict] = []
        for plan in response_plans:
            stakeholder = plan.get("stakeholder", "Unknown")
            priority = plan.get("priority", "")
            for action in plan.get("actions", []):
                if isinstance(action, str):
                    text = action
                else:
                    text = action.get("description", str(action))
                flat.append({
                    "stakeholder": stakeholder,
                    "priority": priority,
                    "action": text,
                })
        return flat

    def _parse_response(
        self, text: str, country: str, actions: list[dict],
    ) -> dict:
        text = (text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        # Some models prepend `json` on the first line.
        if text.lower().startswith("json"):
            text = text.split("\n", 1)[-1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "country": country,
                "verifications": [
                    {
                        "stakeholder": a["stakeholder"],
                        "action": a["action"],
                        "status": "gap",
                        "evidence": "Verifier response could not be parsed; defaulting to gap.",
                        "confidence": "low",
                    }
                    for a in actions
                ],
                "blind_spots": [a["action"] for a in actions],
                "coverage_summary": (
                    f"Verifier response could not be parsed for {country}. "
                    f"Treating all {len(actions)} recommended actions as unverified gaps."
                ),
            }


# ---------------------------------------------------------------------------
# Helpers for tool result summarisation + source extraction
# ---------------------------------------------------------------------------


def _summarise_tool_result(result: dict) -> str:
    if not isinstance(result, dict):
        return str(result)[:120]
    if "reports" in result:
        n = len(result.get("reports") or [])
        return f"{n} reports · source={result.get('source','?')}"
    if "events_30d" in result:
        return (
            f"{result.get('events_30d', 0)} events · "
            f"{result.get('fatalities_30d', 0)} fatalities · "
            f"conflicts={len(result.get('active_conflicts') or [])}"
        )
    return json.dumps(result)[:160]


def _extract_sources(tool_name: str, args: dict, result: dict) -> list[dict]:
    sources: list[dict] = []
    if not isinstance(result, dict):
        return sources

    transport = result.get("source", "")  # "ReliefWeb RSS" / "ReliefWeb API v2" / "unavailable"

    if tool_name in ("search_reliefweb_reports", "lookup_active_response_plans"):
        kind = "reliefweb_plan" if tool_name == "lookup_active_response_plans" else "reliefweb_report"
        for r in result.get("reports") or []:
            sources.append({
                "type": kind,
                "transport": transport,
                "title": r.get("title", ""),
                "date": r.get("date", ""),
                "org": r.get("source", ""),
                "url": r.get("url", ""),
            })
    elif tool_name == "search_acled_recent":
        scope_label = (
            result.get("country")
            or args.get("country")
            or result.get("region")
            or args.get("region", "—")
        )
        sources.append({
            "type": "acled_summary",
            "transport": result.get("source", "ACLED"),
            "title": f"ACLED 30-day summary · {scope_label}",
            "events_30d": result.get("events_30d", 0),
            "fatalities_30d": result.get("fatalities_30d", 0),
            "events_90d": result.get("events_90d"),
            "fatalities_90d": result.get("fatalities_90d"),
            "trend": result.get("trend"),
            "latest_month_label": result.get("latest_month_label"),
            "active_conflicts": result.get("active_conflicts", []),
            "url": result.get("dataset_url"),
        })
    return sources


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for s in sources:
        key = (s.get("type", ""), s.get("url") or s.get("title", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out

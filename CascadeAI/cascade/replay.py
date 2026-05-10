"""Crisis Replay Engine (D1) — backtesting framework for validating
CascadeAI predictions against historical crises.

Pre-loaded scenarios: Ukraine 2022, Sudan 2023-2026, Hormuz/Fertilizer 2026.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cascade.graph import CascadeGraph
from cascade.traversal import run_cascade, run_compound_cascade, CascadeImpact, CountryProfile


BACKTEST_DIR = Path(__file__).resolve().parent.parent / "data" / "backtest"


@dataclass
class BacktestComparison:
    indicator: str
    predicted: str
    actual: str
    accuracy: str
    node: str = ""


@dataclass
class BacktestResult:
    crisis_name: str
    trigger_date: str
    trigger_event: str
    country: str
    cascade_impacts: list[CascadeImpact] = field(default_factory=list)
    comparisons: list[BacktestComparison] = field(default_factory=list)
    mape: Optional[float] = None


def load_backtest_scenario(name: str) -> dict:
    """Load a backtest scenario JSON file."""
    path = BACKTEST_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No backtest scenario: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_backtest(
    scenario_name: str,
    graph: Optional[CascadeGraph] = None,
) -> list[BacktestResult]:
    """Run a full backtest for a scenario across all its target countries."""
    if graph is None:
        graph = CascadeGraph.from_json()

    scenario = load_backtest_scenario(scenario_name)
    trigger = scenario["trigger"]
    results = []

    for country_data in scenario["countries"]:
        country_name = country_data["country"]
        profile = CountryProfile(
            country=country_name,
            vulnerability=country_data.get("pre_crisis_vulnerability", {}),
        )

        if len(trigger.get("nodes", [])) > 1:
            events = [
                {"node": n, "severity": trigger["severity"]}
                for n in trigger["nodes"]
            ]
            cascade_impacts = run_compound_cascade(graph, events, country=profile)
        else:
            node = trigger.get("node", trigger.get("nodes", ["war"])[0])
            cascade_impacts = run_cascade(
                graph, node, trigger["severity"], country=profile
            )

        comparisons = []
        for actual in country_data.get("actuals", []):
            predicted_impact = next(
                (i for i in cascade_impacts if i.node == actual["node"]),
                None,
            )

            predicted_str = (
                f"severity={predicted_impact.severity:.2f}, delay={predicted_impact.delay_days}d"
                if predicted_impact
                else "not reached"
            )

            comparisons.append(BacktestComparison(
                indicator=actual["indicator"],
                predicted=actual.get("predicted_range", predicted_str),
                actual=actual["actual_value"],
                accuracy=actual.get("accuracy", "pending"),
                node=actual["node"],
            ))

        results.append(BacktestResult(
            crisis_name=scenario["name"],
            trigger_date=trigger["date"],
            trigger_event=trigger["description"],
            country=country_name,
            cascade_impacts=cascade_impacts,
            comparisons=comparisons,
        ))

    return results


def available_scenarios() -> list[str]:
    """List available backtest scenario names."""
    return [p.stem for p in sorted(BACKTEST_DIR.glob("*.json"))]

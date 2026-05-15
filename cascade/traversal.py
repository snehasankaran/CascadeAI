"""BFS cascade engine — deterministic, no LLM dependency.

Two entry points:
  run_cascade()          — single seed node
  run_compound_cascade() — multiple seed nodes (D2: multi-crisis)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from cascade.graph import CascadeGraph


@dataclass
class CascadeImpact:
    """One affected node in the cascade."""

    node: str
    severity: float
    delay_days: int
    path: list[str]
    is_seed: bool = False


@dataclass
class CountryProfile:
    """Per-country vulnerability multipliers (loaded from JSON)."""

    country: str
    vulnerability: dict[str, float] = field(default_factory=dict)

    def multiplier(self, node_id: str) -> float:
        return self.vulnerability.get(node_id, 1.0)


def run_cascade(
    graph: CascadeGraph,
    start_node: str,
    severity: float,
    country: Optional[CountryProfile] = None,
    threshold: Optional[float] = None,
) -> list[CascadeImpact]:
    """BFS cascade from a single seed node.

    Returns a list of CascadeImpact sorted by delay_days (earliest first).
    """
    if threshold is None:
        threshold = graph.threshold

    queue: deque[tuple[str, float, int, list[str]]] = deque()
    queue.append((start_node, severity, 0, [start_node]))
    visited: dict[str, CascadeImpact] = {}
    impacts: list[CascadeImpact] = []

    while queue:
        current, sev, delay, path = queue.popleft()

        if current in visited:
            continue

        vuln = country.multiplier(current) if country else 1.0
        adjusted = sev * vuln

        impact = CascadeImpact(
            node=current,
            severity=round(adjusted, 4),
            delay_days=delay,
            path=list(path),
            is_seed=(current == start_node),
        )
        visited[current] = impact
        impacts.append(impact)

        for edge in graph.edges_from(current):
            if edge.dst in visited:
                continue
            propagated = adjusted * edge.weight
            if propagated >= threshold:
                new_delay = delay + edge.delay_mid
                new_path = path + [edge.dst]
                queue.append((edge.dst, propagated, new_delay, new_path))

    return sorted(impacts, key=lambda i: i.delay_days)


def run_compound_cascade(
    graph: CascadeGraph,
    events: list[dict],
    country: Optional[CountryProfile] = None,
    threshold: Optional[float] = None,
) -> list[CascadeImpact]:
    """Multi-seed BFS for compound crises (D2).

    *events* is a list of ``{"node": str, "severity": float}``.

    When two cascades hit the same node, severities are combined using
    probabilistic union: ``a + b - a*b`` (avoids double-counting, caps at 1.0).
    """
    if threshold is None:
        threshold = graph.threshold

    combined: dict[str, CascadeImpact] = {}

    for event in events:
        single = run_cascade(
            graph,
            start_node=event["node"],
            severity=event["severity"],
            country=country,
            threshold=threshold,
        )
        for impact in single:
            if impact.node in combined:
                existing = combined[impact.node]
                a, b = existing.severity, impact.severity
                merged_sev = round(a + b - a * b, 4)
                shorter_delay = min(existing.delay_days, impact.delay_days)
                shorter_path = (
                    existing.path
                    if existing.delay_days <= impact.delay_days
                    else impact.path
                )
                combined[impact.node] = CascadeImpact(
                    node=impact.node,
                    severity=merged_sev,
                    delay_days=shorter_delay,
                    path=shorter_path,
                    is_seed=existing.is_seed or impact.is_seed,
                )
            else:
                combined[impact.node] = impact

    return sorted(combined.values(), key=lambda i: i.delay_days)

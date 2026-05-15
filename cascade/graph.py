"""CascadeAI dependency graph — loads coefficients.json into an adjacency-list
structure for BFS traversal."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    description: str
    indicators: list[str]


@dataclass(frozen=True)
class Edge:
    id: int
    src: str
    dst: str
    weight: float
    delay_min: int
    delay_max: int
    delay_mid: int
    mechanism: str
    source: str


@dataclass
class CascadeGraph:
    """Directed weighted graph of humanitarian crisis dependencies."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    adjacency: dict[str, list[Edge]] = field(default_factory=dict)
    threshold: float = 0.05

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def from_json(cls, path: Optional[str | Path] = None) -> "CascadeGraph":
        """Load graph from coefficients.json.

        If *path* is ``None`` the bundled ``cascade/data/coefficients.json``
        is used.
        """
        if path is None:
            path = Path(__file__).parent / "data" / "coefficients.json"
        else:
            path = Path(path)

        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        graph = cls(threshold=raw.get("threshold", 0.05))

        for n in raw["nodes"]:
            node = Node(
                id=n["id"],
                label=n["label"],
                description=n["description"],
                indicators=n.get("indicators", []),
            )
            graph.nodes[node.id] = node
            graph.adjacency[node.id] = []

        for e in raw["edges"]:
            edge = Edge(
                id=e["id"],
                src=e["from"],
                dst=e["to"],
                weight=e["weight"],
                delay_min=e["delay_min"],
                delay_max=e["delay_max"],
                delay_mid=e["delay_mid"],
                mechanism=e["mechanism"],
                source=e["source"],
            )
            graph.edges.append(edge)
            graph.adjacency[edge.src].append(edge)

        return graph

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def edges_from(self, node_id: str) -> list[Edge]:
        return self.adjacency.get(node_id, [])

    def node_ids(self) -> list[str]:
        return list(self.nodes.keys())

    def __repr__(self) -> str:
        return f"CascadeGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"

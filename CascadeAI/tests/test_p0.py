"""P0 smoke test — verify graph loads, BFS runs, and country profiles work."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cascade.graph import CascadeGraph
from cascade.traversal import run_cascade, run_compound_cascade, CountryProfile
from data.profiles import load_profile, load_all_profiles, available_countries


def test_graph_load():
    g = CascadeGraph.from_json()
    assert len(g.nodes) == 11, f"Expected 11 nodes, got {len(g.nodes)}"
    assert len(g.edges) == 18, f"Expected 18 edges, got {len(g.edges)}"
    assert "war" in g.nodes
    assert "food" in g.nodes
    assert len(g.edges_from("war")) == 4
    print(f"[PASS] Graph loaded: {g}")


def test_single_cascade():
    g = CascadeGraph.from_json()
    impacts = run_cascade(g, "war", severity=0.9)
    assert len(impacts) > 1, "Cascade should hit multiple nodes"
    assert impacts[0].node == "war", "First impact should be the seed node"
    assert impacts[0].is_seed is True

    print(f"[PASS] Single cascade from WAR (severity=0.9):")
    for imp in impacts:
        seed = " [SEED]" if imp.is_seed else ""
        print(f"  {imp.node:15s} severity={imp.severity:.4f}  delay={imp.delay_days:3d}d  path={' -> '.join(imp.path)}{seed}")


def test_cascade_with_country():
    g = CascadeGraph.from_json()
    kenya = load_profile("kenya")
    impacts = run_cascade(g, "war", severity=0.9, country=kenya)
    assert len(impacts) > 1

    food_impact = next((i for i in impacts if i.node == "food"), None)
    assert food_impact is not None, "War cascade should reach food node"

    print(f"\n[PASS] Cascade with Kenya profile (WAR severity=0.9):")
    for imp in impacts:
        print(f"  {imp.node:15s} severity={imp.severity:.4f}  delay={imp.delay_days:3d}d")


def test_compound_cascade():
    g = CascadeGraph.from_json()
    kenya = load_profile("kenya")
    events = [
        {"node": "war", "severity": 0.9},
        {"node": "energy", "severity": 0.7},
    ]
    impacts = run_compound_cascade(g, events, country=kenya)
    assert len(impacts) > 2

    print(f"\n[PASS] Compound cascade (WAR+ENERGY → Kenya):")
    for imp in impacts:
        seed = " [SEED]" if imp.is_seed else ""
        print(f"  {imp.node:15s} severity={imp.severity:.4f}  delay={imp.delay_days:3d}d{seed}")


def test_country_profiles():
    countries = available_countries()
    assert len(countries) == 8, f"Expected 8 countries, got {len(countries)}"
    profiles = load_all_profiles()
    assert len(profiles) == 8

    print(f"\n[PASS] Country profiles loaded: {', '.join(countries)}")
    for name, profile in profiles.items():
        food_v = profile.multiplier("food")
        print(f"  {name:12s} food_vulnerability={food_v:.2f}")


if __name__ == "__main__":
    test_graph_load()
    test_single_cascade()
    test_cascade_with_country()
    test_compound_cascade()
    test_country_profiles()
    print("\n✓ ALL P0 TESTS PASSED")

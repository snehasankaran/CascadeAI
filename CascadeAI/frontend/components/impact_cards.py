"""Impact Cards component — per-country stat cards showing cascade severity,
key affected nodes, and timelines."""

from __future__ import annotations

import streamlit as st

from cascade.graph import CascadeGraph
from cascade.traversal import CascadeImpact
from data.profiles import get_profile_raw


def render_impact_cards(
    all_impacts: dict[str, list[CascadeImpact]],
    graph: CascadeGraph,
):
    """Render impact cards in a responsive grid."""
    countries = list(all_impacts.keys())

    cols_per_row = min(4, len(countries))
    for i in range(0, len(countries), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(countries):
                break

            country_name = countries[idx]
            impacts = all_impacts[country_name]
            _render_single_card(col, country_name, impacts, graph)


def _render_single_card(
    col,
    country_name: str,
    impacts: list[CascadeImpact],
    graph: CascadeGraph,
):
    """Render a single country impact card."""
    try:
        raw = get_profile_raw(country_name.lower())
        display_name = raw.get("country", country_name)
        vulnerability = raw.get("key_vulnerability", "")
        population = raw.get("population", 0)
    except FileNotFoundError:
        display_name = country_name
        vulnerability = ""
        population = 0

    max_sev = max(i.severity for i in impacts) if impacts else 0
    food_impact = next((i for i in impacts if i.node == "food"), None)
    health_impact = next((i for i in impacts if i.node == "health"), None)
    disp_impact = next((i for i in impacts if i.node == "displacement"), None)

    severity_label = _severity_label(max_sev)
    severity_emoji = _severity_emoji(max_sev)

    with col:
        st.markdown(f"### {severity_emoji} {display_name}")
        st.caption(vulnerability)

        m1, m2 = st.columns(2)
        m1.metric("Max Severity", f"{max_sev:.2f}", severity_label)
        m2.metric("Nodes Hit", f"{len(impacts)}/11")

        if food_impact:
            st.markdown(f"**Food:** severity {food_impact.severity:.2f} in {food_impact.delay_days} days")
        if health_impact:
            st.markdown(f"**Health:** severity {health_impact.severity:.2f} in {health_impact.delay_days} days")
        if disp_impact:
            st.markdown(f"**Displacement:** severity {disp_impact.severity:.2f} in {disp_impact.delay_days} days")

        with st.expander("Full cascade path"):
            for imp in impacts:
                bar_width = int(imp.severity * 100)
                label = graph.get_node(imp.node).label
                st.markdown(
                    f"`{label:20s}` "
                    f"{'█' * max(1, bar_width // 5)} "
                    f"{imp.severity:.3f} ({imp.delay_days}d)"
                )


def _severity_label(sev: float) -> str:
    if sev >= 0.8:
        return "CRITICAL"
    elif sev >= 0.6:
        return "SEVERE"
    elif sev >= 0.4:
        return "MODERATE"
    elif sev >= 0.2:
        return "MILD"
    return "LOW"


def _severity_emoji(sev: float) -> str:
    if sev >= 0.8:
        return "🔴"
    elif sev >= 0.6:
        return "🟠"
    elif sev >= 0.4:
        return "🟡"
    return "🟢"

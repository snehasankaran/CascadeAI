"""Cascade Map component — Folium map showing affected countries with
severity-coded markers and cascade path visualization."""

from __future__ import annotations

from typing import Optional

import streamlit as st
from streamlit_folium import st_folium
import folium

from cascade.graph import CascadeGraph
from cascade.traversal import CascadeImpact
from data.profiles import get_profile_raw

SEVERITY_COLORS = [
    (0.0, "green"),
    (0.2, "lightgreen"),
    (0.4, "orange"),
    (0.6, "red"),
    (0.8, "darkred"),
]


def _severity_color(sev: float) -> str:
    color = "gray"
    for threshold, c in SEVERITY_COLORS:
        if sev >= threshold:
            color = c
    return color


def _severity_radius(sev: float) -> int:
    return max(8, int(sev * 30))


def render_cascade_map(
    all_impacts: dict[str, list[CascadeImpact]],
    graph: CascadeGraph,
):
    """Render a Folium map with cascade impact markers per country."""
    m = folium.Map(location=[10, 40], zoom_start=3, tiles="CartoDB dark_matter")

    for country_name, impacts in all_impacts.items():
        try:
            raw = get_profile_raw(country_name.lower())
        except FileNotFoundError:
            continue

        coords = raw.get("coordinates", {})
        lat, lon = coords.get("lat", 0), coords.get("lon", 0)

        max_sev = max(i.severity for i in impacts) if impacts else 0
        food_impact = next((i for i in impacts if i.node == "food"), None)
        health_impact = next((i for i in impacts if i.node == "health"), None)

        popup_lines = [f"<b>{raw.get('country', country_name)}</b><br>"]
        popup_lines.append(f"Max severity: {max_sev:.2f}<br>")
        if food_impact:
            popup_lines.append(f"Food: sev={food_impact.severity:.2f}, delay={food_impact.delay_days}d<br>")
        if health_impact:
            popup_lines.append(f"Health: sev={health_impact.severity:.2f}, delay={health_impact.delay_days}d<br>")
        popup_lines.append(f"Nodes hit: {len(impacts)}/11")

        folium.CircleMarker(
            location=[lat, lon],
            radius=_severity_radius(max_sev),
            color=_severity_color(max_sev),
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup("".join(popup_lines), max_width=250),
            tooltip=f"{raw.get('country', country_name)}: {max_sev:.2f}",
        ).add_to(m)

    st_folium(m, width=None, height=500, use_container_width=True)

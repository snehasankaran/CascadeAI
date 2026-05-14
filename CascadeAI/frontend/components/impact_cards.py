"""Impact Cards component — per-country stat cards showing cascade severity,
key affected nodes, and timelines."""

from __future__ import annotations

import streamlit as st

from cascade.graph import CascadeGraph
from cascade.traversal import CascadeImpact
from data.profiles import get_profile_raw

_SEV_PALETTE = {
    "CRITICAL": ("#7f1d1d", "#ef4444", "🔴"),
    "SEVERE":   ("#78350f", "#f97316", "🟠"),
    "MODERATE": ("#713f12", "#eab308", "🟡"),
    "MILD":     ("#14532d", "#22c55e", "🟢"),
    "LOW":      ("#1e3a5f", "#60a5fa", "🔵"),
}

_NODE_ICONS = {
    "food": "🌾",
    "health": "🏥",
    "displacement": "🏕️",
    "energy": "⚡",
    "fertilizer": "🧪",
    "water": "💧",
    "conflict": "⚔️",
    "economy": "💹",
    "transport": "🚢",
    "governance": "🏛️",
    "climate": "🌡️",
}


def render_impact_cards(
    all_impacts: dict[str, list[CascadeImpact]],
    graph: CascadeGraph,
):
    """Render impact cards in a responsive grid."""
    countries = list(all_impacts.keys())
    cols_per_row = min(3, len(countries))
    for i in range(0, len(countries), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(countries):
                break
            _render_single_card(col, countries[idx], all_impacts[countries[idx]], graph)


def _render_single_card(
    col,
    country_name: str,
    impacts: list[CascadeImpact],
    graph: CascadeGraph,
):
    try:
        raw = get_profile_raw(country_name.lower())
        display_name = raw.get("country", country_name)
        vulnerability = raw.get("key_vulnerability", "")
    except FileNotFoundError:
        display_name = country_name
        vulnerability = ""

    max_sev = max(i.severity for i in impacts) if impacts else 0
    label = _severity_label(max_sev)
    bg, accent, emoji = _SEV_PALETTE[label]

    food_impact  = next((i for i in impacts if i.node == "food"), None)
    health_impact = next((i for i in impacts if i.node == "health"), None)
    disp_impact  = next((i for i in impacts if i.node == "displacement"), None)

    bar_pct = int(max_sev * 100)

    card_html = f"""
<div style="
    background: linear-gradient(145deg, {bg}55 0%, #0f172a 100%);
    border: 1px solid {accent}55;
    border-left: 4px solid {accent};
    border-radius: 12px;
    padding: 18px 20px 14px;
    margin-bottom: 8px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
    <span style="font-size:1.15rem; font-weight:700; color:#e2e8f0;">{emoji} {display_name}</span>
    <span style="
        background:{accent}22; color:{accent};
        font-size:0.68rem; font-weight:700; letter-spacing:0.08em;
        padding:2px 8px; border-radius:20px; border:1px solid {accent}55;
    ">{label}</span>
  </div>
  <div style="font-size:0.75rem; color:#64748b; margin-bottom:12px;">{vulnerability}</div>

  <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
    <div>
      <div style="font-size:0.7rem; color:#64748b; margin-bottom:2px;">MAX SEVERITY</div>
      <div style="font-size:1.6rem; font-weight:800; color:{accent}; line-height:1;">{max_sev:.2f}</div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:0.7rem; color:#64748b; margin-bottom:2px;">NODES HIT</div>
      <div style="font-size:1.6rem; font-weight:800; color:#94a3b8; line-height:1;">{len(impacts)}<span style="font-size:0.9rem; color:#475569;">/11</span></div>
    </div>
  </div>

  <div style="background:#1e293b; border-radius:4px; height:6px; margin-bottom:14px;">
    <div style="background:{accent}; width:{bar_pct}%; height:6px; border-radius:4px;
                transition:width 0.4s ease;"></div>
  </div>

  {"" if not food_impact else f'<div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#cbd5e1; padding:4px 0; border-top:1px solid #1e293b;"><span>🌾 Food</span><span style="color:{accent};">{food_impact.severity:.2f} <span style="color:#475569;">in {food_impact.delay_days}d</span></span></div>'}
  {"" if not health_impact else f'<div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#cbd5e1; padding:4px 0; border-top:1px solid #1e293b;"><span>🏥 Health</span><span style="color:{accent};">{health_impact.severity:.2f} <span style="color:#475569;">in {health_impact.delay_days}d</span></span></div>'}
  {"" if not disp_impact else f'<div style="display:flex; justify-content:space-between; font-size:0.78rem; color:#cbd5e1; padding:4px 0; border-top:1px solid #1e293b;"><span>🏕️ Displacement</span><span style="color:{accent};">{disp_impact.severity:.2f} <span style="color:#475569;">in {disp_impact.delay_days}d</span></span></div>'}
</div>
"""
    with col:
        st.markdown(card_html, unsafe_allow_html=True)
        with st.expander("Full cascade path"):
            for imp in sorted(impacts, key=lambda x: -x.severity):
                node_label = graph.get_node(imp.node).label
                icon = _NODE_ICONS.get(imp.node, "•")
                bar = int(imp.severity * 20)
                fill_color = _SEV_PALETTE[_severity_label(imp.severity)][1]
                st.markdown(
                    f"<div style='display:flex; justify-content:space-between; align-items:center; "
                    f"font-size:0.78rem; color:#cbd5e1; padding:3px 0;'>"
                    f"<span>{icon} {node_label}</span>"
                    f"<span style='color:{fill_color}; font-weight:600;'>{imp.severity:.3f}"
                    f"<span style='color:#475569; font-weight:400;'> · {imp.delay_days}d</span></span>"
                    f"</div>",
                    unsafe_allow_html=True,
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

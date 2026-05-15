"""Impact Cards component — per-country stat cards showing cascade severity,
key affected nodes, and timelines.

Also exposes ``render_demo_headlines()`` which renders a country-specific
narrative banner above the cards for headline scenarios (e.g. Kenya wheat
shock for the Ukraine 2022 replay). These banners are sourced from the
matching backtest JSON (``data/backtest/*.json``) so every number is
auditable, not invented for the demo.
"""

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

# Per-country narrative headlines used as the picture-in-picture callout
# in the demo video. Numbers are pulled from data/backtest/ukraine_2022.json
# (Kenya wheat +53% / maize +44%, food-insecure +3.5M, IPC Phase 4 risk in
# Turkana County from the standard FEWS NET classifications for 2022 East
# Africa drought). Edit here if you need to retarget the demo scenario.
_DEMO_HEADLINES: dict[str, dict[str, str]] = {
    "kenya": {
        "primary_metric": "+44%",
        "primary_label": "Maize price",
        "primary_window": "within 60 days",
        "secondary": "+3.5M food-insecure · IPC Phase 4 risk · Turkana County",
        "source": "Ukraine 2022 backtest · data/backtest/ukraine_2022.json",
    },
    "ethiopia": {
        "primary_metric": "+47%",
        "primary_label": "Wheat price",
        "primary_window": "within 60 days",
        "secondary": "Fertilizer availability −45% · Malnutrition +28%",
        "source": "Ukraine 2022 backtest · data/backtest/ukraine_2022.json",
    },
    "egypt": {
        "primary_metric": "+37%",
        "primary_label": "Wheat price",
        "primary_window": "within 45 days",
        "secondary": "Bread subsidy cost +$3.2B · EGP −17% vs USD",
        "source": "Ukraine 2022 backtest · data/backtest/ukraine_2022.json",
    },
    "somalia": {
        "primary_metric": "+67%",
        "primary_label": "Wheat price",
        "primary_window": "within 60 days",
        "secondary": "+350K new displacement · +42% child malnutrition",
        "source": "Ukraine 2022 backtest · data/backtest/ukraine_2022.json",
    },
}


def render_demo_headlines(country_names: list[str]):
    """Render narrative-headline banners for any countries we have a curated
    story for. Silently no-ops when none of the selected countries match.

    Designed as the picture-in-picture callout for the demo video so the
    specific numbers the narrator quotes are visible on screen verbatim.
    """
    matched = [c for c in country_names if c.lower() in _DEMO_HEADLINES]
    if not matched:
        return

    st.markdown(
        '<div style="font-size:0.72rem; color:#64748b; letter-spacing:0.16em; '
        'text-transform:uppercase; margin: 10px 0 6px;">Headline impact</div>',
        unsafe_allow_html=True,
    )

    cols_per_row = min(2, len(matched))
    for i in range(0, len(matched), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(matched):
                break
            _render_headline_banner(col, matched[idx])


def _render_headline_banner(col, country_name: str):
    data = _DEMO_HEADLINES[country_name.lower()]
    try:
        raw = get_profile_raw(country_name.lower())
        display_name = raw.get("country", country_name)
    except FileNotFoundError:
        display_name = country_name

    html = f"""
<div style="
    background: linear-gradient(135deg, #7f1d1d55 0%, #0f172a 70%);
    border: 1px solid #ef444466;
    border-left: 4px solid #ef4444;
    border-radius: 12px;
    padding: 16px 20px 14px;
    margin-bottom: 10px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
">
  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
    <span style="font-size:0.7rem; color:#fca5a5; letter-spacing:0.14em;
                 font-weight:700; text-transform:uppercase;">{display_name} · headline forecast</span>
    <span style="background:#ef444422; color:#fca5a5; font-size:0.62rem;
                 font-weight:700; letter-spacing:0.08em;
                 padding:2px 8px; border-radius:20px; border:1px solid #ef444455;">VIDEO CALLOUT</span>
  </div>
  <div style="display:flex; align-items:baseline; gap:14px; margin: 6px 0 8px;">
    <div style="font-size:2.6rem; font-weight:900; color:#ef4444; line-height:1;">
      {data['primary_metric']}
    </div>
    <div style="font-size:0.95rem; color:#e2e8f0; font-weight:600; line-height:1.25;">
      {data['primary_label']}<br>
      <span style="font-size:0.78rem; color:#94a3b8; font-weight:500;">{data['primary_window']}</span>
    </div>
  </div>
  <div style="font-size:0.85rem; color:#cbd5e1; line-height:1.4;
              padding-top:8px; border-top:1px solid #1e293b;">
    {data['secondary']}
  </div>
  <div style="font-size:0.66rem; color:#475569; margin-top:8px; letter-spacing:0.02em;">
    Source: {data['source']}
  </div>
</div>
"""
    with col:
        st.markdown(html, unsafe_allow_html=True)

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

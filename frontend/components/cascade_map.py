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

# Severity configurations with colors and labels
SEVERITY_CONFIG = {
    "CRITICAL": {"threshold": 0.8, "color": "#ef4444", "fill": "#7f1d1d", "label": "Critical"},
    "SEVERE": {"threshold": 0.6, "color": "#f97316", "fill": "#9a3412", "label": "Severe"},
    "MODERATE": {"threshold": 0.4, "color": "#eab308", "fill": "#854d0e", "label": "Moderate"},
    "MILD": {"threshold": 0.2, "color": "#22c55e", "fill": "#166534", "label": "Mild"},
    "LOW": {"threshold": 0.0, "color": "#3b82f6", "fill": "#1e40af", "label": "Low"},
}

def _get_severity_level(sev: float) -> dict:
    """Get severity level configuration based on severity value."""
    for level, config in sorted(SEVERITY_CONFIG.items(), key=lambda x: x[1]["threshold"], reverse=True):
        if sev >= config["threshold"]:
            return {**config, "name": level}
    return {**SEVERITY_CONFIG["LOW"], "name": "LOW"}

def _severity_color(sev: float) -> str:
    return _get_severity_level(sev)["color"]

def _severity_radius(sev: float) -> int:
    return max(12, int(sev * 35))

def _severity_pulse_animation(sev: float) -> str:
    """Return CSS animation class for high severity markers."""
    if sev >= 0.8:
        return "animation: pulse 1.5s ease-in-out infinite;"
    elif sev >= 0.6:
        return "animation: pulse 2s ease-in-out infinite;"
    return ""


def render_cascade_map(
    all_impacts: dict[str, list[CascadeImpact]],
    graph: CascadeGraph,
):
    """Render a Folium map with cascade impact markers per country."""
    m = folium.Map(
        location=[20, 0],
        zoom_start=2,
        tiles="CartoDB dark_matter",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    )
    
    # Node icons for popup
    node_icons = {
        "food": "🌾", "health": "🏥", "displacement": "🏕️", "energy": "⚡",
        "fertilizer": "🧪", "water": "💧", "conflict": "⚔️", "economy": "💹",
        "transport": "🚢", "governance": "🏛️", "climate": "🌡️",
    }

    for country_name, impacts in all_impacts.items():
        try:
            raw = get_profile_raw(country_name.lower())
        except FileNotFoundError:
            continue

        coords = raw.get("coordinates", {})
        lat, lon = coords.get("lat", 0), coords.get("lon", 0)

        max_sev = max(i.severity for i in impacts) if impacts else 0
        severity_info = _get_severity_level(max_sev)
        sev_color = severity_info['color']
        sev_fill = severity_info['fill']
        sev_label = severity_info['label'].upper()
        country_display = raw.get('country', country_name)

        top_impacts = sorted(impacts, key=lambda x: -x.severity)[:3]

        # Build the Top Impacts rows separately to avoid nested triple-quoted
        # f-strings (Python 3.10 parser limitation).
        top_rows = []
        for imp in top_impacts:
            row_color = _get_severity_level(imp.severity)['color']
            node_label = graph.get_node(imp.node).label
            icon = node_icons.get(imp.node, '•')
            top_rows.append(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:4px 0;border-bottom:1px solid #1e293b;">'
                f'<span style="color:#94a3b8;font-size:0.8rem;">{icon} {node_label}</span>'
                f'<span style="color:{row_color};font-weight:600;font-size:0.8rem;">'
                f'{imp.severity:.2f}'
                f'<span style="color:#475569;font-weight:400;font-size:0.7rem;"> · {imp.delay_days}d</span>'
                f'</span></div>'
            )
        top_rows_html = ''.join(top_rows)

        vuln_text = raw.get('key_vulnerability', '')
        vuln_html = (
            f'<div style="margin-top:10px;font-size:0.7rem;color:#475569;font-style:italic;">{vuln_text}</div>'
            if vuln_text else ''
        )

        popup_content = f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-width:220px;padding:4px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;padding-bottom:10px;border-bottom:2px solid {sev_color};">
                <span style="font-size:1.3rem;font-weight:700;color:#e2e8f0;">{country_display}</span>
                <span style="background:{sev_color}22;color:{sev_color};font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:12px;border:1px solid {sev_color}55;">{sev_label}</span>
            </div>
            <div style="margin-bottom:12px;">
                <div style="font-size:0.75rem;color:#64748b;margin-bottom:4px;">Max Severity</div>
                <div style="display:flex;align-items:center;gap:8px;">
                    <div style="width:80px;height:8px;background:#1e293b;border-radius:4px;overflow:hidden;">
                        <div style="width:{int(max_sev*100)}%;height:100%;background:linear-gradient(90deg,{sev_color},{sev_fill});border-radius:4px;"></div>
                    </div>
                    <span style="font-size:1.1rem;font-weight:700;color:{sev_color};">{max_sev:.2f}</span>
                </div>
            </div>
            <div style="font-size:0.75rem;color:#64748b;margin-bottom:8px;">
                Nodes Affected: <span style="color:#94a3b8;font-weight:600;">{len(impacts)}/{len(graph.nodes)}</span>
            </div>
            <div style="background:#0f172a;border-radius:8px;padding:10px;margin-top:10px;">
                <div style="font-size:0.7rem;color:#64748b;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.05em;">Top Impacts</div>
                {top_rows_html}
            </div>
            {vuln_html}
        </div>
        """
        
        # Create circle marker with enhanced styling
        folium.CircleMarker(
            location=[lat, lon],
            radius=_severity_radius(max_sev),
            color=severity_info["color"],
            fill=True,
            fill_color=severity_info["fill"],
            fill_opacity=0.75,
            popup=folium.Popup(popup_content, max_width=300, min_width=250),
            tooltip=folium.Tooltip(
                f"<b>{raw.get('country', country_name)}</b><br>Severity: {max_sev:.2f}",
                style="""
                    background-color: #0f172a;
                    border: 1px solid #312e81;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 0.85rem;
                    color: #e2e8f0;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                """,
                sticky=False,
            ),
        ).add_to(m)
    
    # Enhanced legend
    legend_html = """
    <div style="
        position: fixed;
        bottom: 24px;
        left: 24px;
        z-index: 9999;
        background: linear-gradient(145deg, #0f172a, #1e293b);
        color: #e2e8f0;
        padding: 16px 18px;
        border-radius: 12px;
        border: 1px solid #312e81;
        font-size: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        min-width: 160px;
    ">
        <div style="font-weight: 700; margin-bottom: 12px; font-size: 0.85rem; color: #a78bfa; text-transform: uppercase; letter-spacing: 0.05em;">
            Impact Severity
        </div>
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span style="display:inline-block;width:12px;height:12px;background:#ef4444;border-radius:50%;box-shadow:0 0 8px #ef4444;"></span>
            <span style="color: #ef4444; font-weight: 600;">≥ 0.80 Critical</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span style="display:inline-block;width:12px;height:12px;background:#f97316;border-radius:50%;box-shadow:0 0 8px #f97316;"></span>
            <span style="color: #f97316; font-weight: 600;">0.60–0.79 Severe</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span style="display:inline-block;width:12px;height:12px;background:#eab308;border-radius:50%;box-shadow:0 0 8px #eab308;"></span>
            <span style="color: #eab308; font-weight: 600;">0.40–0.59 Moderate</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span style="display:inline-block;width:12px;height:12px;background:#22c55e;border-radius:50%;box-shadow:0 0 8px #22c55e;"></span>
            <span style="color: #22c55e; font-weight: 600;">0.20–0.39 Mild</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="display:inline-block;width:12px;height:12px;background:#3b82f6;border-radius:50%;box-shadow:0 0 8px #3b82f6;"></span>
            <span style="color: #60a5fa; font-weight: 600;">&lt; 0.20 Low</span>
        </div>
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Render map with custom styling
    st_folium(m, height=550, width="stretch", returned_objects=[])

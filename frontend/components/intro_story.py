"""Intro Story component — renders the '120-day gap' opening sequence
used as the hero scene of the demo video. Pure dashboard rendering: no
Canva overlays, no external video assets. Designed to be screen-recorded
as a continuous scroll-down sequence.

Five beats:
  1. Title card · "February 24, 2022 · Russia invades Ukraine"
  2. FAO wheat-price chart spike (Jan – Aug 2022, +53% peak May 2022)
  3. World map with cascade lines to Kenya, Ethiopia, Egypt, Somalia
  4. 120-day timeline bar
  5. The "120" reveal

Data is sourced from data/backtest/ukraine_2022.json and FAO Food Price
Index — every number on screen is auditable.
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go


# ---- Real data, sourced from FAO + Ukraine 2022 backtest JSON ---------------
# FAO wheat price index, indexed so Jan 2022 = 100 and May 2022 peak = 153
# (matches "Global wheat price +53% peak (May 2022 vs Jan 2022)" from
# data/backtest/ukraine_2022.json::global_actuals.global_wheat_price_peak)
_WHEAT_MONTHS = [
    "Jan 2022", "Feb 2022", "Mar 2022", "Apr 2022",
    "May 2022", "Jun 2022", "Jul 2022", "Aug 2022",
]
_WHEAT_INDEX = [100, 105, 138, 147, 153, 144, 128, 120]

# Country impact endpoints — wheat price peaks from ukraine_2022.json::countries[].actuals
_CASCADE_TARGETS = [
    {"name": "Egypt",    "lat": 30.0, "lon": 31.2, "label": "+37% wheat (Apr 2022)"},
    {"name": "Ethiopia", "lat": 9.0,  "lon": 38.7, "label": "+47% wheat (Jun 2022)"},
    {"name": "Kenya",    "lat": -1.3, "lon": 36.8, "label": "+53% wheat (May 2022)"},
    {"name": "Somalia",  "lat": 2.0,  "lon": 45.3, "label": "+67% wheat (Jun 2022)"},
]
# Black Sea origin (Odesa port approx.)
_ORIGIN = {"lat": 46.5, "lon": 30.7}


# =============================================================================
# Public entry point
# =============================================================================

def render_intro_story():
    """Render the full 120-day gap opening sequence plus the Mary persona
    + fragmentation problem (Scene 2 of the demo video)."""
    _inject_animations()

    # Scene 1 · The 120-day gap
    _render_title_card()
    _render_wheat_chart()
    _render_cascade_map()
    _render_timeline_bar()
    _render_120_reveal()
    _render_close_caption()

    # Scene 2 · Meet Mary + the fragmentation problem
    _render_scene_2_divider()
    _render_mary_persona_card()
    _render_decision_stakes()
    _render_fragmentation_grid()
    _render_built_for_mary()


# =============================================================================
# Section renderers
# =============================================================================

def _inject_animations():
    """Inject CSS keyframes used by every reveal animation."""
    st.markdown(
        """
<style>
@keyframes story-fade-up {
    0%   { opacity: 0; transform: translateY(14px); }
    100% { opacity: 1; transform: translateY(0); }
}
@keyframes story-pulse-red {
    0%, 100% { box-shadow: 0 0 22px rgba(239,68,68,0.45); }
    50%      { box-shadow: 0 0 38px rgba(239,68,68,0.85); }
}
@keyframes story-tick {
    0%, 100% { transform: scale(1); }
    50%      { transform: scale(1.04); }
}
.story-fade-1 { animation: story-fade-up 0.7s ease 0.0s both; }
.story-fade-2 { animation: story-fade-up 0.7s ease 0.2s both; }
.story-fade-3 { animation: story-fade-up 0.7s ease 0.4s both; }
.story-fade-4 { animation: story-fade-up 0.7s ease 0.6s both; }
</style>
        """,
        unsafe_allow_html=True,
    )


def _render_title_card():
    st.markdown(
        """
<div class="story-fade-1" style="
    text-align: center;
    padding: 48px 24px 32px;
    margin-top: 8px;
    border-radius: 16px;
    background: radial-gradient(circle at 50% 0%, rgba(139,92,246,0.10) 0%, transparent 70%);
">
  <div style="
      font-family: 'Times New Roman', Georgia, serif;
      font-size: 1.05rem;
      color: #94a3b8;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      margin-bottom: 14px;
  ">February 24, 2022</div>
  <div style="
      font-size: 3.2rem;
      font-weight: 800;
      line-height: 1.15;
      color: #e2e8f0;
      max-width: 820px;
      margin: 0 auto;
  ">Russia invades Ukraine.</div>
  <div style="
      font-size: 1.1rem;
      color: #64748b;
      margin-top: 18px;
      max-width: 640px;
      margin-left: auto;
      margin-right: auto;
  ">The warning signs of a global food catastrophe were visible within hours.<br>
  The world took 120 days to connect the dots.</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_wheat_chart():
    st.markdown(
        '<div class="story-fade-2" style="margin-top:36px;">'
        '<div style="font-size:0.78rem; color:#64748b; letter-spacing:0.14em; '
        'text-transform:uppercase; margin-bottom:6px;">Within weeks · global wheat market</div>'
        '<div style="font-size:1.6rem; font-weight:700; color:#e2e8f0;">'
        'Global wheat price spiked +53% in 90 days.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    fig = go.Figure()

    # Pre-invasion shading
    fig.add_vrect(
        x0=-0.5, x1=1.0,
        fillcolor="rgba(100, 116, 139, 0.08)",
        layer="below", line_width=0,
        annotation_text="Pre-invasion", annotation_position="top left",
        annotation_font_color="#64748b", annotation_font_size=11,
    )
    # Invasion marker
    fig.add_vline(
        x=1.0, line_width=2, line_dash="dash", line_color="#ef4444",
        annotation_text="Feb 24 — Invasion", annotation_position="top",
        annotation_font_color="#ef4444", annotation_font_size=12,
    )

    fig.add_trace(go.Scatter(
        x=_WHEAT_MONTHS, y=_WHEAT_INDEX,
        mode="lines+markers",
        line=dict(color="#a78bfa", width=4, shape="spline"),
        marker=dict(size=10, color="#a78bfa", line=dict(color="#0f172a", width=2)),
        fill="tozeroy", fillcolor="rgba(167, 139, 250, 0.10)",
        hovertemplate="<b>%{x}</b><br>Index: %{y}<extra></extra>",
        name="Wheat Index (Jan 2022 = 100)",
    ))

    # Peak callout
    fig.add_annotation(
        x="May 2022", y=153,
        text="<b>+53%</b><br>peak",
        showarrow=True, arrowhead=2, arrowcolor="#ef4444",
        arrowsize=1.2, ax=40, ay=-50,
        font=dict(color="#ef4444", size=14, family="Arial Black"),
        bgcolor="rgba(239, 68, 68, 0.12)",
        bordercolor="#ef4444", borderwidth=1, borderpad=6,
    )

    fig.update_layout(
        height=340,
        margin=dict(l=20, r=20, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.5)",
        showlegend=False,
        xaxis=dict(showgrid=False, color="#94a3b8", showline=True, linecolor="#334155"),
        yaxis=dict(
            title=dict(text="Price Index (Jan 2022 = 100)", font=dict(color="#94a3b8")),
            gridcolor="#1e293b", color="#94a3b8", range=[80, 170],
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        '<div style="text-align:right; font-size:0.72rem; color:#64748b; '
        'margin-top:-6px; margin-bottom:30px;">'
        'Source: FAO Food Price Index · CascadeAI backtest data/backtest/ukraine_2022.json'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_cascade_map():
    st.markdown(
        '<div class="story-fade-3" style="margin-top:24px;">'
        '<div style="font-size:0.78rem; color:#64748b; letter-spacing:0.14em; '
        'text-transform:uppercase; margin-bottom:6px;">Within months · cascade reach</div>'
        '<div style="font-size:1.6rem; font-weight:700; color:#e2e8f0;">'
        'The cascade reached Kenya, Ethiopia, Egypt, and Somalia.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    fig = go.Figure()

    for target in _CASCADE_TARGETS:
        fig.add_trace(go.Scattergeo(
            lon=[_ORIGIN["lon"], target["lon"]],
            lat=[_ORIGIN["lat"], target["lat"]],
            mode="lines",
            line=dict(width=2, color="#ef4444"),
            opacity=0.55,
            showlegend=False,
            hoverinfo="skip",
        ))

    fig.add_trace(go.Scattergeo(
        lon=[_ORIGIN["lon"]],
        lat=[_ORIGIN["lat"]],
        mode="markers+text",
        marker=dict(size=14, color="#f97316", symbol="x", line=dict(width=2, color="#0f172a")),
        text=["Black Sea"],
        textposition="top right",
        textfont=dict(color="#f97316", size=11, family="Arial Black"),
        showlegend=False,
        hoverinfo="skip",
    ))

    fig.add_trace(go.Scattergeo(
        lon=[t["lon"] for t in _CASCADE_TARGETS],
        lat=[t["lat"] for t in _CASCADE_TARGETS],
        mode="markers+text",
        marker=dict(
            size=22, color="#ef4444",
            line=dict(width=2, color="#0f172a"),
            opacity=0.9,
        ),
        text=[f"<b>{t['name']}</b><br>{t['label']}" for t in _CASCADE_TARGETS],
        textposition="middle right",
        textfont=dict(color="#fca5a5", size=11),
        showlegend=False,
        hovertemplate="<b>%{text}</b><extra></extra>",
    ))

    fig.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(
            scope="world",
            projection_type="natural earth",
            showland=True, landcolor="#1e293b",
            showcountries=True, countrycolor="#334155",
            showocean=True, oceancolor="#0f172a",
            showcoastlines=True, coastlinecolor="#475569",
            lonaxis=dict(range=[15, 55]),
            lataxis=dict(range=[-10, 50]),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        '<div style="text-align:right; font-size:0.72rem; color:#64748b; '
        'margin-top:-6px; margin-bottom:30px;">'
        'Source: World Bank Food Security Update Q3 2022 · CascadeAI Ukraine 2022 backtest'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_timeline_bar():
    st.markdown(
        '<div class="story-fade-4" style="margin-top:24px;">'
        '<div style="font-size:0.78rem; color:#64748b; letter-spacing:0.14em; '
        'text-transform:uppercase; margin-bottom:6px;">The response gap</div>'
        '<div style="font-size:1.6rem; font-weight:700; color:#e2e8f0;">'
        'Time for global humanitarian response to act.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    timeline_html = """
<div style="
    margin: 20px 0 8px;
    padding: 20px 24px;
    background: linear-gradient(90deg,
        rgba(15,23,42,0.6) 0%,
        rgba(127,29,29,0.25) 50%,
        rgba(15,23,42,0.6) 100%);
    border-radius: 12px;
    border: 1px solid #334155;
">
  <div style="display:flex; justify-content:space-between;
              color:#94a3b8; font-size:0.8rem; margin-bottom:10px;
              font-weight:600; letter-spacing:0.04em;">
    <span>Feb 24, 2022 · Trigger</span>
    <span>Jun 24, 2022 · Response</span>
  </div>
  <div style="position:relative; height:14px; background:#1e293b; border-radius:8px; overflow:hidden;">
    <div style="position:absolute; left:0; top:0;
                width:100%; height:100%;
                background: linear-gradient(90deg, #ef4444 0%, #f97316 50%, #eab308 100%);
                border-radius:8px;
                animation: story-fade-up 1.4s ease 0.2s both;"></div>
    <div style="position:absolute; left:-4px; top:-3px;
                width:20px; height:20px; border-radius:50%;
                background:#ef4444; border:3px solid #0f172a;
                box-shadow:0 0 14px rgba(239,68,68,0.7);"></div>
    <div style="position:absolute; right:-4px; top:-3px;
                width:20px; height:20px; border-radius:50%;
                background:#eab308; border:3px solid #0f172a;
                box-shadow:0 0 14px rgba(234,179,8,0.6);"></div>
  </div>
  <div style="text-align:center; margin-top:14px; color:#cbd5e1;
              font-size:0.9rem; font-weight:600;">
    47M+ more people food-insecure in this window.
  </div>
</div>
    """
    st.markdown(timeline_html, unsafe_allow_html=True)


def _render_120_reveal():
    st.markdown(
        """
<div style="
    margin: 36px auto 18px;
    padding: 56px 24px;
    text-align: center;
    background: radial-gradient(circle, rgba(239,68,68,0.10) 0%, transparent 70%);
    border-radius: 18px;
">
  <div style="font-size:0.85rem; color:#94a3b8; letter-spacing:0.22em;
              text-transform:uppercase; margin-bottom:10px;">The gap</div>
  <div style="
      font-size: 12rem;
      line-height: 1;
      font-weight: 900;
      color: #ef4444;
      text-shadow: 0 0 60px rgba(239,68,68,0.35);
      animation: story-tick 2.0s ease-in-out infinite, story-fade-up 0.9s ease 0.2s both;
      letter-spacing: -0.04em;
  ">120</div>
  <div style="font-size:1.4rem; color:#cbd5e1; margin-top:6px; font-weight:600;">days</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_close_caption():
    st.markdown(
        """
<div style="
    text-align: center;
    padding: 12px 24px 36px;
    font-size: 1.25rem;
    color: #e2e8f0;
    font-weight: 500;
    line-height: 1.5;
    max-width: 680px;
    margin: 0 auto;
">
  <span style="color:#a78bfa; font-weight:700;">CascadeAI</span>
  turns 120 days of reaction into 48 hours of preparation.
</div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# Scene 2 · Meet Mary + the fragmentation problem
# =============================================================================
# Designed to be screen-recorded as a continuous scroll-down from the
# "120" reveal. Mirrors Scene 1's pure-dashboard recording technique: no
# stock footage, no on-camera human, no Canva overlay — every pixel in
# the video comes from this Streamlit page.

def _render_scene_2_divider():
    """Visual section break between Scene 1 (the gap) and Scene 2 (the user)."""
    st.markdown(
        """
<div style="margin: 36px 0 12px; padding: 16px 0 0;
            border-top: 1px solid #1e293b; text-align: center;">
  <div style="display:inline-block; background:#0f172a; padding: 0 18px;
              transform: translateY(-30px);
              font-size: 0.72rem; color: #64748b; letter-spacing: 0.22em;
              text-transform: uppercase; font-weight: 700;">
    Scene 2 · The user
  </div>
  <div style="font-size: 2.2rem; font-weight: 800; color: #e2e8f0;
              margin-top: -6px; line-height: 1.2;">
    Now picture one person inside that 120-day gap.
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_mary_persona_card():
    """Persona identity card. NO AI-generated face — uses a clean monogram
    avatar to keep the credibility story intact."""
    st.markdown(
        """
<div class="story-fade-1" style="
    margin: 8px auto 24px;
    max-width: 720px;
    padding: 22px 26px;
    display: flex;
    align-items: center;
    gap: 22px;
    background: linear-gradient(135deg, rgba(139,92,246,0.10) 0%, rgba(15,23,42,0) 70%);
    border: 1px solid #334155;
    border-left: 4px solid #a78bfa;
    border-radius: 14px;
">
  <div style="
      flex-shrink: 0;
      width: 84px;
      height: 84px;
      border-radius: 50%;
      background: linear-gradient(135deg, #8b5cf6 0%, #60a5fa 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2rem;
      font-weight: 800;
      color: #ffffff;
      box-shadow: 0 4px 20px rgba(139,92,246,0.25);
      letter-spacing: -0.02em;
  ">MW</div>
  <div style="flex: 1;">
    <div style="font-size: 1.5rem; font-weight: 800; color: #e2e8f0; line-height: 1.1;">
      Mary Wanjiku
    </div>
    <div style="font-size: 0.95rem; color: #cbd5e1; margin-top: 4px; line-height: 1.35;">
      Senior Programme Officer · Humanitarian agency · Nairobi, Kenya
    </div>
    <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 8px;
                padding-top: 8px; border-top: 1px solid #1e293b;
                font-style: italic;">
      Composite persona based on field interviews with humanitarian agency staff.
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_decision_stakes():
    """The 48-hour Hormuz decision panel — sets the stakes for the cascade."""
    st.markdown(
        """
<div class="story-fade-2" style="
    margin: 8px auto 28px;
    max-width: 720px;
    padding: 18px 24px;
    background: linear-gradient(90deg, rgba(127,29,29,0.18) 0%, rgba(15,23,42,0.6) 100%);
    border: 1px solid #ef444466;
    border-left: 4px solid #ef4444;
    border-radius: 12px;
">
  <div style="font-size: 0.68rem; color: #fca5a5; letter-spacing: 0.18em;
              text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">
    March 2026 · 48-hour decision window
  </div>
  <div style="font-size: 1.05rem; color: #e2e8f0; line-height: 1.5;">
    Shipping through Hormuz has just been disrupted. Mary has
    <span style="color:#ef4444; font-weight:700;">48 hours</span> to decide
    whether her organisation pre-positions <span style="color:#ef4444; font-weight:700;">60,000 tonnes
    of wheat</span> at Mombasa port — before East African market prices begin to move.
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_fragmentation_grid():
    """3 × 3 grid of nine real humanitarian agencies whose data Mary has
    to consult today. The whole point is to look overwhelming."""
    st.markdown(
        '<div style="text-align: center; margin: 12px 0 6px;">'
        '<div style="font-size: 0.72rem; color: #64748b; letter-spacing: 0.18em; '
        'text-transform: uppercase; font-weight: 700;">The data she needs · scattered</div>'
        '<div style="font-size: 1.5rem; font-weight: 700; color: #e2e8f0; margin-top: 2px;">'
        'Nine agencies. Twelve dashboards. Zero time.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    agencies = [
        # (name, data spine, accent, tilt)
        ("WFP HungerMap LIVE",   "Live food insecurity",         "#22c55e",  -1.2),
        ("ReliefWeb",            "Situation reports · OCHA",     "#60a5fa",   0.8),
        ("FEWS NET",             "Early warning · USAID/USGS",   "#f59e0b",  -0.5),
        ("ACLED",                "Conflict events · live",       "#ef4444",   1.4),
        ("OCHA HDX",             "Humanitarian datasets",         "#a78bfa",  -1.0),
        ("UNHCR Data Portal",    "Refugee flows · displacement", "#06b6d4",   0.6),
        ("FAO GIEWS",            "Food supply · trade",          "#84cc16",  -1.3),
        ("WHO Africa",           "Health surveillance",          "#ec4899",   0.9),
        ("IPC Food Insecurity",  "Phase classification",         "#f97316",  -0.7),
    ]

    cards_html = ""
    for name, data_spine, accent, tilt in agencies:
        cards_html += f"""
<div style="
    background: linear-gradient(160deg, rgba(15,23,42,0.95) 0%, #0b1426 100%);
    border: 1px solid #1e293b;
    border-top: 3px solid {accent};
    border-radius: 10px;
    padding: 12px 14px;
    transform: rotate({tilt}deg);
    transition: transform 0.3s ease;
    min-height: 96px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
">
  <div>
    <div style="font-size: 0.82rem; font-weight: 700; color: #e2e8f0; line-height: 1.2;">
      {name}
    </div>
    <div style="font-size: 0.7rem; color: #94a3b8; margin-top: 4px; line-height: 1.3;">
      {data_spine}
    </div>
  </div>
  <div style="font-size: 0.62rem; color: {accent}; letter-spacing: 0.10em;
              text-transform: uppercase; font-weight: 700; margin-top: 8px;">
    ↗ separate portal
  </div>
</div>
"""
    grid_html = f"""
<div style="
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    max-width: 820px;
    margin: 12px auto 24px;
    padding: 8px;
">
{cards_html}
</div>
"""
    st.markdown(grid_html, unsafe_allow_html=True)


def _render_built_for_mary():
    """Closing line of Scene 2 — the emotional pivot that bridges into
    Scene 3 (the unified CascadeAI dashboard)."""
    st.markdown(
        """
<div style="
    text-align: center;
    padding: 28px 24px 48px;
    font-size: 1.5rem;
    color: #e2e8f0;
    font-weight: 600;
    line-height: 1.4;
    max-width: 700px;
    margin: 0 auto;
">
  <span style="color: #a78bfa; font-weight: 800;">CascadeAI</span>
  is built for Mary.
</div>
        """,
        unsafe_allow_html=True,
    )

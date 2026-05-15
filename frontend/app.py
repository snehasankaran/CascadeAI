"""CascadeAI — Streamlit Dashboard

Run: streamlit run frontend/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import os

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: F401 — loads .env


def _gemma_backend() -> tuple[str, str, str, str, str]:
    """Detect which Gemma 4 backend is configured.

    Returns: (mode_id, label, accent_color, dot_color, tooltip)
    mode_id is 'offline' for Ollama (any localhost / 127.0.0.1 / Ollama URL),
    'cloud' for Google AI Studio, 'unset' otherwise.
    """
    api_base = (os.getenv("GEMMA_API_BASE") or "").lower()
    model = os.getenv("GEMMA_MODEL", "")
    if not api_base:
        return ("unset", "Backend Not Configured", "#64748b", "#94a3b8", "Set GEMMA_API_BASE in your .env file")
    if any(s in api_base for s in ("localhost", "127.0.0.1", ":11434", "ollama")):
        return (
            "offline",
            f"Offline · Ollama · {model or 'local'}",
            "#10b981",
            "#22c55e",
            "Running fully on-device via Ollama — no internet required for inference",
        )
    if "generativelanguage.googleapis.com" in api_base:
        return (
            "cloud",
            f"Cloud · Google AI Studio · {model or 'gemma-4'}",
            "#60a5fa",
            "#3b82f6",
            "Running on Google AI Studio (cloud). Toggle to Ollama in .env for offline mode.",
        )
    return ("custom", f"Custom · {model or api_base}", "#a78bfa", "#a855f7", api_base)

from cascade.graph import CascadeGraph
from cascade.traversal import run_cascade, run_compound_cascade, CascadeImpact
from cascade.replay import run_backtest, available_scenarios
from data.profiles import load_profile, load_all_profiles, available_countries, get_profile_raw
from frontend.components.cascade_map import render_cascade_map
from frontend.components.impact_cards import render_impact_cards, render_demo_headlines
from frontend.components.backtest_view import render_backtest_view
from frontend.components.backtest_overview import render_backtest_overview
from frontend.components.audience_selector import render_audience_selector
from frontend.components.predictions_view import render_predictions_view
from frontend.components.action_watch import render_action_watch
from frontend.components.vision_analyst_view import render_vision_analyst
from frontend.components.intro_story import render_intro_story
from data.predictions.loader import available_predictions, load_prediction


st.set_page_config(
    page_title="CascadeAI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ── Typography ── */
    .main-header {
        font-size: 2.8rem; font-weight: 800;
        margin: 0; padding: 6px 0 2px 0;
        line-height: 1.15;
        display: inline-block;
        background: linear-gradient(90deg, #8b5cf6 0%, #a78bfa 30%, #60a5fa 60%, #38bdf8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
        filter: drop-shadow(0 0 16px rgba(139, 92, 246, 0.25));
    }
    .sub-header {
        font-size: 1.1rem; color: var(--cai-text-muted, #94a3b8);
        margin: 0; padding-top: 2px; padding-bottom: 4px;
        letter-spacing: 0.02em; font-weight: 400;
        line-height: 1.4;
    }
    
    /* ── Animations ── */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 5px rgba(139, 92, 246, 0.4); }
        50% { box-shadow: 0 0 20px rgba(139, 92, 246, 0.6), 0 0 40px rgba(139, 92, 246, 0.3); }
    }
    /* Rotate around a tilted axis (0.35, 1, 0.1) — mostly Y but with X/Z tilt.
       This prevents the emoji from ever going fully edge-on, keeping it visible
       throughout the spin and creating a convincing tilted-axis globe effect. */
    @keyframes spinGlobe3D {
        0%   { transform: perspective(160px) rotate3d(0.35,1,0.1,0deg);
               filter: drop-shadow(-8px 6px 18px rgba(139,92,246,0.65)) drop-shadow(0 0 28px rgba(139,92,246,0.25)); }
        25%  { transform: perspective(160px) rotate3d(0.35,1,0.1,-90deg);
               filter: drop-shadow(-2px 6px 14px rgba(96,165,250,0.5))  drop-shadow(0 0 20px rgba(96,165,250,0.2)); }
        50%  { transform: perspective(160px) rotate3d(0.35,1,0.1,-180deg);
               filter: drop-shadow(8px 6px 18px rgba(139,92,246,0.65))  drop-shadow(0 0 28px rgba(139,92,246,0.25)); }
        75%  { transform: perspective(160px) rotate3d(0.35,1,0.1,-270deg);
               filter: drop-shadow(2px 6px 14px rgba(96,165,250,0.5))   drop-shadow(0 0 20px rgba(96,165,250,0.2)); }
        100% { transform: perspective(160px) rotate3d(0.35,1,0.1,-360deg);
               filter: drop-shadow(-8px 6px 18px rgba(139,92,246,0.65)) drop-shadow(0 0 28px rgba(139,92,246,0.25)); }
    }
    @keyframes globeBob {
        0%, 100% { transform: translateY(0px);  }
        50%       { transform: translateY(-5px); }
    }
    /* Realistic axial rotation: continents drift across the face of a clipped
       sphere from left-to-right, rather than flat-rotating the whole icon. */
    @keyframes globeSpin {
        from { transform: translateX(-200px); }
        to   { transform: translateX(0); }
    }
    @keyframes globeClouds {
        from { transform: translateX(-200px); }
        to   { transform: translateX(0); }
    }
    .globe-continents  { animation: globeSpin   22s linear infinite; will-change: transform; }
    .globe-cloud-layer { animation: globeClouds 28s linear infinite; will-change: transform; }
    .globe-spin {
        display: inline-block;
        animation: spinGlobe3D 7s linear infinite;
        will-change: transform;
    }
    .globe-container {
        display: inline-block;
        animation: globeBob 3.5s ease-in-out infinite;
        filter: drop-shadow(0 8px 22px rgba(56, 189, 248, 0.25))
                drop-shadow(0 0 32px rgba(139, 92, 246, 0.18));
    }
    .animate-fade-in { animation: fadeIn 0.5s ease-out; }
    .animate-pulse { animation: pulse 2s ease-in-out infinite; }
    
    /* ── Welcome Cards ── */
    .welcome-card {
        background: linear-gradient(145deg, #1e1b4b 0%, #0f172a 50%, #1e293b 100%);
        border: 1px solid #312e81;
        border-radius: 16px;
        padding: 24px;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .welcome-card:hover {
        border-color: #6366f1;
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(99, 102, 241, 0.2);
    }
    .welcome-card-icon {
        font-size: 2.5rem;
        margin-bottom: 12px;
        display: block;
    }
    .welcome-card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 8px;
    }
    .welcome-card-desc {
        font-size: 0.875rem;
        color: #94a3b8;
        line-height: 1.5;
    }
    
    /* ── Feature Badge ── */
    .feature-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(139, 92, 246, 0.15);
        color: #a78bfa;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 20px;
        border: 1px solid rgba(139, 92, 246, 0.3);
    }

    /* ── Metric cards ── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e1b4b 0%, #1e293b 100%);
        border: 1px solid #312e81; border-radius: 14px; padding: 16px 18px;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    div[data-testid="stMetric"]:before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #8b5cf6, #a78bfa, #60a5fa);
    }
    div[data-testid="stMetric"]:hover { 
        border-color: #6366f1; 
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.2);
    }
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.75rem !important; letter-spacing: 0.05em; text-transform: uppercase; }
    div[data-testid="stMetricValue"] { color: #e2e8f0 !important; font-weight: 800 !important; font-size: 1.6rem !important; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a1a 0%, #0d1117 100%);
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color: #94a3b8 !important; }
    section[data-testid="stSidebar"] .stRadio label { font-size: 0.9rem !important; color: #cbd5e1 !important; }
    section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p { color: #cbd5e1 !important; }
    section[data-testid="stSidebar"] h1 { font-size: 1.6rem !important; color: #f8fafc !important; text-shadow: 0 0 20px rgba(139, 92, 246, 0.4); }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #f1f5f9 !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stMultiSelect label,
    section[data-testid="stSidebar"] .stSubheader { color: #cbd5e1 !important; }
    section[data-testid="stSidebar"] [data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-baseweb="select"] span { color: #e2e8f0 !important; }
    section[data-testid="stSidebar"] [data-testid="stSlider"] * { color: #cbd5e1 !important; }
    /* Sidebar divider styling */
    section[data-testid="stSidebar"] hr { 
        border-color: #312e81 !important; 
        background: linear-gradient(90deg, transparent, #4f46e5, transparent) !important;
        height: 1px !important;
    }

    /* ── Tabs ── */
    button[data-baseweb="tab"] {
        font-size: 0.9rem !important; font-weight: 600 !important;
        color: #64748b !important;
        padding: 12px 20px !important;
        transition: all 0.2s ease;
    }
    button[data-baseweb="tab"]:hover { color: #94a3b8 !important; }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #a78bfa !important;
        border-bottom: 2px solid #a78bfa !important;
        background: linear-gradient(180deg, transparent 0%, rgba(167, 139, 250, 0.1) 100%);
    }

    /* ── Buttons ── */
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #8b5cf6 100%);
        border: none; border-radius: 10px; font-weight: 700;
        letter-spacing: 0.02em; padding: 0.65rem 1.25rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(79, 70, 229, 0.4);
        background: linear-gradient(135deg, #5b54e6 0%, #8b5cf6 50%, #a78bfa 100%);
    }
    div[data-testid="stButton"] > button[kind="primary"]:active {
        transform: translateY(0);
    }

    /* ── Info / Warning / Error boxes ── */
    div[data-testid="stAlert"] { border-radius: 12px !important; border: 1px solid; }
    div[data-testid="stAlert"][data-severity="info"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.8) 100%) !important;
        border-color: #312e81 !important;
    }
    div[data-testid="stAlert"][data-severity="warning"] {
        background: linear-gradient(135deg, rgba(124, 45, 18, 0.3) 0%, rgba(15, 23, 42, 0.8) 100%) !important;
        border-color: #7c2d12 !important;
    }

    /* ── Dataframe ── */
    div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid #1e293b; }

    /* ── Expander ── */
    details { 
        border-radius: 12px !important; 
        border: 1px solid #1e293b !important; 
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
    }
    details summary { color: #e2e8f0 !important; font-weight: 600; }
    details summary:hover { color: #a78bfa !important; }

    /* ── Divider ── */
    hr { 
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, #312e81, transparent) !important;
        margin: 24px 0 !important;
    }

    /* ── Selectbox & Inputs ── */
    div[data-testid="stSelectbox"] > div,
    div[data-testid="stMultiselect"] > div,
    div[data-testid="stSlider"] > div {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
        border-radius: 10px !important;
        border: 1px solid #312e81 !important;
    }
    
    /* ── Text Area ── */
    div[data-testid="stTextArea"] textarea {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
        border: 1px solid #312e81 !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-size: 0.95rem !important;
    }
    div[data-testid="stTextArea"] textarea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
    }
    
    /* ── Toggle ── */
    div[data-testid="stToggle"] > div {
        background: #1e293b !important;
    }
    
    /* ── Spinner ── */
    div[data-testid="stSpinner"] > div {
        color: #a78bfa !important;
    }

    /* ── General ── */
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; }
    .main > div { padding-left: 2rem !important; padding-right: 2rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Helper functions (defined before use) ─────────────────────────

def _globe_svg(size_px: int, pid: str) -> str:
    """Photorealistic 3D globe icon as inline SVG.

    The illusion of axial rotation is created by horizontally scrolling a tiled
    world-map ``<symbol>`` inside a circular clip path, rather than flat-
    rotating the whole element. Soft diffused lighting (specular highlight +
    terminator shadow), an atmospheric halo, ocean depth via radial gradient,
    layered topographic patches, and a drifting cloud layer combine to give
    the icon a polished, modern, photoreal feel suitable for a UI accent.

    ``pid`` namespaces the SVG def IDs so multiple globes can coexist on the
    same page without gradient/clip collisions.
    """
    return f'''<svg width="{size_px}" height="{size_px}" viewBox="0 0 200 200"
  xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Earth globe"
  style="display:block;overflow:visible;">
  <defs>
    <radialGradient id="g-atmos-{pid}" cx="50%" cy="50%" r="50%">
      <stop offset="78%" stop-color="#38bdf8" stop-opacity="0"/>
      <stop offset="90%" stop-color="#7dd3fc" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="#a78bfa" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="g-ocean-{pid}" cx="35%" cy="28%" r="78%">
      <stop offset="0%"   stop-color="#bae6fd"/>
      <stop offset="28%"  stop-color="#38bdf8"/>
      <stop offset="62%"  stop-color="#0284c7"/>
      <stop offset="92%"  stop-color="#075985"/>
      <stop offset="100%" stop-color="#0c4a6e"/>
    </radialGradient>
    <radialGradient id="g-land-{pid}" cx="40%" cy="30%" r="80%">
      <stop offset="0%"   stop-color="#86efac"/>
      <stop offset="40%"  stop-color="#22c55e"/>
      <stop offset="80%"  stop-color="#16a34a"/>
      <stop offset="100%" stop-color="#166534"/>
    </radialGradient>
    <radialGradient id="g-gloss-{pid}" cx="28%" cy="20%" r="42%">
      <stop offset="0%"   stop-color="#ffffff" stop-opacity="0.75"/>
      <stop offset="40%"  stop-color="#ffffff" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="g-shade-{pid}" cx="72%" cy="78%" r="62%">
      <stop offset="0%"   stop-color="#000000" stop-opacity="0"/>
      <stop offset="60%"  stop-color="#000000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#001028" stop-opacity="0.55"/>
    </radialGradient>
    <clipPath id="g-clip-{pid}"><circle cx="100" cy="100" r="80"/></clipPath>
    <symbol id="g-cont-{pid}" viewBox="0 0 200 160" overflow="visible">
      <!-- Antarctic ice cap (continuous bottom band) -->
      <path d="M0,140 Q30,136 60,140 Q100,136 140,140 Q170,138 200,142 L200,160 L0,160 Z"
            fill="#e0f7fa" opacity="0.92"/>
      <path d="M0,142 Q30,138 60,142 Q100,138 140,142 Q170,140 200,144 L200,160 L0,160 Z"
            fill="url(#g-land-{pid})" opacity="0.25"/>
      <!-- Greenland -->
      <path d="M62,10 Q76,6 88,16 L86,28 Q76,32 64,28 Q58,22 62,10 Z" fill="url(#g-land-{pid})"/>
      <!-- North America -->
      <path d="M8,30 Q18,18 38,20 L62,22 Q74,30 74,44 L68,58 Q62,74 50,76 L38,76 Q22,70 12,56 Q4,42 8,30 Z"
            fill="url(#g-land-{pid})"/>
      <!-- Central America -->
      <path d="M46,76 L62,74 L68,86 L60,94 L50,88 Z" fill="url(#g-land-{pid})"/>
      <!-- South America -->
      <path d="M56,92 Q68,88 76,96 L78,114 Q74,130 66,138 L58,132 Q50,118 52,102 Z"
            fill="url(#g-land-{pid})"/>
      <!-- UK / Ireland -->
      <path d="M84,30 L90,28 L92,38 L86,40 Z" fill="url(#g-land-{pid})"/>
      <!-- Europe -->
      <path d="M94,30 L116,28 L126,34 L124,46 L108,50 L94,48 Z" fill="url(#g-land-{pid})"/>
      <!-- Africa (continuous) -->
      <path d="M92,50 Q112,48 130,56 L134,70 L132,86 Q128,104 120,118 L110,132 Q102,138 96,132 L90,114 Q86,92 88,72 Q88,58 92,50 Z"
            fill="url(#g-land-{pid})"/>
      <!-- Madagascar -->
      <path d="M134,98 L140,96 L140,116 L134,118 Z" fill="url(#g-land-{pid})"/>
      <!-- Arabian Peninsula -->
      <path d="M126,52 L140,50 L146,62 L140,72 L130,70 Z" fill="url(#g-land-{pid})"/>
      <!-- Asia (huge northern mass) -->
      <path d="M124,14 Q150,8 180,12 L196,22 Q202,34 198,46 L190,56 L172,60 L150,56 L132,48 L124,40 Q120,26 124,14 Z"
            fill="url(#g-land-{pid})"/>
      <!-- China / Mongolia bulge -->
      <path d="M158,46 Q174,42 188,48 L186,58 L164,60 Z" fill="url(#g-land-{pid})"/>
      <!-- India -->
      <path d="M144,62 L158,60 L158,74 L150,80 L142,72 Z" fill="url(#g-land-{pid})"/>
      <!-- Japan -->
      <path d="M188,30 L194,28 L198,42 L192,46 Z" fill="url(#g-land-{pid})"/>
      <!-- Korea / China east -->
      <path d="M178,42 L186,42 L186,52 L180,54 Z" fill="url(#g-land-{pid})"/>
      <!-- Philippines -->
      <path d="M180,64 L188,62 L190,72 L182,74 Z" fill="url(#g-land-{pid})"/>
      <!-- SE Asia / Indonesia chain -->
      <path d="M156,76 L172,74 L174,82 L160,84 Z" fill="url(#g-land-{pid})"/>
      <path d="M170,84 L188,82 L190,90 L174,92 Z" fill="url(#g-land-{pid})"/>
      <!-- New Guinea -->
      <path d="M188,90 Q198,88 200,94 L198,100 L188,100 Z" fill="url(#g-land-{pid})"/>
      <!-- Australia -->
      <path d="M158,100 Q176,94 194,100 L198,114 Q190,128 174,128 Q160,122 156,112 Q154,104 158,100 Z"
            fill="url(#g-land-{pid})"/>
      <!-- New Zealand -->
      <path d="M192,130 L198,128 L200,138 L194,140 Z" fill="url(#g-land-{pid})"/>
    </symbol>
  </defs>
  <circle cx="100" cy="100" r="94" fill="url(#g-atmos-{pid})"/>
  <circle cx="100" cy="100" r="80" fill="url(#g-ocean-{pid})"/>
  <g clip-path="url(#g-clip-{pid})">
    <g class="globe-continents">
      <use href="#g-cont-{pid}" x="-200" y="20"/>
      <use href="#g-cont-{pid}" x="0"    y="20"/>
      <use href="#g-cont-{pid}" x="200"  y="20"/>
    </g>
  </g>
  <g clip-path="url(#g-clip-{pid})" opacity="0.16">
    <g class="globe-cloud-layer">
      <ellipse cx="-160" cy="62"  rx="26" ry="4" fill="#ffffff"/>
      <ellipse cx="-80"  cy="92"  rx="32" ry="5" fill="#ffffff"/>
      <ellipse cx="20"   cy="74"  rx="24" ry="4" fill="#ffffff"/>
      <ellipse cx="100"  cy="118" rx="30" ry="5" fill="#ffffff"/>
      <ellipse cx="180"  cy="68"  rx="28" ry="4" fill="#ffffff"/>
      <ellipse cx="260"  cy="100" rx="26" ry="5" fill="#ffffff"/>
      <ellipse cx="340"  cy="80"  rx="22" ry="4" fill="#ffffff"/>
    </g>
  </g>
  <circle cx="100" cy="100" r="80" fill="url(#g-shade-{pid})"/>
  <ellipse cx="74" cy="60" rx="46" ry="32" fill="url(#g-gloss-{pid})"/>
  <circle cx="100" cy="100" r="80" fill="none" stroke="#0c4a6e" stroke-width="1.1" opacity="0.85"/>
  <circle cx="100" cy="100" r="80" fill="none" stroke="#7dd3fc" stroke-width="0.4" opacity="0.45"/>
</svg>'''


@st.cache_resource
def get_graph():
    return CascadeGraph.from_json()


_SEV_TIERS = [
    (0.8, "CRITICAL", "#ef4444", "#dc2626", "#7f1d1d", "#fca5a5"),
    (0.6, "SEVERE",   "#f97316", "#ea580c", "#7c2d12", "#fdba74"),
    (0.4, "MODERATE", "#eab308", "#ca8a04", "#713f12", "#fde047"),
    (0.2, "MILD",     "#22c55e", "#16a34a", "#14532d", "#86efac"),
    (0.0, "LOW",      "#60a5fa", "#3b82f6", "#1e3a5f", "#93c5fd"),
]

_NODE_ICONS = {
    "food": "🌾", "health": "🏥", "displacement": "🏕️", "energy": "⚡",
    "fertilizer": "🧪", "water": "💧", "conflict": "⚔️", "economy": "💹",
    "transport": "🚢", "governance": "🏛️", "climate": "🌡️",
}


def _severity_cell(sev: float) -> str:
    for threshold, label, text_color, bar_end, badge_bg, badge_fg in _SEV_TIERS:
        if sev >= threshold:
            pct = int(sev * 100)
            return (
                f'<div style="display:inline-flex;align-items:center;gap:8px;">'
                f'<div style="width:60px;height:6px;background:#1e293b;border-radius:3px;overflow:hidden;">'
                f'<div style="width:{pct}%;height:100%;background:linear-gradient(90deg,{text_color},{bar_end});border-radius:3px;"></div>'
                f'</div>'
                f'<span style="color:{text_color};font-weight:700;font-size:0.85rem;">{sev:.2f}</span>'
                f'<span style="background:{badge_bg};color:{badge_fg};font-size:0.65rem;padding:2px 8px;border-radius:4px;font-weight:600;letter-spacing:0.04em;">{label}</span>'
                f'</div>'
            )
    return ""


def _render_detail_table(all_impacts: dict, graph: CascadeGraph):
    """Render a styled detail table with colored severity indicators.

    Build the entire HTML as a single string and render in ONE st.markdown call
    so Streamlit's markdown parser doesn't break the <table>/<tr>/<td> tags.
    """
    header_cell_style = (
        "padding:14px 16px;text-align:left;color:#a78bfa;font-weight:700;"
        "font-size:0.78rem;text-transform:uppercase;letter-spacing:0.06em;"
        "border-bottom:1px solid #4f46e5;background:transparent;"
    )
    header_cell_center = header_cell_style.replace("text-align:left", "text-align:center")

    rows_html = []
    row_idx = 0
    for country, impacts in all_impacts.items():
        for imp in impacts:
            node_label = graph.get_node(imp.node).label
            icon = _NODE_ICONS.get(imp.node, "•")
            row_bg = "#0f172a" if row_idx % 2 == 0 else "#131c2f"
            row_idx += 1

            if imp.is_seed:
                seed_badge = (
                    '<span style="background:linear-gradient(135deg,#4f46e5,#7c3aed);'
                    'color:#fff;font-size:0.65rem;padding:3px 9px;border-radius:4px;'
                    'font-weight:700;letter-spacing:0.05em;">SEED</span>'
                )
            else:
                seed_badge = '<span style="color:#475569;font-size:0.75rem;">—</span>'

            rows_html.append(
                f'<tr style="background:{row_bg};">'
                f'<td style="padding:12px 16px;color:#e2e8f0;font-weight:600;border-bottom:1px solid #1e293b;">{country}</td>'
                f'<td style="padding:12px 16px;color:#94a3b8;border-bottom:1px solid #1e293b;">'
                f'<span style="margin-right:8px;">{icon}</span>{node_label}'
                f'</td>'
                f'<td style="padding:12px 16px;border-bottom:1px solid #1e293b;">{_severity_cell(imp.severity)}</td>'
                f'<td style="padding:12px 16px;text-align:center;color:#cbd5e1;font-weight:600;border-bottom:1px solid #1e293b;">{imp.delay_days}d</td>'
                f'<td style="padding:12px 16px;text-align:center;border-bottom:1px solid #1e293b;">{seed_badge}</td>'
                f'</tr>'
            )

    table_html = (
        '<div style="background:linear-gradient(135deg,#0f172a,#1e293b);'
        'border:1px solid #312e81;border-radius:12px;overflow:hidden;'
        'box-shadow:0 4px 20px rgba(0,0,0,0.3);margin-top:8px;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.9rem;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
        '<thead><tr style="background:linear-gradient(90deg,#1e1b4b,#312e81);">'
        f'<th style="{header_cell_style}">Country</th>'
        f'<th style="{header_cell_style}">System Node</th>'
        f'<th style="{header_cell_style}">Severity</th>'
        f'<th style="{header_cell_center}">Delay</th>'
        f'<th style="{header_cell_center}">Type</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table></div>'
    )

    st.markdown(table_html, unsafe_allow_html=True)


def _impacts_to_dicts(impacts: list[CascadeImpact]) -> list[dict]:
    return [
        {"node": i.node, "severity": i.severity, "delay_days": i.delay_days, "path": i.path}
        for i in impacts
    ]


def _show_welcome():
    n_nodes = len(graph.nodes)
    n_edges = len(graph.edges)
    n_countries = len(available_countries())

    # ── Animated header section (single-line HTML — no leading indent) ──
    header_html = (
        '<div style="text-align:center;margin-bottom:36px;">'
          '<div style="display:inline-block;background:linear-gradient(135deg,rgba(139,92,246,0.2),rgba(59,130,246,0.2));'
          'border:1px solid rgba(139,92,246,0.3);border-radius:50px;padding:8px 20px;margin-bottom:20px;">'
            '<span style="color:#a78bfa;font-size:0.85rem;font-weight:600;letter-spacing:0.05em;">'
              '🚀 POWERED BY GEMMA 4'
            '</span>'
          '</div>'
          '<h2 style="color:#e2e8f0;font-size:2rem;font-weight:700;margin-bottom:12px;">'
            'Predict Crisis Cascades Across Global Systems'
          '</h2>'
          f'<p style="color:#94a3b8;font-size:1.05rem;max-width:640px;margin:0 auto;line-height:1.6;">'
            f'Model how disruptions in energy, food, health, and displacement interconnect '
            f'and cascade across {n_countries} countries.'
          '</p>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    # ── Stats row ──
    col1, col2, col3, col4 = st.columns(4)
    stats = [
        ("📊", n_nodes, "System Nodes", "Energy, food, health, displacement & more"),
        ("🔗", n_edges, "Cascade Edges", "Interconnection pathways"),
        ("🌍", n_countries, "Countries", "Profiles with vulnerability data"),
        ("🤖", "Gemma 4", "AI Engine", "Natural language event detection"),
    ]
    for col, (icon, value, label, desc) in zip([col1, col2, col3, col4], stats):
        stat_html = (
            '<div style="background:linear-gradient(145deg,#1e1b4b,#0f172a);'
            'border:1px solid #312e81;border-radius:14px;padding:20px 16px;text-align:center;'
            'transition:all 0.3s ease;">'
            f'<div style="font-size:2rem;margin-bottom:8px;">{icon}</div>'
            f'<div style="font-size:1.55rem;font-weight:800;color:#e2e8f0;margin-bottom:4px;">{value}</div>'
            f'<div style="font-size:0.82rem;font-weight:600;color:#a78bfa;margin-bottom:4px;letter-spacing:0.02em;">{label}</div>'
            f'<div style="font-size:0.7rem;color:#64748b;line-height:1.4;">{desc}</div>'
            '</div>'
        )
        with col:
            st.markdown(stat_html, unsafe_allow_html=True)

    st.markdown("<div style='margin:32px 0;'></div>", unsafe_allow_html=True)

    # ── Section title ──
    st.markdown(
        '<h3 style="color:#e2e8f0;font-size:1.25rem;font-weight:600;margin-bottom:18px;text-align:center;">'
        'Select a Mode to Begin'
        '</h3>',
        unsafe_allow_html=True,
    )

    modes = [
        {"icon": "🎯", "title": "Crisis Simulator",
         "desc": "Select a crisis type and severity level. Visualize real-time cascade impacts across multiple countries with interactive maps and severity metrics.",
         "color": "#8b5cf6", "badge": "Most Popular"},
        {"icon": "📈", "title": "Backtest Validation",
         "desc": "Validate against real historical data including Ukraine 2022, Sudan 2023, BEV Crash 2025, and Hormuz 2026 scenarios.",
         "color": "#3b82f6", "badge": None},
        {"icon": "🔮", "title": "Forward Predictions",
         "desc": "Explore forward-looking scenarios currently being tracked: BEV Second Wave, EU Auto Cascade, Hormuz Escalation, and more.",
         "color": "#10b981", "badge": "Active"},
        {"icon": "⚡", "title": "Compound Crisis",
         "desc": "Model multiple simultaneous events with probabilistic severity combination. See overlapping cascade paths and amplified impacts.",
         "color": "#f59e0b", "badge": None},
        {"icon": "🧠", "title": "Event Detector",
         "desc": "Describe any crisis in natural language. Gemma 4 automatically classifies the event type, estimates severity, and runs the full cascade analysis.",
         "color": "#ec4899", "badge": "AI-Powered"},
        {"icon": "🛰️", "title": "Vision Analyst",
         "desc": "Upload a satellite image, sitrep page, or field photo. Gemma 4 multimodal extracts crisis indicators, estimates severity, and seeds the cascade.",
         "color": "#06b6d4", "badge": "Multimodal"},
    ]

    def _build_card(mode: dict) -> str:
        color = mode["color"]
        if mode["badge"]:
            badge_html = (
                f'<div style="display:inline-block;background:{color}22;color:{color};'
                f'font-size:0.65rem;font-weight:700;padding:3px 10px;border-radius:20px;'
                f'border:1px solid {color}55;margin-bottom:10px;letter-spacing:0.04em;">'
                f'{mode["badge"]}'
                f'</div>'
            )
        else:
            badge_html = (
                '<div style="display:inline-block;font-size:0.65rem;padding:3px 10px;'
                'margin-bottom:10px;visibility:hidden;">.</div>'
            )
        return (
            '<div style="background:linear-gradient(145deg,#1e1b4b 0%,#0f172a 50%,#1e293b 100%);'
            f'border:1px solid {color}40;border-radius:16px;padding:24px;'
            'height:100%;min-height:230px;transition:all 0.3s ease;position:relative;overflow:hidden;'
            'box-shadow:0 4px 20px rgba(0,0,0,0.3);">'
            '<div style="position:absolute;top:0;left:0;right:0;height:3px;'
            f'background:linear-gradient(90deg,{color},{color}80);"></div>'
            f'{badge_html}'
            f'<div style="font-size:2.4rem;margin-bottom:12px;line-height:1;">{mode["icon"]}</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin-bottom:10px;">{mode["title"]}</div>'
            f'<div style="font-size:0.85rem;color:#94a3b8;line-height:1.6;">{mode["desc"]}</div>'
            '</div>'
        )

    # 3-column grid
    for i in range(0, len(modes), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(modes):
                with col:
                    st.markdown(_build_card(modes[idx]), unsafe_allow_html=True)
        if i + 3 < len(modes):
            st.markdown("<div style='margin:14px 0;'></div>", unsafe_allow_html=True)

    # ── Bottom CTA ──
    cta_html = (
        '<div style="text-align:center;margin-top:36px;padding:28px;'
        'background:linear-gradient(135deg,rgba(139,92,246,0.1),rgba(59,130,246,0.1));'
        'border:1px solid rgba(139,92,246,0.2);border-radius:16px;">'
        '<div style="font-size:1.5rem;margin-bottom:10px;">👈</div>'
        '<div style="font-size:1.1rem;font-weight:600;color:#e2e8f0;margin-bottom:6px;">'
        'Choose Your Mode From the Sidebar'
        '</div>'
        '<div style="font-size:0.88rem;color:#64748b;">'
        'Configure your crisis scenario and click Run to see the cascade unfold'
        '</div>'
        '</div>'
    )
    st.markdown(cta_html, unsafe_allow_html=True)


# ── Load graph ────────────────────────────────────────────────────
graph = get_graph()


# ── Sidebar ───────────────────────────────────────────────────────
_backend_mode, _backend_label, _backend_accent, _backend_dot, _backend_tooltip = _gemma_backend()

with st.sidebar:
    icon = {"offline": "📡", "cloud": "☁️", "custom": "🛠️", "unset": "⚠️"}.get(_backend_mode, "🤖")
    st.markdown(
        '<div style="text-align:center;padding:14px 0 20px;">'
        '<div class="globe-container" style="margin-bottom:10px;width:78px;height:78px;">'
        f'{_globe_svg(78, "sb")}'
        '</div>'
        '<h1 style="margin:0;font-size:1.5rem;font-weight:800;'
        'background:linear-gradient(90deg,#8b5cf6,#a78bfa,#60a5fa);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;">CascadeAI</h1>'
        '<p style="color:#64748b;font-size:0.8rem;margin:6px 0 0;">Crisis Cascade Prediction</p>'
        f'<div title="{_backend_tooltip}" style="display:inline-flex;align-items:center;gap:6px;margin-top:12px;'
        f'background:{_backend_accent}1f;padding:5px 12px;border-radius:20px;'
        f'border:1px solid {_backend_accent}55;">'
        f'<span style="width:8px;height:8px;background:{_backend_dot};border-radius:50%;display:inline-block;'
        f'box-shadow:0 0 8px {_backend_dot}99;"></span>'
        f'<span style="color:{_backend_accent};font-size:0.72rem;font-weight:700;letter-spacing:0.02em;">'
        f'{icon} {_backend_label}</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    mode = st.radio(
        "Mode",
        [
            "📖 The Story",
            "Crisis Simulator",
            "Backtest Validation",
            "Forward Predictions",
            "Compound Crisis",
            "Event Detector (Gemma 4)",
            "Vision Analyst (Gemma 4 Multimodal)",
        ],
        index=1,
    )
    st.divider()

    if mode == "📖 The Story":
        st.subheader("The 120-Day Gap")
        st.caption("Why CascadeAI exists · the scene every humanitarian agency knows by heart")
        run_btn = False

    elif mode == "Crisis Simulator":
        st.subheader("Event Configuration")
        event_node = st.selectbox(
            "Crisis Type",
            options=graph.node_ids(),
            format_func=lambda x: graph.get_node(x).label,
            index=0,
        )
        severity = st.slider("Severity", 0.1, 1.0, 0.8, 0.05)
        selected_countries = st.multiselect(
            "Countries",
            options=available_countries(),
            default=["Kenya", "Ethiopia", "Somalia", "Egypt"],
        )
        run_btn = st.button("Run Cascade", type="primary", width="stretch")
        st.caption("Runs deterministic BFS from the selected node — no LLM needed.")

    elif mode == "Backtest Validation":
        st.subheader("Backtest Settings")
        scenarios = available_scenarios()
        scenario_labels = {
            "bev_crash_2025": "BEV Crash 2025 — US Policy Cascade",
            "ukraine_2022": "Ukraine 2022 — Russia Invasion",
            "sudan_2023": "Sudan 2023-2026 — Civil War",
            "hormuz_2026": "Hormuz 2026 — Fertilizer Surge",
        }
        scenario = st.selectbox(
            "Scenario",
            scenarios,
            format_func=lambda x: scenario_labels.get(x, x),
        )
        run_btn = st.button("Run Backtest", type="primary", width="stretch")
        st.caption("Replays a historical crisis and compares predictions to actuals.")

    elif mode == "Forward Predictions":
        st.subheader("Forward Predictions")
        st.caption("Active cascades CascadeAI is tracking right now")
        pred_names = available_predictions()
        pred_labels = {
            "bev_second_wave_2026": "BEV Second Wave — Gigafactory Graveyard",
            "eu_auto_collapse_2026": "EU Auto Cascade — German Crisis",
            "hormuz_escalation_2026": "Hormuz Closure — Energy-Food Cascade",
            "sudan_famine_spread_2026": "Sudan Famine — Cross-Border Emergency",
        }
        selected_pred = st.selectbox(
            "Prediction Scenario",
            pred_names,
            format_func=lambda x: pred_labels.get(x, x),
        )
        run_btn = st.button("View Prediction", type="primary", width="stretch")
        st.caption("Loads the curated forward scenario JSON.")

    elif mode == "Compound Crisis":
        st.subheader("Compound Crisis")
        st.caption("Simulate multiple simultaneous events")
        event1_node = st.selectbox("Event 1", options=graph.node_ids(),
                                    format_func=lambda x: graph.get_node(x).label, index=0, key="e1")
        event1_sev = st.slider("Severity 1", 0.1, 1.0, 0.9, 0.05, key="s1")
        event2_node = st.selectbox("Event 2", options=graph.node_ids(),
                                    format_func=lambda x: graph.get_node(x).label, index=1, key="e2")
        event2_sev = st.slider("Severity 2", 0.1, 1.0, 0.7, 0.05, key="s2")
        compound_country = st.selectbox("Country", options=available_countries(), index=0, key="cc")
        run_btn = st.button("Run Compound", type="primary", width="stretch")
        st.caption("Combines both severities via probabilistic union (a + b − a·b).")

    elif mode == "Event Detector (Gemma 4)":
        st.subheader("Natural Language Event")
        st.caption("Describe a crisis and Gemma 4 will classify it")
        run_btn = False

    else:  # Vision Analyst (Gemma 4 Multimodal)
        st.subheader("Vision Analyst")
        st.caption("Upload an image — Gemma 4 multimodal reads it and seeds the cascade.")
        run_btn = False


# ── Main Content ──────────────────────────────────────────────────
_header_icon = {"offline": "📡", "cloud": "☁️", "custom": "🛠️", "unset": "⚠️"}.get(_backend_mode, "🤖")
_header_backend_pill = (
    f'<span title="{_backend_tooltip}" style="display:inline-flex;align-items:center;gap:6px;'
    f'background:{_backend_accent}1f;padding:5px 12px;border-radius:20px;'
    f'border:1px solid {_backend_accent}55;font-size:0.72rem;font-weight:700;'
    f'color:{_backend_accent};letter-spacing:0.02em;">'
    f'<span style="width:8px;height:8px;background:{_backend_dot};border-radius:50%;display:inline-block;'
    f'box-shadow:0 0 8px {_backend_dot}99;"></span>'
    f'{_header_icon} {_backend_label}'
    '</span>'
)

st.markdown(
    '<div style="display:flex; align-items:center; gap:16px; margin:24px 0 8px 0; overflow:visible;">'
    '<div class="globe-container" style="width:58px;height:58px;flex-shrink:0;">'
    f'{_globe_svg(58, "hdr")}'
    '</div>'
    '<div style="flex:1; min-width:0; overflow:visible;">'
      '<div style="font-size:2.8rem; font-weight:800; line-height:1.25; padding:4px 0;'
      ' background:linear-gradient(90deg,#8b5cf6 0%,#a78bfa 30%,#60a5fa 60%,#38bdf8 100%);'
      ' -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'
      ' filter:drop-shadow(0 0 14px rgba(139,92,246,0.25));">CascadeAI</div>'
      '<div style="font-size:1.05rem; color:#94a3b8; line-height:1.45; margin-top:2px;">'
      'Predicting how crises cascade across energy · food · health · displacement — powered by Gemma 4'
      '</div>'
    '</div>'
    f'<div style="flex-shrink:0;">{_header_backend_pill}</div>'
    '</div>',
    unsafe_allow_html=True,
)
st.divider()


if mode == "📖 The Story":
    render_intro_story()

elif mode == "Crisis Simulator":
    if run_btn and not selected_countries:
        st.warning("Select at least one country in the sidebar to run the cascade.")
        st.session_state.pop("sim_impacts", None)
        _show_welcome()
    elif run_btn and selected_countries:
        all_impacts = {}
        for country_name in selected_countries:
            profile = load_profile(country_name.lower())
            impacts = run_cascade(graph, event_node, severity, country=profile)
            all_impacts[country_name] = impacts
        st.session_state["sim_impacts"] = all_impacts
        st.session_state["sim_countries"] = selected_countries

    if st.session_state.get("sim_impacts"):
        all_impacts = st.session_state["sim_impacts"]
        sim_countries = st.session_state.get("sim_countries", list(all_impacts.keys()))

        tab_map, tab_cards, tab_table, tab_action, tab_audience = st.tabs(
            ["🗺️ Cascade Map", "📊 Impact Cards", "📋 Detail Table", "🛰️ Action Watch", "📢 Audience Narratives"]
        )

        with tab_map:
            render_cascade_map(all_impacts, graph)

        with tab_cards:
            render_demo_headlines(sim_countries)
            render_impact_cards(all_impacts, graph)

        with tab_table:
            _render_detail_table(all_impacts, graph)

        with tab_action:
            action_country = st.selectbox(
                "Country to verify",
                options=sim_countries,
                key="sim_action_country",
            )
            use_live_action = st.toggle(
                "Use live action verification (calls Gemma 4 + ReliefWeb)",
                value=False,
                key="sim_action_live",
            )
            render_action_watch(
                country=action_country,
                response_plans=None,
                event_summary=f"{graph.get_node(event_node).label} crisis at severity {severity:.2f}" if run_btn else "",
                use_live_generation=use_live_action,
            )

        with tab_audience:
            audience_country = st.selectbox(
                "Select country for narratives",
                options=sim_countries,
                key="audience_country",
            )
            use_live = st.toggle("Use live Gemma 4 generation", value=False)
            render_audience_selector(
                country=audience_country.lower(),
                cascade_impacts=_impacts_to_dicts(all_impacts[audience_country]),
                use_live_generation=use_live,
            )
    elif not run_btn:
        _show_welcome()

elif mode == "Backtest Validation":
    render_backtest_overview()
    st.divider()

    if run_btn:
        with st.spinner("Running backtest..."):
            results = run_backtest(scenario)
        st.session_state["backtest_results"] = results
        st.session_state["backtest_scenario"] = scenario

    if st.session_state.get("backtest_results"):
        render_backtest_view(st.session_state["backtest_results"])
    else:
        st.info("Select a backtest scenario above and click **Run Backtest** in the sidebar to drill into per-country predictions vs actuals.")

elif mode == "Forward Predictions":
    if run_btn:
        pred_data = load_prediction(selected_pred)
        st.session_state["pred_data"] = pred_data

    if st.session_state.get("pred_data"):
        render_predictions_view(st.session_state["pred_data"])
    else:
        st.markdown("""
### Forward Predictions — What CascadeAI Sees Coming

These are **active cascades** CascadeAI is tracking right now. Each prediction includes:
- **Confidence level** based on validated model accuracy (38/39 backtests within range)
- **Verification window** — when the prediction can be checked
- **Data sources** — exactly where to look to verify

| Prediction | Status | Confidence |
|---|---|---|
| BEV Second Wave | ACTIVE | HIGH |
| EU Auto Cascade | ACTIVE | HIGH |
| Hormuz Closure | MONITORING | SCENARIO-BASED |
| Sudan Famine Spread | ACTIVE | VERY HIGH |

*Select a scenario and click **View Prediction** to see the full analysis.*
        """)

elif mode == "Compound Crisis":
    if run_btn:
        events = [
            {"node": event1_node, "severity": event1_sev},
            {"node": event2_node, "severity": event2_sev},
        ]
        profile = load_profile(compound_country.lower())
        impacts = run_compound_cascade(graph, events, country=profile)
        st.session_state["compound_impacts"] = {compound_country: impacts}
        st.session_state["compound_meta"] = {
            "country": compound_country,
            "label1": graph.get_node(event1_node).label,
            "label2": graph.get_node(event2_node).label,
        }

    if st.session_state.get("compound_impacts"):
        compound_impacts = st.session_state["compound_impacts"]
        meta = st.session_state["compound_meta"]

        st.subheader(f"Compound: {meta['label1']} + {meta['label2']}")
        st.caption(f"Target: {meta['country']}")

        tab_map, tab_cards, tab_table = st.tabs(["🗺️ Cascade Map", "📊 Impact Cards", "📋 Detail Table"])

        with tab_map:
            render_cascade_map(compound_impacts, graph)
        with tab_cards:
            render_impact_cards(compound_impacts, graph)
        with tab_table:
            _render_detail_table(compound_impacts, graph)
    else:
        st.info("Configure two simultaneous events and click **Run Compound** to see overlapping cascade paths.")

elif mode == "Event Detector (Gemma 4)":
    st.subheader("Event Detector — Natural Language Input")
    st.caption("Describe a crisis event in plain text. Gemma 4 will classify it and run the cascade.")

    event_text = st.text_area(
        "Describe the crisis event",
        value="Russia invades Ukraine on February 24, 2022, blocking Black Sea wheat exports and disrupting global fertilizer supply.",
        height=100,
    )
    detect_countries = st.multiselect(
        "Countries to analyze",
        options=available_countries(),
        default=["Kenya", "Ethiopia", "Somalia", "Egypt"],
        key="detect_countries",
    )
    detect_btn = st.button("Detect & Cascade", type="primary", width="stretch")

    if detect_btn and not detect_countries:
        st.warning("Select at least one country to analyze.")
        st.session_state.pop("detect_result", None)
    elif detect_btn and not event_text:
        st.warning("Enter a crisis description for Gemma 4 to classify.")
        st.session_state.pop("detect_result", None)
    elif detect_btn and event_text and detect_countries:
        from agents.event_detector import EventDetector
        from models.gemma_client import GemmaClient

        with st.spinner("Gemma 4 is classifying the event..."):
            client = GemmaClient()
            detector = EventDetector(client)
            event = detector.detect(event_text)

        all_impacts = {}
        for country_name in detect_countries:
            profile = load_profile(country_name.lower())
            impacts = run_cascade(graph, event.node, event.severity, country=profile)
            all_impacts[country_name] = impacts

        st.session_state["detect_result"] = {
            "event": event,
            "all_impacts": all_impacts,
            "countries": detect_countries,
        }

    if st.session_state.get("detect_result"):
        res = st.session_state["detect_result"]
        event = res["event"]
        all_impacts = res["all_impacts"]
        saved_countries = res["countries"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Detected Node", graph.get_node(event.node).label)
        col2.metric("Severity", f"{event.severity:.1f}")
        col3.metric("Region", event.region)
        st.info(f"**Summary:** {event.summary}")
        if event.secondary_nodes:
            st.caption(f"Secondary nodes: {', '.join(event.secondary_nodes)}")

        st.divider()

        tab_map, tab_cards, tab_table, tab_action, tab_audience = st.tabs(
            ["🗺️ Cascade Map", "📊 Impact Cards", "📋 Detail Table", "🛰️ Action Watch", "📢 Audience Narratives"]
        )

        with tab_map:
            render_cascade_map(all_impacts, graph)
        with tab_cards:
            render_demo_headlines(saved_countries)
            render_impact_cards(all_impacts, graph)
        with tab_table:
            _render_detail_table(all_impacts, graph)
        with tab_action:
            action_country_det = st.selectbox(
                "Country to verify",
                options=saved_countries,
                key="detect_action_country",
            )
            use_live_action_det = st.toggle(
                "Use live action verification (calls Gemma 4 + ReliefWeb)",
                value=False,
                key="detect_action_live",
            )
            render_action_watch(
                country=action_country_det,
                response_plans=None,
                event_summary=event.summary or "",
                use_live_generation=use_live_action_det,
            )
        with tab_audience:
            audience_country = st.selectbox(
                "Select country for narratives",
                options=saved_countries,
                key="detect_audience_country",
            )
            use_live = st.toggle("Use live Gemma 4 generation", value=False, key="detect_live")
            render_audience_selector(
                country=audience_country.lower(),
                cascade_impacts=_impacts_to_dicts(all_impacts[audience_country]),
                use_live_generation=use_live,
            )

else:  # Vision Analyst (Gemma 4 Multimodal)
    render_vision_analyst()

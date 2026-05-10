"""CascadeAI — Streamlit Dashboard

Run: streamlit run frontend/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: F401 — loads .env

from cascade.graph import CascadeGraph
from cascade.traversal import run_cascade, run_compound_cascade, CascadeImpact
from cascade.replay import run_backtest, available_scenarios
from data.profiles import load_profile, load_all_profiles, available_countries, get_profile_raw
from frontend.components.cascade_map import render_cascade_map
from frontend.components.impact_cards import render_impact_cards
from frontend.components.backtest_view import render_backtest_view
from frontend.components.audience_selector import render_audience_selector
from frontend.components.predictions_view import render_predictions_view
from data.predictions.loader import available_predictions, load_prediction


st.set_page_config(
    page_title="CascadeAI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {font-size: 2.4rem; font-weight: 700; margin-bottom: 0;}
    .sub-header {font-size: 1.1rem; color: #888; margin-top: -10px;}
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2a2a4a; border-radius: 10px; padding: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ── Helper functions (defined before use) ─────────────────────────

@st.cache_resource
def get_graph():
    return CascadeGraph.from_json()


def _render_detail_table(all_impacts: dict, graph: CascadeGraph):
    rows = []
    for country, impacts in all_impacts.items():
        for imp in impacts:
            rows.append({
                "Country": country,
                "Node": graph.get_node(imp.node).label,
                "Severity": f"{imp.severity:.4f}",
                "Delay (days)": imp.delay_days,
                "Path": " -> ".join(imp.path),
                "Seed": "Yes" if imp.is_seed else "",
            })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _impacts_to_dicts(impacts: list[CascadeImpact]) -> list[dict]:
    return [
        {"node": i.node, "severity": i.severity, "delay_days": i.delay_days, "path": i.path}
        for i in impacts
    ]


def _show_welcome():
    st.markdown("""
### Welcome to CascadeAI

**CascadeAI** predicts how a single crisis cascades across interconnected
global systems — energy, food, health, and displacement.

**Choose a mode from the sidebar:**

- **Crisis Simulator** — Select a crisis type and severity, see cascade impacts across countries
- **Backtest Validation** — Validate against real historical data (Ukraine 2022, Sudan 2023, Hormuz 2026)
- **Compound Crisis** — Model multiple simultaneous events with overlapping cascades
- **Event Detector** — Describe a crisis in natural language, Gemma 4 classifies and cascades it

---

*Built with Gemma 4 | 11 nodes, 18 edges, 8 countries | Open source*
    """)


# ── Load graph ────────────────────────────────────────────────────
graph = get_graph()


# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.title("🌍 CascadeAI")
    st.caption("Humanitarian Crisis Cascade Prediction")
    st.caption("Powered by Gemma 4")
    st.divider()

    mode = st.radio(
        "Mode",
        ["Crisis Simulator", "Backtest Validation", "Live Predictions", "Compound Crisis", "Event Detector (Gemma 4)"],
        index=0,
    )
    st.divider()

    if mode == "Crisis Simulator":
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
        run_btn = st.button("Run Cascade", type="primary", use_container_width=True)

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
        run_btn = st.button("Run Backtest", type="primary", use_container_width=True)

    elif mode == "Live Predictions":
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
        run_btn = st.button("View Prediction", type="primary", use_container_width=True)

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
        run_btn = st.button("Run Compound", type="primary", use_container_width=True)

    else:  # Event Detector
        st.subheader("Natural Language Event")
        st.caption("Describe a crisis and Gemma 4 will classify it")
        run_btn = False


# ── Main Content ──────────────────────────────────────────────────
st.markdown('<p class="main-header">CascadeAI</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Predicting how crises cascade across energy, food, health, and displacement — powered by Gemma 4</p>',
            unsafe_allow_html=True)
st.divider()


if mode == "Crisis Simulator":
    if run_btn and selected_countries:
        all_impacts = {}
        for country_name in selected_countries:
            profile = load_profile(country_name.lower())
            impacts = run_cascade(graph, event_node, severity, country=profile)
            all_impacts[country_name] = impacts

        tab_map, tab_cards, tab_table, tab_audience = st.tabs(
            ["🗺️ Cascade Map", "📊 Impact Cards", "📋 Detail Table", "📢 Audience Narratives"]
        )

        with tab_map:
            render_cascade_map(all_impacts, graph)

        with tab_cards:
            render_impact_cards(all_impacts, graph)

        with tab_table:
            _render_detail_table(all_impacts, graph)

        with tab_audience:
            audience_country = st.selectbox(
                "Select country for narratives",
                options=selected_countries,
                key="audience_country",
            )
            use_live = st.toggle("Use live Gemma 4 generation", value=False)
            render_audience_selector(
                country=audience_country.lower(),
                cascade_impacts=_impacts_to_dicts(all_impacts[audience_country]),
                use_live_generation=use_live,
            )
    else:
        _show_welcome()

elif mode == "Backtest Validation":
    if run_btn:
        with st.spinner("Running backtest..."):
            results = run_backtest(scenario)
        render_backtest_view(results)
    else:
        st.info("Select a backtest scenario and click **Run Backtest** to validate CascadeAI against real historical data.")

elif mode == "Live Predictions":
    if run_btn:
        pred_data = load_prediction(selected_pred)
        render_predictions_view(pred_data)
    else:
        st.markdown("""
### Live Predictions — What CascadeAI Sees Coming

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

        st.subheader(f"Compound: {graph.get_node(event1_node).label} + {graph.get_node(event2_node).label}")
        st.caption(f"Target: {compound_country}")

        tab_map, tab_cards, tab_table = st.tabs(["🗺️ Cascade Map", "📊 Impact Cards", "📋 Detail Table"])

        compound_impacts = {compound_country: impacts}
        with tab_map:
            render_cascade_map(compound_impacts, graph)
        with tab_cards:
            render_impact_cards(compound_impacts, graph)
        with tab_table:
            _render_detail_table(compound_impacts, graph)
    else:
        st.info("Configure two simultaneous events and click **Run Compound** to see overlapping cascade paths.")

else:  # Event Detector
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
    detect_btn = st.button("Detect & Cascade", type="primary", use_container_width=True)

    if detect_btn and event_text:
        from agents.event_detector import EventDetector
        from models.gemma_client import GemmaClient

        with st.spinner("Gemma 4 is classifying the event..."):
            client = GemmaClient()
            detector = EventDetector(client)
            event = detector.detect(event_text)

        col1, col2, col3 = st.columns(3)
        col1.metric("Detected Node", graph.get_node(event.node).label)
        col2.metric("Severity", f"{event.severity:.1f}")
        col3.metric("Region", event.region)
        st.info(f"**Summary:** {event.summary}")
        if event.secondary_nodes:
            st.caption(f"Secondary nodes: {', '.join(event.secondary_nodes)}")

        st.divider()

        all_impacts = {}
        for country_name in detect_countries:
            profile = load_profile(country_name.lower())
            impacts = run_cascade(graph, event.node, event.severity, country=profile)
            all_impacts[country_name] = impacts

        tab_map, tab_cards, tab_table, tab_audience = st.tabs(
            ["🗺️ Cascade Map", "📊 Impact Cards", "📋 Detail Table", "📢 Audience Narratives"]
        )

        with tab_map:
            render_cascade_map(all_impacts, graph)
        with tab_cards:
            render_impact_cards(all_impacts, graph)
        with tab_table:
            _render_detail_table(all_impacts, graph)
        with tab_audience:
            audience_country = st.selectbox(
                "Select country for narratives",
                options=detect_countries,
                key="detect_audience_country",
            )
            use_live = st.toggle("Use live Gemma 4 generation", value=False, key="detect_live")
            render_audience_selector(
                country=audience_country.lower(),
                cascade_impacts=_impacts_to_dicts(all_impacts[audience_country]),
                use_live_generation=use_live,
            )

"""Predictions View component — displays forward-looking predictions
with confidence levels, timelines, and verification sources."""

from __future__ import annotations

import streamlit as st
import pandas as pd


CONFIDENCE_COLORS = {
    "VERY HIGH":               "#ef4444",
    "HIGH":                    "#f97316",
    "MEDIUM-HIGH":             "#eab308",
    "MEDIUM":                  "#22c55e",
    "SCENARIO-BASED (IF/THEN)":"#a78bfa",
}

STATUS_COLORS = {
    "ACTIVE":      ("#14532d", "#22c55e"),
    "MONITORING":  ("#1e3a5f", "#60a5fa"),
    "WATCH":       ("#78350f", "#f97316"),
}


def _conf_badge(confidence: str) -> str:
    color = CONFIDENCE_COLORS.get(confidence, "#64748b")
    return (
        f"<span style='background:{color}22; color:{color}; font-size:0.72rem; font-weight:700;"
        f"letter-spacing:0.06em; padding:3px 10px; border-radius:20px; border:1px solid {color}55;'>"
        f"{confidence}</span>"
    )


def _status_badge(status: str) -> str:
    key = status.split(" — ")[0].upper()
    bg, fg = STATUS_COLORS.get(key, ("#1e293b", "#94a3b8"))
    label = status.split(" — ")[0]
    return (
        f"<span style='background:{bg}; color:{fg}; font-size:0.72rem; font-weight:700;"
        f"letter-spacing:0.06em; padding:3px 10px; border-radius:20px; border:1px solid {fg}55;'>"
        f"● {label}</span>"
    )


def render_predictions_view(prediction: dict):
    """Render a single forward-looking prediction scenario."""
    status = prediction.get("status", "UNKNOWN")
    confidence = prediction.get("confidence", "UNKNOWN")
    conf_color = CONFIDENCE_COLORS.get(confidence, "#64748b")

    st.markdown(
        f"<h2 style='color:#e2e8f0; margin-bottom:6px;'>🔭 {prediction['name']}</h2>"
        f"<div style='display:flex; gap:8px; align-items:center; margin-bottom:16px;'>"
        f"{_status_badge(status)} {_conf_badge(confidence)}"
        f"<span style='color:#64748b; font-size:0.8rem;'>· Verify by: "
        f"<b style='color:#94a3b8;'>{prediction.get('verification_window', 'TBD')}</b></span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.info(f"**Trigger:** {prediction['trigger']['description']}")

    if "reasoning" in prediction:
        with st.expander("📖 CascadeAI Reasoning"):
            st.markdown(prediction["reasoning"])

    st.divider()

    if "scenario_stages" in prediction:
        _render_scenario_stages(prediction["scenario_stages"])
        st.divider()

    predictions_list = prediction.get("predictions", prediction.get("country_predictions", []))
    if predictions_list:
        _render_predictions_table(predictions_list, prediction)

    if "compound_prediction" in prediction:
        st.divider()
        cp = prediction["compound_prediction"]
        st.warning(f"**COMPOUND PREDICTION:** {cp['description']}")
        st.markdown(f"*{cp['prediction']}*")
        st.caption(f"Confidence: {cp.get('confidence', 'N/A')} | Mechanism: {cp.get('mechanism', 'N/A')}")

    if "key_insight" in prediction:
        st.divider()
        st.success(f"**Key Insight:** {prediction['key_insight']}")

    if "demo_moment" in prediction:
        with st.expander("🎬 Demo Script"):
            st.markdown(f"*{prediction['demo_moment']}*")


def _render_scenario_stages(stages: dict):
    """Render scenario stages as a timeline."""
    st.markdown("<h4 style='color:#94a3b8; letter-spacing:0.05em; font-size:0.8rem;'>CASCADE STAGES</h4>", unsafe_allow_html=True)
    stage_list = list(stages.items())
    cols = st.columns(len(stage_list))
    colors = ["#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd", "#ddd6fe"]
    for i, (stage_key, stage) in enumerate(stage_list):
        color = colors[i % len(colors)]
        connector = "" if i == len(stage_list) - 1 else ""
        with cols[i]:
            st.markdown(
                f"<div style='background:#1e1b4b55; border:1px solid {color}44; border-top:3px solid {color};"
                f"border-radius:8px; padding:12px; text-align:center;'>"
                f"<div style='font-size:0.72rem; font-weight:700; color:{color}; letter-spacing:0.06em;'>{stage['timeline']}</div>"
                f"<div style='font-size:0.82rem; font-weight:600; color:#e2e8f0; margin:4px 0;'>{stage_key.replace('_', ' ').title()}</div>"
                f"<div style='font-size:0.74rem; color:#94a3b8;'>{stage['prediction']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_predictions_table(predictions: list, scenario: dict):
    """Render predictions as detailed cards."""
    st.markdown("### Predictions")

    for pred in predictions:
        if isinstance(pred, dict) and "predictions" in pred:
            st.markdown(f"#### {pred['country'].replace('_', ' ').title()}")
            for sub in pred["predictions"]:
                _render_single_prediction(sub)
        else:
            _render_single_prediction(pred)


def _render_single_prediction(pred: dict):
    """Render a single prediction card."""
    pred_id = pred.get("id", "")
    country = pred.get("country", "").replace("_", " ").title()
    node = pred.get("node", "").upper()
    confidence = pred.get("confidence", "N/A")
    prediction_text = pred.get("prediction", "")
    mechanism = pred.get("mechanism", "")
    verify = pred.get("data_source_to_verify", "")
    delay = pred.get("delay_from_trigger", "")

    conf_color = CONFIDENCE_COLORS.get(confidence, "#64748b")
    id_part = f"<span style='color:#475569; font-size:0.72rem;'>[{pred_id}]</span> " if pred_id else ""
    country_part = f"<b style='color:#e2e8f0;'>{country}</b> " if country else ""
    node_part = f"<span style='background:#1e293b; color:#94a3b8; font-size:0.72rem; padding:2px 7px; border-radius:4px;'>{node}</span>" if node else ""

    meta_parts = []
    if delay:
        meta_parts.append(f"⏱ {delay}")
    if verify:
        meta_parts.append(f"🔍 {verify[:55]}…" if len(verify) > 55 else f"🔍 {verify}")
    if mechanism:
        meta_parts.append(f"⚙ {mechanism}")

    st.markdown(
        f"<div style='background:#0f172a; border:1px solid #1e293b; border-left:3px solid {conf_color};"
        f"border-radius:8px; padding:14px 16px; margin-bottom:10px;'>"
        f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>"
        f"<span>{id_part}{country_part}{node_part}</span>"
        f"{_conf_badge(confidence)}"
        f"</div>"
        f"<div style='color:#cbd5e1; font-size:0.85rem; margin-bottom:10px;'>{prediction_text}</div>"
        f"<div style='display:flex; flex-wrap:wrap; gap:10px;'>"
        + "".join(
            f"<span style='color:#64748b; font-size:0.75rem;'>{p}</span>"
            for p in meta_parts
        )
        + f"</div></div>",
        unsafe_allow_html=True,
    )

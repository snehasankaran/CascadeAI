"""Predictions View component — displays forward-looking predictions
with confidence levels, timelines, and verification sources."""

from __future__ import annotations

import streamlit as st
import pandas as pd


CONFIDENCE_COLORS = {
    "VERY HIGH": "#ff4444",
    "HIGH": "#ff8800",
    "MEDIUM-HIGH": "#ffaa00",
    "MEDIUM": "#ffcc00",
    "SCENARIO-BASED (IF/THEN)": "#6644ff",
}


def render_predictions_view(prediction: dict):
    """Render a single forward-looking prediction scenario."""
    st.subheader(prediction["name"])

    status = prediction.get("status", "UNKNOWN")
    confidence = prediction.get("confidence", "UNKNOWN")

    col1, col2, col3 = st.columns(3)
    col1.metric("Status", status.split(" — ")[0] if " — " in status else status)
    col2.metric("Confidence", confidence)
    col3.metric("Verify By", prediction.get("verification_window", "TBD"))

    st.info(f"**Trigger:** {prediction['trigger']['description']}")

    if "reasoning" in prediction:
        with st.expander("CascadeAI Reasoning"):
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
        with st.expander("Demo Script"):
            st.markdown(f"*{prediction['demo_moment']}*")


def _render_scenario_stages(stages: dict):
    """Render scenario stages as a timeline."""
    st.markdown("### Cascade Stages")
    cols = st.columns(len(stages))
    for i, (stage_key, stage) in enumerate(stages.items()):
        with cols[i]:
            st.markdown(f"**{stage['timeline']}**")
            st.markdown(f"*{stage_key.replace('_', ' ').title()}*")
            st.caption(stage["prediction"])


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

    conf_color = CONFIDENCE_COLORS.get(confidence, "#888888")

    header = f"**[{pred_id}]** " if pred_id else ""
    header += f"**{country}** | {node}" if country else f"**{node}**"

    st.markdown(f"{header}")
    st.markdown(f"> {prediction_text}")

    detail_cols = st.columns(3)
    detail_cols[0].caption(f"Confidence: **{confidence}**")
    if delay:
        detail_cols[1].caption(f"Timeline: {delay}")
    if verify:
        detail_cols[2].caption(f"Verify: {verify[:60]}...")

    if mechanism:
        st.caption(f"Mechanism: `{mechanism}`")

    st.markdown("---")

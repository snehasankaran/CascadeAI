"""Backtest View component — shows predicted vs actual comparison tables
for historical crisis validation. Enhanced for BEV crash scenario with
OEM write-down data and upstream policy triggers."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import pandas as pd

from cascade.replay import BacktestResult


BACKTEST_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "backtest"


def render_backtest_view(results: list[BacktestResult]):
    """Render the full backtest comparison view."""
    if not results:
        st.warning("No backtest results to display.")
        return

    first = results[0]
    st.markdown(
        f"<h2 style='color:#e2e8f0; margin-bottom:2px;'>📊 {first.crisis_name}</h2>"
        f"<p style='color:#64748b; font-size:0.85rem; margin-top:0;'>"
        f"Trigger: {first.trigger_event} &nbsp;·&nbsp; {first.trigger_date}</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    total_comparisons = sum(len(r.comparisons) for r in results)
    within_range = sum(
        1 for r in results for c in r.comparisons if c.accuracy == "within_range"
    )
    accuracy_pct = (within_range / total_comparisons * 100) if total_comparisons > 0 else 0

    acc_color = "#22c55e" if accuracy_pct >= 80 else "#f97316" if accuracy_pct >= 60 else "#ef4444"
    col1, col2, col3 = st.columns(3)
    col1.metric("Countries Tested", len(results))
    col2.metric("Predictions", total_comparisons)
    col3.metric("Within Range", f"{accuracy_pct:.0f}%")

    scenario_data = _load_scenario_data(first.crisis_name)
    if scenario_data:
        _render_upstream_context(scenario_data)

    st.divider()

    for result in results:
        _render_country_backtest(result, scenario_data)


def _load_scenario_data(crisis_name: str) -> dict | None:
    """Load the raw scenario JSON for enhanced rendering."""
    for path in BACKTEST_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("name") == crisis_name:
                return data
        except Exception:
            continue
    return None


def _render_upstream_context(scenario: dict):
    """Render OEM write-downs, policy triggers, and tier-1 impact if present."""

    if "oem_write_downs" in scenario:
        st.divider()
        st.markdown("### OEM Financial Impact")

        writedowns = scenario["oem_write_downs"]
        total = writedowns.pop("total_industry", None)

        cols = st.columns(min(len(writedowns), 5))
        for i, (oem, data) in enumerate(writedowns.items()):
            if isinstance(data, dict):
                cols[i % len(cols)].metric(
                    oem.upper(),
                    data.get("amount", "N/A"),
                    delta=data.get("reason", "")[:50],
                    delta_color="inverse",
                )

        if total:
            st.error(f"**Total OEM Write-Downs:** {total}")

    if "tier1_supplier_impact" in scenario:
        with st.expander("Tier-1 Supplier Impact"):
            tier1 = scenario["tier1_supplier_impact"]
            for supplier, impact in tier1.items():
                if supplier != "total_tier1_jobs_lost":
                    st.markdown(f"- **{supplier.title()}:** {impact}")
            if "total_tier1_jobs_lost" in tier1:
                st.warning(f"**Total Tier-1 Jobs Lost:** {tier1['total_tier1_jobs_lost']}")

    if "upstream_policy_triggers" in scenario:
        with st.expander("US Policy Triggers (Root Cause)"):
            for trigger_name, trigger_data in scenario["upstream_policy_triggers"].items():
                if isinstance(trigger_data, dict):
                    st.markdown(f"**{trigger_name.replace('_', ' ').title()}** ({trigger_data.get('date', 'N/A')})")
                    st.caption(trigger_data.get("description", ""))
                    for k, v in trigger_data.items():
                        if k not in ("date", "description"):
                            st.markdown(f"- {k.replace('_', ' ').title()}: `{v}`")
                    st.markdown("---")

    if "global_actuals" in scenario:
        ga = scenario["global_actuals"]
        if "cascade_timeline" in ga:
            with st.expander("Cascade Timeline"):
                for day, event in ga["cascade_timeline"].items():
                    st.markdown(f"**{day.replace('_', ' ').title()}:** {event}")


def _render_country_backtest(result: BacktestResult, scenario_data: dict | None = None):
    """Render backtest results for a single country."""
    country_title = result.country.replace("_", " ").title()

    st.markdown(
        f"<div style='background:linear-gradient(90deg,#1e1b4b,#0f172a); "
        f"border-left:4px solid #6366f1; border-radius:8px; padding:10px 16px; margin-bottom:8px;'>"
        f"<span style='font-size:1.05rem; font-weight:700; color:#e2e8f0;'>🌍 {country_title}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    cascade_path = None
    if scenario_data:
        for cd in scenario_data.get("countries", []):
            if cd.get("country") == result.country:
                cascade_path = cd.get("cascade_path")
                break
    if cascade_path:
        st.info(f"**Cascade Path:** {cascade_path}")

    if result.comparisons:
        rows = []
        for c in result.comparisons:
            if c.accuracy == "within_range":
                accuracy_icon = "✅ Within Range"
            elif c.accuracy == "close":
                accuracy_icon = "🟡 Close"
            else:
                accuracy_icon = "❌ Miss"
            rows.append({
                "Node": c.node.upper() if c.node else "",
                "Indicator": c.indicator,
                "CascadeAI Predicted": c.predicted,
                "Actual Outcome": c.actual,
                "Accuracy": accuracy_icon,
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander(f"BFS Cascade Detail — {country_title}"):
        for imp in result.cascade_impacts:
            seed_badge = (
                "<span style='background:#312e81;color:#a5b4fc;font-size:0.65rem;"
                "padding:1px 6px;border-radius:4px;margin-left:6px;'>SEED</span>"
                if imp.is_seed else ""
            )
            sev_color = "#ef4444" if imp.severity >= 0.8 else "#f97316" if imp.severity >= 0.6 else "#eab308" if imp.severity >= 0.4 else "#22c55e"
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center; "
                f"font-size:0.78rem; color:#cbd5e1; padding:3px 0; border-bottom:1px solid #1e293b;'>"
                f"<span style='color:#94a3b8;'>{imp.node}</span>"
                f"<span style='color:{sev_color}; font-weight:600;'>{imp.severity:.4f}"
                f"<span style='color:#475569;font-weight:400;'> · {imp.delay_days}d</span></span>"
                f"{seed_badge}</div>",
                unsafe_allow_html=True,
            )

    st.divider()

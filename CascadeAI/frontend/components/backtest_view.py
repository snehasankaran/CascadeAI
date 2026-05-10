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
    st.subheader(f"Backtest: {first.crisis_name}")
    st.caption(f"Trigger: {first.trigger_event} ({first.trigger_date})")
    st.divider()

    total_comparisons = sum(len(r.comparisons) for r in results)
    within_range = sum(
        1 for r in results for c in r.comparisons if c.accuracy == "within_range"
    )
    accuracy_pct = (within_range / total_comparisons * 100) if total_comparisons > 0 else 0

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
    st.markdown(f"### {result.country.replace('_', ' ').title()}")

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
            accuracy_icon = (
                "Within Range" if c.accuracy == "within_range"
                else "Close" if c.accuracy == "close"
                else "Miss"
            )
            rows.append({
                "Node": c.node.upper() if c.node else "",
                "Indicator": c.indicator,
                "CascadeAI Predicted": c.predicted,
                "Actual Outcome": c.actual,
                "Accuracy": accuracy_icon,
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander(f"BFS Cascade Detail for {result.country.replace('_', ' ').title()}"):
        for imp in result.cascade_impacts:
            seed = " [SEED]" if imp.is_seed else ""
            st.text(
                f"  {imp.node:15s} severity={imp.severity:.4f}  "
                f"delay={imp.delay_days:3d}d  "
                f"path={' -> '.join(imp.path)}{seed}"
            )

    st.divider()

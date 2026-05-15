"""Backtest Overview component — single-screen scorecard of every backtest
scenario currently shipped in ``data/backtest/``.

Used as the headline view at the top of the Backtest Validation mode so a
demo recording captures the full retrospective record (Ukraine 2022,
Sudan 2023-2026, Hormuz 2026, BEV Crash 2025) in one pixel-accurate
screenshot — no Canva overlay required.

Every cell is computed by reading the source JSON: counts of predictions
classified as ``within_range`` vs total predictions per scenario. If a
scenario file is missing or malformed the row is silently dropped so the
component is safe to render even when partial data ships.
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


_BACKTEST_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "backtest"

# Stable display order for the scorecard. Filenames must match the keys.
_SCENARIO_ORDER = [
    "ukraine_2022",
    "sudan_2023",
    "hormuz_2026",
    "bev_crash_2025",
]

# Short, demo-ready descriptions of each trigger. Falls back to the
# scenario's own description if a key is missing.
_TRIGGER_LABELS = {
    "ukraine_2022": "Russia invasion → wheat / fertilizer shock",
    "sudan_2023":   "Civil war → cascading collapse",
    "hormuz_2026":  "Shipping disruption → energy → fertilizer surge",
    "bev_crash_2025": "US tariffs → mineral price collapse",
}


def render_backtest_overview():
    """Render the four-scenario scorecard. Designed to be the first thing
    visible when the user lands on Backtest Validation mode."""

    rows = [r for r in (_load_scenario(s) for s in _SCENARIO_ORDER) if r is not None]
    if not rows:
        st.info("No backtest scenarios found in `data/backtest/`.")
        return

    total_within = sum(r["within_range"] for r in rows)
    total_preds  = sum(r["total"] for r in rows)
    total_countries = sum(r["countries"] for r in rows)

    _render_header(total_within, total_preds, total_countries, len(rows))
    _render_scorecard_grid(rows)
    _render_footer_caption()


# =============================================================================
# Internals
# =============================================================================

def _load_scenario(scenario_key: str) -> dict | None:
    path = _BACKTEST_DIR / f"{scenario_key}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    countries = data.get("countries", [])
    total = 0
    within_range = 0
    country_names = []
    for c in countries:
        country_names.append(c.get("country", "").title())
        for actual in c.get("actuals", []):
            total += 1
            if actual.get("accuracy") == "within_range":
                within_range += 1

    return {
        "key": scenario_key,
        "name": data.get("name", scenario_key),
        "trigger": _TRIGGER_LABELS.get(scenario_key, data.get("context", "")[:80]),
        "trigger_date": data.get("trigger", {}).get("date", ""),
        "country_names": country_names,
        "countries": len(country_names),
        "within_range": within_range,
        "total": total,
        "accuracy_pct": (within_range / total * 100) if total else 0,
    }


def _render_header(within: int, total: int, n_countries: int, n_scenarios: int):
    pct = (within / total * 100) if total else 0
    st.markdown(
        f"""
<div style="
    margin: 8px 0 18px;
    padding: 18px 22px;
    background: linear-gradient(135deg, rgba(34,197,94,0.10) 0%, rgba(15,23,42,0) 70%);
    border-left: 4px solid #22c55e;
    border-radius: 12px;
">
  <div style="font-size:0.72rem; color:#94a3b8; letter-spacing:0.18em;
              text-transform:uppercase; margin-bottom:8px;">Backtest record · all scenarios</div>
  <div style="display:flex; align-items:baseline; gap:18px; flex-wrap:wrap;">
    <div style="font-size:2.6rem; font-weight:900; color:#22c55e; line-height:1;">
      {within} <span style="color:#475569; font-weight:600;">/</span> {total}
    </div>
    <div style="font-size:1.05rem; color:#cbd5e1; font-weight:500;">
      retrospective forecasts within predefined scenario ranges<br>
      <span style="font-size:0.85rem; color:#94a3b8;">
        across {n_scenarios} crises · {n_countries} countries · {pct:.0f}% within-range
      </span>
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_scorecard_grid(rows: list[dict]):
    cols = st.columns(len(rows))
    for col, row in zip(cols, rows):
        accent = "#22c55e" if row["accuracy_pct"] == 100 else "#f97316" if row["accuracy_pct"] >= 80 else "#ef4444"
        countries_str = ", ".join(row["country_names"][:4])
        if len(row["country_names"]) > 4:
            countries_str += ", …"

        html = f"""
<div style="
    background: linear-gradient(160deg, rgba(15,23,42,0.95) 0%, #0b1426 100%);
    border: 1px solid #1e293b;
    border-top: 3px solid {accent};
    border-radius: 12px;
    padding: 14px 16px 12px;
    height: 100%;
    min-height: 175px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
">
  <div>
    <div style="font-size:0.7rem; color:{accent}; letter-spacing:0.14em;
                text-transform:uppercase; font-weight:700; margin-bottom:4px;">
      {row['trigger_date']}
    </div>
    <div style="font-size:1.02rem; font-weight:700; color:#e2e8f0; line-height:1.2;
                margin-bottom:6px;">
      {row['name']}
    </div>
    <div style="font-size:0.74rem; color:#94a3b8; line-height:1.4; margin-bottom:10px;">
      {row['trigger']}
    </div>
  </div>
  <div>
    <div style="font-size:0.62rem; color:#64748b; letter-spacing:0.12em;
                text-transform:uppercase; margin-bottom:2px;">Countries</div>
    <div style="font-size:0.74rem; color:#cbd5e1; line-height:1.3; margin-bottom:8px;">
      {countries_str}
    </div>
    <div style="display:flex; align-items:baseline; justify-content:space-between;
                padding-top:8px; border-top:1px solid #1e293b;">
      <div>
        <div style="font-size:0.62rem; color:#64748b; letter-spacing:0.10em;
                    text-transform:uppercase;">Within range</div>
        <div style="font-size:1.8rem; font-weight:900; color:{accent}; line-height:1;">
          {row['within_range']}<span style="color:#475569; font-weight:600;">/{row['total']}</span>
        </div>
      </div>
      <div style="font-size:1.0rem; font-weight:700; color:{accent};">{row['accuracy_pct']:.0f}%</div>
    </div>
  </div>
</div>
"""
        with col:
            st.markdown(html, unsafe_allow_html=True)


def _render_footer_caption():
    st.markdown(
        '<div style="text-align:center; font-size:0.74rem; color:#64748b; '
        'margin: 12px 0 22px;">Computed live from <code>data/backtest/*.json</code> · '
        'every prediction tagged <code>within_range</code> in the source data counts as a hit.</div>',
        unsafe_allow_html=True,
    )

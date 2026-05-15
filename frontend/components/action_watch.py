"""Action Watch component — renders the Action Verifier output.

Closes the loop on the cascade pipeline: shows which Dispatcher-recommended
actions are already being executed on the ground (per live ReliefWeb / ACLED
data) and which are blind spots no responder has covered yet.

Demo mode shows realistic placeholder verifications so the video demo works
without a live Gemma 4 call. Live mode hits the ActionVerifier agent.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from agents.action_verifier import ActionVerifier
from data.profiles import get_profile_raw


STATUS_META = {
    "in_progress": {
        "label": "IN PROGRESS",
        "icon": "✅",
        "fg": "#22c55e",
        "bg": "rgba(34, 197, 94, 0.12)",
        "border": "rgba(34, 197, 94, 0.35)",
    },
    "partial": {
        "label": "PARTIAL",
        "icon": "⚠️",
        "fg": "#f59e0b",
        "bg": "rgba(245, 158, 11, 0.12)",
        "border": "rgba(245, 158, 11, 0.35)",
    },
    "gap": {
        "label": "BLIND SPOT",
        "icon": "🚨",
        "fg": "#ef4444",
        "bg": "rgba(239, 68, 68, 0.12)",
        "border": "rgba(239, 68, 68, 0.35)",
    },
}


# Pre-built realistic verifications keyed by country — used when live
# generation is off so the demo always shows compelling content.
PLACEHOLDER_VERIFICATIONS: dict[str, dict] = {
    "kenya": {
        "verifications": [
            {
                "stakeholder": "WFP",
                "action": "Pre-position 60,000 MT of wheat reserves at Mombasa port",
                "status": "in_progress",
                "evidence": "ReliefWeb · GIEWS Country Brief: Kenya 04-May-2026 — maize prices elevated up to +15% YoY on high fuel costs; pre-positioning across ASAL pipeline reported active.",
                "confidence": "high",
            },
            {
                "stakeholder": "WFP",
                "action": "Scale up cash transfers to 1.2M food-insecure households in ASAL counties",
                "status": "partial",
                "evidence": "ReliefWeb · IPC Acute Food Insecurity Analysis Jan–Dec 2026 (12 Mar) — 3.3M in ASAL at IPC 3+, cash response constrained by underfunding; coverage gap in Mandera and Wajir.",
                "confidence": "high",
            },
            {
                "stakeholder": "WHO",
                "action": "Activate health-cluster surge for IPC Phase 5 acute malnutrition in Turkana",
                "status": "in_progress",
                "evidence": "ReliefWeb · IPC Jan–Dec 2026 — IPC Phase 5 (Extremely Critical) confirmed in Mandera, North Horr/Chalbi (Marsabit) and Turkana South/East; nutrition surge documented in those counties.",
                "confidence": "high",
            },
            {
                "stakeholder": "WHO",
                "action": "Pre-position cholera ORS and RUTF supplies in 14 sub-counties",
                "status": "gap",
                "evidence": "No matching pre-positioning evidence in last 30 days of ReliefWeb Kenya reporting; outreach explicitly flagged as limited by funding.",
                "confidence": "medium",
            },
            {
                "stakeholder": "UNHCR",
                "action": "Open Sudanese refugee corridor planning with Ethiopia and South Sudan",
                "status": "gap",
                "evidence": "ReliefWeb · Sudan Regional Refugee Response Plan 2026 — lists Egypt, Chad, Ethiopia, Libya, South Sudan, CAR, Uganda as asylum countries; Kenya is NOT among them despite documented spillover.",
                "confidence": "high",
            },
            {
                "stakeholder": "UNHCR",
                "action": "Expand Dadaab and Kakuma camp WASH capacity by 25%",
                "status": "partial",
                "evidence": "ReliefWeb · IFRC Kenya Complex Emergency Operation Update MDRKE068 — refugee response includes 429K refugees at IPC 3+; WASH expansion partial.",
                "confidence": "medium",
            },
            {
                "stakeholder": "Government of Kenya",
                "action": "Suspend wheat and fertilizer import duties for 6 months",
                "status": "in_progress",
                "evidence": "ReliefWeb · GIEWS Kenya 04-May-2026 — Treasury duty-relief measures referenced alongside elevated staple prices.",
                "confidence": "medium",
            },
            {
                "stakeholder": "Government of Kenya",
                "action": "Release strategic grain reserves to stabilise maize prices",
                "status": "gap",
                "evidence": "No NCPB release reported in May 2026 ReliefWeb feed; maize prices remain +15% YoY (GIEWS 04-May-2026).",
                "confidence": "high",
            },
        ],
        "coverage_summary": (
            "Of 8 recommended actions across WFP, WHO, UNHCR and the Government of Kenya, 3 are clearly "
            "in progress, 2 are partial, and 3 are blind spots. The most critical blind spot is the "
            "absence of a Kenya-side Sudanese refugee corridor plan: the 2026 Sudan Regional Refugee "
            "Response Plan lists seven asylum countries but Kenya is not among them, even as the "
            "spillover from the world's largest displacement crisis (4.3–4.4M refugees) reaches East "
            "African borders."
        ),
        "evidence_sources": [
            {
                "type": "reliefweb_report",
                "title": "GIEWS Country Brief: Kenya 04-May-2026",
                "date": "2026-05-04",
                "org": "FAO GIEWS",
                "url": "https://reliefweb.int/report/kenya/giews-country-brief-kenya-04-may-2026",
            },
            {
                "type": "reliefweb_report",
                "title": "Kenya: Climatic shocks drive Extremely Critical acute malnutrition — IPC Acute Food Insecurity and Acute Malnutrition Analysis (January – December 2026)",
                "date": "2026-03-12",
                "org": "IPC Global Partners",
                "url": "https://reliefweb.int/node/4202581",
            },
            {
                "type": "reliefweb_report",
                "title": "Kenya | Complex Emergency Operation Update MDRKE068",
                "date": "2026-04-30",
                "org": "IFRC",
                "url": "https://reliefweb.int/report/kenya/kenya-complex-emergency-operation-update-mdrke068",
            },
            {
                "type": "reliefweb_plan",
                "title": "Sudan Regional Refugee Response Plan 2026",
                "date": "2026-01-15",
                "org": "UNHCR",
                "url": "https://reliefweb.int/report/sudan/sudan-regional-refugee-response-plan-2026",
            },
            {
                "type": "acled_summary",
                "title": "ACLED 30-day summary · East Africa",
                "events_30d": 450,
                "fatalities_30d": 2500,
                "active_conflicts": ["Sudan civil war (SAF vs RSF)", "Somalia (Al-Shabaab)", "Ethiopia (residual Tigray)"],
            },
        ],
    },
    "ethiopia": {
        "verifications": [
            {
                "stakeholder": "WFP",
                "action": "Restart Tigray food convoys with 40,000 MT monthly delivery",
                "status": "partial",
                "evidence": "ReliefWeb · Sudan Regional Refugee Response Plan 2026 — Ethiopia cited among 7 asylum countries with constrained humanitarian access; food pipeline below cluster target.",
                "confidence": "high",
            },
            {
                "stakeholder": "WHO",
                "action": "Cholera vaccination campaign in Amhara and Oromia border districts",
                "status": "in_progress",
                "evidence": "ReliefWeb · 2026 Sudan Situation RRP — cholera outbreaks in Ethiopia linked to Sudan outbreak documented since 2025; vaccination campaigns active in border woredas.",
                "confidence": "high",
            },
            {
                "stakeholder": "UNHCR",
                "action": "Register Sudanese arrivals at Metema and Kurmuk crossings",
                "status": "in_progress",
                "evidence": "ReliefWeb · UNHCR Sudan – Ethiopian Refugees in Sudan Dashboard (31 Mar 2026) — bilateral registration flows active; biometric screening operating at Metema.",
                "confidence": "high",
            },
            {
                "stakeholder": "UNHCR",
                "action": "Pre-position shelter kits for projected 120K additional arrivals",
                "status": "gap",
                "evidence": "ReliefWeb · Sudan RRP 2026 — total $1.6B regional ask coordinated by 123 partners; shelter cluster funding documented well below requirement, no Ethiopia-specific pre-positioning report.",
                "confidence": "medium",
            },
            {
                "stakeholder": "Government of Ethiopia",
                "action": "Expand productive safety net programme (PSNP) by 1.5M beneficiaries",
                "status": "partial",
                "evidence": "PSNP expansion announced by World Bank earlier in 2026; rollout pending — no May 2026 ReliefWeb confirmation of expanded caseload.",
                "confidence": "medium",
            },
        ],
        "coverage_summary": (
            "Ethiopia shows strong coverage on cross-border registration and cholera vaccination but "
            "lags on shelter pre-positioning for projected Sudanese arrivals. The shelter cluster blind "
            "spot is the highest-risk gap given Ethiopia is one of seven named asylum countries in the "
            "2026 Sudan RRP yet shelter funding is documented below requirement."
        ),
        "evidence_sources": [
            {
                "type": "reliefweb_plan",
                "title": "Sudan Regional Refugee Response Plan 2026",
                "date": "2026-01-15",
                "org": "UNHCR",
                "url": "https://reliefweb.int/report/sudan/sudan-regional-refugee-response-plan-2026",
            },
            {
                "type": "reliefweb_report",
                "title": "UNHCR Sudan — Ethiopian Refugees in Sudan Dashboard as of 31 March 2026",
                "date": "2026-03-31",
                "org": "UNHCR",
                "url": "https://reliefweb.int/report/sudan/unhcr-sudan-ethiopian-refugees-sudan-dashboard-31-march-2026",
            },
            {
                "type": "acled_summary",
                "title": "ACLED 30-day summary · East Africa",
                "events_30d": 450,
                "fatalities_30d": 2500,
                "active_conflicts": ["Sudan civil war (SAF vs RSF)", "Somalia (Al-Shabaab)", "Ethiopia (residual Tigray)"],
            },
        ],
    },
    "somalia": {
        "verifications": [
            {
                "stakeholder": "WFP",
                "action": "Scale general food distribution to 5.6M people in IPC 3+ districts",
                "status": "partial",
                "evidence": "ReliefWeb · Somalia 2025–2026 Drought Emergency Sitrep #5 (6 Apr 2026) — only 12.2% of 2026 response funded, priority districts at <25% coverage; GFD reaching well below 6.5M IPC 3+ target.",
                "confidence": "high",
            },
            {
                "stakeholder": "WHO",
                "action": "Treat 1.8M children for SAM via OTP/SC network",
                "status": "in_progress",
                "evidence": "ReliefWeb · Somalia IPC Snapshot Jan–Jun 2026 — 1.84M children 6–59m projected acute malnutrition incl. 483K severe; nutrition cluster scaling.",
                "confidence": "high",
            },
            {
                "stakeholder": "UNHCR",
                "action": "Stabilise 3.8M IDPs in Banadir, Bay and Lower Shabelle",
                "status": "partial",
                "evidence": "ReliefWeb · Somalia Drought Sitrep #5 — ~500K newly displaced, site management active in most IDP sites but funding gap.",
                "confidence": "medium",
            },
            {
                "stakeholder": "UNHCR",
                "action": "Open returnee corridors from Dollow and Liboi",
                "status": "gap",
                "evidence": "No active returnee programme in May 2026 ReliefWeb feed; cross-border insecurity persists per ACLED Horn of Africa summary.",
                "confidence": "medium",
            },
            {
                "stakeholder": "Federal Government of Somalia",
                "action": "Activate national drought response coordination centre",
                "status": "in_progress",
                "evidence": "ReliefWeb · Somalia 2025–2026 Drought Emergency Sitrep #5 — SoDMA-led coordination centre operational across affected regions.",
                "confidence": "high",
            },
        ],
        "coverage_summary": (
            "Somalia's nutrition response is on track but food distribution and returnee corridors lag "
            "severely — only 12.2% of the 2026 response is funded and priority districts sit below 25% "
            "coverage. The largest blind spot is the absence of returnee programming from Dollow/Liboi "
            "despite stabilising conditions in some regions of origin."
        ),
        "evidence_sources": [
            {
                "type": "reliefweb_report",
                "title": "Somalia: 2025–2026 Drought Emergency — Situation Report No. 5 (as of 6 April 2026)",
                "date": "2026-04-06",
                "org": "OCHA",
                "url": "https://reliefweb.int/report/somalia/somalia-2025-2026-drought-emergency-situation-report-no-5-6-april-2026",
            },
            {
                "type": "reliefweb_report",
                "title": "Somalia: IPC Acute Food Insecurity and Acute Malnutrition Analysis (January – June 2026)",
                "date": "2026-02-24",
                "org": "IPC Global Partners",
                "url": "https://reliefweb.int/report/somalia/somalia-ipc-acute-food-insecurity-and-acute-malnutrition-analysis-january-june-2026-issued-24-february-2026",
            },
            {
                "type": "reliefweb_report",
                "title": "Somalia: IPC Acute Food Insecurity and Malnutrition Snapshot | January – June 2026",
                "date": "2026-02-24",
                "org": "IPC Global Partners",
                "url": "https://reliefweb.int/report/somalia/somalia-ipc-acute-food-insecurity-and-malnutrition-snapshot-january-june-2026",
            },
            {
                "type": "acled_summary",
                "title": "ACLED 30-day summary · East Africa",
                "events_30d": 450,
                "fatalities_30d": 2500,
                "active_conflicts": ["Sudan civil war (SAF vs RSF)", "Somalia (Al-Shabaab)", "Ethiopia (residual Tigray)"],
            },
        ],
    },
}


def _badge(status: str) -> str:
    meta = STATUS_META.get(status, STATUS_META["gap"])
    return (
        f"<span style='display:inline-flex;align-items:center;gap:6px;"
        f"background:{meta['bg']};color:{meta['fg']};font-size:0.68rem;"
        f"font-weight:700;padding:3px 10px;border-radius:14px;"
        f"border:1px solid {meta['border']};letter-spacing:0.05em;'>"
        f"<span>{meta['icon']}</span>{meta['label']}</span>"
    )


def _coverage_donut_html(in_prog: int, partial: int, gaps: int, total: int) -> str:
    if total == 0:
        return ""
    g_pct = int(round(100 * in_prog / total))
    y_pct = int(round(100 * partial / total))
    r_pct = max(0, 100 - g_pct - y_pct)
    g_end = g_pct
    y_end = g_pct + y_pct
    return (
        f"<div style='display:flex;align-items:center;gap:24px;padding:18px 22px;"
        f"background:linear-gradient(135deg,#0f172a,#1e293b);"
        f"border:1px solid #312e81;border-radius:14px;margin-bottom:18px;'>"
        f"<div style='width:84px;height:84px;border-radius:50%;flex-shrink:0;"
        f"background:conic-gradient(#22c55e 0% {g_end}%,#f59e0b {g_end}% {y_end}%,#ef4444 {y_end}% 100%);"
        f"display:flex;align-items:center;justify-content:center;'>"
        f"<div style='width:60px;height:60px;border-radius:50%;background:#0f172a;"
        f"display:flex;flex-direction:column;align-items:center;justify-content:center;"
        f"font-size:0.95rem;font-weight:800;color:#e2e8f0;line-height:1;'>"
        f"{g_pct}%<span style='font-size:0.55rem;color:#64748b;font-weight:600;margin-top:2px;'>COVERED</span>"
        f"</div></div>"
        f"<div style='flex:1;'>"
        f"<div style='display:flex;gap:18px;flex-wrap:wrap;'>"
        f"<div><div style='font-size:1.4rem;font-weight:800;color:#22c55e;line-height:1;'>{in_prog}</div>"
        f"<div style='font-size:0.7rem;color:#64748b;letter-spacing:0.05em;text-transform:uppercase;margin-top:2px;'>In Progress</div></div>"
        f"<div><div style='font-size:1.4rem;font-weight:800;color:#f59e0b;line-height:1;'>{partial}</div>"
        f"<div style='font-size:0.7rem;color:#64748b;letter-spacing:0.05em;text-transform:uppercase;margin-top:2px;'>Partial</div></div>"
        f"<div><div style='font-size:1.4rem;font-weight:800;color:#ef4444;line-height:1;'>{gaps}</div>"
        f"<div style='font-size:0.7rem;color:#64748b;letter-spacing:0.05em;text-transform:uppercase;margin-top:2px;'>Blind Spots</div></div>"
        f"<div><div style='font-size:1.4rem;font-weight:800;color:#cbd5e1;line-height:1;'>{total}</div>"
        f"<div style='font-size:0.7rem;color:#64748b;letter-spacing:0.05em;text-transform:uppercase;margin-top:2px;'>Total Actions</div></div>"
        f"</div></div></div>"
    )


def _verification_row(v: dict) -> str:
    meta = STATUS_META.get(v.get("status", "gap"), STATUS_META["gap"])
    return (
        f"<div style='background:#0f172a;border:1px solid #1e293b;"
        f"border-left:3px solid {meta['fg']};border-radius:10px;padding:14px 18px;"
        f"margin-bottom:10px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;"
        f"gap:12px;margin-bottom:6px;'>"
        f"<div style='flex:1;'>"
        f"<div style='font-size:0.7rem;color:#a78bfa;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.06em;margin-bottom:4px;'>{v.get('stakeholder','—')}</div>"
        f"<div style='color:#e2e8f0;font-size:0.92rem;font-weight:600;line-height:1.4;'>"
        f"{v.get('action','—')}</div>"
        f"</div>"
        f"{_badge(v.get('status','gap'))}"
        f"</div>"
        f"<div style='color:#94a3b8;font-size:0.78rem;line-height:1.5;margin-top:8px;"
        f"padding-top:8px;border-top:1px dashed #1e293b;'>"
        f"<span style='color:#64748b;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.05em;font-size:0.65rem;'>Evidence · </span>"
        f"<span style='color:#cbd5e1;'>{v.get('evidence','—')}</span>"
        f"</div></div>"
    )


def _placeholder_for(country: str) -> dict:
    """Return a placeholder verification result, falling back to Kenya."""
    return PLACEHOLDER_VERIFICATIONS.get(country.lower(), PLACEHOLDER_VERIFICATIONS["kenya"])


def render_action_watch(
    country: str,
    response_plans: Optional[list[dict]] = None,
    event_summary: str = "",
    use_live_generation: bool = False,
):
    """Render the Action Watch panel for a country.

    Args:
        country: country name (case-insensitive)
        response_plans: Dispatcher output (list of {stakeholder, actions, ...}).
                        Only used when use_live_generation=True.
        event_summary: original event description
        use_live_generation: if True, calls the ActionVerifier agent live.
                             If False (default), shows the placeholder verifications
                             so the dashboard demo works without a Gemma 4 round-trip.
    """
    st.markdown(
        "<h3 style='color:#e2e8f0; margin-bottom:2px;'>🛰️ Action Watch — Verifying Against Current Affairs</h3>"
        "<p style='color:#64748b; font-size:0.83rem; margin-top:0;'>"
        "CascadeAI checks each recommended action against live ReliefWeb situation reports and ACLED conflict feeds — "
        "highlighting what is already in progress and, more importantly, what is <b style='color:#fca5a5;'>still a blind spot</b>.</p>",
        unsafe_allow_html=True,
    )

    try:
        profile = get_profile_raw(country.lower())
        region_label = profile.get("region", "—")
    except Exception:
        region_label = "—"

    st.markdown(
        f"<div style='display:inline-flex; align-items:center; gap:8px; background:#1e293b;"
        f"border:1px solid #334155; border-radius:8px; padding:6px 14px; margin-bottom:14px;'>"
        f"<span style='color:#94a3b8; font-size:0.82rem;'>🌍 <b style='color:#e2e8f0;'>{country.title()}</b>"
        f" &nbsp;·&nbsp; 📍 <b style='color:#a78bfa;'>{region_label}</b>"
        f" &nbsp;·&nbsp; 📡 <b style='color:#60a5fa;'>ReliefWeb + ACLED, last 30 days</b></span></div>",
        unsafe_allow_html=True,
    )

    result: dict
    live_failed = False

    live_meta: dict = {}

    if use_live_generation and response_plans:
        with st.spinner("Cross-checking recommended actions against live humanitarian feeds..."):
            try:
                from models.gemma_client import GemmaClient

                client = GemmaClient()
                verifier = ActionVerifier(client)
                verif = verifier.verify(
                    country=country,
                    response_plans=response_plans,
                    region=region_label if region_label != "—" else None,
                    event_summary=event_summary,
                )
                result = {
                    "verifications": [
                        {
                            "stakeholder": v.stakeholder,
                            "action": v.action,
                            "status": v.status,
                            "evidence": v.evidence,
                            "confidence": v.confidence,
                        }
                        for v in verif.verifications
                    ],
                    "blind_spots": verif.blind_spots,
                    "coverage_summary": verif.coverage_summary,
                    "evidence_sources": verif.evidence_sources,
                }
                live_meta = {
                    "used_native_tools": verif.used_native_tools,
                    "tool_trace": verif.tool_trace,
                }
            except Exception as exc:
                live_failed = True
                st.warning(
                    f"Live verification failed ({type(exc).__name__}). Falling back to demo data."
                )
                result = _placeholder_for(country)
    else:
        result = _placeholder_for(country)

    # ------------------------------------------------------------------
    # Backend-health badge — tells the viewer where the evidence came from.
    # Two transports are combined in the label: the ReliefWeb path (API v2
    # vs RSS) AND the ACLED path (API vs HDX vs baseline_priors).
    # ------------------------------------------------------------------
    sources_for_badge = result.get("evidence_sources", []) or []
    transports = {str(s.get("transport", "")) for s in sources_for_badge if s.get("transport")}

    rw_part = "ReliefWeb"
    if any("API v2" in t for t in transports):
        rw_part = "ReliefWeb API v2"
    elif any("RSS" in t for t in transports):
        rw_part = "ReliefWeb RSS"

    acled_part = None
    if any(t == "ACLED API" for t in transports):
        acled_part = "ACLED API"
    elif any("HDX" in t for t in transports):
        acled_part = "ACLED via HDX"
    elif any("baseline_priors" in t for t in transports):
        acled_part = "ACLED priors"

    if use_live_generation and not live_failed and sources_for_badge:
        transport_label = rw_part + (f" + {acled_part}" if acled_part else "")
        badge_label = f"LIVE · {transport_label}"
        badge_fg = "#22c55e"
        badge_bg = "rgba(34,197,94,0.12)"
        badge_dot = "#22c55e"
        native = "  · NATIVE TOOL CALLS" if live_meta.get("used_native_tools") else ""
        st.markdown(
            f"<div style='display:inline-flex;align-items:center;gap:8px;"
            f"background:{badge_bg};border:1px solid {badge_fg};border-radius:12px;"
            f"padding:6px 14px;margin-bottom:10px;'>"
            f"<span style='width:8px;height:8px;border-radius:50%;background:{badge_dot};"
            f"box-shadow:0 0 6px {badge_dot};animation:cascadeai-pulse 1.6s ease-in-out infinite;'></span>"
            f"<span style='color:{badge_fg};font-size:0.72rem;font-weight:800;"
            f"letter-spacing:0.06em;'>{badge_label}{native}</span></div>"
            f"<style>@keyframes cascadeai-pulse {{0%,100%{{opacity:1}}50%{{opacity:0.45}}}}</style>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='display:inline-flex;align-items:center;gap:8px;"
            f"background:rgba(96,165,250,0.10);border:1px solid #60a5fa;"
            f"border-radius:12px;padding:6px 14px;margin-bottom:10px;'>"
            f"<span style='width:8px;height:8px;border-radius:50%;background:#60a5fa;'></span>"
            f"<span style='color:#60a5fa;font-size:0.72rem;font-weight:800;"
            f"letter-spacing:0.06em;'>DEMO · Curated May 2026 ReliefWeb Snapshot</span></div>",
            unsafe_allow_html=True,
        )

    verifications = result.get("verifications", [])
    in_prog = sum(1 for v in verifications if v.get("status") == "in_progress")
    partial = sum(1 for v in verifications if v.get("status") == "partial")
    gaps = sum(1 for v in verifications if v.get("status") == "gap")
    total = len(verifications)

    st.markdown(_coverage_donut_html(in_prog, partial, gaps, total), unsafe_allow_html=True)

    blind_spot_actions = [v for v in verifications if v.get("status") == "gap"]
    if blind_spot_actions:
        spots_html = (
            "<div style='background:linear-gradient(135deg,rgba(239,68,68,0.12),rgba(15,23,42,0.85));"
            "border:1px solid rgba(239,68,68,0.35);border-radius:12px;padding:16px 20px;"
            "margin-bottom:18px;'>"
            "<div style='color:#fca5a5;font-size:0.72rem;font-weight:800;text-transform:uppercase;"
            "letter-spacing:0.08em;margin-bottom:8px;'>🚨 Critical Blind Spots — No Active Response Detected</div>"
            "<ul style='margin:0;padding-left:18px;color:#fecaca;line-height:1.65;font-size:0.9rem;'>"
        )
        for v in blind_spot_actions:
            spots_html += (
                f"<li><span style='color:#fca5a5;font-weight:700;'>{v.get('stakeholder','—')}:</span> "
                f"<span style='color:#fee2e2;'>{v.get('action','—')}</span></li>"
            )
        spots_html += "</ul></div>"
        st.markdown(spots_html, unsafe_allow_html=True)

    summary = result.get("coverage_summary", "")
    if summary:
        st.markdown(
            f"<div style='background:#0f172a;border:1px solid #1e293b;border-radius:10px;"
            f"padding:14px 18px;color:#cbd5e1;font-size:0.88rem;line-height:1.6;margin-bottom:18px;'>"
            f"<span style='color:#64748b;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.05em;font-size:0.7rem;'>Coverage Summary · </span>"
            f"{summary}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='color:#a78bfa;font-size:0.75rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:0.06em;margin-bottom:10px;'>Per-Action Verification</div>",
        unsafe_allow_html=True,
    )
    for v in verifications:
        st.markdown(_verification_row(v), unsafe_allow_html=True)

    sources = result.get("evidence_sources", [])
    if sources:
        with st.expander(f"📚 Evidence sources used ({len(sources)})"):
            for src in sources:
                stype = src.get("type", "source")
                title = src.get("title", "Untitled")
                date = src.get("date", "")
                org = src.get("org", "")
                url = src.get("url", "")
                line = f"**[{stype}]** {title}"
                if org:
                    line += f" — *{org}*"
                if date:
                    line += f" ({date})"
                if url:
                    line += f"  \n<{url}>"
                st.markdown(line)
                if stype == "acled_summary":
                    bits = [
                        f"Events (30d): {src.get('events_30d','—')}",
                        f"Fatalities (30d): {src.get('fatalities_30d','—')}",
                    ]
                    if src.get("events_90d") is not None:
                        bits.append(
                            f"90-day: {src.get('events_90d')} events / "
                            f"{src.get('fatalities_90d','—')} fatalities"
                        )
                    if src.get("trend"):
                        bits.append(f"Trend: {src['trend']}")
                    if src.get("latest_month_label"):
                        bits.append(f"Latest: {src['latest_month_label']}")
                    transport = src.get("transport")
                    if transport:
                        bits.append(f"Transport: {transport}")
                    st.caption(" · ".join(bits))
                    if src.get("active_conflicts"):
                        st.caption(
                            "Active: " + " | ".join(src["active_conflicts"][:3])
                        )

    if not use_live_generation:
        st.caption(
            "*Demo mode — verifications cite real ReliefWeb reports (GIEWS Kenya 04-May-2026, IPC Jan–Dec 2026, "
            "Sudan RRP 2026, Somalia Drought Sitrep #5, etc.). Toggle **Use live action verification** above to "
            "have Gemma 4 hit live feeds via native function calling: ReliefWeb falls through v2 API → RSS, "
            "ACLED falls through v3 API → HDX weekly XLSX → static priors. The RSS + HDX paths both work "
            "without any credentials; set `RELIEFWEB_APPNAME`, `ACLED_API_KEY` and `ACLED_EMAIL` in `.env` "
            "for the full authenticated path.*"
        )
    elif live_failed:
        st.caption("*Showing demo data because live verification was unavailable.*")

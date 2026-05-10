"""Audience Selector component — toggles between 6 narrative audiences
and displays the appropriate output. For demo without Gemma 4, shows
pre-generated placeholder narratives."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from agents.narrative_generator import (
    NarrativeGenerator,
    AUDIENCE_CONFIGS,
    LANGUAGE_MAP,
)

PLACEHOLDER_NARRATIVES = {
    "who_briefing": {
        "title": "WHO Technical Briefing",
        "icon": "🏥",
        "sample": """**Situation Overview:** Following the cascade event, IPC Phase 3+ populations
in the target region are projected to increase by 25-40% within 90 days.

**Health Impact Assessment:**
- Acute malnutrition (GAM) rates projected to exceed emergency threshold (15%)
- Disease burden: cholera risk elevated due to water system stress
- Healthcare access reduced by estimated 30-45% in affected areas

**Recommendations:**
1. Activate health cluster surge capacity
2. Pre-position ORS and therapeutic feeding supplies
3. Establish disease surveillance in displacement areas""",
    },
    "field_worker": {
        "title": "Field Worker Alert",
        "icon": "📱",
        "sample": """**SITUATION:** A crisis cascade is affecting food and water systems in your area.
Prices of staple foods are expected to rise 30-50% in the next 60 days.

**ACTIONS:**
1. Survey current food stock levels at distribution points
2. Identify most vulnerable households (female-headed, elderly, under-5)
3. Coordinate with local suppliers for emergency procurement
4. Set up community early warning messaging in local language
5. Report stock levels to regional coordinator by end of day

**CONTACTS:** Regional coordinator: [contact], Supply chain: [contact]""",
    },
    "policy_brief": {
        "title": "Policy Brief",
        "icon": "📋",
        "sample": """**Executive Summary:** The cascade event is projected to increase food import
costs by $800M-$1.2B annually and affect 4-6M additional people.

**Economic Impact:**
- Food price inflation: +15-25% within 60 days
- GDP impact: -0.3 to -0.5 percentage points
- Trade balance deterioration: $400-600M

**Policy Options:**
1. Release strategic grain reserves (immediate, 30-day buffer)
2. Expand social protection coverage (+2M beneficiaries, $180M)
3. Negotiate bilateral grain purchase agreements
4. Suspend import tariffs on wheat and fertilizer (6-month window)""",
    },
    "media_summary": {
        "title": "Media Summary",
        "icon": "📰",
        "sample": """**Headline:** Crisis Cascade Threatens Food Security for Millions

**Key Facts:**
- Cascade origin: conflict/economic shock affecting supply chains
- 4-6 million additional people at risk of food insecurity
- Staple food prices projected to rise 30-50% in 60 days
- Healthcare systems under compounding pressure

**Timeline:**
- Day 0-7: Energy and transport disruption
- Day 7-30: Fertilizer and food price transmission
- Day 30-90: Health and displacement impacts emerge

**Context:** This follows a pattern seen in the 2022 Ukraine crisis, where
supply chain disruption led to a 120-day gap between onset and response.""",
    },
    "community_alert": {
        "title": "Community Preparedness Alert",
        "icon": "🌍",
        "sample": """Bei ya ngano katika eneo lako inaweza kupanda 30-40% katika miezi 2.
Fikiria kuhifadhi nafaka sasa.

Maji safi yanaweza kuathiriwa. Hifadhi maji ya kunywa kwa siku 7.

Kama una watoto wadogo, hakikisha wanakula vyakula vyenye virutubisho.
Tembelea kituo cha afya kikiwa karibu kwa ushauri.

Habari hii ni kutoka CascadeAI. Tutaendelea kutoa taarifa.""",
    },
    "public_brief": {
        "title": "Public Awareness Brief",
        "icon": "📢",
        "sample": """**Situation Summary:** A crisis cascade is developing that may affect food
prices and availability in the coming weeks. This brief provides factual
information for community leaders and civil society organizations.

**Key Data Points:**
- Staple food prices may rise 30-50% in 60 days
- Water and sanitation systems may be stressed in some areas
- Health services are preparing for increased demand

**What This Means for Communities:**
- Plan household budgets for potential food price increases
- Ensure clean water storage for 7 days
- Monitor community health, especially for children under 5

**Where to Find Help:**
- National emergency hotline: [number]
- WFP food distribution points: [link]
- WHO health advisories: [link]""",
    },
}


def render_audience_selector(
    country: str = "kenya",
    cascade_impacts: Optional[list[dict]] = None,
    predictions: Optional[list[dict]] = None,
    use_live_generation: bool = False,
):
    """Render the audience narrative selector with toggle."""
    st.subheader("Audience-Adaptive Narratives")
    st.caption("Same crisis data, tailored for different stakeholders")

    lang_name, lang_code = LANGUAGE_MAP.get(country.lower(), ("English", "en"))
    st.info(f"Country: **{country.title()}** | Native language: **{lang_name}** ({lang_code})")

    audience_keys = list(AUDIENCE_CONFIGS.keys())
    labels = [f"{PLACEHOLDER_NARRATIVES[k]['icon']} {PLACEHOLDER_NARRATIVES[k]['title']}" for k in audience_keys]

    selected_idx = st.radio(
        "Select audience",
        range(len(labels)),
        format_func=lambda i: labels[i],
        horizontal=True,
    )

    selected_key = audience_keys[selected_idx]
    placeholder = PLACEHOLDER_NARRATIVES[selected_key]

    st.divider()
    st.markdown(f"### {placeholder['icon']} {placeholder['title']}")

    if selected_key in ("field_worker", "community_alert"):
        st.caption(f"Language: {lang_name} ({lang_code})")

    if use_live_generation and cascade_impacts:
        with st.spinner(f"Generating {placeholder['title']} with Gemma 4..."):
            from models.gemma_client import GemmaClient
            client = GemmaClient()
            gen = NarrativeGenerator(client)
            narrative = gen.generate_single(
                audience_key=selected_key,
                country=country,
                cascade_impacts=cascade_impacts or [],
                predictions=predictions or [],
                event_summary="Crisis cascade event",
            )
            st.markdown(narrative.content)
    else:
        st.markdown(placeholder["sample"])
        st.caption("*Demo mode — using pre-generated narrative. Connect Gemma 4 for live generation.*")

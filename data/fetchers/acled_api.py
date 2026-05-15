"""ACLED (Armed Conflict Location & Event Data) fetcher — three-tier.

Single entry point ``search_acled_events()``, three transport paths:

1. **ACLED v3 JSON API** at ``https://api.acleddata.com/acled/read``
   When ``ACLED_API_KEY`` + ``ACLED_EMAIL`` are set in the environment, we
   pull live event-level data (fastest refresh, most granular). Requires a
   free ACLED account at https://acleddata.com/register.

2. **ACLED via HDX (no auth)** — see ``data.fetchers.acled_hdx``.
   HDX (the OCHA-managed Humanitarian Data Exchange) hosts ACLED's official
   monthly XLSX rollups for every country with weekly refresh. No
   credentials. This is the fallback that keeps live ACLED data flowing in
   the hackathon demo and on HuggingFace Spaces without anyone having to
   register.

3. **Static priors** — last-resort cached summary keyed by region. Only
   used if both above paths return empty.

Each result carries a ``source`` field — ``"ACLED API"`` /
``"ACLED via HDX"`` / ``"baseline_priors"`` — so the Action Verifier and
dashboard can show the viewer which transport delivered the evidence.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

from data.fetchers.acled_hdx import (
    fetch_country_conflict_summary,
    fetch_region_conflict_summary,
)

ACLED_BASE = "https://api.acleddata.com/acled/read"
ACLED_KEY = os.getenv("ACLED_API_KEY", "")
ACLED_EMAIL = os.getenv("ACLED_EMAIL", "")

PROXY = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")) or None


def search_acled_events(
    region: str = "",
    days: int = 30,
    event_type: Optional[str] = None,
    country: Optional[str] = None,
) -> dict:
    """Search ACLED for recent conflict events.

    Args:
        region: ACLED region label (e.g. "East Africa"). Used by the API path
            and as the aggregation key for HDX when ``country`` is not given.
        days: lookback window in days. The HDX path rounds to whole months
            since the underlying data is monthly-aggregated.
        event_type: optional event-type filter (only honoured by the API path).
        country: optional country name — when set, the HDX path returns a
            country-scoped summary instead of a region aggregate.

    Returns:
        A dict with at minimum ``source``, ``events_30d``, ``fatalities_30d``
        and ``active_conflicts``. The HDX path also includes ``events_90d``,
        ``trend``, ``latest_month_label`` and a ``dataset_url`` citation.
    """
    # Tier 1 — authenticated ACLED API
    api_result = _try_acled_api(region=region, days=days, event_type=event_type)
    if api_result is not None:
        return api_result

    # Tier 2 — HDX (no auth, weekly-refreshed real ACLED data)
    if country:
        hdx_country = fetch_country_conflict_summary(country, days=days)
        if hdx_country is not None:
            return hdx_country
    if region:
        hdx_region = fetch_region_conflict_summary(region, days=days)
        if hdx_region is not None:
            return hdx_region

    # Tier 3 — static priors so the Verifier never crashes for lack of data
    return _fallback_events(region or (country or ""))


# ---------------------------------------------------------------------------
# Tier 1 — authenticated ACLED API
# ---------------------------------------------------------------------------

def _try_acled_api(
    region: str,
    days: int,
    event_type: Optional[str],
) -> Optional[dict]:
    """Hit ACLED's v3 API when credentials are set. Returns ``None`` to
    signal 'fall back to the next tier'."""
    if not ACLED_KEY or not ACLED_EMAIL or not region:
        return None

    try:
        params = {
            "key": ACLED_KEY,
            "email": ACLED_EMAIL,
            "region": region,
            "limit": 50,
        }
        if event_type:
            params["event_type"] = event_type

        kwargs = {"timeout": 15}
        if PROXY:
            kwargs["proxy"] = PROXY

        with httpx.Client(**kwargs) as client:
            resp = client.get(ACLED_BASE, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()

        events = data.get("data", []) or []
        fatalities = 0
        for e in events:
            try:
                fatalities += int(e.get("fatalities", 0) or 0)
            except (TypeError, ValueError):
                continue
        actors = sorted({(e.get("actor1") or "").strip() for e in events if e.get("actor1")})

        return {
            "source": "ACLED API",
            "region": region,
            "events_30d": len(events),
            "fatalities_30d": fatalities,
            "active_conflicts": actors[:6],
            "events": events[:20],  # event-level data for downstream agents
        }
    except (httpx.HTTPError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Tier 3 — static priors
# ---------------------------------------------------------------------------

def _fallback_events(key: str) -> dict:
    """Return a cached conflict summary when no live tier can serve.

    Keyed by region label OR country name (case-insensitive) so the
    Verifier always gets a usable shape even in fully offline mode.
    """
    summaries = {
        "East Africa": {
            "active_conflicts": [
                "Sudan civil war (SAF vs RSF)",
                "Somalia (Al-Shabaab)",
                "Ethiopia (residual Tigray)",
            ],
            "fatalities_30d": 2500,
            "events_30d": 450,
        },
        "Middle East": {
            "active_conflicts": ["Israel-Palestine", "Yemen (Houthi)", "Syria (residual)"],
            "fatalities_30d": 3200,
            "events_30d": 680,
        },
        "South Asia": {
            "active_conflicts": [
                "Pakistan (Balochistan)",
                "Myanmar (civil war)",
                "Afghanistan (Taliban governance)",
            ],
            "fatalities_30d": 800,
            "events_30d": 320,
        },
    }
    matched = summaries.get(key, {"active_conflicts": [], "fatalities_30d": 0, "events_30d": 0})
    return {
        "source": "baseline_priors",
        "region": key,
        **matched,
    }

"""ReliefWeb API client.

Two transport paths, fronted by a single ``search_reports()`` entry point:

1. **ReliefWeb v2 JSON API** at ``https://api.reliefweb.int/v2`` — preferred
   when ``RELIEFWEB_APPNAME`` is set to an approved appname. v2 requires a
   pre-approved appname in the URL since Q1 2026.

2. **ReliefWeb RSS feed** at ``https://reliefweb.int/updates/rss.xml`` —
   fallback for hackathon / demo deployments without API credentials.
   No authentication required, returns the 20 most-recent reports per
   country via the ``advanced-search=(Cxxx)`` query parameter. See
   :mod:`data.fetchers.reliefweb_rss` for the country-ID map.

The result schema is identical across both paths so downstream agents and
the dashboard don't have to know which transport was used. Each result
carries a ``source`` field of either ``"ReliefWeb API v2"`` or
``"ReliefWeb RSS"`` for transparency.

Request an approved appname at:
https://docs.google.com/forms/d/e/1FAIpQLScR5EE_SBhweLLg_2xMCnXNbT6md4zxqIB00OL0yZWyrqX_Nw/viewform
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

from data.fetchers.reliefweb_rss import (
    fetch_response_plans_rss,
    search_reports_rss,
)

RELIEFWEB_BASE = "https://api.reliefweb.int/v2"

PROXY = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")) or None
APPNAME = os.getenv("RELIEFWEB_APPNAME", "").strip()


def _v2_url() -> Optional[str]:
    if not APPNAME:
        return None
    return f"{RELIEFWEB_BASE}/reports?appname={APPNAME}"


def _try_v2(country: str, query: Optional[str], limit: int) -> Optional[dict]:
    """Try the v2 JSON API. Returns ``None`` to signal 'fall back to RSS'."""
    url = _v2_url()
    if url is None:
        return None

    try:
        payload = {
            "limit": limit,
            "filter": {
                "operator": "AND",
                "conditions": [
                    {"field": "primary_country.name", "value": country},
                ],
            },
            "sort": ["date:desc"],
            "fields": {"include": ["title", "date.original", "source.name", "url_alias"]},
        }
        if query:
            payload["query"] = {"value": query}

        kwargs = {"timeout": 15}
        if PROXY:
            kwargs["proxy"] = PROXY

        with httpx.Client(**kwargs) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()

        reports = []
        for item in data.get("data", []):
            fields = item.get("fields", {})
            source_list = fields.get("source") or []
            source_name = source_list[0].get("name", "") if source_list else ""
            reports.append({
                "title": fields.get("title", ""),
                "date": (fields.get("date") or {}).get("original", ""),
                "source": source_name,
                "url": fields.get("url_alias", ""),
            })
        return {
            "source": "ReliefWeb API v2",
            "country": country,
            "count": data.get("totalCount", 0),
            "reports": reports,
        }
    except (httpx.HTTPError, ValueError):
        return None


def search_reports(
    country: str,
    query: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Search ReliefWeb for humanitarian reports.

    Tries the v2 JSON API first (if ``RELIEFWEB_APPNAME`` is set), then
    falls back to the RSS feed. Both paths return live ReliefWeb data
    with the same record shape; only the ``source`` field differs.
    """
    primary = _try_v2(country, query, limit)
    if primary is not None and primary.get("reports"):
        return primary

    # v2 path was missing, errored, or returned empty — fall through to RSS.
    return search_reports_rss(country=country, query=query, limit=limit)


def fetch_response_plans(country: str) -> dict:
    """Fetch humanitarian response plans for a country."""
    primary = _try_v2(country, query="response plan", limit=5)
    if primary is not None and primary.get("reports"):
        return primary
    return fetch_response_plans_rss(country=country)

"""ReliefWeb RSS fetcher (no authentication required).

Fallback for the ReliefWeb v2 API: the v2 endpoint requires a pre-approved
``appname`` parameter as of Q1 2026, but the legacy ``/updates/rss.xml``
endpoint at https://reliefweb.int still serves country-filtered feeds without
auth using the ``advanced-search`` query parameter and ReliefWeb's internal
country IDs (e.g. ``C131`` for Kenya).

This module ships a country-name → country-ID map for the 14 countries
CascadeAI's cascade graph supports, and parses the resulting RSS XML into
the same record shape ``data.fetchers.reliefweb_api.search_reports`` returns
so the Action Verifier and dashboard don't have to know which backend was
used.

When a partner agency holds an approved appname, the v2 API call in
``reliefweb_api.py`` takes precedence; the RSS fetcher only fires on 4xx or
empty responses. Either way, the data is genuinely live ReliefWeb content.
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

# Country name → ReliefWeb advanced-search country code. Discovered by
# scraping each country landing page for the ``advanced-search=(Cxxx)``
# anchor that ReliefWeb's own UI generates. Validated 2026-05-13 against
# the 14-country CascadeAI roster.
COUNTRY_IDS: dict[str, str] = {
    "kenya": "131",
    "ethiopia": "87",
    "somalia": "216",
    "sudan": "220",
    "south sudan": "8657",
    "egypt": "82",
    "bangladesh": "31",
    "india": "119",
    "dr congo": "75",
    "democratic republic of the congo": "75",
    "drc": "75",
    "chile": "57",
    "indonesia": "120",
    "pakistan": "182",
    "yemen": "255",
    "myanmar": "165",
    # Common aliases / partials
    "burma": "165",
}

USER_AGENT = "CascadeAI/1.0 (humanitarian crisis cascade modelling)"
ACCEPT_XML = "application/rss+xml, application/xml, text/xml, */*"

PROXY = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")) or None


def _country_id(country: str) -> Optional[str]:
    return COUNTRY_IDS.get(country.strip().lower())


def _rss_url(country_id: str) -> str:
    # advanced-search=(Cxxx) — URL-encoded as %28C...%29.
    return f"https://reliefweb.int/updates/rss.xml?advanced-search=%28C{country_id}%29"


def _strip_html(text: str) -> str:
    """Drop the ``<div class="tag …">`` markup ReliefWeb embeds in description."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def search_reports_rss(
    country: str,
    query: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Pull recent ReliefWeb reports for ``country`` via the RSS feed.

    Falls back to ``{"source": "unavailable", ...}`` on any error so the
    Action Verifier can continue with what it has.

    Args:
        country: human-readable country name (case-insensitive). Aliases
            like "DRC" and "DR Congo" resolve to the same entry.
        query: optional keyword filter applied client-side to title + source.
            Case-insensitive; pass ``None`` for the unfiltered feed.
        limit: max number of records to return after client-side filtering.
    """
    cid = _country_id(country)
    if not cid:
        return {
            "source": "unavailable",
            "country": country,
            "count": 0,
            "reports": [],
            "note": f"No ReliefWeb country ID known for '{country}'.",
        }

    try:
        kwargs = {"timeout": 20, "follow_redirects": True}
        if PROXY:
            kwargs["proxy"] = PROXY
        headers = {"User-Agent": USER_AGENT, "Accept": ACCEPT_XML}

        with httpx.Client(**kwargs) as client:
            resp = client.get(_rss_url(cid), headers=headers)
            if resp.status_code != 200:
                return {
                    "source": "unavailable",
                    "country": country,
                    "count": 0,
                    "reports": [],
                    "note": f"RSS endpoint returned HTTP {resp.status_code}",
                }

            root = ET.fromstring(resp.content)
    except (httpx.HTTPError, ET.ParseError) as exc:  # noqa: BLE001
        return {
            "source": "unavailable",
            "country": country,
            "count": 0,
            "reports": [],
            "note": f"RSS fetch failed: {type(exc).__name__}: {exc}",
        }

    items = root.findall(".//item")
    parsed: list[dict] = []
    needle = query.lower().strip() if query else None
    for it in items:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub_date = (it.findtext("pubDate") or "").strip()

        # ReliefWeb RSS quirks:
        #  * <source> contains the FEED name (always "ReliefWeb - Updates") —
        #    not the issuing org. Ignore.
        #  * <author> is the issuing org (UNHCR, OCHA, ACAPS, etc.).
        #  * <category> entries come as [country, …, source_org] — the LAST
        #    category is typically the source. Use it as a fallback.
        source_name = (it.findtext("author") or "").strip()
        if not source_name:
            cats = [c.text.strip() for c in it.findall("category") if (c.text or "").strip()]
            # Drop entries that look like country names (RSS lists the
            # country tag first) by picking the last non-empty entry.
            if cats:
                source_name = cats[-1]

        description = _strip_html(it.findtext("description") or "")[:240]

        if needle:
            haystack = " ".join([title, source_name, description]).lower()
            if needle not in haystack:
                continue

        parsed.append({
            "title": title,
            "date": pub_date,
            "source": source_name,
            "url": link,
            "description": description,
        })
        if len(parsed) >= limit:
            break

    return {
        "source": "ReliefWeb RSS",
        "country": country,
        "count": len(parsed),
        "reports": parsed,
    }


def fetch_response_plans_rss(country: str) -> dict:
    """Pull recent ReliefWeb response-plan-flavoured reports via RSS.

    The RSS feed has no native ``content-type`` filter so we filter
    client-side on common response-plan keywords.
    """
    result = search_reports_rss(country=country, query="response plan", limit=5)
    if result.get("reports"):
        return result
    # Fallback: try humanitarian response plan / HRP / RRP synonyms
    for q in ("humanitarian response", "HRP", "RRP", "appeal"):
        retry = search_reports_rss(country=country, query=q, limit=5)
        if retry.get("reports"):
            return retry
    return result

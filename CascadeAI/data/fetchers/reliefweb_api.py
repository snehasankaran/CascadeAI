"""ReliefWeb API client.

Fetches humanitarian situation reports and response plans.
Free API, no key required.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

RELIEFWEB_BASE = "https://api.reliefweb.int/v1"

PROXY = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")) or None


def search_reports(
    country: str,
    query: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Search ReliefWeb for humanitarian reports."""
    try:
        url = f"{RELIEFWEB_BASE}/reports"
        payload = {
            "appname": "cascadeai",
            "limit": limit,
            "filter": {
                "operator": "AND",
                "conditions": [
                    {"field": "primary_country.name", "value": country},
                ],
            },
            "sort": ["date:desc"],
            "fields": {
                "include": ["title", "date.original", "source.name", "url_alias"]
            },
        }
        if query:
            payload["query"] = {"value": query}

        kwargs = {"timeout": 15}
        if PROXY:
            kwargs["proxy"] = PROXY

        with httpx.Client(**kwargs) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                reports = []
                for item in data.get("data", []):
                    fields = item.get("fields", {})
                    reports.append({
                        "title": fields.get("title", ""),
                        "date": fields.get("date", {}).get("original", ""),
                        "source": fields.get("source", [{}])[0].get("name", "") if fields.get("source") else "",
                        "url": fields.get("url_alias", ""),
                    })
                return {
                    "source": "ReliefWeb API",
                    "country": country,
                    "count": data.get("totalCount", 0),
                    "reports": reports,
                }
    except Exception:
        pass

    return {"source": "unavailable", "country": country, "count": 0, "reports": []}


def fetch_response_plans(country: str) -> dict:
    """Fetch humanitarian response plans for a country."""
    return search_reports(country, query="response plan", limit=5)

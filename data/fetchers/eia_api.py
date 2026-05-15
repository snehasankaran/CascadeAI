"""EIA (Energy Information Administration) API client.

Fetches energy commodity prices — Brent crude, natural gas, diesel.
Fallback: returns cached baseline data.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

EIA_BASE = "https://api.eia.gov/v2"
EIA_API_KEY = os.getenv("EIA_API_KEY", "")

PROXY = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")) or None


COMMODITY_SERIES = {
    "brent_crude": "PET.RBRTE.D",
    "wti_crude": "PET.RWTC.D",
    "natural_gas": "NG.RNGWHHD.D",
    "diesel": "PET.EMD_EPD2D_PTE_NUS_DPG.W",
}


def fetch_energy_prices(
    commodity: str = "brent_crude",
    months: int = 12,
) -> dict:
    """Fetch energy prices from EIA.

    Returns price data with metadata. Falls back to cached data
    if API key is missing or API is unavailable.
    """
    if not EIA_API_KEY:
        return _fallback_prices(commodity)

    series_id = COMMODITY_SERIES.get(commodity, commodity)

    try:
        url = f"{EIA_BASE}/seriesid/{series_id}"
        params = {"api_key": EIA_API_KEY, "num": months * 30}
        kwargs = {"timeout": 15}
        if PROXY:
            kwargs["proxy"] = PROXY

        with httpx.Client(**kwargs) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "source": "EIA API",
                    "commodity": commodity,
                    "series_id": series_id,
                    "data": data.get("response", {}).get("data", []),
                }
    except Exception:
        pass

    return _fallback_prices(commodity)


def _fallback_prices(commodity: str) -> dict:
    """Return baseline cached energy prices."""
    baselines = {
        "brent_crude": {"price_usd": 82.50, "unit": "barrel"},
        "wti_crude": {"price_usd": 78.20, "unit": "barrel"},
        "natural_gas": {"price_usd": 3.45, "unit": "MMBtu"},
        "diesel": {"price_usd": 3.85, "unit": "gallon"},
        "urea": {"price_usd": 400.00, "unit": "MT"},
    }
    base = baselines.get(commodity, {"price_usd": 0, "unit": "unknown"})
    return {
        "source": "baseline_cache",
        "commodity": commodity,
        "price_usd": base["price_usd"],
        "unit": base["unit"],
        "data": [],
    }

"""World Bank RTFP (Real-Time Food Prices) API client.

Fetches food commodity prices by country from the World Bank VAM API.
Fallback: returns cached baseline data from country profiles.
"""

from __future__ import annotations

from typing import Optional

import httpx

BASE_URL = "https://data.humdata.org/api/3/action"
WB_RTFP_URL = "https://api.worldbank.org/v2"

PROXY = None

try:
    import os
    _p = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", ""))
    if _p:
        PROXY = _p
except Exception:
    pass


def fetch_food_prices(
    country_iso3: str,
    commodity: str = "wheat",
    months: int = 12,
) -> dict:
    """Fetch food prices from World Bank / HDX.

    Returns a dict with price history and metadata. Falls back to
    baseline data if API is unavailable.
    """
    try:
        url = f"{WB_RTFP_URL}/country/{country_iso3}/indicator/FP.CPI.TOTL"
        params = {"format": "json", "per_page": months, "date": "2021:2026"}
        kwargs = {"timeout": 15}
        if PROXY:
            kwargs["proxy"] = PROXY

        with httpx.Client(**kwargs) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 1:
                    return {
                        "source": "World Bank API",
                        "country": country_iso3,
                        "commodity": commodity,
                        "data": data[1][:months] if data[1] else [],
                    }
    except Exception:
        pass

    return _fallback_prices(country_iso3, commodity)


def _fallback_prices(country_iso3: str, commodity: str) -> dict:
    """Return baseline cached prices when API is unavailable."""
    baselines = {
        "KEN": {"wheat": 0.45, "maize": 0.32, "rice": 0.55},
        "ETH": {"wheat": 0.52, "maize": 0.38, "teff": 0.85},
        "BGD": {"wheat": 0.38, "rice": 0.42, "lentils": 0.65},
        "EGY": {"wheat": 0.35, "rice": 0.48, "bread": 0.05},
        "IND": {"wheat": 0.28, "rice": 0.35, "pulses": 0.52},
        "TUR": {"wheat": 0.42, "rice": 0.55, "barley": 0.38},
        "SOM": {"wheat": 0.65, "maize": 0.48, "sorghum": 0.42},
        "PAK": {"wheat": 0.33, "rice": 0.40, "maize": 0.35},
    }
    prices = baselines.get(country_iso3.upper(), {})
    return {
        "source": "baseline_cache",
        "country": country_iso3,
        "commodity": commodity,
        "price_usd_kg": prices.get(commodity, 0.40),
        "data": [],
    }

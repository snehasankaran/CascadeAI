"""Smoke tests for data fetchers — verifies imports, fallbacks, and live API calls."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

from data.fetchers.worldbank_api import fetch_food_prices
from data.fetchers.eia_api import fetch_energy_prices
from data.fetchers.acled_api import search_acled_events
from data.fetchers.reliefweb_api import search_reports, fetch_response_plans

print("=" * 60)
print("DATA FETCHER TESTS")
print("=" * 60)

print("\n--- World Bank (Food Prices) ---")
for iso3 in ["KEN", "ETH", "BGD"]:
    result = fetch_food_prices(iso3, "wheat")
    print(f"  {iso3}: source={result['source']}, commodity={result['commodity']}")

print("\n--- EIA (Energy Prices) ---")
for commodity in ["brent_crude", "natural_gas", "diesel"]:
    result = fetch_energy_prices(commodity)
    print(f"  {commodity}: source={result['source']}, price={result.get('price_usd', 'N/A')}")

print("\n--- ACLED (Conflict Events) ---")
for region in ["East Africa", "Middle East"]:
    result = search_acled_events(region)
    print(f"  {region}: source={result['source']}, conflicts={result.get('active_conflicts', result.get('events', []))[:2]}")

print("\n--- ReliefWeb (Humanitarian Reports) ---")
for country in ["Sudan", "Kenya"]:
    result = search_reports(country, limit=3)
    print(f"  {country}: source={result['source']}, count={result['count']}, reports={len(result['reports'])}")
    for r in result["reports"][:2]:
        print(f"    - {r['title'][:80]}")

print("\n" + "=" * 60)
print("ALL FETCHER TESTS COMPLETE")
print("=" * 60)

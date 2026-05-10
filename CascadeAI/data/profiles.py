"""Country profile loader — reads JSON files from data/country_profiles/ and
returns CountryProfile objects for use in the BFS engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from cascade.traversal import CountryProfile

PROFILES_DIR = Path(__file__).parent / "country_profiles"

_cache: dict[str, CountryProfile] = {}


def load_profile(country: str) -> CountryProfile:
    """Load a single country profile by name (case-insensitive).

    Returns a CountryProfile with vulnerability multipliers for the BFS engine.
    """
    key = country.lower().strip()
    if key in _cache:
        return _cache[key]

    path = PROFILES_DIR / f"{key}.json"
    if not path.exists():
        raise FileNotFoundError(f"No profile for country '{country}' at {path}")

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    profile = CountryProfile(
        country=raw["country"],
        vulnerability=raw.get("vulnerability", {}),
    )
    _cache[key] = profile
    return profile


def load_all_profiles() -> dict[str, CountryProfile]:
    """Load all available country profiles."""
    profiles = {}
    for path in sorted(PROFILES_DIR.glob("*.json")):
        name = path.stem
        profiles[name] = load_profile(name)
    return profiles


def get_profile_raw(country: str) -> dict:
    """Load the raw JSON data for a country (full metadata, not just vulnerability)."""
    key = country.lower().strip()
    path = PROFILES_DIR / f"{key}.json"
    if not path.exists():
        raise FileNotFoundError(f"No profile for country '{country}' at {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def available_countries() -> list[str]:
    """List all countries with profiles."""
    return [p.stem.title() for p in sorted(PROFILES_DIR.glob("*.json"))]

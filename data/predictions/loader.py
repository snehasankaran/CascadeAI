"""Prediction loader — loads forward-looking predictions from JSON files."""

from __future__ import annotations

import json
from pathlib import Path

PREDICTION_DIR = Path(__file__).resolve().parent


def load_prediction(name: str) -> dict:
    path = PREDICTION_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No prediction: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def available_predictions() -> list[str]:
    return [
        p.stem for p in sorted(PREDICTION_DIR.glob("*.json"))
        if p.stem != "__init__"
    ]


def load_all_predictions() -> list[dict]:
    return [load_prediction(name) for name in available_predictions()]

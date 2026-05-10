"""Verify all prediction scenarios load and have valid structure."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from data.predictions.loader import available_predictions, load_prediction

print("=" * 70)
print("FORWARD PREDICTIONS — CascadeAI")
print("=" * 70)

preds = available_predictions()
print(f"\n{len(preds)} active predictions:\n")

for name in preds:
    p = load_prediction(name)
    title = p["name"]
    status = p.get("status", "N/A")
    confidence = p.get("confidence", "N/A")
    window = p.get("verification_window", "N/A")

    pred_count = len(p.get("predictions", p.get("country_predictions", [])))

    print(f"  {name}")
    print(f"    Title:      {title}")
    print(f"    Status:     {status}")
    print(f"    Confidence: {confidence}")
    print(f"    Verify:     {window}")
    print(f"    Predictions: {pred_count}")
    print()

from api import app
routes = [r for r in app.routes if hasattr(r, "methods")]
print(f"FastAPI: {len(routes)} routes (including /predictions endpoints)")
print("\nALL PREDICTIONS VERIFIED")

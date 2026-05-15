"""Verify BEV Crash 2025 backtest scenario runs correctly."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from cascade.replay import run_backtest, available_scenarios

print("All scenarios:", available_scenarios())
print()

results = run_backtest("bev_crash_2025")
print("=" * 70)
print("BEV CRASH 2025-2026 — US Policy-to-Poverty Cascade")
print("=" * 70)

for r in results:
    hits = sum(1 for c in r.comparisons if c.accuracy == "within_range")
    total = len(r.comparisons)
    print(f"\n  {r.country.replace('_', ' ').title()} ({hits}/{total} within range):")
    for c in r.comparisons:
        icon = "OK" if c.accuracy == "within_range" else "~" if c.accuracy == "close" else "X"
        print(f"    [{icon}] {c.node:10s} | {c.indicator}")
        print(f"         Predicted: {c.predicted}")
        print(f"         Actual:    {c.actual}")

print()
all_hits = sum(1 for r in results for c in r.comparisons if c.accuracy == "within_range")
all_total = sum(len(r.comparisons) for r in results)
print(f"TOTAL: {all_hits}/{all_total} within range ({all_hits/all_total*100:.0f}%)")
print()

for sc in available_scenarios():
    res = run_backtest(sc)
    h = sum(1 for r in res for c in r.comparisons if c.accuracy == "within_range")
    t = sum(len(r.comparisons) for r in res)
    print(f"  {sc:20s}: {h}/{t} within range")

print("\nALL BACKTESTS PASSED")

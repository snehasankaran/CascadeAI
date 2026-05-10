"""Full pipeline test — Event Detection + BFS Cascade + Impact Prediction
+ Narrative Generation, all powered by Gemma 4 31B."""

import sys, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["GEMMA_API_BASE"] = "https://generativelanguage.googleapis.com/v1beta"
os.environ["GEMMA_API_KEY"] = "AIzaSyBGxomsSzlRzTFa123XjLqVvQHutBrjSc0"
os.environ["GEMMA_MODEL"] = "gemma-4-31b-it"

from models.gemma_client import GemmaClient
from cascade.graph import CascadeGraph
from cascade.traversal import run_cascade
from data.profiles import load_profile, get_profile_raw
from agents.event_detector import EventDetector
from agents.narrative_generator import NarrativeGenerator

client = GemmaClient()
graph = CascadeGraph.from_json()

EVENT = "Russia invades Ukraine on February 24, 2022, blocking Black Sea wheat exports and disrupting global fertilizer supply chains."

# Step 1: Event Detection (Gemma 4)
print("=" * 60)
print("STEP 1: EVENT DETECTION (Gemma 4 31B)")
print("=" * 60)
print(f"Input: {EVENT}\n")

detector = EventDetector(client)
event = detector.detect(EVENT)
print(f"Node:       {event.node}")
print(f"Severity:   {event.severity}")
print(f"Region:     {event.region}")
print(f"Summary:    {event.summary}")
print(f"Secondary:  {event.secondary_nodes}")

# Step 2: BFS Cascade (deterministic, no LLM)
print("\n" + "=" * 60)
print("STEP 2: BFS CASCADE (Kenya)")
print("=" * 60)

kenya = load_profile("kenya")
impacts = run_cascade(graph, event.node, event.severity, country=kenya)

for imp in impacts:
    seed = " [SEED]" if imp.is_seed else ""
    print(f"  {imp.node:15s} severity={imp.severity:.4f}  delay={imp.delay_days:3d}d{seed}")

# Step 3: Narrative Generation — Community Alert in Swahili (Gemma 4)
print("\n" + "=" * 60)
print("STEP 3: COMMUNITY ALERT IN SWAHILI (Gemma 4 31B)")
print("=" * 60)

impacts_dicts = [
    {"node": i.node, "severity": i.severity, "delay_days": i.delay_days, "path": i.path}
    for i in impacts
]

gen = NarrativeGenerator(client)
narrative = gen.generate_single(
    audience_key="community_alert",
    country="kenya",
    cascade_impacts=impacts_dicts,
    predictions=[],
    event_summary=EVENT,
)
print(f"Audience:  {narrative.label}")
print(f"Language:  {narrative.language}")
print(f"\n{narrative.content}")

print("\n" + "=" * 60)
print("FULL PIPELINE TEST COMPLETE")
print("=" * 60)

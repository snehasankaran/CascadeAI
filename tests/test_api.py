"""Test Gemma 4 via the updated GemmaClient.

Reads credentials from CascadeAI/.env (loaded by config.py). Skips itself
if GEMMA_API_KEY is unset or set to the local-Ollama placeholder.
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: F401 — loads .env

if not os.getenv("GEMMA_API_KEY") or os.getenv("GEMMA_API_KEY") == "ollama":
    print("SKIP: set GEMMA_API_KEY in CascadeAI/.env to run this live test.")
    sys.exit(0)

from models.gemma_client import GemmaClient

client = GemmaClient()
print(f"Client: {client}")
print("Sending test message to Gemma 4 31B...")

resp = client.complete(
    system="You are a helpful assistant. Respond in exactly one sentence.",
    user="What is a humanitarian crisis cascade?",
)
print(f"Response: {resp}")
print("GEMMA 4 CONNECTION SUCCESSFUL")

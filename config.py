"""Central configuration — loads .env and provides settings to all modules."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

GEMMA_API_BASE = os.getenv("GEMMA_API_BASE", "http://localhost:11434/v1")
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY", "ollama")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4:e2b")

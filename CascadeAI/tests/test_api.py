"""Test Gemma 4 via the updated GemmaClient."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["GEMMA_API_BASE"] = "https://generativelanguage.googleapis.com/v1beta"
os.environ["GEMMA_API_KEY"] = "AIzaSyBGxomsSzlRzTFa123XjLqVvQHutBrjSc0"
os.environ["GEMMA_MODEL"] = "gemma-4-31b-it"

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

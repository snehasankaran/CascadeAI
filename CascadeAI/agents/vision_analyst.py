"""Agent 5: Vision Analyst — analyzes satellite imagery, scanned reports,
and field photos using Gemma 4 multimodal capabilities."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

SYSTEM_PROMPT = """You are CascadeAI's Vision Analyst agent. You analyze satellite imagery,
field photos, and scanned documents related to humanitarian crises.

For each image, provide a structured assessment:
- "scene_description": what you see in the image
- "crisis_indicators": list of observable crisis indicators (e.g., destroyed buildings, displacement camps, flood damage, drought conditions)
- "severity_estimate": "critical" / "severe" / "moderate" / "mild" / "none"
- "affected_nodes": which cascade graph nodes are relevant (war, energy, transport, food, health, water, displacement, etc.)
- "recommendations": 1-2 sentence recommendation based on observations

Return ONLY valid JSON."""


@dataclass
class VisionAssessment:
    scene_description: str
    crisis_indicators: list[str]
    severity_estimate: str
    affected_nodes: list[str]
    recommendations: str


class VisionAnalyst:
    def __init__(self):
        self.api_base = os.getenv("GEMMA_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
        self.api_key = os.getenv("GEMMA_API_KEY", "")
        self.model = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
        self.proxy = os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")) or None

    def analyze_image(self, image_path: str, context: str = "") -> VisionAssessment:
        """Analyze an image file using Gemma 4 multimodal."""
        image_data = self._encode_image(image_path)
        mime_type = self._get_mime_type(image_path)

        url = f"{self.api_base}/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "parts": [
                        {"inlineData": {"mimeType": mime_type, "data": image_data}},
                        {"text": f"Analyze this image for humanitarian crisis indicators. Context: {context}" if context else "Analyze this image for humanitarian crisis indicators."},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }

        kwargs = {"timeout": 60}
        if self.proxy:
            kwargs["proxy"] = self.proxy

        with httpx.Client(**kwargs) as client:
            resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            data = resp.json()

        text = self._extract_text(data)
        return self._parse_response(text)

    def analyze_image_base64(self, b64_data: str, mime_type: str = "image/jpeg", context: str = "") -> VisionAssessment:
        """Analyze a base64-encoded image."""
        url = f"{self.api_base}/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "parts": [
                        {"inlineData": {"mimeType": mime_type, "data": b64_data}},
                        {"text": f"Analyze this image for humanitarian crisis indicators. Context: {context}" if context else "Analyze this image for humanitarian crisis indicators."},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }

        kwargs = {"timeout": 60}
        if self.proxy:
            kwargs["proxy"] = self.proxy

        with httpx.Client(**kwargs) as client:
            resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            data = resp.json()

        text = self._extract_text(data)
        return self._parse_response(text)

    def _encode_image(self, path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_mime_type(self, path: str) -> str:
        ext = Path(path).suffix.lower()
        return {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "image/jpeg")

    def _extract_text(self, data: dict) -> str:
        candidates = data.get("candidates", [{}])
        if not candidates:
            return "{}"
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p["text"] for p in parts if "text" in p and not p.get("thought")]
        return "\n".join(text_parts)

    def _parse_response(self, text: str) -> VisionAssessment:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        try:
            d = json.loads(text)
            return VisionAssessment(
                scene_description=d.get("scene_description", ""),
                crisis_indicators=d.get("crisis_indicators", []),
                severity_estimate=d.get("severity_estimate", "unknown"),
                affected_nodes=d.get("affected_nodes", []),
                recommendations=d.get("recommendations", ""),
            )
        except json.JSONDecodeError:
            return VisionAssessment(
                scene_description=text[:200],
                crisis_indicators=[],
                severity_estimate="unknown",
                affected_nodes=[],
                recommendations="Could not parse structured response.",
            )

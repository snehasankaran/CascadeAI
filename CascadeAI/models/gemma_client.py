"""Unified Gemma 4 client — works with Google AI Studio (cloud) and Ollama
(local/edge). Auto-detects which API format to use based on the endpoint.

Switch backend by changing environment variables:
    GEMMA_API_BASE  — e.g. https://generativelanguage.googleapis.com/v1beta
    GEMMA_API_KEY   — your API key (use "ollama" for local)
    GEMMA_MODEL     — e.g. gemma-4-31b-it or gemma4:e2b
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

DEFAULT_API_BASE = "http://localhost:11434/v1"
DEFAULT_MODEL = "gemma4:e2b"

GOOGLE_AI_STUDIO = "generativelanguage.googleapis.com"


@dataclass
class GemmaClient:
    """HTTP client that auto-switches between Google AI Studio (native Gemini API)
    and Ollama (OpenAI-compatible API)."""

    api_base: str = field(default_factory=lambda: os.getenv("GEMMA_API_BASE", DEFAULT_API_BASE))
    api_key: str = field(default_factory=lambda: os.getenv("GEMMA_API_KEY", "ollama"))
    model: str = field(default_factory=lambda: os.getenv("GEMMA_MODEL", DEFAULT_MODEL))
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: float = 120.0
    proxy: str = field(default_factory=lambda: os.getenv("HTTPS_PROXY", os.getenv("HTTP_PROXY", "")))

    @property
    def _is_google(self) -> bool:
        return GOOGLE_AI_STUDIO in self.api_base

    @property
    def _http_kwargs(self) -> dict:
        kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self.proxy:
            kwargs["proxy"] = self.proxy
        return kwargs

    # ------------------------------------------------------------------
    # Google AI Studio (native Gemini API)
    # ------------------------------------------------------------------

    def _google_url(self) -> str:
        base = self.api_base.rstrip("/")
        return f"{base}/models/{self.model}:generateContent?key={self.api_key}"

    def _to_google_payload(
        self, messages: list[dict], temperature: float, max_tokens: int,
        tools: Optional[list[dict]] = None,
    ) -> dict:
        contents = []
        system_text = ""

        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "system":
                system_text = text
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": text}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        if tools:
            google_tools = self._convert_tools_to_google(tools)
            if google_tools:
                payload["tools"] = google_tools

        return payload

    def _convert_tools_to_google(self, openai_tools: list[dict]) -> list[dict]:
        declarations = []
        for t in openai_tools:
            fn = t.get("function", {})
            declarations.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
            })
        return [{"functionDeclarations": declarations}] if declarations else []

    def _parse_google_response(self, data: dict) -> dict:
        """Convert Google AI Studio response to OpenAI-compatible format."""
        candidates = data.get("candidates", [{}])
        if not candidates:
            return {"choices": [{"message": {"content": "No response generated."}}]}

        parts = candidates[0].get("content", {}).get("parts", [])

        text_parts = [p["text"] for p in parts if "text" in p and not p.get("thought")]
        content = "\n".join(text_parts) if text_parts else ""

        fn_calls = [p["functionCall"] for p in parts if "functionCall" in p]

        message: dict[str, Any] = {"role": "assistant", "content": content}

        if fn_calls:
            message["tool_calls"] = [
                {
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": fc["name"],
                        "arguments": json.dumps(fc.get("args", {})),
                    },
                }
                for i, fc in enumerate(fn_calls)
            ]

        return {"choices": [{"message": message}]}

    # ------------------------------------------------------------------
    # Ollama (OpenAI-compatible)
    # ------------------------------------------------------------------

    def _ollama_url(self) -> str:
        return f"{self.api_base.rstrip('/')}/chat/completions"

    def _ollama_headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _to_ollama_payload(
        self, messages: list[dict], temperature: float, max_tokens: int,
        tools: Optional[list[dict]] = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
        return payload

    # ------------------------------------------------------------------
    # Unified interface
    # ------------------------------------------------------------------

    def chat_sync(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """Send a chat completion request. Returns OpenAI-compatible format."""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        with httpx.Client(**self._http_kwargs) as client:
            if self._is_google:
                url = self._google_url()
                payload = self._to_google_payload(messages, temp, tokens, tools)
                resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
                resp.raise_for_status()
                return self._parse_google_response(resp.json())
            else:
                url = self._ollama_url()
                payload = self._to_ollama_payload(messages, temp, tokens, tools)
                resp = client.post(url, json=payload, headers=self._ollama_headers())
                resp.raise_for_status()
                return resp.json()

    async def chat(
        self,
        messages: list[dict[str, str]],
        tools: Optional[list[dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """Async version of chat_sync()."""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        async with httpx.AsyncClient(**self._http_kwargs) as client:
            if self._is_google:
                url = self._google_url()
                payload = self._to_google_payload(messages, temp, tokens, tools)
                resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                resp.raise_for_status()
                return self._parse_google_response(resp.json())
            else:
                url = self._ollama_url()
                payload = self._to_ollama_payload(messages, temp, tokens, tools)
                resp = await client.post(url, json=payload, headers=self._ollama_headers())
                resp.raise_for_status()
                return resp.json()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def complete(self, system: str, user: str, **kwargs) -> str:
        """Simple system+user -> assistant text response."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resp = self.chat_sync(messages, **kwargs)
        return resp["choices"][0]["message"]["content"]

    def complete_with_tools(
        self,
        system: str,
        user: str,
        tools: list[dict],
        **kwargs,
    ) -> dict[str, Any]:
        """System+user+tools -> full message (may contain tool_calls)."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resp = self.chat_sync(messages, tools=tools, **kwargs)
        return resp["choices"][0]["message"]

    def extract_tool_calls(self, message: dict) -> list[dict]:
        """Pull structured tool calls from a response message."""
        raw = message.get("tool_calls", [])
        results = []
        for tc in raw:
            fn = tc.get("function", {})
            args = fn.get("arguments", "{}")
            if isinstance(args, str):
                args = json.loads(args)
            results.append({
                "id": tc.get("id"),
                "name": fn.get("name"),
                "arguments": args,
            })
        return results

    def __repr__(self) -> str:
        backend = "Google AI Studio" if self._is_google else "Ollama"
        return f"GemmaClient(model={self.model!r}, backend={backend})"

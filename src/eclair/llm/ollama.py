"""Ollama provider adapter (M02).

Ollama is the permanent zero-cost local fallback (Spec sec.4.11). Talks to the
local Ollama HTTP API (``/api/generate``) via HTTPX. Implements the same
``LLMProvider`` interface as every other provider through ``BaseHTTPProvider``.
"""

from __future__ import annotations

from typing import Any

from eclair.llm.base import BaseHTTPProvider, LLMRequest

__all__ = ["OllamaProvider"]


class OllamaProvider(BaseHTTPProvider):
    """Adapter for a local Ollama server."""

    name = "ollama"

    def _build_request(
        self, request: LLMRequest, model: str
    ) -> tuple[str, dict[str, Any], dict[str, str]]:
        url = f"{self._base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": model,
            "prompt": request.prompt,
            "stream": False,
        }
        if request.json_mode:
            payload["format"] = "json"
        options: dict[str, Any] = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        if options:
            payload["options"] = options
        return url, payload, {}

    def _parse_response(self, data: dict[str, Any]) -> str:
        return data["response"]

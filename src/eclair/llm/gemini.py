"""Gemini provider adapter (M02).

Optional free-tier provider (Spec sec.4.11). Talks to the Google Generative
Language ``generateContent`` HTTP API via HTTPX. Implements the same
``LLMProvider`` interface as every other provider through ``BaseHTTPProvider``.
The API key is supplied via M01 configuration and passed as a query parameter;
it is never hardcoded.
"""

from __future__ import annotations

from typing import Any

from eclair.llm.base import BaseHTTPProvider, LLMRequest

__all__ = ["GeminiProvider"]


class GeminiProvider(BaseHTTPProvider):
    """Adapter for the Gemini generateContent API."""

    name = "gemini"

    def __init__(
        self, *, base_url: str, model: str, timeout_seconds: float, api_key: str
    ) -> None:
        super().__init__(base_url=base_url, model=model, timeout_seconds=timeout_seconds)
        self._api_key = api_key

    def _build_request(
        self, request: LLMRequest, model: str
    ) -> tuple[str, dict[str, Any], dict[str, str]]:
        url = f"{self._base_url}/models/{model}:generateContent?key={self._api_key}"
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": request.prompt}]}],
        }
        generation_config: dict[str, Any] = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if request.json_mode:
            generation_config["responseMimeType"] = "application/json"
        if generation_config:
            payload["generationConfig"] = generation_config
        return url, payload, {}

    def _parse_response(self, data: dict[str, Any]) -> str:
        return data["candidates"][0]["content"]["parts"][0]["text"]

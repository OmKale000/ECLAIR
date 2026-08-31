"""OpenRouter provider adapter (M02).

Optional free-tier provider (Spec sec.4.11). Talks to OpenRouter's
OpenAI-compatible chat-completions HTTP API via HTTPX. Implements the same
``LLMProvider`` interface as every other provider through ``BaseHTTPProvider``.
The API key is supplied via M01 configuration and passed as a bearer token; it
is never hardcoded.
"""

from __future__ import annotations

from typing import Any

from eclair.llm.base import BaseHTTPProvider, LLMRequest

__all__ = ["OpenRouterProvider"]


class OpenRouterProvider(BaseHTTPProvider):
    """Adapter for the OpenRouter chat-completions API."""

    name = "openrouter"

    def __init__(
        self, *, base_url: str, model: str, timeout_seconds: float, api_key: str
    ) -> None:
        super().__init__(base_url=base_url, model=model, timeout_seconds=timeout_seconds)
        self._api_key = api_key

    def _build_request(
        self, request: LLMRequest, model: str
    ) -> tuple[str, dict[str, Any], dict[str, str]]:
        url = f"{self._base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self._api_key}"}
        return url, payload, headers

    def _parse_response(self, data: dict[str, Any]) -> str:
        return data["choices"][0]["message"]["content"]

"""LLM Gateway base types and provider base class (M02).

Defines the module-owned request/response contracts and a shared HTTP provider
base. ``LLMRequest`` / ``LLMResponse`` are owned by M02 (see
``eclair.contracts.interfaces`` note: the ``LLMProvider`` Protocol positions
those types as ``Any`` and leaves M02 to refine them within its boundary).

Every concrete provider (Ollama/Gemini/Groq/OpenRouter) subclasses
``BaseHTTPProvider`` and therefore conforms to the frozen M01
``LLMProvider`` Protocol: ``generate(request) -> response``.

This module implements NO reliability logic (no claim extraction, retrieval,
verification, confidence, calibration, risk, or persistence). It only performs
text / structured-JSON generation. Errors use the shared M01 exception hierarchy
(``eclair.exceptions``); no new error format is introduced.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from eclair.exceptions import ModuleError

__all__ = ["LLMRequest", "LLMResponse", "BaseHTTPProvider"]


class LLMRequest(BaseModel):
    """A provider-agnostic generation request (M02-owned contract).

    Carries the prompt, an optional model override (model selection), generic
    generation parameters, and a flag requesting structured JSON output.
    """

    model_config = {"extra": "forbid"}

    prompt: str = Field(
        ...,
        min_length=1,
        description="The prompt text to generate from.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model override; when None the provider's configured model is used.",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Optional sampling temperature.",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Optional maximum number of tokens to generate.",
    )
    json_mode: bool = Field(
        default=False,
        description="When True, request structured JSON generation.",
    )


class LLMResponse(BaseModel):
    """A provider-agnostic generation response (M02-owned contract).

    ``text`` is the raw generated text. When the request used ``json_mode`` and
    the text parsed as JSON, ``structured`` holds the parsed object; otherwise it
    is ``None``.
    """

    model_config = {"extra": "forbid"}

    text: str = Field(
        ...,
        description="The generated text returned by the provider.",
    )
    model: str = Field(
        ...,
        min_length=1,
        description="The model that produced the response.",
    )
    provider: str = Field(
        ...,
        min_length=1,
        description="The provider name that produced the response.",
    )
    structured: Any | None = Field(
        default=None,
        description="Parsed JSON object when json_mode produced valid JSON; else None.",
    )


class BaseHTTPProvider(ABC):
    """Shared HTTP provider base implementing the M01 ``LLMProvider`` Protocol.

    Subclasses supply provider-specific request-building and response-parsing.
    This base owns the HTTPX call, timeout enforcement, and mapping of transport
    and decoding failures onto the shared ``ModuleError``.
    """

    #: Stable provider name (e.g. "ollama"); set by each subclass.
    name: str

    def __init__(self, *, base_url: str, model: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    @property
    def model(self) -> str:
        """The provider's configured default model."""
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response for ``request`` (conforms to M01 LLMProvider).

        Validates the request, dispatches a single HTTP call under the configured
        timeout, and returns a parsed ``LLMResponse``. Transport, timeout, HTTP
        status, and decoding failures are raised as ``ModuleError`` (no error
        format is invented). Retries and fallback are handled by the router, not
        here.
        """
        if not isinstance(request, LLMRequest):
            try:
                request = LLMRequest.model_validate(request)
            except ValidationError as exc:
                raise ModuleError(
                    f"Invalid LLMRequest for provider {self.name!r}: {exc}",
                    code="llm_invalid_request",
                ) from exc

        model = request.model or self._model
        url, payload, headers = self._build_request(request, model)

        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as exc:
            raise ModuleError(
                f"Provider {self.name!r} timed out after {self._timeout_seconds}s",
                code="llm_timeout",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ModuleError(
                f"Provider {self.name!r} returned HTTP {exc.response.status_code}",
                code="llm_http_error",
            ) from exc
        except httpx.HTTPError as exc:
            raise ModuleError(
                f"Provider {self.name!r} request failed: {exc}",
                code="llm_request_failed",
            ) from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise ModuleError(
                f"Provider {self.name!r} returned undecodable response: {exc}",
                code="llm_bad_response",
            ) from exc

        try:
            text = self._parse_response(data)
        except (KeyError, IndexError, TypeError) as exc:
            raise ModuleError(
                f"Provider {self.name!r} returned an unexpected response shape: {exc}",
                code="llm_bad_response",
            ) from exc

        structured = self._maybe_parse_json(text) if request.json_mode else None
        return LLMResponse(
            text=text,
            model=model,
            provider=self.name,
            structured=structured,
        )

    @staticmethod
    def _maybe_parse_json(text: str) -> Any | None:
        """Return parsed JSON for ``text`` or ``None`` if it is not valid JSON."""
        try:
            return json.loads(text)
        except (ValueError, json.JSONDecodeError):
            return None

    @abstractmethod
    def _build_request(
        self, request: LLMRequest, model: str
    ) -> tuple[str, dict[str, Any], dict[str, str]]:
        """Build the ``(url, json_payload, headers)`` for the provider call."""
        raise NotImplementedError

    @abstractmethod
    def _parse_response(self, data: dict[str, Any]) -> str:
        """Extract the generated text from the decoded provider response body."""
        raise NotImplementedError

"""LLM router / gateway (M02).

The provider-agnostic entry point callers use as ``llm.generate(request)``.
Owns routing (active provider selection), retry handling, and provider-failure
fallback to Ollama (the permanent zero-cost fallback, Spec sec.4.11). Model
selection is honoured per-request via ``LLMRequest.model`` (handled by the
providers) — the router does not reinterpret it.

This module performs NO reliability logic; it only routes generation calls.
All failures surface through the shared M01 ``ModuleError``.
"""

from __future__ import annotations

from eclair.config import LLMProviderConfig
from eclair.exceptions import ModuleError
from eclair.llm.base import BaseHTTPProvider, LLMRequest, LLMResponse
from eclair.llm.factory import build_provider

__all__ = ["LLMRouter", "FALLBACK_PROVIDER"]

#: Provider used as the permanent zero-cost fallback (Spec sec.4.11).
FALLBACK_PROVIDER = "ollama"


class LLMRouter:
    """Routes generation through the active provider with retries and fallback.

    Callers depend only on ``generate(request) -> LLMResponse`` and remain
    provider-agnostic. The router builds providers from the shared
    ``LLMProviderConfig`` via the factory, retries the active provider up to
    ``config.retries`` additional attempts, and falls back to Ollama if the
    active provider ultimately fails (unless Ollama already is the active
    provider).
    """

    def __init__(
        self, config: LLMProviderConfig, *, provider: BaseHTTPProvider | None = None
    ) -> None:
        self._config = config
        self._active_name = config.active_provider
        # Allow an explicit provider injection (used in tests); otherwise build
        # the configured active provider from the factory.
        self._active_provider = provider or build_provider(self._active_name, config)

    @property
    def active_provider(self) -> str:
        """Name of the active provider this router routes to first."""
        return self._active_name

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response, retrying the active provider then falling back.

        Order of attempts:
            1. Active provider, retried up to ``config.retries`` extra times.
            2. If the active provider is not Ollama, fall back to Ollama
               (also retried up to ``config.retries`` extra times).

        Raises:
            ModuleError: if the active provider and the fallback both fail.
        """
        try:
            return self._attempt(self._active_provider, request)
        except ModuleError as active_exc:
            if self._active_name == FALLBACK_PROVIDER:
                raise
            try:
                fallback = build_provider(FALLBACK_PROVIDER, self._config)
                return self._attempt(fallback, request)
            except ModuleError as fallback_exc:
                raise ModuleError(
                    f"Active provider {self._active_name!r} and fallback "
                    f"{FALLBACK_PROVIDER!r} both failed: {fallback_exc}",
                    code="llm_all_providers_failed",
                ) from active_exc

    def _attempt(
        self, provider: BaseHTTPProvider, request: LLMRequest
    ) -> LLMResponse:
        """Attempt generation with ``provider``, retrying on ModuleError."""
        attempts = self._config.retries + 1
        last_exc: ModuleError | None = None
        for _ in range(attempts):
            try:
                return provider.generate(request)
            except ModuleError as exc:
                last_exc = exc
        assert last_exc is not None  # noqa: S101 - loop runs >= 1 time
        raise last_exc

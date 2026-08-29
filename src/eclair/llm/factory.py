"""Provider factory (M02).

Builds concrete provider adapters from the shared M01 ``LLMProviderConfig``
(``eclair.config``). Reads provider endpoints/models/keys from configuration
only — nothing is hardcoded and no configuration mechanism is introduced here.

Ollama is always buildable (permanent zero-cost local fallback, Spec sec.4.11).
Optional providers (Gemini/Groq/OpenRouter) require their base_url, model, and
api_key to be configured; if any is missing, building them raises the shared
``ModuleError`` rather than silently substituting a default.
"""

from __future__ import annotations

from eclair.config import LLMProviderConfig
from eclair.exceptions import ModuleError
from eclair.llm.base import BaseHTTPProvider
from eclair.llm.gemini import GeminiProvider
from eclair.llm.groq import GroqProvider
from eclair.llm.ollama import OllamaProvider
from eclair.llm.openrouter import OpenRouterProvider

__all__ = ["build_provider", "SUPPORTED_PROVIDERS"]

#: Provider names recognised by this factory.
SUPPORTED_PROVIDERS: tuple[str, ...] = ("ollama", "gemini", "groq", "openrouter")


def build_provider(name: str, config: LLMProviderConfig) -> BaseHTTPProvider:
    """Construct the provider ``name`` from ``config``.

    Args:
        name: Provider name (one of ``SUPPORTED_PROVIDERS``).
        config: The shared M01 LLM-provider configuration.

    Returns:
        A concrete provider conforming to the M01 ``LLMProvider`` Protocol.

    Raises:
        ModuleError: if ``name`` is unknown or an optional provider is not fully
            configured.
    """
    if name == "ollama":
        return OllamaProvider(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
            timeout_seconds=config.timeout_seconds,
        )
    if name == "gemini":
        return _build_optional(
            GeminiProvider,
            name="gemini",
            base_url=config.gemini_base_url,
            model=config.gemini_model,
            api_key=config.gemini_api_key,
            timeout_seconds=config.timeout_seconds,
        )
    if name == "groq":
        return _build_optional(
            GroqProvider,
            name="groq",
            base_url=config.groq_base_url,
            model=config.groq_model,
            api_key=config.groq_api_key,
            timeout_seconds=config.timeout_seconds,
        )
    if name == "openrouter":
        return _build_optional(
            OpenRouterProvider,
            name="openrouter",
            base_url=config.openrouter_base_url,
            model=config.openrouter_model,
            api_key=config.openrouter_api_key,
            timeout_seconds=config.timeout_seconds,
        )
    raise ModuleError(
        f"Unknown LLM provider {name!r}; supported: {', '.join(SUPPORTED_PROVIDERS)}",
        code="llm_unknown_provider",
    )


def _build_optional(
    provider_cls: type[BaseHTTPProvider],
    *,
    name: str,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
    timeout_seconds: float,
) -> BaseHTTPProvider:
    """Build an optional provider, requiring full configuration."""
    missing = [
        field
        for field, value in (
            ("base_url", base_url),
            ("model", model),
            ("api_key", api_key),
        )
        if not value
    ]
    if missing:
        raise ModuleError(
            f"Provider {name!r} is not configured (missing: {', '.join(missing)})",
            code="llm_provider_unconfigured",
        )
    return provider_cls(
        base_url=base_url,  # type: ignore[arg-type]
        model=model,  # type: ignore[arg-type]
        timeout_seconds=timeout_seconds,
        api_key=api_key,  # type: ignore[arg-type]
    )

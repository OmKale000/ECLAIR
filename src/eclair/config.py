"""Shared application configuration for ECLAIR (M01 Foundation).

Provides the single, shared configuration mechanism that every module reuses
(COMMON_RULES sec.10). Built on Pydantic v2 for validation, with values loaded
from environment variables via the standard library only — no configuration
library beyond the approved stack is added.

Modules MUST NOT hardcode values that belong here, and MUST NOT invent their own
configuration mechanism.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field, ValidationError

from eclair.exceptions import ConfigurationError

__all__ = ["EclairConfig", "LLMProviderConfig", "load_config"]


class LLMProviderConfig(BaseModel):
    """Generic, validated LLM-provider configuration (M01 Foundation).

    This carries only the generic provider-configuration values needed to
    *construct* a provider. It encodes NO routing/fallback/HTTP/reliability
    logic (that is M02, the LLM Gateway) and NO provider-specific behaviour.

    The default ``active_provider`` and the default Ollama base URL/model reflect
    the permanent zero-cost local fallback (Spec sec.4.11); they are default
    *values*, not hardcoded behaviour. ``active_provider`` is a free-form string,
    not an enum, so M02 may recognise additional providers without changing M01.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    active_provider: str = Field(
        default="ollama",
        min_length=1,
        description="Name of the provider a consumer should build by default (free-form).",
    )
    timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Generic request timeout in seconds (must be > 0).",
    )
    retries: int = Field(
        default=2,
        ge=0,
        description="Generic retry count (must be >= 0).",
    )

    # Ollama — permanent zero-cost local fallback (Spec sec.4.11).
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the local Ollama provider.",
    )
    ollama_model: str = Field(
        default="llama3",
        description="Model name for the Ollama provider.",
    )

    # Gemini — optional provider (free quota only; may be unconfigured).
    gemini_api_key: str | None = Field(
        default=None,
        description="API key for Gemini; None when not configured.",
    )
    gemini_base_url: str | None = Field(
        default=None,
        description="Base URL for Gemini; None when not configured.",
    )
    gemini_model: str | None = Field(
        default=None,
        description="Model name for Gemini; None when not configured.",
    )

    # Groq — optional provider (free quota only; may be unconfigured).
    groq_api_key: str | None = Field(
        default=None,
        description="API key for Groq; None when not configured.",
    )
    groq_base_url: str | None = Field(
        default=None,
        description="Base URL for Groq; None when not configured.",
    )
    groq_model: str | None = Field(
        default=None,
        description="Model name for Groq; None when not configured.",
    )

    # OpenRouter — optional provider (free quota only; may be unconfigured).
    openrouter_api_key: str | None = Field(
        default=None,
        description="API key for OpenRouter; None when not configured.",
    )
    openrouter_base_url: str | None = Field(
        default=None,
        description="Base URL for OpenRouter; None when not configured.",
    )
    openrouter_model: str | None = Field(
        default=None,
        description="Model name for OpenRouter; None when not configured.",
    )


class EclairConfig(BaseModel):
    """Shared, validated ECLAIR configuration.

    Fields are intentionally minimal for the Foundation module. Later modules
    that require additional configuration must propose new fields through M01
    rather than introducing a separate configuration mechanism.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    environment: str = Field(
        default="development",
        description="Deployment environment name (e.g. development, production).",
    )
    debug: bool = Field(
        default=False,
        description="Whether debug behaviour is enabled.",
    )
    llm: LLMProviderConfig = Field(
        default_factory=LLMProviderConfig,
        description="Generic LLM-provider configuration consumed by the LLM Gateway (M02).",
    )


def load_config() -> EclairConfig:
    """Build an :class:`EclairConfig` from environment variables.

    Recognised variables:
        ECLAIR_ENVIRONMENT      -> environment
        ECLAIR_DEBUG            -> debug (truthy: "1", "true", "yes", case-insensitive)

        LLM provider configuration (populates ``EclairConfig.llm``):
        ECLAIR_LLM_ACTIVE_PROVIDER  -> llm.active_provider
        ECLAIR_LLM_TIMEOUT_SECONDS  -> llm.timeout_seconds (float > 0)
        ECLAIR_LLM_RETRIES          -> llm.retries (int >= 0)
        OLLAMA_BASE_URL             -> llm.ollama_base_url
        OLLAMA_MODEL                -> llm.ollama_model
        GEMINI_API_KEY              -> llm.gemini_api_key
        GEMINI_BASE_URL             -> llm.gemini_base_url
        GEMINI_MODEL                -> llm.gemini_model
        GROQ_API_KEY                -> llm.groq_api_key
        GROQ_BASE_URL               -> llm.groq_base_url
        GROQ_MODEL                  -> llm.groq_model
        OPENROUTER_API_KEY          -> llm.openrouter_api_key
        OPENROUTER_BASE_URL         -> llm.openrouter_base_url
        OPENROUTER_MODEL            -> llm.openrouter_model

    Missing variables fall back to safe defaults (Ollama local is the permanent
    zero-cost fallback, Spec sec.4.11).

    Raises:
        ConfigurationError: if the resolved values fail validation.
    """
    raw_debug = os.getenv("ECLAIR_DEBUG", "")
    debug = raw_debug.strip().lower() in {"1", "true", "yes"}

    llm_defaults = LLMProviderConfig()

    llm_fields: dict[str, object] = {
        "active_provider": os.getenv(
            "ECLAIR_LLM_ACTIVE_PROVIDER", llm_defaults.active_provider
        ),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", llm_defaults.ollama_base_url),
        "ollama_model": os.getenv("OLLAMA_MODEL", llm_defaults.ollama_model),
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
        "gemini_base_url": os.getenv("GEMINI_BASE_URL"),
        "gemini_model": os.getenv("GEMINI_MODEL"),
        "groq_api_key": os.getenv("GROQ_API_KEY"),
        "groq_base_url": os.getenv("GROQ_BASE_URL"),
        "groq_model": os.getenv("GROQ_MODEL"),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
        "openrouter_base_url": os.getenv("OPENROUTER_BASE_URL"),
        "openrouter_model": os.getenv("OPENROUTER_MODEL"),
    }

    raw_timeout = os.getenv("ECLAIR_LLM_TIMEOUT_SECONDS")
    if raw_timeout is not None:
        try:
            llm_fields["timeout_seconds"] = float(raw_timeout)
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid ECLAIR_LLM_TIMEOUT_SECONDS: {raw_timeout!r} is not a number",
                code="config_invalid",
            ) from exc

    raw_retries = os.getenv("ECLAIR_LLM_RETRIES")
    if raw_retries is not None:
        try:
            llm_fields["retries"] = int(raw_retries)
        except ValueError as exc:
            raise ConfigurationError(
                f"Invalid ECLAIR_LLM_RETRIES: {raw_retries!r} is not an integer",
                code="config_invalid",
            ) from exc

    try:
        return EclairConfig(
            environment=os.getenv("ECLAIR_ENVIRONMENT", "development"),
            debug=debug,
            llm=LLMProviderConfig(**llm_fields),
        )
    except ValidationError as exc:
        raise ConfigurationError(
            f"Invalid ECLAIR configuration: {exc}", code="config_invalid"
        ) from exc

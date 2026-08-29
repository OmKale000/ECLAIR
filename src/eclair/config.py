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

__all__ = ["EclairConfig", "load_config"]


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


def load_config() -> EclairConfig:
    """Build an :class:`EclairConfig` from environment variables.

    Recognised variables:
        ECLAIR_ENVIRONMENT -> environment
        ECLAIR_DEBUG       -> debug (truthy: "1", "true", "yes", case-insensitive)

    Raises:
        ConfigurationError: if the resolved values fail validation.
    """
    raw_debug = os.getenv("ECLAIR_DEBUG", "")
    debug = raw_debug.strip().lower() in {"1", "true", "yes"}

    try:
        return EclairConfig(
            environment=os.getenv("ECLAIR_ENVIRONMENT", "development"),
            debug=debug,
        )
    except ValidationError as exc:  # pragma: no cover - defensive mapping
        raise ConfigurationError(
            f"Invalid ECLAIR configuration: {exc}", code="config_invalid"
        ) from exc

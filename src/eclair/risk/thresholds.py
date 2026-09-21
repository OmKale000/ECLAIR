"""Configurable risk and decision policy thresholds for M13.

Provides the validated threshold configuration for ECS evaluation, risk levels,
hallucination boundaries, and reflection limits.
Reuses M01 ConfigurationError when environment variable resolution fails.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field, ValidationError, model_validator

from eclair.exceptions import ConfigurationError

__all__ = [
    "DEFAULT_HIGH_ECS_THRESHOLD",
    "DEFAULT_LOW_ECS_THRESHOLD",
    "DEFAULT_HALLUCINATION_THRESHOLD",
    "DEFAULT_CRITICAL_RISK_THRESHOLD",
    "DEFAULT_HIGH_RISK_THRESHOLD",
    "DEFAULT_MEDIUM_RISK_THRESHOLD",
    "DEFAULT_MIN_AGREEMENT_THRESHOLD",
    "DEFAULT_MAX_UNKNOWN_RATIO",
    "DEFAULT_MAX_CONTRADICTED_CLAIMS",
    "DEFAULT_MAX_REFLECTION_ITERATIONS",
    "RiskThresholds",
    "load_risk_thresholds",
]

DEFAULT_HIGH_ECS_THRESHOLD: float = 0.70
DEFAULT_LOW_ECS_THRESHOLD: float = 0.40
DEFAULT_HALLUCINATION_THRESHOLD: float = 0.50
DEFAULT_CRITICAL_RISK_THRESHOLD: float = 0.80
DEFAULT_HIGH_RISK_THRESHOLD: float = 0.60
DEFAULT_MEDIUM_RISK_THRESHOLD: float = 0.30
DEFAULT_MIN_AGREEMENT_THRESHOLD: float = 0.50
DEFAULT_MAX_UNKNOWN_RATIO: float = 0.50
DEFAULT_MAX_CONTRADICTED_CLAIMS: int = 0
DEFAULT_MAX_REFLECTION_ITERATIONS: int = 3


class RiskThresholds(BaseModel):
    """Validated threshold settings for M13 Risk & Decision Engine."""

    model_config = {"frozen": True, "extra": "forbid"}

    high_ecs_threshold: float = Field(
        default=DEFAULT_HIGH_ECS_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum calibrated ECS required for high-confidence RETURN.",
    )
    low_ecs_threshold: float = Field(
        default=DEFAULT_LOW_ECS_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Threshold below which ECS is considered low confidence (triggers reflection/abstain).",
    )
    hallucination_threshold: float = Field(
        default=DEFAULT_HALLUCINATION_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Hallucination probability above which a response is flagged as high-risk hallucination.",
    )
    critical_risk_threshold: float = Field(
        default=DEFAULT_CRITICAL_RISK_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Risk score at or above which risk level is CRITICAL.",
    )
    high_risk_threshold: float = Field(
        default=DEFAULT_HIGH_RISK_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Risk score at or above which risk level is HIGH.",
    )
    medium_risk_threshold: float = Field(
        default=DEFAULT_MEDIUM_RISK_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Risk score at or above which risk level is MEDIUM.",
    )
    min_agreement_threshold: float = Field(
        default=DEFAULT_MIN_AGREEMENT_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum model agreement score before disagreement adds to risk.",
    )
    max_unknown_ratio: float = Field(
        default=DEFAULT_MAX_UNKNOWN_RATIO,
        ge=0.0,
        le=1.0,
        description="Maximum fraction of UNKNOWN verified claims tolerated before requesting VERIFY_MORE.",
    )
    max_contradicted_claims: int = Field(
        default=DEFAULT_MAX_CONTRADICTED_CLAIMS,
        ge=0,
        description="Maximum number of CONTRADICTED claims tolerated before rejecting RETURN.",
    )
    max_reflection_iterations: int = Field(
        default=DEFAULT_MAX_REFLECTION_ITERATIONS,
        ge=1,
        description="Maximum reflection iterations allowed before ABSTAIN is enforced on low ECS.",
    )

    @model_validator(mode="after")
    def validate_threshold_relationships(self) -> RiskThresholds:
        """Validate logical ordering between related thresholds."""
        if self.low_ecs_threshold > self.high_ecs_threshold:
            raise ValueError(
                f"low_ecs_threshold ({self.low_ecs_threshold}) cannot exceed "
                f"high_ecs_threshold ({self.high_ecs_threshold})."
            )
        if not (
            self.medium_risk_threshold
            <= self.high_risk_threshold
            <= self.critical_risk_threshold
        ):
            raise ValueError(
                f"Risk thresholds must follow medium ({self.medium_risk_threshold}) <= "
                f"high ({self.high_risk_threshold}) <= critical ({self.critical_risk_threshold})."
            )
        return self


def load_risk_thresholds() -> RiskThresholds:
    """Build a RiskThresholds instance from environment variables with safe defaults.

    Recognised environment variables:
        ECLAIR_RISK_HIGH_ECS_THRESHOLD         -> high_ecs_threshold (float 0.0-1.0)
        ECLAIR_RISK_LOW_ECS_THRESHOLD          -> low_ecs_threshold (float 0.0-1.0)
        ECLAIR_RISK_HALLUCINATION_THRESHOLD    -> hallucination_threshold (float 0.0-1.0)
        ECLAIR_RISK_CRITICAL_RISK_THRESHOLD    -> critical_risk_threshold (float 0.0-1.0)
        ECLAIR_RISK_HIGH_RISK_THRESHOLD        -> high_risk_threshold (float 0.0-1.0)
        ECLAIR_RISK_MEDIUM_RISK_THRESHOLD      -> medium_risk_threshold (float 0.0-1.0)
        ECLAIR_RISK_MIN_AGREEMENT_THRESHOLD    -> min_agreement_threshold (float 0.0-1.0)
        ECLAIR_RISK_MAX_UNKNOWN_RATIO          -> max_unknown_ratio (float 0.0-1.0)
        ECLAIR_RISK_MAX_CONTRADICTED_CLAIMS    -> max_contradicted_claims (int >= 0)
        ECLAIR_RISK_MAX_REFLECTION_ITERATIONS  -> max_reflection_iterations (int >= 1)

    Raises:
        ConfigurationError: if environment variables contain invalid values.
    """
    fields: dict[str, object] = {}

    float_mappings = {
        "ECLAIR_RISK_HIGH_ECS_THRESHOLD": "high_ecs_threshold",
        "ECLAIR_RISK_LOW_ECS_THRESHOLD": "low_ecs_threshold",
        "ECLAIR_RISK_HALLUCINATION_THRESHOLD": "hallucination_threshold",
        "ECLAIR_RISK_CRITICAL_RISK_THRESHOLD": "critical_risk_threshold",
        "ECLAIR_RISK_HIGH_RISK_THRESHOLD": "high_risk_threshold",
        "ECLAIR_RISK_MEDIUM_RISK_THRESHOLD": "medium_risk_threshold",
        "ECLAIR_RISK_MIN_AGREEMENT_THRESHOLD": "min_agreement_threshold",
        "ECLAIR_RISK_MAX_UNKNOWN_RATIO": "max_unknown_ratio",
    }

    for env_var, field_name in float_mappings.items():
        val = os.getenv(env_var)
        if val is not None:
            try:
                fields[field_name] = float(val)
            except ValueError as exc:
                raise ConfigurationError(
                    f"Invalid {env_var}: {val!r} is not a valid float",
                    code="config_invalid",
                ) from exc

    int_mappings = {
        "ECLAIR_RISK_MAX_CONTRADICTED_CLAIMS": "max_contradicted_claims",
        "ECLAIR_RISK_MAX_REFLECTION_ITERATIONS": "max_reflection_iterations",
    }

    for env_var, field_name in int_mappings.items():
        val = os.getenv(env_var)
        if val is not None:
            try:
                fields[field_name] = int(val)
            except ValueError as exc:
                raise ConfigurationError(
                    f"Invalid {env_var}: {val!r} is not a valid integer",
                    code="config_invalid",
                ) from exc

    try:
        return RiskThresholds(**fields)
    except (ValidationError, ValueError) as exc:
        raise ConfigurationError(
            f"Invalid risk threshold configuration: {exc}",
            code="config_invalid",
        ) from exc

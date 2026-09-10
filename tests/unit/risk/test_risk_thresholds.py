"""Unit tests for M13 Risk & Decision Engine thresholds and configuration (Spec sec.M13)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair.exceptions import ConfigurationError
from eclair.risk.thresholds import (
    DEFAULT_CRITICAL_RISK_THRESHOLD,
    DEFAULT_HALLUCINATION_THRESHOLD,
    DEFAULT_HIGH_ECS_THRESHOLD,
    DEFAULT_HIGH_RISK_THRESHOLD,
    DEFAULT_LOW_ECS_THRESHOLD,
    DEFAULT_MAX_CONTRADICTED_CLAIMS,
    DEFAULT_MAX_REFLECTION_ITERATIONS,
    DEFAULT_MAX_UNKNOWN_RATIO,
    DEFAULT_MEDIUM_RISK_THRESHOLD,
    DEFAULT_MIN_AGREEMENT_THRESHOLD,
    RiskThresholds,
    load_risk_thresholds,
)


def test_default_threshold_values() -> None:
    """Verify default threshold constants match specifications."""
    thresholds = RiskThresholds()
    assert thresholds.high_ecs_threshold == DEFAULT_HIGH_ECS_THRESHOLD
    assert thresholds.low_ecs_threshold == DEFAULT_LOW_ECS_THRESHOLD
    assert thresholds.hallucination_threshold == DEFAULT_HALLUCINATION_THRESHOLD
    assert thresholds.critical_risk_threshold == DEFAULT_CRITICAL_RISK_THRESHOLD
    assert thresholds.high_risk_threshold == DEFAULT_HIGH_RISK_THRESHOLD
    assert thresholds.medium_risk_threshold == DEFAULT_MEDIUM_RISK_THRESHOLD
    assert thresholds.min_agreement_threshold == DEFAULT_MIN_AGREEMENT_THRESHOLD
    assert thresholds.max_unknown_ratio == DEFAULT_MAX_UNKNOWN_RATIO
    assert thresholds.max_contradicted_claims == DEFAULT_MAX_CONTRADICTED_CLAIMS
    assert thresholds.max_reflection_iterations == DEFAULT_MAX_REFLECTION_ITERATIONS


def test_custom_thresholds_valid() -> None:
    """Verify custom valid thresholds can be configured."""
    thresholds = RiskThresholds(
        high_ecs_threshold=0.85,
        low_ecs_threshold=0.50,
        hallucination_threshold=0.40,
        critical_risk_threshold=0.90,
        high_risk_threshold=0.70,
        medium_risk_threshold=0.40,
        max_reflection_iterations=5,
    )
    assert thresholds.high_ecs_threshold == 0.85
    assert thresholds.low_ecs_threshold == 0.50
    assert thresholds.max_reflection_iterations == 5


def test_threshold_ordering_validation() -> None:
    """Verify invalid relative threshold orderings raise ValidationError."""
    # low_ecs > high_ecs
    with pytest.raises(ValidationError, match="cannot exceed high_ecs_threshold"):
        RiskThresholds(low_ecs_threshold=0.80, high_ecs_threshold=0.60)

    # medium_risk > high_risk
    with pytest.raises(ValidationError, match="Risk thresholds must follow"):
        RiskThresholds(medium_risk_threshold=0.70, high_risk_threshold=0.50)

    # high_risk > critical_risk
    with pytest.raises(ValidationError, match="Risk thresholds must follow"):
        RiskThresholds(high_risk_threshold=0.85, critical_risk_threshold=0.75)


def test_threshold_out_of_bounds_validation() -> None:
    """Verify values outside [0.0, 1.0] are rejected."""
    with pytest.raises(ValidationError):
        RiskThresholds(high_ecs_threshold=1.1)

    with pytest.raises(ValidationError):
        RiskThresholds(low_ecs_threshold=-0.1)

    with pytest.raises(ValidationError):
        RiskThresholds(max_reflection_iterations=0)


def test_load_risk_thresholds_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify loading thresholds from environment variables."""
    monkeypatch.setenv("ECLAIR_RISK_HIGH_ECS_THRESHOLD", "0.82")
    monkeypatch.setenv("ECLAIR_RISK_LOW_ECS_THRESHOLD", "0.45")
    monkeypatch.setenv("ECLAIR_RISK_HALLUCINATION_THRESHOLD", "0.35")
    monkeypatch.setenv("ECLAIR_RISK_MAX_REFLECTION_ITERATIONS", "4")

    loaded = load_risk_thresholds()
    assert loaded.high_ecs_threshold == 0.82
    assert loaded.low_ecs_threshold == 0.45
    assert loaded.hallucination_threshold == 0.35
    assert loaded.max_reflection_iterations == 4


def test_load_risk_thresholds_invalid_float_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify non-numeric float env vars raise ConfigurationError."""
    monkeypatch.setenv("ECLAIR_RISK_HIGH_ECS_THRESHOLD", "invalid_float")
    with pytest.raises(ConfigurationError) as exc_info:
        load_risk_thresholds()
    assert exc_info.value.code == "config_invalid"
    assert "not a valid float" in str(exc_info.value)


def test_load_risk_thresholds_invalid_int_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify non-numeric int env vars raise ConfigurationError."""
    monkeypatch.setenv("ECLAIR_RISK_MAX_REFLECTION_ITERATIONS", "not_an_int")
    with pytest.raises(ConfigurationError) as exc_info:
        load_risk_thresholds()
    assert exc_info.value.code == "config_invalid"
    assert "not a valid integer" in str(exc_info.value)


def test_load_risk_thresholds_out_of_range_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify out-of-range env var values raise ConfigurationError."""
    monkeypatch.setenv("ECLAIR_RISK_HIGH_ECS_THRESHOLD", "1.5")
    with pytest.raises(ConfigurationError) as exc_info:
        load_risk_thresholds()
    assert exc_info.value.code == "config_invalid"

"""Unit tests for M10 Confidence Estimation data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair.confidence.models import (
    DEFAULT_WEIGHT_AGREEMENT,
    DEFAULT_WEIGHT_CONSISTENCY,
    DEFAULT_WEIGHT_EVIDENCE,
    DEFAULT_WEIGHT_MODEL_CONFIDENCE,
    DEFAULT_WEIGHT_VERIFICATION,
    ClaimConfidenceResult,
    ConfidenceBreakdown,
    ConfidenceFusionConfig,
    ConfidenceSignals,
    ResponseConfidenceResult,
    SignalContribution,
)
from eclair.contracts.confidence import ConfidenceResult


def test_default_fusion_config() -> None:
    """Verify default fusion config weights and validation."""
    cfg = ConfidenceFusionConfig()
    assert cfg.weight_verification == DEFAULT_WEIGHT_VERIFICATION
    assert cfg.weight_evidence == DEFAULT_WEIGHT_EVIDENCE
    assert cfg.weight_agreement == DEFAULT_WEIGHT_AGREEMENT
    assert cfg.weight_consistency == DEFAULT_WEIGHT_CONSISTENCY
    assert cfg.weight_model_confidence == DEFAULT_WEIGHT_MODEL_CONFIDENCE
    assert cfg.response_aggregation == "mean"
    assert cfg.renormalize_missing is True


def test_custom_fusion_config() -> None:
    """Verify custom fusion weights initialization."""
    cfg = ConfidenceFusionConfig(
        weight_verification=0.5,
        weight_evidence=0.3,
        weight_agreement=0.1,
        weight_consistency=0.05,
        weight_model_confidence=0.05,
        response_aggregation="min",
    )
    assert cfg.weight_verification == 0.5
    assert cfg.response_aggregation == "min"


def test_fusion_config_invalid_zero_total_weight() -> None:
    """Verify validation fails if all weights are zero."""
    with pytest.raises(ValidationError):
        ConfidenceFusionConfig(
            weight_verification=0.0,
            weight_evidence=0.0,
            weight_agreement=0.0,
            weight_consistency=0.0,
            weight_model_confidence=0.0,
        )


def test_confidence_signals_available_and_missing() -> None:
    """Verify available and missing signal properties on ConfidenceSignals."""
    signals = ConfidenceSignals(
        verification_score=0.9,
        evidence_score=0.8,
        agreement_score=None,
        consistency_score=0.95,
        model_confidence_score=None,
    )
    assert signals.available_signals == {
        "verification": 0.9,
        "evidence": 0.8,
        "consistency": 0.95,
    }
    assert signals.missing_signals == ["agreement", "model_confidence"]


def test_confidence_signals_all_present() -> None:
    """Verify behavior when all signals are supplied."""
    signals = ConfidenceSignals(
        verification_score=1.0,
        evidence_score=0.8,
        agreement_score=0.9,
        consistency_score=0.85,
        model_confidence_score=0.75,
    )
    assert len(signals.available_signals) == 5
    assert len(signals.missing_signals) == 0


def test_signal_contribution_model() -> None:
    """Verify SignalContribution fields."""
    contrib = SignalContribution(
        signal_name="verification",
        raw_value=0.9,
        configured_weight=0.35,
        effective_weight=0.50,
        weighted_contribution=0.45,
        is_available=True,
    )
    assert contrib.signal_name == "verification"
    assert contrib.raw_value == 0.9
    assert contrib.weighted_contribution == 0.45
    assert contrib.is_available is True


def test_confidence_breakdown_model() -> None:
    """Verify ConfidenceBreakdown initialization and attributes."""
    breakdown = ConfidenceBreakdown(
        contributions={},
        effective_weights={"verification": 0.6, "evidence": 0.4},
        total_raw_confidence=0.82,
        available_signals=["verification", "evidence"],
        missing_signals=["agreement", "consistency", "model_confidence"],
    )
    assert breakdown.total_raw_confidence == 0.82
    assert "verification" in breakdown.available_signals
    assert "agreement" in breakdown.missing_signals


def test_claim_confidence_result_model() -> None:
    """Verify ClaimConfidenceResult structure."""
    signals = ConfidenceSignals(verification_score=0.9)
    breakdown = ConfidenceBreakdown(
        total_raw_confidence=0.9,
        available_signals=["verification"],
    )
    res = ClaimConfidenceResult(
        claim_id="c1",
        raw_confidence=0.9,
        signals=signals,
        breakdown=breakdown,
    )
    assert res.claim_id == "c1"
    assert res.raw_confidence == 0.9


def test_response_confidence_result_to_confidence_result() -> None:
    """Verify ResponseConfidenceResult converts to M01 ConfidenceResult with calibrated_ecs=None."""
    resp = ResponseConfidenceResult(
        raw_confidence=0.84,
        claim_confidences=[],
        aggregation_method="mean",
    )
    contract_res = resp.to_confidence_result()
    assert isinstance(contract_res, ConfidenceResult)
    assert contract_res.raw_confidence == 0.84
    assert contract_res.calibrated_ecs is None  # Critical reliability invariant!

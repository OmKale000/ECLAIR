"""Unit tests for M13 Risk & Decision Engine data models (Spec sec.M13)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import DecisionAction, VerificationStatus
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.hallucination.models import HallucinationResult, HallucinationSignals, ResponseHallucinationResult
from eclair.risk.models import RiskAssessmentResult, RiskLevel, RiskSignals


def test_risk_level_values() -> None:
    """Verify all RiskLevel enum values match expected strings."""
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.MEDIUM.value == "medium"
    assert RiskLevel.HIGH.value == "high"
    assert RiskLevel.CRITICAL.value == "critical"
    assert {lvl.value for lvl in RiskLevel} == {"low", "medium", "high", "critical"}


def test_risk_signals_defaults() -> None:
    """Verify RiskSignals default attributes."""
    signals = RiskSignals()
    assert signals.calibrated_ecs is None
    assert signals.raw_confidence is None
    assert signals.confidence_result is None
    assert signals.verifications == []
    assert signals.hallucination_probability is None
    assert signals.is_hallucination is None
    assert signals.agreement_score is None
    assert signals.unsafe_action is False
    assert signals.escalate_to_human is False
    assert signals.iteration_count == 0
    assert signals.total_claims_count == 0
    assert signals.unknown_ratio == 0.0
    assert signals.contradicted_ratio == 0.0


def test_risk_signals_bounds_validation() -> None:
    """Verify numeric signal fields reject out-of-bounds values."""
    with pytest.raises(ValidationError):
        RiskSignals(calibrated_ecs=1.5)

    with pytest.raises(ValidationError):
        RiskSignals(calibrated_ecs=-0.1)

    with pytest.raises(ValidationError):
        RiskSignals(hallucination_probability=1.2)

    with pytest.raises(ValidationError):
        RiskSignals(iteration_count=-1)


def test_risk_signals_extra_fields_forbidden() -> None:
    """Verify extra arbitrary fields are forbidden on RiskSignals."""
    with pytest.raises(ValidationError):
        RiskSignals(unsupported_field="invalid")


def test_risk_signals_sync_from_confidence_result() -> None:
    """Verify calibrated_ecs and raw_confidence are synchronized from ConfidenceResult."""
    conf = ConfidenceResult(raw_confidence=0.85, calibrated_ecs=0.78)
    signals = RiskSignals(confidence_result=conf)

    assert signals.calibrated_ecs == 0.78
    assert signals.raw_confidence == 0.85
    assert signals.effective_ecs == 0.78


def test_risk_signals_sync_from_hallucination_result() -> None:
    """Verify hallucination fields sync from ResponseHallucinationResult and HallucinationResult."""
    # From ResponseHallucinationResult
    resp_halluc = ResponseHallucinationResult(
        claim_results=[],
        overall_hallucination_probability=0.72,
        has_hallucination=True,
    )
    signals_resp = RiskSignals(hallucination_result=resp_halluc)
    assert signals_resp.hallucination_probability == 0.72
    assert signals_resp.is_hallucination is True

    # From single HallucinationResult
    claim_halluc = HallucinationResult(
        claim_id="c1",
        hallucination_probability=0.65,
        is_hallucination=True,
        signals=HallucinationSignals(),
    )
    signals_claim = RiskSignals(hallucination_result=claim_halluc)
    assert signals_claim.hallucination_probability == 0.65
    assert signals_claim.is_hallucination is True


def test_risk_signals_verification_properties() -> None:
    """Verify verification status counters and ratios on RiskSignals."""
    verifications = [
        VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED, evidence_ids=["e1"]),
        VerificationResult(claim_id="c2", status=VerificationStatus.SUPPORTED, evidence_ids=["e2"]),
        VerificationResult(claim_id="c3", status=VerificationStatus.CONTRADICTED, evidence_ids=["e3"]),
        VerificationResult(claim_id="c4", status=VerificationStatus.UNKNOWN, evidence_ids=[]),
    ]
    signals = RiskSignals(verifications=verifications)

    assert signals.total_claims_count == 4
    assert signals.supported_claims_count == 2
    assert signals.contradicted_claims_count == 1
    assert signals.unknown_claims_count == 1
    assert signals.unknown_ratio == 0.25
    assert signals.contradicted_ratio == 0.25


def test_risk_assessment_result_valid() -> None:
    """Verify RiskAssessmentResult construction and field access."""
    risk = RiskResult(risk_level="low", risk_score=0.15)
    decision = DecisionResult(action=DecisionAction.RETURN, reason="High ECS")
    signals = RiskSignals(calibrated_ecs=0.85)

    result = RiskAssessmentResult(
        risk=risk,
        decision=decision,
        signals=signals,
        reasons=["High calibrated ECS"],
        policy_rule="RETURN",
    )

    assert result.risk.risk_level == "low"
    assert result.risk.risk_score == 0.15
    assert result.decision.action is DecisionAction.RETURN
    assert result.policy_rule == "RETURN"
    assert "High calibrated ECS" in result.reasons

    # Verify serialization round-trip
    dumped = result.model_dump()
    assert dumped["risk"]["risk_level"] == "low"
    assert dumped["decision"]["action"] == "RETURN"

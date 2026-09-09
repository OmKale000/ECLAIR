"""Unit tests for M12 reflection data models and configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import ClaimType, VerificationStatus
from eclair.contracts.verification import VerificationResult
from eclair.reflection.models import (
    DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    DEFAULT_MAX_ITERATIONS,
    CritiqueItem,
    CritiqueReport,
    IterationRecord,
    ReflectionConfig,
    ReflectionResult,
)


def test_reflection_config_defaults() -> None:
    config = ReflectionConfig()
    assert config.max_iterations == DEFAULT_MAX_ITERATIONS
    assert config.low_confidence_threshold == DEFAULT_LOW_CONFIDENCE_THRESHOLD
    assert config.min_improvement_margin == 0.01
    assert config.model is None
    assert config.temperature == 0.3


def test_reflection_config_validation() -> None:
    # max_iterations must be >= 1
    with pytest.raises(ValidationError):
        ReflectionConfig(max_iterations=0)

    # low_confidence_threshold must be in [0.0, 1.0]
    with pytest.raises(ValidationError):
        ReflectionConfig(low_confidence_threshold=-0.1)

    with pytest.raises(ValidationError):
        ReflectionConfig(low_confidence_threshold=1.1)

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        ReflectionConfig(unsupported_field="invalid")


def test_critique_item_and_report() -> None:
    item = CritiqueItem(
        claim_id="c1",
        claim_text="Returns are allowed for 90 days.",
        verification_status=VerificationStatus.CONTRADICTED,
        issue="Contradicted by policy",
        recommendation="Change to 30 days",
    )
    assert item.claim_id == "c1"
    assert item.verification_status == VerificationStatus.CONTRADICTED

    report = CritiqueReport(
        has_weak_claims=True,
        weak_claim_count=1,
        items=[item],
        summary="One contradicted claim",
    )
    assert report.has_weak_claims is True
    assert report.weak_claim_count == 1
    assert len(report.items) == 1


def test_iteration_record() -> None:
    claim = Claim(text="Return window is 30 days.", claim_type=ClaimType.NUMERIC)
    verif = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.SUPPORTED,
        evidence_ids=["e1"],
    )
    conf = ConfidenceResult(raw_confidence=0.85, calibrated_ecs=0.82)

    record = IterationRecord(
        iteration=1,
        answer="The return window is 30 days.",
        claims=[claim],
        verifications=[verif],
        confidence=conf,
        improved=True,
        stop_reason="all_claims_supported",
    )
    assert record.iteration == 1
    assert record.improved is True
    assert record.stop_reason == "all_claims_supported"


def test_reflection_result() -> None:
    claim = Claim(text="Final verified statement.")
    verif = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.SUPPORTED,
        evidence_ids=["e1"],
    )
    conf = ConfidenceResult(raw_confidence=0.90, calibrated_ecs=0.88)

    result = ReflectionResult(
        original_answer="Original ungrounded text.",
        improved_answer="Revised grounded text.",
        final_claims=[claim],
        final_verifications=[verif],
        final_confidence=conf,
        iterations_completed=1,
        max_iterations=3,
        triggered=True,
        improved=True,
        stop_reason="all_claims_supported",
        history=[],
    )
    assert result.original_answer == "Original ungrounded text."
    assert result.improved_answer == "Revised grounded text."
    assert result.iterations_completed == 1
    assert result.triggered is True
    assert result.improved is True

"""Unit tests for M10 ConfidenceEstimator service and Protocol conformance."""

from __future__ import annotations

import pytest

from eclair.confidence.estimator import ConfidenceEstimator
from eclair.confidence.models import (
    ClaimConfidenceResult,
    ConfidenceBreakdown,
    ConfidenceSignals,
    ResponseConfidenceResult,
)
from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import ClaimType, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.interfaces import (
    ConfidenceEstimator as ConfidenceEstimatorProtocol,
)
from eclair.contracts.verification import VerificationResult
from eclair.exceptions import ModuleError


def test_protocol_conformance() -> None:
    """Verify ConfidenceEstimator implements the canonical ConfidenceEstimator protocol."""
    estimator = ConfidenceEstimator()
    assert isinstance(estimator, ConfidenceEstimatorProtocol)


def test_estimate_claim_confidence() -> None:
    """Verify claim confidence estimation."""
    estimator = ConfidenceEstimator()
    claim = Claim(text="Standard refunds take 14 days.", claim_type=ClaimType.NUMERIC)
    verif = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.SUPPORTED,
        evidence_ids=["ev_1"],
    )
    evidence = [Evidence(text="Refunds are completed within 14 calendar days.", relevance_score=0.95)]

    res = estimator.estimate_claim_confidence(
        claim=claim,
        verification=verif,
        evidence=evidence,
        agreement_score=0.85,
    )
    assert isinstance(res, ClaimConfidenceResult)
    assert res.claim_id == claim.claim_id
    assert 0.80 <= res.raw_confidence <= 1.0
    assert "verification" in res.breakdown.available_signals
    assert "evidence" in res.breakdown.available_signals
    assert "agreement" in res.breakdown.available_signals


def test_estimate_batch_claims() -> None:
    """Verify batch claim confidence estimation."""
    estimator = ConfidenceEstimator()
    c1 = Claim(text="First claim.", claim_type=ClaimType.FACTUAL)
    c2 = Claim(text="Second claim.", claim_type=ClaimType.NUMERIC)
    v1 = VerificationResult(claim_id=c1.claim_id, status=VerificationStatus.SUPPORTED)
    v2 = VerificationResult(claim_id=c2.claim_id, status=VerificationStatus.CONTRADICTED)

    batch_res = estimator.estimate_batch_claims(
        claims=[c1, c2],
        verifications=[v1, v2],
        agreement_score=0.8,
    )
    assert len(batch_res) == 2
    assert batch_res[0].raw_confidence > batch_res[1].raw_confidence


def test_estimate_response_confidence() -> None:
    """Verify response confidence estimation from claims."""
    estimator = ConfidenceEstimator()
    c1 = Claim(text="Claim A")
    c2 = Claim(text="Claim B")
    v1 = VerificationResult(claim_id=c1.claim_id, status=VerificationStatus.SUPPORTED)
    v2 = VerificationResult(claim_id=c2.claim_id, status=VerificationStatus.SUPPORTED)

    resp_res = estimator.estimate_response_confidence(
        claims=[c1, c2],
        verifications=[v1, v2],
        agreement_score=0.9,
    )
    assert isinstance(resp_res, ResponseConfidenceResult)
    assert 0.80 <= resp_res.raw_confidence <= 1.0
    assert len(resp_res.claim_confidences) == 2

    # Check contract conversion
    contract_res = resp_res.to_confidence_result()
    assert isinstance(contract_res, ConfidenceResult)
    assert contract_res.raw_confidence == resp_res.raw_confidence
    assert contract_res.calibrated_ecs is None  # MUST remain uncalibrated raw confidence


def test_calculate_with_confidence_signals() -> None:
    """Verify calculate() with ConfidenceSignals object."""
    estimator = ConfidenceEstimator()
    signals = ConfidenceSignals(
        verification_score=0.95,
        evidence_score=0.85,
        agreement_score=0.90,
    )
    res = estimator.calculate(signals)
    assert isinstance(res, ConfidenceResult)
    assert 0.80 <= res.raw_confidence <= 1.0
    assert res.calibrated_ecs is None


def test_calculate_with_claim_confidence_result() -> None:
    """Verify calculate() with ClaimConfidenceResult."""
    estimator = ConfidenceEstimator()
    claim_res = ClaimConfidenceResult(
        claim_id="c1",
        raw_confidence=0.88,
        signals=ConfidenceSignals(),
        breakdown=ConfidenceBreakdown(total_raw_confidence=0.88),
    )
    res = estimator.calculate(claim_res)
    assert isinstance(res, ConfidenceResult)
    assert res.raw_confidence == 0.88
    assert res.calibrated_ecs is None


def test_calculate_with_dict() -> None:
    """Verify calculate() with dict signal representation."""
    estimator = ConfidenceEstimator()
    res = estimator.calculate({
        "verification_score": 0.90,
        "evidence_score": 0.80,
    })
    assert isinstance(res, ConfidenceResult)
    assert 0.80 <= res.raw_confidence <= 0.90
    assert res.calibrated_ecs is None


def test_calculate_with_float() -> None:
    """Verify calculate() with direct float in [0.0, 1.0]."""
    estimator = ConfidenceEstimator()
    res = estimator.calculate(0.78)
    assert isinstance(res, ConfidenceResult)
    assert res.raw_confidence == 0.78
    assert res.calibrated_ecs is None


def test_calculate_invalid_float() -> None:
    """Verify calculate() with out-of-bounds float raises ModuleError."""
    estimator = ConfidenceEstimator()
    with pytest.raises(ModuleError):
        estimator.calculate(1.5)


def test_calculate_unsupported_type() -> None:
    """Verify calculate() with unsupported type raises ModuleError."""
    estimator = ConfidenceEstimator()
    with pytest.raises(ModuleError):
        estimator.calculate(object())

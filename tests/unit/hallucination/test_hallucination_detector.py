"""Unit tests for M08 HallucinationDetector orchestrator."""

from __future__ import annotations

import pytest

from eclair.contracts.claim import Claim
from eclair.contracts.enums import ClaimType, ConsensusLevel, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult
from eclair.evidence.models import (
    ConflictDetail,
    EvidenceQualityReport,
    EvidenceQualitySignals,
    ScoredEvidence,
)
from eclair.hallucination.detector import HallucinationDetector
from eclair.hallucination.models import HallucinationReason


def test_detector_clean_supported_claim() -> None:
    detector = HallucinationDetector()
    claim = Claim(
        text="Customers may return products within 30 days of purchase.",
        claim_type=ClaimType.FACTUAL,
    )
    ev = Evidence(
        text="Products may be returned within 30 days of initial purchase for a full refund.",
        relevance_score=0.95,
        source="refund_policy.md",
    )
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.SUPPORTED,
        evidence_ids=[ev.evidence_id],
    )
    result = detector.detect_claim(
        claim=claim,
        verification=verification,
        evidence=[ev],
        agreement_score=0.98,
        consensus_level=ConsensusLevel.FULL,
    )

    assert result.claim_id == claim.claim_id
    assert result.hallucination_probability <= 0.15
    assert result.is_hallucination is False
    assert len(result.reasons) == 0


def test_detector_contradicted_claim() -> None:
    detector = HallucinationDetector()
    claim = Claim(
        text="Customers can return opened software anytime.",
        claim_type=ClaimType.FACTUAL,
    )
    ev = Evidence(
        text="Opened software is strictly non-refundable and cannot be returned.",
        relevance_score=0.90,
    )
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.CONTRADICTED,
        evidence_ids=[ev.evidence_id],
    )
    result = detector.detect_claim(
        claim=claim,
        verification=verification,
        evidence=[ev],
    )

    assert result.is_hallucination is True
    assert result.hallucination_probability >= 0.85
    assert len(result.reasons) >= 1
    assert any(HallucinationReason.CONTRADICTORY_EVIDENCE.value in r for r in result.reasons)


def test_detector_unevidenced_claim() -> None:
    detector = HallucinationDetector()
    claim = Claim(
        text="The company guarantees free lifetime replacements on all items.",
        claim_type=ClaimType.FACTUAL,
    )
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.UNKNOWN,
        evidence_ids=[],
    )
    result = detector.detect_claim(
        claim=claim,
        verification=verification,
        evidence=[],
    )

    assert result.is_hallucination is True
    assert result.hallucination_probability >= 0.65
    assert any(HallucinationReason.NO_EVIDENCE.value in r for r in result.reasons)


def test_detector_numerical_disparity_claim() -> None:
    detector = HallucinationDetector()
    claim = Claim(
        text="Refund processing takes 90 business days.",
        claim_type=ClaimType.NUMERIC,
    )
    ev = Evidence(
        text="Refund processing typically takes 3 to 5 business days.",
        relevance_score=0.85,
    )
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.UNKNOWN,
        evidence_ids=[ev.evidence_id],
    )
    result = detector.detect_claim(
        claim=claim,
        verification=verification,
        evidence=[ev],
    )

    assert result.is_hallucination is True
    assert result.signals.numerical_inconsistency_score >= 0.8
    assert any(HallucinationReason.NUMERICAL_INCONSISTENCY.value in r for r in result.reasons)


def test_detector_model_disagreement_elevates_risk() -> None:
    detector = HallucinationDetector()
    claim = Claim(text="Policy allows international warranty claims.")
    ev = Evidence(text="Warranty covers domestic purchases.", relevance_score=0.40)
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.UNKNOWN,
        evidence_ids=[ev.evidence_id],
    )

    res_high_agreement = detector.detect_claim(
        claim=claim,
        verification=verification,
        evidence=[ev],
        agreement_score=0.90,
    )

    res_low_agreement = detector.detect_claim(
        claim=claim,
        verification=verification,
        evidence=[ev],
        agreement_score=0.10,
    )

    assert (
        res_low_agreement.hallucination_probability
        > res_high_agreement.hallucination_probability
    )
    assert res_low_agreement.signals.model_disagreement_score == pytest.approx(0.90, abs=1e-2)


def test_detect_claims_batch() -> None:
    detector = HallucinationDetector()
    c1 = Claim(text="Refund within 30 days is allowed.", claim_type=ClaimType.NUMERIC)
    c2 = Claim(text="Warranty covers damage from space aliens.", claim_type=ClaimType.OTHER)

    ev1 = Evidence(text="Refund within 30 days is allowed.", relevance_score=0.95)
    v1 = VerificationResult(
        claim_id=c1.claim_id,
        status=VerificationStatus.SUPPORTED,
        evidence_ids=[ev1.evidence_id],
    )
    v2 = VerificationResult(
        claim_id=c2.claim_id,
        status=VerificationStatus.UNKNOWN,
        evidence_ids=[],
    )

    batch_result = detector.detect_claims(
        claims=[c1, c2],
        verifications=[v1, v2],
        evidence=[ev1],
    )

    assert len(batch_result.claim_results) == 2
    assert batch_result.has_hallucination is True
    assert c2.claim_id in batch_result.hallucinated_claim_ids
    assert c1.claim_id not in batch_result.hallucinated_claim_ids
    assert len(batch_result.summary_reasons) >= 1


def test_detect_claims_empty() -> None:
    detector = HallucinationDetector()
    batch_result = detector.detect_claims(claims=[])
    assert batch_result.claim_results == []
    assert batch_result.overall_hallucination_probability == 0.0
    assert batch_result.has_hallucination is False
    assert batch_result.hallucinated_claim_ids == []
    assert batch_result.summary_reasons == []


def test_detector_with_m06_evidence_quality_report() -> None:
    detector = HallucinationDetector()
    claim = Claim(text="Item replacement is provided within 14 days.")
    ev1 = Evidence(text="Item replacement policy: 14 days.", relevance_score=0.9)
    ev2 = Evidence(text="Item replacement policy: 60 days.", relevance_score=0.8)

    conflict = ConflictDetail(
        evidence_id_a=ev1.evidence_id,
        evidence_id_b=ev2.evidence_id,
        conflict_score=0.90,
        conflict_type="numerical",
        reason="Replacement timeframe mismatch: 14 days vs 60 days",
    )
    quality_report = EvidenceQualityReport(
        items=[
            ScoredEvidence(
                evidence=ev1,
                signals=EvidenceQualitySignals(
                    evidence_id=ev1.evidence_id,
                    relevance_score=0.9,
                    is_conflicting=True,
                    conflict_score=0.9,
                ),
            )
        ],
        average_quality=0.7,
        has_conflicts=True,
        conflicts=[conflict],
    )

    res = detector.detect_claim(
        claim=claim,
        evidence=[ev1, ev2],
        quality_report=quality_report,
    )
    assert res.signals.contradiction_score >= 0.8
    assert res.is_hallucination is True

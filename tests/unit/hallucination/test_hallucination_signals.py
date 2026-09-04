"""Unit tests for M08 Hallucination Detection signal extractors."""

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
)
from eclair.hallucination.signals import (
    extract_contradiction_signal,
    extract_hallucination_signals,
    extract_model_disagreement_signal,
    extract_no_evidence_signal,
    extract_numerical_inconsistency_signal,
    extract_semantic_support_signal,
)


def test_no_evidence_signal_no_evidence_at_all() -> None:
    claim = Claim(text="Refunds are available for 100 days.")
    score, details = extract_no_evidence_signal(claim, evidence=[])
    assert score == 1.0
    assert "No evidence passages" in details["reason"]


def test_no_evidence_signal_supported_verification() -> None:
    claim = Claim(text="Refunds are available for 30 days.")
    ev = Evidence(text="Refunds within 30 days are accepted.", relevance_score=0.95)
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.SUPPORTED,
        evidence_ids=[ev.evidence_id],
    )
    score, details = extract_no_evidence_signal(
        claim, verification=verification, evidence=[ev]
    )
    assert score == 0.0
    assert "SUPPORTED" in details["reason"]


def test_no_evidence_signal_unknown_verification() -> None:
    claim = Claim(text="Product warranty lasts 10 years.")
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.UNKNOWN,
        evidence_ids=[],
    )
    score, details = extract_no_evidence_signal(claim, verification=verification, evidence=[])
    assert score == 1.0


def test_no_evidence_signal_insufficient_quality_report() -> None:
    claim = Claim(text="Some claim")
    report = EvidenceQualityReport(
        items=[],
        average_quality=0.0,
        is_insufficient=True,
    )
    score, details = extract_no_evidence_signal(claim, quality_report=report)
    assert score == 1.0
    assert "insufficient" in details["reason"]


def test_contradiction_signal_contradicted_status() -> None:
    claim = Claim(text="Refunds are accepted indefinitely.")
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.CONTRADICTED,
        evidence_ids=["ev-1"],
    )
    score, details = extract_contradiction_signal(claim, verification=verification)
    assert score == 1.0
    assert "CONTRADICTED" in details["reason"]


def test_contradiction_signal_quality_conflict() -> None:
    claim = Claim(text="Refund period is 30 days.")
    conflict = ConflictDetail(
        evidence_id_a="ev-1",
        evidence_id_b="ev-2",
        conflict_score=0.85,
        conflict_type="numerical",
        reason="30 days vs 14 days contradiction",
    )
    report = EvidenceQualityReport(
        items=[],
        average_quality=0.5,
        has_conflicts=True,
        conflicts=[conflict],
    )
    score, details = extract_contradiction_signal(claim, quality_report=report)
    assert score == 0.85
    assert "conflict" in details["reason"].lower()


def test_contradiction_signal_clean() -> None:
    claim = Claim(text="Refund period is 30 days.")
    ev = Evidence(text="30 day returns allowed.", relevance_score=0.9)
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.SUPPORTED,
        evidence_ids=[ev.evidence_id],
    )
    score, _ = extract_contradiction_signal(claim, verification=verification, evidence=[ev])
    assert score == 0.0


def test_semantic_support_signal_high_relevance() -> None:
    claim = Claim(text="Customers receive full refund within 30 days.")
    ev = Evidence(text="Full refund is issued within 30 days.", relevance_score=0.92)
    score, details = extract_semantic_support_signal(claim, evidence=[ev])
    assert score == pytest.approx(0.08, abs=1e-2)
    assert details["max_relevance"] == 0.92


def test_semantic_support_signal_low_relevance() -> None:
    claim = Claim(text="Company sells rocket engines.")
    ev = Evidence(text="Company policy on invoice refunds.", relevance_score=0.15)
    score, details = extract_semantic_support_signal(claim, evidence=[ev])
    assert score == pytest.approx(0.85, abs=1e-2)


def test_semantic_support_signal_quality_signals() -> None:
    claim = Claim(text="Some claim")
    sig = EvidenceQualitySignals(evidence_id="ev-1", relevance_score=0.80)
    score, _ = extract_semantic_support_signal(claim, quality_signals=[sig])
    assert score == pytest.approx(0.20, abs=1e-2)


def test_model_disagreement_signal_agreement_score() -> None:
    score, details = extract_model_disagreement_signal(agreement_score=0.8)
    assert score == pytest.approx(0.2, abs=1e-2)
    assert details["agreement_score"] == 0.8

    score_low, _ = extract_model_disagreement_signal(agreement_score=0.2)
    assert score_low == pytest.approx(0.8, abs=1e-2)


def test_model_disagreement_signal_consensus_level() -> None:
    score_full, _ = extract_model_disagreement_signal(consensus_level=ConsensusLevel.FULL)
    assert score_full == 0.0

    score_partial, _ = extract_model_disagreement_signal(consensus_level=ConsensusLevel.PARTIAL)
    assert score_partial == 0.4


def test_model_disagreement_signal_omitted() -> None:
    score, details = extract_model_disagreement_signal()
    assert score == 0.0
    assert "not provided" in details["reason"]


def test_numerical_inconsistency_matching_numbers() -> None:
    claim = Claim(
        text="Customers can request a refund within 30 days.",
        claim_type=ClaimType.NUMERIC,
    )
    ev = Evidence(text="Refund requests must be made within 30 days of purchase.")
    score, details = extract_numerical_inconsistency_signal(claim, evidence=[ev])
    assert score == 0.0
    assert "supported" in details["reason"]


def test_numerical_inconsistency_disparity() -> None:
    claim = Claim(
        text="Customers have 90 days to return items.",
        claim_type=ClaimType.NUMERIC,
    )
    ev = Evidence(text="All returns must occur within 14 days or 30 days.")
    score, details = extract_numerical_inconsistency_signal(claim, evidence=[ev])
    assert score == 0.9
    assert "Numerical disparity" in details["reason"]


def test_numerical_inconsistency_no_numbers() -> None:
    claim = Claim(text="Items must be in original condition.", claim_type=ClaimType.FACTUAL)
    ev = Evidence(text="Items must be unused and in original packaging.")
    score, details = extract_numerical_inconsistency_signal(claim, evidence=[ev])
    assert score == 0.0


def test_extract_hallucination_signals_full_aggregation() -> None:
    claim = Claim(text="Refund period is 30 days.", claim_type=ClaimType.NUMERIC)
    ev = Evidence(text="Refund period is 30 days.", relevance_score=0.9)
    verification = VerificationResult(
        claim_id=claim.claim_id,
        status=VerificationStatus.SUPPORTED,
        evidence_ids=[ev.evidence_id],
    )
    signals = extract_hallucination_signals(
        claim=claim,
        verification=verification,
        evidence=[ev],
        agreement_score=0.95,
        consensus_level=ConsensusLevel.FULL,
    )
    assert signals.no_evidence_score == 0.0
    assert signals.contradiction_score == 0.0
    assert signals.low_semantic_support_score == pytest.approx(0.1, abs=1e-2)
    assert signals.model_disagreement_score == pytest.approx(0.05, abs=1e-2)
    assert signals.numerical_inconsistency_score == 0.0
    assert "no_evidence" in signals.details

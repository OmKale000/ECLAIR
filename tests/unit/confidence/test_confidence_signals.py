"""Unit tests for M10 Confidence Estimation signal extraction."""

from __future__ import annotations

from eclair.confidence.signals import (
    extract_agreement_signal,
    extract_claim_signals,
    extract_consistency_signal,
    extract_evidence_signal,
    extract_model_confidence_signal,
    extract_response_signals,
    extract_verification_signal,
)
from eclair.contracts.claim import Claim
from eclair.contracts.enums import ClaimType, ConsensusLevel, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult
from eclair.evidence.models import (
    EvidenceQualityReport,
    EvidenceQualitySignals,
    ScoredEvidence,
)
from eclair.hallucination.models import (
    HallucinationResult,
    HallucinationSignals,
    ResponseHallucinationResult,
)


def test_extract_verification_signal_supported() -> None:
    """Verify SUPPORTED verification maps to high confidence signal."""
    v = VerificationResult(
        claim_id="c1",
        status=VerificationStatus.SUPPORTED,
        evidence_ids=["e1"],
    )
    score, details = extract_verification_signal(v)
    assert score is not None
    assert score >= 0.90
    assert details["status"] == "SUPPORTED"


def test_extract_verification_signal_contradicted() -> None:
    """Verify CONTRADICTED verification maps to very low confidence signal."""
    v = VerificationResult(
        claim_id="c1",
        status=VerificationStatus.CONTRADICTED,
        evidence_ids=["e1"],
    )
    score, details = extract_verification_signal(v)
    assert score is not None
    assert score <= 0.10
    assert details["status"] == "CONTRADICTED"


def test_extract_verification_signal_unknown() -> None:
    """Verify UNKNOWN verification maps to low confidence (never supported)."""
    v = VerificationResult(
        claim_id="c1",
        status=VerificationStatus.UNKNOWN,
        evidence_ids=[],
    )
    score, details = extract_verification_signal(v)
    assert score is not None
    assert score <= 0.30
    assert details["status"] == "UNKNOWN"


def test_extract_verification_signal_none() -> None:
    """Verify omitted verification returns None signal."""
    score, details = extract_verification_signal(None)
    assert score is None
    assert "not provided" in details["reason"]


def test_extract_evidence_signal_quality_report() -> None:
    """Verify evidence quality report extraction with conflict penalty."""
    ev = Evidence(text="Passage text", source="doc1", relevance_score=0.9)
    sig = EvidenceQualitySignals(evidence_id=ev.evidence_id, overall_score=0.85)
    report = EvidenceQualityReport(
        items=[ScoredEvidence(evidence=ev, signals=sig)],
        average_quality=0.85,
        has_conflicts=False,
    )
    score, details = extract_evidence_signal(quality_report=report)
    assert score == 0.85
    assert details["has_conflicts"] is False


def test_extract_evidence_signal_insufficient() -> None:
    """Verify insufficient evidence quality maps to zero score."""
    report = EvidenceQualityReport(
        items=[],
        average_quality=0.0,
        is_insufficient=True,
    )
    score, details = extract_evidence_signal(quality_report=report)
    assert score == 0.0
    assert "insufficient" in details["reason"]


def test_extract_evidence_signal_raw_evidence() -> None:
    """Verify raw evidence items extraction with relevance scores."""
    ev1 = Evidence(text="First passage", relevance_score=0.8)
    ev2 = Evidence(text="Second passage", relevance_score=0.6)
    score, details = extract_evidence_signal(evidence=[ev1, ev2])
    assert score == 0.70
    assert details["reason"] is not None


def test_extract_agreement_signal_score() -> None:
    """Verify direct agreement score normalization."""
    score, details = extract_agreement_signal(agreement_score=0.85)
    assert score == 0.85
    assert details["agreement_score"] == 0.85


def test_extract_agreement_signal_consensus_level() -> None:
    """Verify consensus level enum conversion."""
    score_full, _ = extract_agreement_signal(consensus_level=ConsensusLevel.FULL)
    score_partial, _ = extract_agreement_signal(consensus_level=ConsensusLevel.PARTIAL)
    assert score_full == 1.0
    assert score_partial == 0.50


def test_extract_consistency_signal_from_hallucination() -> None:
    """Verify consistency derived from hallucination probability."""
    h_result = HallucinationResult(
        claim_id="c1",
        hallucination_probability=0.15,
        is_hallucination=False,
        reasons=[],
        signals=HallucinationSignals(),
    )
    score, details = extract_consistency_signal(hallucination=h_result)
    assert score == 0.85
    assert details["hallucination_probability"] == 0.15


def test_extract_consistency_signal_from_response_hallucination() -> None:
    """Verify consistency derived from response hallucination result."""
    resp_h = ResponseHallucinationResult(
        overall_hallucination_probability=0.20,
        has_hallucination=False,
    )
    score, details = extract_consistency_signal(response_hallucination=resp_h)
    assert score == 0.80


def test_extract_model_confidence_signal() -> None:
    """Verify model confidence direct and logprobs calculation."""
    score_dir, _ = extract_model_confidence_signal(model_confidence=0.92)
    assert score_dir == 0.92

    score_logp, _ = extract_model_confidence_signal(logprobs=[-0.1, -0.2, -0.05])
    assert score_logp is not None
    assert 0.80 <= score_logp <= 1.0


def test_extract_claim_signals_full() -> None:
    """Verify full claim signal assembly."""
    claim = Claim(text="Payment is processed in 3 business days.", claim_type=ClaimType.NUMERIC)
    verif = VerificationResult(claim_id=claim.claim_id, status=VerificationStatus.SUPPORTED)
    signals = extract_claim_signals(
        claim=claim,
        verification=verif,
        agreement_score=0.9,
        consistency_score=0.95,
        model_confidence=0.88,
    )
    assert signals.verification_score is not None
    assert signals.agreement_score == 0.9
    assert signals.consistency_score == 0.95
    assert signals.model_confidence_score == 0.88
    assert signals.details["claim_id"] == claim.claim_id


def test_extract_response_signals_aggregation() -> None:
    """Verify response-level signal assembly across multiple verifications."""
    v1 = VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED)
    v2 = VerificationResult(claim_id="c2", status=VerificationStatus.SUPPORTED)
    v3 = VerificationResult(claim_id="c3", status=VerificationStatus.UNKNOWN)
    signals = extract_response_signals(
        verifications=[v1, v2, v3],
        agreement_score=0.8,
    )
    assert signals.verification_score is not None
    assert 0.60 <= signals.verification_score <= 0.80
    assert signals.agreement_score == 0.8

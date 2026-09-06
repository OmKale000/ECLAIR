"""Signal extraction and normalization for M10 Confidence Estimation.

Extracts, normalizes, and packages the 5 core reliability signals into
``ConfidenceSignals`` containers for claim-level and response-level fusion:
1. Verification signal (M07)
2. Evidence signal (M06)
3. Agreement signal (M09)
4. Consistency signal (M08 / evidence)
5. Model confidence signal (LLM Gateway / model generation)
"""

from __future__ import annotations

import math
from typing import Any

from eclair.confidence.models import ConfidenceSignals
from eclair.contracts.claim import Claim
from eclair.contracts.enums import ConsensusLevel, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult
from eclair.evidence.models import EvidenceQualityReport, EvidenceQualitySignals
from eclair.hallucination.models import HallucinationResult, ResponseHallucinationResult

__all__ = [
    "extract_verification_signal",
    "extract_evidence_signal",
    "extract_agreement_signal",
    "extract_consistency_signal",
    "extract_model_confidence_signal",
    "extract_claim_signals",
    "extract_response_signals",
]


def extract_verification_signal(
    verification: VerificationResult | None = None,
    support_score: float | None = None,
    contradiction_score: float | None = None,
) -> tuple[float | None, dict[str, Any]]:
    """Extract and normalize the verification reliability signal from M07.

    Reliability invariant (Spec sec.4.9): absence of evidence is mapped to
    UNKNOWN and must NOT be treated as SUPPORTED.
    """
    details: dict[str, Any] = {}

    if verification is None:
        if support_score is not None:
            score = max(0.0, min(1.0, support_score))
            details["support_score"] = score
            details["reason"] = f"Direct support score provided: {score:.2f}."
            return score, details
        return None, {"reason": "Verification signal not provided."}

    details["status"] = verification.status.value
    details["evidence_count"] = len(verification.evidence_ids)

    if verification.status == VerificationStatus.SUPPORTED:
        if support_score is not None:
            score = max(0.60, min(1.0, support_score))
        else:
            score = 0.95
        details["reason"] = f"Claim verified as SUPPORTED (score={score:.2f})."
        return score, details

    if verification.status == VerificationStatus.CONTRADICTED:
        if contradiction_score is not None:
            score = max(0.0, min(0.40, 1.0 - contradiction_score))
        else:
            score = 0.05
        details["reason"] = f"Claim verified as CONTRADICTED (score={score:.2f})."
        return score, details

    # UNKNOWN status
    if not verification.evidence_ids:
        score = 0.15
        details["reason"] = "Verification status is UNKNOWN with zero evidence passages."
    else:
        score = 0.30
        details["reason"] = "Verification status is UNKNOWN (evidence does not entail claim)."
    return score, details


def extract_evidence_signal(
    evidence: list[Evidence] | None = None,
    quality_signals: list[EvidenceQualitySignals] | None = None,
    quality_report: EvidenceQualityReport | None = None,
) -> tuple[float | None, dict[str, Any]]:
    """Extract and normalize the evidence quality and support signal from M06."""
    details: dict[str, Any] = {}

    if quality_report is not None:
        details["item_count"] = len(quality_report.items)
        details["has_conflicts"] = quality_report.has_conflicts
        details["is_insufficient"] = quality_report.is_insufficient

        if quality_report.is_insufficient:
            details["reason"] = "Evidence is flagged as insufficient by quality analysis."
            return 0.0, details

        base_score = quality_report.average_quality
        if quality_report.has_conflicts:
            base_score = max(0.0, base_score * 0.7)
            details["conflict_penalty"] = True

        score = max(0.0, min(1.0, base_score))
        details["reason"] = f"Evidence quality report composite score: {score:.2f}."
        return score, details

    if quality_signals:
        scores = [s.overall_score for s in quality_signals]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        has_conf = any(s.is_conflicting for s in quality_signals)
        if has_conf:
            avg_score = max(0.0, avg_score * 0.7)

        score = max(0.0, min(1.0, avg_score))
        details["count"] = len(quality_signals)
        details["reason"] = f"Averaged quality signals from {len(quality_signals)} items: {score:.2f}."
        return score, details

    if evidence is not None:
        if not evidence:
            details["reason"] = "Empty evidence list provided (zero evidence)."
            return 0.0, details

        relevance_scores = [ev.relevance_score for ev in evidence if ev.relevance_score is not None]
        if relevance_scores:
            avg_rel = sum(relevance_scores) / len(relevance_scores)
            score = max(0.0, min(1.0, avg_rel))
            details["reason"] = f"Average evidence relevance score from {len(evidence)} items: {score:.2f}."
            return score, details

        score = 0.50
        details["reason"] = f"{len(evidence)} unannotated evidence items present (neutral baseline)."
        return score, details

    return None, {"reason": "Evidence signal not provided."}


def extract_agreement_signal(
    agreement_score: float | None = None,
    consensus_level: ConsensusLevel | None = None,
) -> tuple[float | None, dict[str, Any]]:
    """Extract and normalize the cross-model agreement signal from M09.

    Reliability invariant (Spec sec.4.6): model agreement is NOT proof of truth.
    It is used only as one contributor to raw confidence.
    """
    details: dict[str, Any] = {}

    if agreement_score is not None:
        score = max(0.0, min(1.0, agreement_score))
        details["agreement_score"] = score
        details["reason"] = f"Consensus agreement score: {score:.2f}."
        return score, details

    if consensus_level is not None:
        details["consensus_level"] = consensus_level.value
        if consensus_level == ConsensusLevel.FULL:
            score = 1.0
            details["reason"] = "Full multi-model consensus reported."
        else:
            score = 0.50
            details["reason"] = "Partial multi-model consensus reported."
        return score, details

    return None, {"reason": "Agreement signal not provided."}


def extract_consistency_signal(
    hallucination: HallucinationResult | None = None,
    response_hallucination: ResponseHallucinationResult | None = None,
    consistency_score: float | None = None,
    conflict_score: float | None = None,
) -> tuple[float | None, dict[str, Any]]:
    """Extract and normalize the consistency signal (logical, semantic, numerical)."""
    details: dict[str, Any] = {}

    if consistency_score is not None:
        score = max(0.0, min(1.0, consistency_score))
        details["consistency_score"] = score
        details["reason"] = f"Direct consistency score provided: {score:.2f}."
        return score, details

    if hallucination is not None:
        score = max(0.0, min(1.0, 1.0 - hallucination.hallucination_probability))
        details["hallucination_probability"] = hallucination.hallucination_probability
        details["is_hallucination"] = hallucination.is_hallucination
        details["reason"] = (
            f"Derived consistency from claim hallucination analysis (1 - {hallucination.hallucination_probability:.2f} = {score:.2f})."
        )
        return score, details

    if response_hallucination is not None:
        score = max(0.0, min(1.0, 1.0 - response_hallucination.overall_hallucination_probability))
        details["overall_hallucination_probability"] = response_hallucination.overall_hallucination_probability
        details["has_hallucination"] = response_hallucination.has_hallucination
        details["reason"] = (
            f"Derived consistency from response hallucination analysis: {score:.2f}."
        )
        return score, details

    if conflict_score is not None:
        score = max(0.0, min(1.0, 1.0 - conflict_score))
        details["conflict_score"] = conflict_score
        details["reason"] = f"Derived consistency from conflict score: {score:.2f}."
        return score, details

    return None, {"reason": "Consistency signal not provided."}


def extract_model_confidence_signal(
    model_confidence: float | None = None,
    logprobs: list[float] | None = None,
) -> tuple[float | None, dict[str, Any]]:
    """Extract and normalize model self-reported or token logprob confidence."""
    details: dict[str, Any] = {}

    if model_confidence is not None:
        score = max(0.0, min(1.0, model_confidence))
        details["model_confidence"] = score
        details["reason"] = f"Direct model confidence provided: {score:.2f}."
        return score, details

    if logprobs:
        # Convert average logprob to probability in [0.0, 1.0]
        mean_logprob = sum(logprobs) / len(logprobs)
        prob = math.exp(max(-10.0, min(0.0, mean_logprob)))
        score = max(0.0, min(1.0, prob))
        details["mean_logprob"] = mean_logprob
        details["reason"] = f"Exponentiated average token logprob: {score:.2f}."
        return score, details

    return None, {"reason": "Model confidence signal not provided."}


def extract_claim_signals(
    claim: Claim | None = None,
    verification: VerificationResult | None = None,
    evidence: list[Evidence] | None = None,
    quality_signals: list[EvidenceQualitySignals] | None = None,
    quality_report: EvidenceQualityReport | None = None,
    agreement_score: float | None = None,
    consensus_level: ConsensusLevel | None = None,
    hallucination: HallucinationResult | None = None,
    consistency_score: float | None = None,
    model_confidence: float | None = None,
    logprobs: list[float] | None = None,
    support_score: float | None = None,
    contradiction_score: float | None = None,
) -> ConfidenceSignals:
    """Extract all 5 reliability signals for an individual claim."""
    v_score, v_det = extract_verification_signal(
        verification=verification,
        support_score=support_score,
        contradiction_score=contradiction_score,
    )
    e_score, e_det = extract_evidence_signal(
        evidence=evidence,
        quality_signals=quality_signals,
        quality_report=quality_report,
    )
    a_score, a_det = extract_agreement_signal(
        agreement_score=agreement_score,
        consensus_level=consensus_level,
    )
    c_score, c_det = extract_consistency_signal(
        hallucination=hallucination,
        consistency_score=consistency_score,
    )
    m_score, m_det = extract_model_confidence_signal(
        model_confidence=model_confidence,
        logprobs=logprobs,
    )

    combined_details = {
        "verification": v_det,
        "evidence": e_det,
        "agreement": a_det,
        "consistency": c_det,
        "model_confidence": m_det,
    }
    if claim is not None:
        combined_details["claim_id"] = claim.claim_id
        combined_details["claim_type"] = claim.claim_type.value

    return ConfidenceSignals(
        verification_score=v_score,
        evidence_score=e_score,
        agreement_score=a_score,
        consistency_score=c_score,
        model_confidence_score=m_score,
        details=combined_details,
    )


def extract_response_signals(
    verifications: list[VerificationResult] | None = None,
    evidence: list[Evidence] | None = None,
    quality_report: EvidenceQualityReport | None = None,
    agreement_score: float | None = None,
    consensus_level: ConsensusLevel | None = None,
    response_hallucination: ResponseHallucinationResult | None = None,
    consistency_score: float | None = None,
    model_confidence: float | None = None,
) -> ConfidenceSignals:
    """Extract composite response-level reliability signals."""
    v_score: float | None = None
    v_det: dict[str, Any] = {}
    if verifications is not None:
        if not verifications:
            v_score = 0.15
            v_det = {"reason": "Zero verifications provided for response."}
        else:
            supported_count = sum(1 for v in verifications if v.status == VerificationStatus.SUPPORTED)
            contradicted_count = sum(1 for v in verifications if v.status == VerificationStatus.CONTRADICTED)
            unknown_count = sum(1 for v in verifications if v.status == VerificationStatus.UNKNOWN)
            total = len(verifications)
            # Weighted ratio: supported adds 1.0, unknown adds 0.25, contradicted adds 0.0
            v_score = (supported_count * 1.0 + unknown_count * 0.25) / total
            v_det = {
                "total_claims": total,
                "supported": supported_count,
                "contradicted": contradicted_count,
                "unknown": unknown_count,
                "reason": f"Response verification ratio: {supported_count}/{total} supported, {contradicted_count}/{total} contradicted.",
            }

    e_score, e_det = extract_evidence_signal(
        evidence=evidence,
        quality_report=quality_report,
    )
    a_score, a_det = extract_agreement_signal(
        agreement_score=agreement_score,
        consensus_level=consensus_level,
    )
    c_score, c_det = extract_consistency_signal(
        response_hallucination=response_hallucination,
        consistency_score=consistency_score,
    )
    m_score, m_det = extract_model_confidence_signal(
        model_confidence=model_confidence,
    )

    combined_details = {
        "verification": v_det,
        "evidence": e_det,
        "agreement": a_det,
        "consistency": c_det,
        "model_confidence": m_det,
    }

    return ConfidenceSignals(
        verification_score=v_score,
        evidence_score=e_score,
        agreement_score=a_score,
        consistency_score=c_score,
        model_confidence_score=m_score,
        details=combined_details,
    )

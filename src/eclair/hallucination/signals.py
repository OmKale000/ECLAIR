"""Signal extraction logic for M08 Hallucination Detection.

Extracts and scores the 5 core hallucination reliability signals:
1. No evidence / insufficient evidence
2. Contradictory evidence
3. Low semantic support
4. Model disagreement
5. Numerical inconsistency
"""

from __future__ import annotations

import re
from typing import Any

from eclair.contracts.claim import Claim
from eclair.contracts.enums import ConsensusLevel, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult
from eclair.evidence.models import EvidenceQualityReport, EvidenceQualitySignals
from eclair.hallucination.models import HallucinationSignals

__all__ = [
    "extract_no_evidence_signal",
    "extract_contradiction_signal",
    "extract_semantic_support_signal",
    "extract_model_disagreement_signal",
    "extract_numerical_inconsistency_signal",
    "extract_hallucination_signals",
]

_NUMERIC_PATTERN = re.compile(
    r"\b(?:\$|€|£)?\d+(?:[.,]\d+)?%?(?:\s*(?:days?|months?|years?|hours?|weeks?|dollars?|usd|eur|gbp|percent))?\b",
    re.IGNORECASE,
)
_DIGITS_ONLY_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")


def extract_no_evidence_signal(
    claim: Claim,
    verification: VerificationResult | None = None,
    evidence: list[Evidence] | None = None,
    quality_report: EvidenceQualityReport | None = None,
) -> tuple[float, dict[str, Any]]:
    """Evaluate whether the claim lacks supporting evidence.

    In ECLAIR, absence of evidence MUST never be interpreted as support (Spec sec.4.9).
    If evidence is missing or marked insufficient, no_evidence_score is high.
    """
    details: dict[str, Any] = {}
    evidence_list = evidence or []
    has_evidence = len(evidence_list) > 0

    if quality_report is not None and quality_report.is_insufficient:
        details["reason"] = "Evidence set is marked as insufficient by quality analysis."
        return 1.0, details

    if verification is not None:
        if verification.status == VerificationStatus.UNKNOWN:
            if not verification.evidence_ids and not has_evidence:
                details["reason"] = "Verification status is UNKNOWN with zero evidence passages."
                return 1.0, details
            details["reason"] = "Verification status is UNKNOWN (evidence does not entail claim)."
            return 0.8, details
        if verification.status == VerificationStatus.SUPPORTED:
            details["reason"] = "Claim is verified as SUPPORTED by evidence."
            return 0.0, details
        if verification.status == VerificationStatus.CONTRADICTED:
            details["reason"] = "Evidence is present but contradicts the claim."
            return 0.0, details

    if not has_evidence:
        details["reason"] = "No evidence passages provided for claim."
        return 1.0, details

    details["reason"] = f"{len(evidence_list)} evidence passages available without verification result."
    return 0.3, details


def extract_contradiction_signal(
    claim: Claim,
    verification: VerificationResult | None = None,
    evidence: list[Evidence] | None = None,
    quality_signals: list[EvidenceQualitySignals] | None = None,
    quality_report: EvidenceQualityReport | None = None,
) -> tuple[float, dict[str, Any]]:
    """Evaluate whether the claim is contradicted by evidence or conflicting sources."""
    details: dict[str, Any] = {}

    if verification is not None and verification.status == VerificationStatus.CONTRADICTED:
        details["reason"] = "Claim is verified as CONTRADICTED by evidence (M07)."
        return 1.0, details

    if quality_report is not None and quality_report.has_conflicts:
        max_conflict = max(
            (c.conflict_score for c in quality_report.conflicts),
            default=0.0,
        )
        if max_conflict >= 0.7:
            details["reason"] = (
                f"Severe evidence conflict detected (conflict_score={max_conflict:.2f})."
            )
            return min(1.0, max_conflict), details
        if max_conflict > 0.0:
            details["reason"] = (
                f"Moderate evidence conflict detected (conflict_score={max_conflict:.2f})."
            )
            return max_conflict * 0.7, details

    if quality_signals:
        max_conf_signal = max((s.conflict_score for s in quality_signals), default=0.0)
        if max_conf_signal > 0.0:
            details["reason"] = (
                f"Evidence quality signal reports conflict (score={max_conf_signal:.2f})."
            )
            return min(1.0, max_conf_signal), details

    details["reason"] = "No contradictory evidence detected."
    return 0.0, details


def _compute_lexical_similarity(text_a: str, text_b: str) -> float:
    """Compute token-level Jaccard overlap as a deterministic lexical support baseline."""
    words_a = set(re.findall(r"\w+", text_a.lower()))
    words_b = set(re.findall(r"\w+", text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a.intersection(words_b)
    union = words_a.union(words_b)
    return len(intersection) / len(union) if union else 0.0


def extract_semantic_support_signal(
    claim: Claim,
    evidence: list[Evidence] | None = None,
    quality_signals: list[EvidenceQualitySignals] | None = None,
) -> tuple[float, dict[str, Any]]:
    """Evaluate degree of low semantic support between claim and evidence passages."""
    details: dict[str, Any] = {}
    evidence_list = evidence or []

    if not evidence_list and not quality_signals:
        details["reason"] = "No evidence available to evaluate semantic support."
        return 1.0, details

    relevance_scores: list[float] = []

    if quality_signals:
        for sig in quality_signals:
            relevance_scores.append(sig.relevance_score)

    for ev in evidence_list:
        if ev.relevance_score is not None:
            relevance_scores.append(ev.relevance_score)
        else:
            sim = _compute_lexical_similarity(claim.text, ev.text)
            relevance_scores.append(sim)

    if not relevance_scores:
        details["reason"] = "Could not compute semantic relevance scores."
        return 0.8, details

    max_rel = max(relevance_scores)
    low_support = max(0.0, min(1.0, 1.0 - max_rel))
    details["max_relevance"] = max_rel
    details["reason"] = f"Max evidence relevance is {max_rel:.2f}; low support is {low_support:.2f}."
    return low_support, details


def extract_model_disagreement_signal(
    agreement_score: float | None = None,
    consensus_level: ConsensusLevel | None = None,
) -> tuple[float, dict[str, Any]]:
    """Evaluate cross-model disagreement from multi-model consensus (M09).

    Model agreement is a reliability signal, not ground truth (Spec sec.4.6).
    High disagreement elevates hallucination risk; agreement reduces this signal.
    """
    details: dict[str, Any] = {}

    if agreement_score is not None:
        score = max(0.0, min(1.0, agreement_score))
        disagreement = 1.0 - score
        details["agreement_score"] = score
        details["reason"] = f"Consensus agreement score is {score:.2f} (disagreement={disagreement:.2f})."
        return disagreement, details

    if consensus_level is not None:
        if consensus_level == ConsensusLevel.FULL:
            details["reason"] = "Full multi-model consensus reported."
            return 0.0, details
        if consensus_level == ConsensusLevel.PARTIAL:
            details["reason"] = "Partial multi-model consensus reported."
            return 0.4, details

    details["reason"] = "Multi-model consensus signal not provided (neutral)."
    return 0.0, details


def _extract_numbers(text: str) -> set[str]:
    """Extract normalized numeric tokens from text."""
    matches = _DIGITS_ONLY_PATTERN.findall(text)
    return set(matches)


def extract_numerical_inconsistency_signal(
    claim: Claim,
    evidence: list[Evidence] | None = None,
    quality_report: EvidenceQualityReport | None = None,
) -> tuple[float, dict[str, Any]]:
    """Evaluate numerical, quantitative, or temporal inconsistency between claim and evidence."""
    details: dict[str, Any] = {}

    if quality_report is not None and quality_report.conflicts:
        for conf in quality_report.conflicts:
            if conf.conflict_type == "numerical" and conf.conflict_score >= 0.5:
                details["reason"] = f"Numerical conflict in evidence report: {conf.reason}"
                return min(1.0, conf.conflict_score), details

    claim_numbers = _extract_numbers(claim.text)
    if not claim_numbers:
        details["reason"] = "Claim contains no numerical or quantitative statements."
        return 0.0, details

    evidence_list = evidence or []
    if not evidence_list:
        details["reason"] = f"Claim makes numeric assertions {claim_numbers} with zero evidence."
        return 0.8, details

    all_evidence_text = " ".join(ev.text for ev in evidence_list)
    evidence_numbers = _extract_numbers(all_evidence_text)

    unsupported_numbers = claim_numbers - evidence_numbers
    if unsupported_numbers:
        if evidence_numbers:
            details["reason"] = (
                f"Numerical disparity: claim states {sorted(unsupported_numbers)} "
                f"while evidence contains {sorted(evidence_numbers)}."
            )
            return 0.9, details
        details["reason"] = (
            f"Numerical claim assertions {sorted(unsupported_numbers)} are unmentioned in evidence."
        )
        return 0.7, details

    details["reason"] = f"Claim numbers {sorted(claim_numbers)} are supported in evidence text."
    return 0.0, details


def extract_hallucination_signals(
    claim: Claim,
    verification: VerificationResult | None = None,
    evidence: list[Evidence] | None = None,
    quality_signals: list[EvidenceQualitySignals] | None = None,
    quality_report: EvidenceQualityReport | None = None,
    agreement_score: float | None = None,
    consensus_level: ConsensusLevel | None = None,
) -> HallucinationSignals:
    """Extract all 5 hallucination reliability signals for a given claim."""
    no_ev_score, no_ev_det = extract_no_evidence_signal(
        claim, verification=verification, evidence=evidence, quality_report=quality_report
    )
    contra_score, contra_det = extract_contradiction_signal(
        claim,
        verification=verification,
        evidence=evidence,
        quality_signals=quality_signals,
        quality_report=quality_report,
    )
    sem_score, sem_det = extract_semantic_support_signal(
        claim, evidence=evidence, quality_signals=quality_signals
    )
    disagree_score, disagree_det = extract_model_disagreement_signal(
        agreement_score=agreement_score, consensus_level=consensus_level
    )
    num_score, num_det = extract_numerical_inconsistency_signal(
        claim, evidence=evidence, quality_report=quality_report
    )

    combined_details = {
        "no_evidence": no_ev_det,
        "contradiction": contra_det,
        "low_semantic_support": sem_det,
        "model_disagreement": disagree_det,
        "numerical_inconsistency": num_det,
    }

    return HallucinationSignals(
        no_evidence_score=max(0.0, min(1.0, no_ev_score)),
        contradiction_score=max(0.0, min(1.0, contra_score)),
        low_semantic_support_score=max(0.0, min(1.0, sem_score)),
        model_disagreement_score=max(0.0, min(1.0, disagree_score)),
        numerical_inconsistency_score=max(0.0, min(1.0, num_score)),
        details=combined_details,
    )

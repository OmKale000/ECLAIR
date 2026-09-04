"""Evidence-level verification aggregator for M07 Claim Verification.

Aggregates multiple evidence evaluations for a single claim into a canonical
``VerificationResult`` (Spec sec.M07, sec.4.9).

Reliability Invariant (Spec sec.4.9):
    Absence of evidence (evidence = []) MUST produce ``VerificationStatus.UNKNOWN``
    with ``evidence_ids=[]``, never ``SUPPORTED`` or ``CONTRADICTED``.
"""

from __future__ import annotations

from eclair.contracts.claim import Claim
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.verification import VerificationResult
from eclair.exceptions import ContractValidationError
from eclair.verification.models import EvidenceVerification, VerificationDetail

__all__ = ["EvidenceAggregator"]


class EvidenceAggregator:
    """Aggregates per-evidence verification evaluations into a final VerificationResult."""

    def __init__(
        self,
        *,
        support_threshold: float = 0.5,
        contradiction_threshold: float = 0.5,
    ) -> None:
        """Initialize the aggregator with decision thresholds.

        Args:
            support_threshold: Minimum score to count evidence as supporting (default 0.5).
            contradiction_threshold: Minimum score to count evidence as contradicting (default 0.5).
        """
        self._support_threshold = support_threshold
        self._contradiction_threshold = contradiction_threshold

    def aggregate(
        self,
        claim: Claim,
        evidence_verifications: list[EvidenceVerification],
    ) -> tuple[VerificationResult, VerificationDetail]:
        """Aggregate evidence verifications for a single claim.

        Args:
            claim: The claim that was evaluated.
            evidence_verifications: List of per-evidence evaluation results.

        Returns:
            Tuple of (canonical VerificationResult, rich VerificationDetail).

        Raises:
            ContractValidationError: If claim or evidence_verifications are invalid types.
        """
        if not isinstance(claim, Claim):
            raise ContractValidationError(
                f"Expected Claim instance, got {type(claim).__name__}",
                code="aggregator_invalid_claim",
            )
        if not isinstance(evidence_verifications, list):
            raise ContractValidationError(
                f"Expected list of EvidenceVerification, got {type(evidence_verifications).__name__}",
                code="aggregator_invalid_evaluations",
            )

        # 1. Non-negotiable no-evidence rule (Spec sec.4.9)
        if not evidence_verifications:
            result = VerificationResult(
                claim_id=claim.claim_id,
                status=VerificationStatus.UNKNOWN,
                evidence_ids=[],
            )
            detail = VerificationDetail(
                claim_id=claim.claim_id,
                status=VerificationStatus.UNKNOWN,
                support_score=0.0,
                contradiction_score=0.0,
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[],
                evidence_verifications=[],
            )
            return result, detail

        # 2. Extract supporting and contradicting evidence subsets
        supporting_ids: list[str] = []
        contradicting_ids: list[str] = []

        max_support = 0.0
        max_contradiction = 0.0

        for ev in evidence_verifications:
            max_support = max(max_support, ev.support_score)
            max_contradiction = max(max_contradiction, ev.contradiction_score)

            if ev.status is VerificationStatus.SUPPORTED or (
                ev.support_score >= self._support_threshold
                and ev.support_score > ev.contradiction_score
            ):
                supporting_ids.append(ev.evidence_id)

            if ev.status is VerificationStatus.CONTRADICTED or (
                ev.contradiction_score >= self._contradiction_threshold
                and ev.contradiction_score > ev.support_score
            ):
                contradicting_ids.append(ev.evidence_id)

        # 3. Decision resolution
        if contradicting_ids and max_contradiction > max_support:
            final_status = VerificationStatus.CONTRADICTED
            attached_evidence_ids = contradicting_ids
        elif supporting_ids and max_support > max_contradiction:
            final_status = VerificationStatus.SUPPORTED
            attached_evidence_ids = supporting_ids
        else:
            final_status = VerificationStatus.UNKNOWN
            attached_evidence_ids = [ev.evidence_id for ev in evidence_verifications]

        result = VerificationResult(
            claim_id=claim.claim_id,
            status=final_status,
            evidence_ids=attached_evidence_ids,
        )

        detail = VerificationDetail(
            claim_id=claim.claim_id,
            status=final_status,
            support_score=round(max_support, 4),
            contradiction_score=round(max_contradiction, 4),
            supporting_evidence_ids=supporting_ids,
            contradicting_evidence_ids=contradicting_ids,
            evidence_verifications=evidence_verifications,
        )

        return result, detail

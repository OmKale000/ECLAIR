"""Module-local interim types for M07 Claim Verification.

These are *internal* structures used within M07 (NLI outputs, intermediate evidence
evaluations, aggregated support/contradiction details). They are NOT shared
cross-module contracts. The shared, cross-module contract is ``VerificationResult``,
owned by M01 and imported from :mod:`eclair.contracts` (COMMON_RULES sec.2, sec.16).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from eclair.contracts.enums import VerificationStatus

__all__ = [
    "NLILabel",
    "NLIPrediction",
    "EvidenceVerification",
    "VerificationDetail",
    "LLMVerificationResult",
]


class NLILabel(str, Enum):
    """Raw NLI classification labels (Spec sec.M07, sec.4.9)."""

    ENTAILMENT = "ENTAILMENT"
    CONTRADICTION = "CONTRADICTION"
    NEUTRAL = "NEUTRAL"

    def to_verification_status(self) -> VerificationStatus:
        """Map NLI label to canonical VerificationStatus (Spec sec.4.9)."""
        if self is NLILabel.ENTAILMENT:
            return VerificationStatus.SUPPORTED
        if self is NLILabel.CONTRADICTION:
            return VerificationStatus.CONTRADICTED
        return VerificationStatus.UNKNOWN


class NLIPrediction(BaseModel):
    """Raw classification prediction and probabilities from the NLI engine."""

    model_config = {"extra": "forbid"}

    label: NLILabel = Field(..., description="Top predicted NLI label.")
    entailment_score: float = Field(
        ..., ge=0.0, le=1.0, description="Entailment probability [0.0, 1.0]."
    )
    contradiction_score: float = Field(
        ..., ge=0.0, le=1.0, description="Contradiction probability [0.0, 1.0]."
    )
    neutral_score: float = Field(
        ..., ge=0.0, le=1.0, description="Neutral probability [0.0, 1.0]."
    )


class EvidenceVerification(BaseModel):
    """Evaluation of a single evidence passage against a claim."""

    model_config = {"extra": "forbid"}

    evidence_id: str = Field(..., description="ID of the evaluated evidence passage.")
    status: VerificationStatus = Field(
        ..., description="Verification status for this individual evidence item."
    )
    support_score: float = Field(
        ..., ge=0.0, le=1.0, description="Evidence-level support score."
    )
    contradiction_score: float = Field(
        ..., ge=0.0, le=1.0, description="Evidence-level contradiction score."
    )
    nli_prediction: NLIPrediction | None = Field(
        default=None, description="Detailed NLI prediction if NLI was executed."
    )


class VerificationDetail(BaseModel):
    """Detailed intermediate record of verification aggregation."""

    model_config = {"extra": "forbid"}

    claim_id: str = Field(..., description="Identifier of the verified claim.")
    status: VerificationStatus = Field(
        ..., description="Aggregated verification status."
    )
    support_score: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated support score across all evidence."
    )
    contradiction_score: float = Field(
        ..., ge=0.0, le=1.0, description="Aggregated contradiction score across all evidence."
    )
    supporting_evidence_ids: list[str] = Field(
        default_factory=list,
        description="IDs of evidence passages that support the claim.",
    )
    contradicting_evidence_ids: list[str] = Field(
        default_factory=list,
        description="IDs of evidence passages that contradict the claim.",
    )
    evidence_verifications: list[EvidenceVerification] = Field(
        default_factory=list,
        description="Per-evidence verification evaluations.",
    )


class LLMVerificationResult(BaseModel):
    """Secondary LLM verification assessment for a claim against evidence."""

    model_config = {"extra": "forbid"}

    status: VerificationStatus = Field(
        ..., description="LLM-derived verification status."
    )
    support_score: float = Field(
        ..., ge=0.0, le=1.0, description="Estimated support score."
    )
    contradiction_score: float = Field(
        ..., ge=0.0, le=1.0, description="Estimated contradiction score."
    )
    reasoning: str | None = Field(
        default=None, description="Brief explanation from the LLM."
    )

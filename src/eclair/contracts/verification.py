"""VerificationResult contract (M01 Foundation).

The outcome of verifying one claim against its evidence. Produced by M07
(Claim Verification) and consumed by M08/M10/M12 and the engine (Spec sec.4.1).

Reliability invariant (Spec sec.4.9): absence of supporting evidence MUST be
represented as ``VerificationStatus.UNKNOWN`` — never ``SUPPORTED``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from eclair.contracts.enums import VerificationStatus

__all__ = ["VerificationResult"]


class VerificationResult(BaseModel):
    """Verification status for a single claim against evidence."""

    model_config = {"extra": "forbid"}

    claim_id: str = Field(
        ...,
        description="Identifier of the claim that was verified.",
    )
    status: VerificationStatus = Field(
        ...,
        description="SUPPORTED, CONTRADICTED, or UNKNOWN (no evidence -> UNKNOWN).",
    )
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers of the evidence considered during verification.",
    )

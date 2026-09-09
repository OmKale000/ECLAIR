"""Data models and configuration for M12 Self-Reflection & Self-Correction.

Defines the configuration, critique models, iteration tracking, and reflection
results for the bounded low-confidence correction loop.

Reliability Invariants:
    * M12 does NOT define, calculate, or calibrate ECS (owned by M10/M11).
    * M12 does NOT define risk policy (owned by M13).
    * M12 enforces a strict, deterministic iteration limit to prevent infinite loops.
    * Regenerated responses are re-verified; absence of evidence is never supported.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.verification import VerificationResult

__all__ = [
    "DEFAULT_LOW_CONFIDENCE_THRESHOLD",
    "DEFAULT_MAX_ITERATIONS",
    "CritiqueItem",
    "CritiqueReport",
    "IterationRecord",
    "ReflectionConfig",
    "ReflectionResult",
]

DEFAULT_MAX_ITERATIONS: int = 3
DEFAULT_LOW_CONFIDENCE_THRESHOLD: float = 0.60


class ReflectionConfig(BaseModel):
    """Configuration for the M12 Self-Reflection & Self-Correction loop."""

    model_config = {"extra": "forbid"}

    max_iterations: int = Field(
        default=DEFAULT_MAX_ITERATIONS,
        ge=1,
        description="Hard maximum number of reflection/regeneration iterations to prevent infinite loops.",
    )
    low_confidence_threshold: float = Field(
        default=DEFAULT_LOW_CONFIDENCE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Confidence/ECS threshold below which reflection is triggered.",
    )
    min_improvement_margin: float = Field(
        default=0.01,
        ge=0.0,
        le=1.0,
        description="Minimum confidence improvement required to satisfy the improvement stopping condition.",
    )
    model: str | None = Field(
        default=None,
        description="Optional model override passed to the LLM Gateway.",
    )
    temperature: float | None = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for corrective regeneration (lower is more factual).",
    )


class CritiqueItem(BaseModel):
    """Critique for an individual weak or failed claim."""

    model_config = {"extra": "forbid"}

    claim_id: str = Field(..., description="ID of the claim being critiqued.")
    claim_text: str = Field(..., min_length=1, description="Original claim text.")
    verification_status: VerificationStatus = Field(
        ...,
        description="Verification outcome from M07 (SUPPORTED, CONTRADICTED, UNKNOWN).",
    )
    issue: str = Field(..., min_length=1, description="Detailed description of the issue with the claim.")
    recommendation: str = Field(..., min_length=1, description="Actionable instruction for how to fix or remove the claim.")


class CritiqueReport(BaseModel):
    """Aggregate critique report identifying failing claims in a response."""

    model_config = {"extra": "forbid"}

    has_weak_claims: bool = Field(..., description="True if any contradicted or ungrounded claims exist.")
    weak_claim_count: int = Field(default=0, ge=0, description="Total count of weak/failing claims.")
    items: list[CritiqueItem] = Field(default_factory=list, description="Per-claim critique items.")
    summary: str = Field(default="", description="Summary of weaknesses and correction strategy.")


class IterationRecord(BaseModel):
    """Detailed record of a single reflection iteration."""

    model_config = {"extra": "forbid"}

    iteration: int = Field(..., ge=1, description="Iteration number (1-based).")
    answer: str = Field(..., description="Response text produced in this iteration.")
    claims: list[Claim] = Field(default_factory=list, description="Claims extracted from this iteration.")
    verifications: list[VerificationResult] = Field(
        default_factory=list,
        description="Verification results for this iteration's claims.",
    )
    confidence: ConfidenceResult | None = Field(
        default=None,
        description="ConfidenceResult (raw and/or calibrated ECS) if available.",
    )
    critique: CritiqueReport | None = Field(
        default=None,
        description="Critique report generated during this iteration.",
    )
    improved: bool = Field(
        default=False,
        description="Whether this iteration improved over the previous iteration.",
    )
    stop_reason: str | None = Field(
        default=None,
        description="Reason if the loop stopped on this iteration.",
    )


class ReflectionResult(BaseModel):
    """Output of the M12 Self-Reflection & Self-Correction loop.

    Returned to the engine for final re-confidence scoring and decision making.
    """

    model_config = {"extra": "forbid"}

    original_answer: str = Field(..., description="Original uncorrected answer.")
    improved_answer: str = Field(..., description="Final improved/corrected answer after reflection.")
    final_claims: list[Claim] = Field(default_factory=list, description="Final re-extracted claims.")
    final_verifications: list[VerificationResult] = Field(
        default_factory=list,
        description="Final verification results for the improved answer.",
    )
    final_confidence: ConfidenceResult | None = Field(
        default=None,
        description="Final confidence if recomputed during the loop.",
    )
    iterations_completed: int = Field(
        default=0,
        ge=0,
        description="Number of reflection iterations executed.",
    )
    max_iterations: int = Field(..., ge=1, description="Configured hard iteration cap.")
    triggered: bool = Field(
        ...,
        description="Whether reflection was triggered based on the low-confidence/weak-claim criteria.",
    )
    improved: bool = Field(
        default=False,
        description="True if the response reliability/confidence measurably improved.",
    )
    stop_reason: str = Field(..., description="Deterministic reason why reflection terminated.")
    history: list[IterationRecord] = Field(
        default_factory=list,
        description="Audit history of all reflection iterations.",
    )

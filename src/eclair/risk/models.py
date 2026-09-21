"""Data models for M13 Risk & Decision Engine.

Defines the internal representations for risk levels, reliability signals container,
and unified risk assessment output.

Reliability invariant (Spec sec.4.4, SHARED_CONTRACTS_REFERENCE sec.6):
M13 does NOT calculate raw confidence (M10) or calibrated ECS (M11).
M13 strictly consumes them through existing shared contracts or validated signal models.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import ConsensusLevel, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.hallucination.models import HallucinationResult, ResponseHallucinationResult

__all__ = [
    "RiskLevel",
    "RiskSignals",
    "RiskAssessmentResult",
]


class RiskLevel(str, Enum):
    """Standard qualitative risk levels assigned by M13 Risk Classifier."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskSignals(BaseModel):
    """Container for reliability signals evaluated by M13 Risk & Decision Engine."""

    model_config = {"extra": "forbid"}

    calibrated_ecs: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Calibrated Epistemic Confidence Score produced by M11.",
    )
    raw_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Raw confidence score produced by M10.",
    )
    confidence_result: ConfidenceResult | None = Field(
        default=None,
        description="ConfidenceResult contract instance containing raw and/or calibrated ECS.",
    )
    verifications: list[VerificationResult] = Field(
        default_factory=list,
        description="Claim verification results produced by M07.",
    )
    hallucination_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Overall probability of hallucination produced by M08.",
    )
    is_hallucination: bool | None = Field(
        default=None,
        description="Boolean flag indicating whether hallucination was detected by M08.",
    )
    hallucination_result: ResponseHallucinationResult | HallucinationResult | None = Field(
        default=None,
        description="Structured hallucination result from M08.",
    )
    agreement_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Multi-model agreement score produced by M09.",
    )
    consensus_level: ConsensusLevel | None = Field(
        default=None,
        description="Consensus level enum produced by M09.",
    )
    evidence_conflict_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Evidence conflict score produced by M06.",
    )
    evidence_quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Overall evidence quality score produced by M06.",
    )
    evidence_list: list[Evidence] = Field(
        default_factory=list,
        description="Retrieved and scored evidence items.",
    )
    unsafe_action: bool = Field(
        default=False,
        description="Flag indicating an unsafe action or critical safety/policy breach.",
    )
    escalate_to_human: bool = Field(
        default=False,
        description="Explicit flag indicating escalation for human review is requested.",
    )
    iteration_count: int = Field(
        default=0,
        ge=0,
        description="Current reflection iteration count (tracked by engine / reflection loop).",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional diagnostic metadata or signal details.",
    )

    @model_validator(mode="after")
    def sync_nested_signals(self) -> RiskSignals:
        """Synchronize nested contract/model values if top-level fields were omitted."""
        # Sync calibrated_ecs from confidence_result if not explicitly set
        if self.calibrated_ecs is None and self.confidence_result is not None:
            if self.confidence_result.calibrated_ecs is not None:
                self.calibrated_ecs = self.confidence_result.calibrated_ecs

        # Sync raw_confidence from confidence_result if not explicitly set
        if self.raw_confidence is None and self.confidence_result is not None:
            self.raw_confidence = self.confidence_result.raw_confidence

        # Sync hallucination fields from structured hallucination result if provided
        if self.hallucination_result is not None:
            if isinstance(self.hallucination_result, ResponseHallucinationResult):
                if self.hallucination_probability is None:
                    self.hallucination_probability = (
                        self.hallucination_result.overall_hallucination_probability
                    )
                if self.is_hallucination is None:
                    self.is_hallucination = self.hallucination_result.has_hallucination
            elif isinstance(self.hallucination_result, HallucinationResult):
                if self.hallucination_probability is None:
                    self.hallucination_probability = (
                        self.hallucination_result.hallucination_probability
                    )
                if self.is_hallucination is None:
                    self.is_hallucination = self.hallucination_result.is_hallucination

        return self

    @property
    def effective_ecs(self) -> float | None:
        """Return the effective calibrated ECS."""
        return self.calibrated_ecs

    @property
    def contradicted_claims_count(self) -> int:
        """Return number of claims marked CONTRADICTED by verification."""
        return sum(
            1 for v in self.verifications if v.status == VerificationStatus.CONTRADICTED
        )

    @property
    def unknown_claims_count(self) -> int:
        """Return number of claims marked UNKNOWN by verification."""
        return sum(
            1 for v in self.verifications if v.status == VerificationStatus.UNKNOWN
        )

    @property
    def supported_claims_count(self) -> int:
        """Return number of claims marked SUPPORTED by verification."""
        return sum(
            1 for v in self.verifications if v.status == VerificationStatus.SUPPORTED
        )

    @property
    def total_claims_count(self) -> int:
        """Return total number of verified claims."""
        return len(self.verifications)

    @property
    def unknown_ratio(self) -> float:
        """Return the fraction of claims that have UNKNOWN verification status."""
        if not self.verifications:
            return 0.0
        return self.unknown_claims_count / len(self.verifications)

    @property
    def contradicted_ratio(self) -> float:
        """Return the fraction of claims that have CONTRADICTED verification status."""
        if not self.verifications:
            return 0.0
        return self.contradicted_claims_count / len(self.verifications)


class RiskAssessmentResult(BaseModel):
    """Composite output of the Risk & Decision Engine."""

    model_config = {"extra": "forbid"}

    risk: RiskResult = Field(
        ...,
        description="Structured risk assessment contract (M01).",
    )
    decision: DecisionResult = Field(
        ...,
        description="Structured decision action contract (M01).",
    )
    signals: RiskSignals = Field(
        ...,
        description="Input reliability signals evaluated during assessment.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="List of explanatory reasons justifying the risk score and decision.",
    )
    policy_rule: str | None = Field(
        default=None,
        description="Identifier of the specific policy rule that fired.",
    )

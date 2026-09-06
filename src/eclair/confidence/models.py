"""Data models for M10 Confidence Estimation.

Defines the structured reliability signal containers, signal contributions,
confidence breakdowns, claim-level confidence results, response-level confidence
results, and configurable fusion settings.

Reliability invariant (Spec sec.4.4, SHARED_CONTRACTS_REFERENCE sec.6):
M10 produces RAW confidence only. Raw confidence is NOT calibrated ECS.
Only M11 may convert raw confidence into calibrated ECS.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from eclair.contracts.confidence import ConfidenceResult

__all__ = [
    "DEFAULT_WEIGHT_VERIFICATION",
    "DEFAULT_WEIGHT_EVIDENCE",
    "DEFAULT_WEIGHT_AGREEMENT",
    "DEFAULT_WEIGHT_CONSISTENCY",
    "DEFAULT_WEIGHT_MODEL_CONFIDENCE",
    "ConfidenceFusionConfig",
    "ConfidenceSignals",
    "SignalContribution",
    "ConfidenceBreakdown",
    "ClaimConfidenceResult",
    "ResponseConfidenceResult",
]

DEFAULT_WEIGHT_VERIFICATION: float = 0.35
DEFAULT_WEIGHT_EVIDENCE: float = 0.25
DEFAULT_WEIGHT_AGREEMENT: float = 0.15
DEFAULT_WEIGHT_CONSISTENCY: float = 0.15
DEFAULT_WEIGHT_MODEL_CONFIDENCE: float = 0.10


class ConfidenceFusionConfig(BaseModel):
    """Configuration for reliability signal fusion weights and aggregation methods."""

    model_config = {"frozen": True, "extra": "forbid"}

    weight_verification: float = Field(
        default=DEFAULT_WEIGHT_VERIFICATION,
        ge=0.0,
        le=1.0,
        description="Weight for claim verification signal (from M07).",
    )
    weight_evidence: float = Field(
        default=DEFAULT_WEIGHT_EVIDENCE,
        ge=0.0,
        le=1.0,
        description="Weight for evidence quality & support signal (from M06).",
    )
    weight_agreement: float = Field(
        default=DEFAULT_WEIGHT_AGREEMENT,
        ge=0.0,
        le=1.0,
        description="Weight for multi-model consensus agreement signal (from M09).",
    )
    weight_consistency: float = Field(
        default=DEFAULT_WEIGHT_CONSISTENCY,
        ge=0.0,
        le=1.0,
        description="Weight for internal/factual consistency signal (from M08/evidence).",
    )
    weight_model_confidence: float = Field(
        default=DEFAULT_WEIGHT_MODEL_CONFIDENCE,
        ge=0.0,
        le=1.0,
        description="Weight for model self-reported/logprob confidence signal.",
    )
    response_aggregation: str = Field(
        default="mean",
        description="Aggregation method for combining claim confidences ('mean', 'min', 'weighted').",
    )
    renormalize_missing: bool = Field(
        default=True,
        description="Whether to renormalize weights across available signals when some are missing.",
    )

    @model_validator(mode="after")
    def validate_weights(self) -> ConfidenceFusionConfig:
        """Ensure that at least one signal weight is positive."""
        total = (
            self.weight_verification
            + self.weight_evidence
            + self.weight_agreement
            + self.weight_consistency
            + self.weight_model_confidence
        )
        if total <= 0.0:
            raise ValueError("Total fusion weight must be greater than 0.0.")
        return self


class ConfidenceSignals(BaseModel):
    """Container for the 5 individual reliability signals evaluated for confidence."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    verification_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Signal from verification status and entailment score in [0.0, 1.0].",
    )
    evidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Signal from evidence quality, relevance, and lack of conflict in [0.0, 1.0].",
    )
    agreement_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Signal from multi-model consensus agreement in [0.0, 1.0].",
    )
    consistency_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Signal from semantic, factual, and numerical consistency in [0.0, 1.0].",
    )
    model_confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Signal from model self-reported or token logprob confidence in [0.0, 1.0].",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic metadata and signal-specific extraction details.",
    )

    @property
    def available_signals(self) -> dict[str, float]:
        """Return a mapping of available (non-None) signal names to their values."""
        signals: dict[str, float] = {}
        if self.verification_score is not None:
            signals["verification"] = self.verification_score
        if self.evidence_score is not None:
            signals["evidence"] = self.evidence_score
        if self.agreement_score is not None:
            signals["agreement"] = self.agreement_score
        if self.consistency_score is not None:
            signals["consistency"] = self.consistency_score
        if self.model_confidence_score is not None:
            signals["model_confidence"] = self.model_confidence_score
        return signals

    @property
    def missing_signals(self) -> list[str]:
        """Return a list of signal names that were not provided."""
        missing: list[str] = []
        if self.verification_score is None:
            missing.append("verification")
        if self.evidence_score is None:
            missing.append("evidence")
        if self.agreement_score is None:
            missing.append("agreement")
        if self.consistency_score is None:
            missing.append("consistency")
        if self.model_confidence_score is None:
            missing.append("model_confidence")
        return missing


class SignalContribution(BaseModel):
    """Detailed record of an individual signal's contribution to the fused confidence."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    signal_name: str = Field(..., description="Name of the reliability signal.")
    raw_value: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Raw signal value in [0.0, 1.0], or None if missing.",
    )
    configured_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Configured nominal weight for this signal.",
    )
    effective_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Effective normalized weight used in fusion.",
    )
    weighted_contribution: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Contribution of this signal to the final confidence (effective_weight * raw_value).",
    )
    is_available: bool = Field(
        ...,
        description="Whether the signal was available and included in fusion.",
    )


class ConfidenceBreakdown(BaseModel):
    """Complete transparent breakdown of signal fusion into raw confidence."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    contributions: dict[str, SignalContribution] = Field(
        default_factory=dict,
        description="Per-signal contribution breakdown keyed by signal name.",
    )
    effective_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Normalized weights for available signals summing to 1.0.",
    )
    total_raw_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calculated RAW confidence in [0.0, 1.0] (NOT calibrated ECS).",
    )
    available_signals: list[str] = Field(
        default_factory=list,
        description="List of signal names present during estimation.",
    )
    missing_signals: list[str] = Field(
        default_factory=list,
        description="List of signal names omitted/missing during estimation.",
    )


class ClaimConfidenceResult(BaseModel):
    """Raw confidence estimation result for an individual claim."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    claim_id: str = Field(..., description="Identifier of the evaluated claim.")
    raw_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Raw fused confidence for this claim in [0.0, 1.0] (NOT calibrated ECS).",
    )
    signals: ConfidenceSignals = Field(
        ...,
        description="Reliability signals evaluated for this claim.",
    )
    breakdown: ConfidenceBreakdown = Field(
        ...,
        description="Detailed signal contribution breakdown.",
    )


class ResponseConfidenceResult(BaseModel):
    """Aggregate raw confidence estimation result for a complete response."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    raw_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Aggregate response-level RAW confidence in [0.0, 1.0] (NOT calibrated ECS).",
    )
    claim_confidences: list[ClaimConfidenceResult] = Field(
        default_factory=list,
        description="Per-claim confidence assessment results.",
    )
    overall_signals: ConfidenceSignals | None = Field(
        default=None,
        description="Composite response-level signals if direct fusion was performed.",
    )
    overall_breakdown: ConfidenceBreakdown | None = Field(
        default=None,
        description="Composite response-level breakdown if direct fusion was performed.",
    )
    aggregation_method: str = Field(
        default="mean",
        description="Method used to derive response confidence ('mean', 'min', 'weighted', 'direct_fusion').",
    )

    def to_confidence_result(self) -> ConfidenceResult:
        """Convert to the canonical M01 ConfidenceResult contract.

        Maintains reliability invariant: calibrated_ecs is None (populated only by M11).
        """
        return ConfidenceResult(
            raw_confidence=self.raw_confidence,
            calibrated_ecs=None,
        )

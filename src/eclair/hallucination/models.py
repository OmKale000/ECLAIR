"""Data models for M08 Hallucination Detection.

Defines the structured hallucination signals, individual claim hallucination results,
and aggregate response hallucination results.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "HallucinationReason",
    "HallucinationSignals",
    "HallucinationResult",
    "ResponseHallucinationResult",
]


class HallucinationReason(str, Enum):
    """Standardized reasons for flagging a claim as a potential hallucination."""

    NO_EVIDENCE = "No supporting evidence found in knowledge base"
    CONTRADICTORY_EVIDENCE = "Evidence directly contradicts the claim"
    LOW_SEMANTIC_SUPPORT = "Retrieved evidence has low semantic support for the claim"
    MODEL_DISAGREEMENT = "High model disagreement across independent model outputs"
    NUMERICAL_INCONSISTENCY = "Numerical or quantitative inconsistency detected"
    INSUFFICIENT_EVIDENCE = "Available evidence is insufficient or of low quality"


class HallucinationSignals(BaseModel):
    """Container for the 5 individual hallucination reliability signals."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    no_evidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Degree of missing or insufficient evidence in [0.0, 1.0] (1.0 = no evidence).",
    )
    contradiction_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Degree of direct or indirect contradiction with evidence in [0.0, 1.0].",
    )
    low_semantic_support_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Degree of semantic divergence between claim and evidence in [0.0, 1.0].",
    )
    model_disagreement_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Degree of cross-model consensus disagreement in [0.0, 1.0].",
    )
    numerical_inconsistency_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Degree of numerical, date, or entity mismatch in [0.0, 1.0].",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic metadata and signal-specific extraction details.",
    )


class HallucinationResult(BaseModel):
    """Structured hallucination assessment for an individual claim."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    claim_id: str = Field(
        ...,
        description="Identifier of the evaluated claim.",
    )
    hallucination_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated probability that the claim is a hallucination in [0.0, 1.0].",
    )
    is_hallucination: bool = Field(
        ...,
        description="Boolean flag indicating whether the claim exceeds the hallucination threshold.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Human-readable explanations for the flag (guaranteed non-empty when flagged).",
    )
    signals: HallucinationSignals = Field(
        ...,
        description="Detailed breakdown of the 5 extracted hallucination signals.",
    )


class ResponseHallucinationResult(BaseModel):
    """Aggregate hallucination assessment across all claims in a response."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    claim_results: list[HallucinationResult] = Field(
        default_factory=list,
        description="Per-claim hallucination assessment results.",
    )
    overall_hallucination_probability: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Aggregate response-level hallucination probability in [0.0, 1.0].",
    )
    has_hallucination: bool = Field(
        default=False,
        description="Whether any claim in the response was flagged as a hallucination.",
    )
    hallucinated_claim_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers of claims flagged as hallucinations.",
    )
    summary_reasons: list[str] = Field(
        default_factory=list,
        description="Deduplicated summary of reasons across all flagged claims.",
    )

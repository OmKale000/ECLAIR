"""Data models for M06 Evidence Quality & Conflict Detection.

Defines the structured quality signal representations, conflict details,
scored evidence containers, and batch assessment reports.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from eclair.contracts.evidence import Evidence

__all__ = [
    "EvidenceQualitySignals",
    "ConflictDetail",
    "ScoredEvidence",
    "EvidenceQualityReport",
]


class EvidenceQualitySignals(BaseModel):
    """Structured quality signals for an individual evidence item."""

    model_config = {"extra": "forbid"}

    evidence_id: str = Field(
        ...,
        description="Identifier of the evaluated evidence item.",
    )
    relevance_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Relevance of evidence to query/claim in [0.0, 1.0].",
    )
    authority_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Credibility and authority of the source in [0.0, 1.0].",
    )
    freshness_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Recency and temporal validity in [0.0, 1.0].",
    )
    completeness_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Informativeness and passage completeness in [0.0, 1.0].",
    )
    conflict_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Degree of conflict with other evidence in [0.0, 1.0] (0.0 = no conflict).",
    )
    overall_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Composite overall quality score in [0.0, 1.0].",
    )
    is_outdated: bool = Field(
        default=False,
        description="Whether the evidence is identified as outdated or deprecated.",
    )
    is_duplicate: bool = Field(
        default=False,
        description="Whether the evidence is identified as duplicate/redundant.",
    )
    is_conflicting: bool = Field(
        default=False,
        description="Whether the evidence has significant conflicts with other evidence.",
    )
    is_low_quality: bool = Field(
        default=False,
        description="Whether the evidence falls below the minimum quality threshold.",
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Quality and diagnostic flags (e.g. 'OUTDATED', 'DUPLICATE', 'LOW_AUTHORITY').",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional contextual or diagnostic metadata.",
    )


class ConflictDetail(BaseModel):
    """Detailed record of a conflict between two evidence items or evidence and claim."""

    model_config = {"extra": "forbid"}

    evidence_id_a: str = Field(
        ...,
        description="Identifier of the first conflicting evidence item.",
    )
    evidence_id_b: str = Field(
        ...,
        description="Identifier of the second conflicting evidence item.",
    )
    conflict_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Severity of the detected conflict in [0.0, 1.0].",
    )
    conflict_type: str = Field(
        default="semantic",
        description="Type of conflict (e.g. 'numerical', 'polarity', 'semantic', 'policy').",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation of why a conflict was detected.",
    )
    passage_a_snippet: str | None = Field(
        default=None,
        description="Short excerpt from the first passage highlighting the contradiction.",
    )
    passage_b_snippet: str | None = Field(
        default=None,
        description="Short excerpt from the second passage highlighting the contradiction.",
    )


class ScoredEvidence(BaseModel):
    """Container pairing an M01 Evidence contract with its evaluated quality signals."""

    model_config = {"extra": "forbid"}

    evidence: Evidence = Field(
        ...,
        description="The original M01 Evidence instance.",
    )
    signals: EvidenceQualitySignals = Field(
        ...,
        description="Structured quality signals for this evidence item.",
    )


class EvidenceQualityReport(BaseModel):
    """Comprehensive assessment report for a batch of retrieved evidence."""

    model_config = {"extra": "forbid"}

    items: list[ScoredEvidence] = Field(
        default_factory=list,
        description="List of scored evidence containers.",
    )
    average_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Mean composite quality score across all evidence items.",
    )
    is_insufficient: bool = Field(
        default=False,
        description="Signal indicating whether evidence is missing or of insufficient quality.",
    )
    has_conflicts: bool = Field(
        default=False,
        description="Whether any pairwise conflicts were detected in the evidence set.",
    )
    conflicts: list[ConflictDetail] = Field(
        default_factory=list,
        description="Detailed list of all detected conflicts.",
    )
    duplicate_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers of evidence items flagged as duplicates.",
    )
    outdated_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers of evidence items flagged as outdated.",
    )
    low_quality_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers of evidence items flagged as low quality.",
    )
    summary_flags: list[str] = Field(
        default_factory=list,
        description="Summary-level assessment flags (e.g. 'HAS_CONFLICTS', 'INSUFFICIENT_EVIDENCE').",
    )

    @property
    def evidence_list(self) -> list[Evidence]:
        """Return the raw list of M01 Evidence objects."""
        return [item.evidence for item in self.items]

    @property
    def signals_list(self) -> list[EvidenceQualitySignals]:
        """Return the list of EvidenceQualitySignals objects."""
        return [item.signals for item in self.items]

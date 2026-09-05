"""Data models for M09 Multi-Agent / Multi-Model Consensus.

Defines the configuration, model output representations, voting results,
agreement calculations, diversity metrics, and aggregate consensus results.
Reuses frozen shared enums from M01 (``ConsensusLevel``) and maintains the
non-negotiable reliability invariant: model agreement is NOT proof of truth
(Spec sec.4.6, SHARED_CONTRACTS_REFERENCE sec.6).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from eclair.contracts.enums import ConsensusLevel

__all__ = [
    "ModelCallConfig",
    "ModelOutput",
    "VoteCluster",
    "VotingResult",
    "AgreementResult",
    "DiversityResult",
    "ConsensusResult",
]


class ModelCallConfig(BaseModel):
    """Specification for an individual model call in consensus execution."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    provider: str = Field(
        default="ollama",
        min_length=1,
        description="Provider name (e.g. 'ollama', 'gemini', 'groq', 'openrouter').",
    )
    model: str | None = Field(
        default=None,
        description="Optional model override; when None, provider default model is used.",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Optional sampling temperature for generation.",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Optional maximum number of tokens to generate.",
    )
    json_mode: bool = Field(
        default=False,
        description="Whether to request structured JSON output from the model.",
    )


class ModelOutput(BaseModel):
    """Result of an individual model generation within a consensus run."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    model: str = Field(
        ...,
        min_length=1,
        description="Identifier of the model that produced the output.",
    )
    provider: str = Field(
        ...,
        min_length=1,
        description="Provider name that produced the output.",
    )
    text: str = Field(
        default="",
        description="Raw generated text or answer from the model.",
    )
    success: bool = Field(
        default=True,
        description="Whether the generation call succeeded without error.",
    )
    error: str | None = Field(
        default=None,
        description="Error description if the model call failed.",
    )
    latency_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Time taken for the individual model call in seconds.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic metadata and provider details.",
    )


class VoteCluster(BaseModel):
    """Cluster of equivalent or matching model outputs."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    representative_text: str = Field(
        ...,
        description="Canonical or representative text for this vote cluster.",
    )
    vote_count: int = Field(
        ...,
        ge=1,
        description="Number of model outputs supporting this cluster.",
    )
    vote_share: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Proportion of total valid votes assigned to this cluster.",
    )
    model_names: list[str] = Field(
        default_factory=list,
        description="Names of models that voted for this cluster.",
    )


class VotingResult(BaseModel):
    """Outcome of majority voting over independent model outputs."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    majority_answer: str | None = Field(
        default=None,
        description="The winning or plurality answer text.",
    )
    winning_vote_count: int = Field(
        default=0,
        ge=0,
        description="Vote count received by the winning cluster.",
    )
    total_votes: int = Field(
        default=0,
        ge=0,
        description="Total number of valid successful model votes tallied.",
    )
    majority_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of total votes received by the winning cluster.",
    )
    has_majority: bool = Field(
        default=False,
        description="True if majority_ratio > 0.5 with at least one vote.",
    )
    unanimous: bool = Field(
        default=False,
        description="True if all successful models agreed on the exact same cluster.",
    )
    clusters: list[VoteCluster] = Field(
        default_factory=list,
        description="All vote clusters ordered by descending vote count.",
    )
    vote_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Summary mapping of cluster representatives to vote counts.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic details of the voting process.",
    )


class AgreementResult(BaseModel):
    """Outcome of agreement score and consensus classification calculation."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    agreement_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quantified cross-model agreement score in [0.0, 1.0].",
    )
    consensus_level: ConsensusLevel = Field(
        ...,
        description="Categorical consensus indicator: FULL or PARTIAL (Spec sec.M09).",
    )
    mean_pairwise_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average pairwise semantic/lexical similarity across model pairs.",
    )
    pairwise_similarities: list[float] = Field(
        default_factory=list,
        description="Pairwise similarity values for all evaluated model pairs.",
    )
    unanimous: bool = Field(
        default=False,
        description="Whether all models agreed unanimously.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed diagnostic metadata on agreement calculation.",
    )


class DiversityResult(BaseModel):
    """Metrics measuring output and provider diversity in consensus execution."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    diversity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Normalized diversity metric in [0.0, 1.0] (0.0 = identical, 1.0 = maximally diverse).",
    )
    unique_answer_count: int = Field(
        default=0,
        ge=0,
        description="Count of distinct answer clusters generated by models.",
    )
    mean_pairwise_distance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average pairwise distance (1 - similarity) across model pairs.",
    )
    provider_diversity_count: int = Field(
        default=0,
        ge=0,
        description="Number of distinct provider architectures represented.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional diversity diagnostics.",
    )


class ConsensusResult(BaseModel):
    """Aggregate multi-model consensus evaluation for a prompt or query."""

    model_config = {"extra": "forbid", "protected_namespaces": ()}

    query: str = Field(
        ...,
        min_length=1,
        description="The query or prompt evaluated across independent models.",
    )
    agreement_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quantified agreement score in [0.0, 1.0] (Spec sec.M09).",
    )
    consensus_level: ConsensusLevel = Field(
        ...,
        description="ConsensusLevel.FULL or ConsensusLevel.PARTIAL (frozen enum).",
    )
    majority_answer: str | None = Field(
        default=None,
        description="The winning or plurality answer text identified by voting.",
    )
    model_outputs: list[ModelOutput] = Field(
        default_factory=list,
        description="Outputs from all queried models, including any failed calls.",
    )
    successful_models: list[str] = Field(
        default_factory=list,
        description="Names of models that completed generation successfully.",
    )
    failed_models: list[str] = Field(
        default_factory=list,
        description="Names of models that failed or returned errors.",
    )
    voting: VotingResult | None = Field(
        default=None,
        description="Voting tally and cluster breakdown.",
    )
    agreement: AgreementResult | None = Field(
        default=None,
        description="Detailed pairwise agreement calculation.",
    )
    diversity: DiversityResult | None = Field(
        default=None,
        description="Output and provider diversity analysis.",
    )
    is_truth: bool = Field(
        default=False,
        description="Non-negotiable reliability invariant: model agreement is NOT truth (Spec sec.4.6).",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic metadata and execution information.",
    )

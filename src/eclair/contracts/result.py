"""EclairResult contract (M01 Foundation).

The final aggregate result produced by the engine/orchestrator (Spec sec.4.1).
It ties the pipeline stage outputs together, keyed by ``query_id`` for
provenance (Spec sec.M14).

Fields mirror the pipeline stage outputs (Spec sec.5). Stage outputs are
optional so the engine can assemble the result incrementally; M01 defines the
shape only and computes nothing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.evidence import Evidence
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult

__all__ = ["EclairResult"]


class EclairResult(BaseModel):
    """Aggregate of the full reliability pipeline for a single query."""

    model_config = {"extra": "forbid"}

    query_id: str = Field(
        ...,
        description="Identifier tying this result to its provenance lineage.",
    )
    answer: str | None = Field(
        default=None,
        description="The final answer text, if one is returned.",
    )
    claims: list[Claim] = Field(
        default_factory=list,
        description="Claims extracted from the generated answer (M03).",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Evidence retrieved and quality-annotated (M05/M06).",
    )
    verifications: list[VerificationResult] = Field(
        default_factory=list,
        description="Per-claim verification results (M07).",
    )
    confidence: ConfidenceResult | None = Field(
        default=None,
        description="Confidence result (raw from M10, calibrated ECS from M11).",
    )
    risk: RiskResult | None = Field(
        default=None,
        description="Risk assessment (M13).",
    )
    decision: DecisionResult | None = Field(
        default=None,
        description="Final decision/action (M13).",
    )

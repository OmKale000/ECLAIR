"""Evidence contract (M01 Foundation).

A retrieved evidence passage. Produced by M05 (RAG) as ``list[Evidence]`` and
quality-annotated by M06 (Evidence Quality) before verification (Spec sec.4.1).

The quality-annotation fields are optional so that M05 may emit un-annotated
evidence and M06 may populate the annotations, without either module redefining
the contract.
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

__all__ = ["Evidence"]


class Evidence(BaseModel):
    """A single evidence passage retrieved from the controlled knowledge base."""

    model_config = {"extra": "forbid"}

    evidence_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Stable identifier for this evidence item.",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="The evidence passage text.",
    )
    source: str | None = Field(
        default=None,
        description="Origin of the passage (e.g. knowledge-base document name).",
    )
    relevance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Retrieval/quality relevance score (annotated by M05/M06).",
    )

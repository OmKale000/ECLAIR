"""Data models for M05 RAG / Evidence Retrieval.

Defines the internal chunk representations and retrieval score containers used
across the chunking, embedding, indexing, and retrieval pipeline.
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from eclair.contracts.evidence import Evidence
from eclair.ingestion.metadata import DocumentMetadata

__all__ = ["TextChunk", "ScoredChunk"]


class TextChunk(BaseModel):
    """A single searchable passage extracted from an M04 standardized document."""

    model_config = {"extra": "forbid"}

    chunk_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Stable identifier for this chunk.",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="The textual content of the chunk passage.",
    )
    doc_id: str = Field(
        ...,
        min_length=1,
        description="ID of the parent M04 document this chunk originated from.",
    )
    metadata: DocumentMetadata = Field(
        ...,
        description="Standardized document metadata preserved from the source document.",
    )
    chunk_index: int = Field(
        default=0,
        ge=0,
        description="0-indexed position of this chunk within the parent document.",
    )

    def to_evidence(self, relevance_score: float | None = None) -> Evidence:
        """Convert this chunk into an M01 Evidence contract.

        Args:
            relevance_score: Optional retrieval/similarity score in [0.0, 1.0].

        Returns:
            A valid M01 :class:`Evidence` instance.
        """
        score: float | None = None
        if relevance_score is not None:
            # Ensure score is strictly bounded within [0.0, 1.0] for M01 Evidence validation
            score = max(0.0, min(1.0, float(relevance_score)))

        return Evidence(
            evidence_id=self.chunk_id,
            text=self.text,
            source=self.metadata.source,
            relevance_score=score,
        )


class ScoredChunk(BaseModel):
    """Container pairing a chunk with its similarity/relevance score."""

    model_config = {"extra": "forbid"}

    chunk: TextChunk = Field(..., description="The retrieved text chunk.")
    score: float = Field(..., description="Similarity or ranking score.")

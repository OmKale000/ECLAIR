"""Optional reranking for M05 RAG / Evidence Retrieval.

Provides reranking abstractions and implementations to reorder retrieved candidate
evidence without modifying Evidence contracts or performing verification.
"""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

from eclair.contracts.evidence import Evidence

__all__ = ["Reranker", "NoOpReranker", "SimilarityReranker"]


@runtime_checkable
class Reranker(Protocol):
    """Interface for candidate evidence rerankers."""

    def rerank(self, query: str, candidates: list[Evidence]) -> list[Evidence]:
        """Reorder candidate evidence based on refined relevance scoring."""
        ...


class NoOpReranker:
    """Default pass-through reranker that leaves candidate ordering unchanged."""

    def rerank(self, query: str, candidates: list[Evidence]) -> list[Evidence]:
        """Return candidate evidence unchanged."""
        return list(candidates)


class SimilarityReranker:
    """Reranks candidate evidence based on lexical or custom similarity scoring.

    Only reorders candidate evidence and adjusts relevance_score; never alters
    text, source, or verification semantics.
    """

    def __init__(
        self,
        *,
        scorer: Callable[[str, Evidence], float] | None = None,
    ) -> None:
        self._scorer = scorer or self._default_lexical_scorer

    def rerank(self, query: str, candidates: list[Evidence]) -> list[Evidence]:
        """Rerank candidates using the configured scorer in descending order."""
        if not candidates or not query.strip():
            return list(candidates)

        scored_items: list[tuple[Evidence, float]] = []
        for item in candidates:
            score = self._scorer(query, item)
            clamped_score = max(0.0, min(1.0, float(score)))
            # Create a copy with updated relevance_score
            updated = Evidence(
                evidence_id=item.evidence_id,
                text=item.text,
                source=item.source,
                relevance_score=clamped_score,
            )
            scored_items.append((updated, clamped_score))

        # Sort descending by score
        scored_items.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in scored_items]

    @staticmethod
    def _default_lexical_scorer(query: str, evidence: Evidence) -> float:
        """Compute word-overlap Jaccard similarity between query and evidence."""
        query_words = set(query.lower().split())
        evidence_words = set(evidence.text.lower().split())
        if not query_words or not evidence_words:
            return evidence.relevance_score if evidence.relevance_score is not None else 0.0

        intersection = query_words.intersection(evidence_words)
        union = query_words.union(evidence_words)
        jaccard = len(intersection) / len(union) if union else 0.0

        base_score = evidence.relevance_score if evidence.relevance_score is not None else 0.5
        # Blend base vector score with lexical overlap (70% vector score + 30% lexical)
        blended = 0.7 * base_score + 0.3 * jaccard
        return max(0.0, min(1.0, blended))

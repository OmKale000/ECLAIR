"""Unit tests for M05 Rerankers (NoOpReranker and SimilarityReranker).

Tests reranking candidate evidence without altering contract integrity or verification.
"""

from __future__ import annotations

import pytest

from eclair.contracts.evidence import Evidence
from eclair.rag.reranker import NoOpReranker, SimilarityReranker


def _make_evidence(text: str, source: str = "doc.md", score: float | None = 0.5) -> Evidence:
    return Evidence(text=text, source=source, relevance_score=score)


def test_noop_reranker_returns_unchanged_order() -> None:
    reranker = NoOpReranker()
    ev1 = _make_evidence("First evidence item", score=0.8)
    ev2 = _make_evidence("Second evidence item", score=0.6)

    result = reranker.rerank("query text", [ev1, ev2])
    assert len(result) == 2
    assert result[0] == ev1
    assert result[1] == ev2


def test_similarity_reranker_reorders_by_relevance() -> None:
    reranker = SimilarityReranker()
    ev1 = _make_evidence("General company policy on office hours.", score=0.4)
    ev2 = _make_evidence("Full refund available within thirty days of purchase.", score=0.5)

    query = "thirty days refund policy"
    reranked = reranker.rerank(query, [ev1, ev2])

    assert len(reranked) == 2
    # ev2 has higher lexical overlap with query and should be ranked first
    assert "refund" in reranked[0].text
    assert reranked[0].source == "doc.md"
    assert reranked[0].relevance_score is not None
    assert reranked[0].relevance_score >= (reranked[1].relevance_score or 0.0)


def test_similarity_reranker_empty_inputs() -> None:
    reranker = SimilarityReranker()

    assert reranker.rerank("", []) == []

    ev = _make_evidence("Some text")
    assert reranker.rerank("", [ev]) == [ev]
    assert reranker.rerank("query", []) == []


def test_custom_scorer_injection() -> None:
    def custom_scorer(query: str, evidence: Evidence) -> float:
        # Boost if word "urgent" appears (case-insensitive)
        return 0.95 if "urgent" in evidence.text.lower() else 0.1

    reranker = SimilarityReranker(scorer=custom_scorer)
    ev1 = _make_evidence("Standard routine update", score=0.8)
    ev2 = _make_evidence("Urgent action required for account", score=0.2)

    reranked = reranker.rerank("query", [ev1, ev2])
    assert reranked[0].text == "Urgent action required for account"
    assert reranked[0].relevance_score == pytest.approx(0.95)
    assert reranked[1].relevance_score == pytest.approx(0.1)

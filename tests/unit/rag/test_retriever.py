"""Unit tests for M05 Retriever orchestrator.

Tests search/retrieve interfaces, top_k limits, empty handling, ranking order,
and M01 Evidence contract compliance.
"""

from __future__ import annotations

import pytest

from eclair.contracts.evidence import Evidence
from eclair.contracts.interfaces import Retriever as RetrieverProtocol
from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import Document, DocumentMetadata
from eclair.rag.embeddings import EmbeddingGenerator
from eclair.rag.index import VectorIndex
from eclair.rag.reranker import SimilarityReranker
from eclair.rag.retriever import DEFAULT_TOP_K, Retriever


class DeterministicWordEncoder:
    """Deterministic offline encoder for retriever testing."""

    def __init__(self, dim: int = 16) -> None:
        self.dim = dim

    def encode(self, sentences: list[str]) -> list[list[float]]:
        vecs: list[list[float]] = []
        for s in sentences:
            v = [0.0] * self.dim
            for w in s.lower().replace(".", "").replace(",", "").split():
                idx = abs(hash(w)) % self.dim
                v[idx] += 1.0
            norm = sum(x * x for x in v) ** 0.5
            if norm > 0:
                v = [x / norm for x in v]
            else:
                v[0] = 1.0
            vecs.append(v)
        return vecs


def _make_doc(text: str, doc_id: str, source: str = "kb/refund.md") -> Document:
    meta = DocumentMetadata(
        filename=source.split("/")[-1],
        source=source,
        created_date="2026-01-01T00:00:00Z",
        modified_date="2026-01-02T00:00:00Z",
        page_number=1,
        document_version="1.0",
    )
    return Document(doc_id=doc_id, text=text, metadata=meta)


def _build_test_retriever() -> Retriever:
    encoder = DeterministicWordEncoder(dim=16)
    embedder = EmbeddingGenerator(encoder=encoder)
    index = VectorIndex(dimension=16)
    return Retriever(index=index, embedder=embedder)


def test_retriever_protocol_conformance() -> None:
    retriever = _build_test_retriever()
    assert isinstance(retriever, RetrieverProtocol)


def test_search_and_retrieve_empty_index_returns_empty_list() -> None:
    retriever = _build_test_retriever()
    assert retriever.search("refund policy") == []
    assert retriever.retrieve("refund policy") == []


def test_search_empty_query_returns_empty_list() -> None:
    retriever = _build_test_retriever()
    doc = _make_doc("Refund policy allows returns within 30 days.", "doc-1")
    retriever.index_documents([doc])

    assert retriever.search("") == []
    assert retriever.search("   \n\t  ") == []
    assert retriever.retrieve("") == []


def test_invalid_top_k_raises_module_error() -> None:
    retriever = _build_test_retriever()
    doc = _make_doc("Sample content.", "doc-1")
    retriever.index_documents([doc])

    with pytest.raises(ModuleError) as exc1:
        retriever.search("sample", top_k=0)
    assert exc1.value.code == "rag_invalid_top_k"

    with pytest.raises(ModuleError) as exc2:
        retriever.retrieve("sample", top_k=-5)
    assert exc2.value.code == "rag_invalid_top_k"


def test_retrieve_default_top_k_and_custom_top_k() -> None:
    retriever = _build_test_retriever()
    docs = [
        _make_doc("Document number zero with unique words zero.", "doc-0"),
        _make_doc("Document number one with unique words one.", "doc-1"),
        _make_doc("Document number two with unique words two.", "doc-2"),
        _make_doc("Document number three with unique words three.", "doc-3"),
        _make_doc("Document number four with unique words four.", "doc-4"),
        _make_doc("Document number five with unique words five.", "doc-5"),
        _make_doc("Document number six with unique words six.", "doc-6"),
    ]
    retriever.index_documents(docs)

    # Default top_k is 5
    default_results = retriever.search("Document words")
    assert len(default_results) == DEFAULT_TOP_K
    assert len(default_results) == 5

    # top_k = 1
    top1_results = retriever.retrieve("Document words", top_k=1)
    assert len(top1_results) == 1

    # top_k = 3
    top3_results = retriever.retrieve("Document words", top_k=3)
    assert len(top3_results) == 3

    # top_k larger than total candidates returns total candidates
    large_results = retriever.retrieve("Document words", top_k=100)
    assert len(large_results) == len(docs)


def test_returned_objects_are_valid_m01_evidence_contracts() -> None:
    retriever = _build_test_retriever()
    doc = _make_doc("Refunds are processed within 14 days.", "doc-1", "kb/refund.md")
    retriever.index_documents([doc])

    results = retriever.search("refunds days", top_k=1)
    assert len(results) == 1

    ev = results[0]
    assert isinstance(ev, Evidence)
    assert ev.text == "Refunds are processed within 14 days."
    assert ev.source == "kb/refund.md"
    assert ev.evidence_id is not None
    assert isinstance(ev.evidence_id, str)
    assert ev.relevance_score is not None
    assert 0.0 <= ev.relevance_score <= 1.0


def test_ranking_order_descending() -> None:
    retriever = _build_test_retriever()
    docs = [
        _make_doc("Completely unrelated text about aviation.", "doc-1"),
        _make_doc("Full refund is issued within 30 days of purchase.", "doc-2"),
        _make_doc("Partial refund may apply for opened products.", "doc-3"),
    ]
    retriever.index_documents(docs)

    results = retriever.search("full refund purchase 30 days", top_k=3)
    assert len(results) == 3

    # Top result should be doc-2
    assert "Full refund is issued" in results[0].text
    # Scores must be in descending order
    for i in range(len(results) - 1):
        assert (results[i].relevance_score or 0.0) >= (results[i + 1].relevance_score or 0.0)


def test_retriever_with_reranker() -> None:
    encoder = DeterministicWordEncoder(dim=16)
    embedder = EmbeddingGenerator(encoder=encoder)
    index = VectorIndex(dimension=16)
    reranker = SimilarityReranker()
    retriever = Retriever(index=index, embedder=embedder, reranker=reranker)

    docs = [
        _make_doc("General terms and conditions.", "doc-1"),
        _make_doc("Special policy for international customers.", "doc-2"),
    ]
    retriever.index_documents(docs)

    results = retriever.retrieve("international customer policy", top_k=2)
    assert len(results) == 2
    assert "international" in results[0].text

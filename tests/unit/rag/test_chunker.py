"""Unit tests for M05 DocumentChunker.

Tests document chunking, metadata preservation, source traceability,
small/large document handling, and edge cases.
"""

from __future__ import annotations

import pytest

from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import Document, DocumentMetadata
from eclair.rag.chunker import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, DocumentChunker


def _make_document(
    text: str,
    *,
    filename: str = "refund_policy.md",
    source: str = "data/knowledge_base/refund_policy/refund_policy.md",
    page_number: int | None = 1,
    doc_id: str = "doc-123",
) -> Document:
    meta = DocumentMetadata(
        filename=filename,
        source=source,
        created_date="2026-01-01T00:00:00Z",
        modified_date="2026-01-02T00:00:00Z",
        page_number=page_number,
        document_version="1.0",
    )
    return Document(doc_id=doc_id, text=text, metadata=meta)


def test_chunker_initialization_defaults() -> None:
    chunker = DocumentChunker()
    assert chunker.chunk_size == DEFAULT_CHUNK_SIZE
    assert chunker.chunk_overlap == DEFAULT_CHUNK_OVERLAP


def test_chunker_invalid_parameters() -> None:
    with pytest.raises(ModuleError) as exc_info:
        DocumentChunker(chunk_size=0)
    assert exc_info.value.code == "rag_invalid_chunk_size"

    with pytest.raises(ModuleError) as exc_info2:
        DocumentChunker(chunk_size=100, chunk_overlap=150)
    assert exc_info2.value.code == "rag_invalid_chunk_overlap"

    with pytest.raises(ModuleError) as exc_info3:
        DocumentChunker(chunk_size=100, chunk_overlap=-1)
    assert exc_info3.value.code == "rag_invalid_chunk_overlap"


def test_valid_document_produces_chunks_and_preserves_metadata() -> None:
    doc = _make_document("Customers may request a full refund within 30 days of purchase.")
    chunker = DocumentChunker(chunk_size=100)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.text == "Customers may request a full refund within 30 days of purchase."
    assert chunk.doc_id == "doc-123"
    assert chunk.metadata.filename == "refund_policy.md"
    assert chunk.metadata.source == "data/knowledge_base/refund_policy/refund_policy.md"
    assert chunk.metadata.page_number == 1
    assert chunk.metadata.document_version == "1.0"
    assert chunk.chunk_index == 0


def test_small_document_smaller_than_chunk_size() -> None:
    doc = _make_document("Short text.")
    chunker = DocumentChunker(chunk_size=500)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) == 1
    assert chunks[0].text == "Short text."
    assert chunks[0].chunk_index == 0


def test_document_requiring_multiple_chunks() -> None:
    paragraphs = [
        "Paragraph one is discussing the initial terms of service and refund windows.",
        "Paragraph two describes exceptions for digital goods and gift cards after purchase.",
        "Paragraph three covers shipping fees and return labels for international orders.",
    ]
    long_text = "\n\n".join(paragraphs)
    doc = _make_document(long_text)
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 3
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.doc_id == "doc-123"
        assert c.metadata.source == "data/knowledge_base/refund_policy/refund_policy.md"
        assert len(c.text) > 0


def test_chunk_documents_multiple_inputs() -> None:
    doc1 = _make_document("Doc 1 content text.", doc_id="doc-1")
    doc2 = _make_document("Doc 2 content text.", doc_id="doc-2")

    chunker = DocumentChunker()
    chunks = chunker.chunk_documents([doc1, doc2])

    assert len(chunks) == 2
    assert chunks[0].doc_id == "doc-1"
    assert chunks[1].doc_id == "doc-2"


def test_chunk_documents_empty_list() -> None:
    chunker = DocumentChunker()
    chunks = chunker.chunk_documents([])
    assert chunks == []


def test_text_chunk_to_evidence_conversion() -> None:
    doc = _make_document("Refunds are processed in 5-7 business days.")
    chunker = DocumentChunker()
    chunks = chunker.chunk_document(doc)
    assert len(chunks) == 1

    evidence = chunks[0].to_evidence(relevance_score=0.88)
    assert evidence.evidence_id == chunks[0].chunk_id
    assert evidence.text == "Refunds are processed in 5-7 business days."
    assert evidence.source == "data/knowledge_base/refund_policy/refund_policy.md"
    assert evidence.relevance_score == pytest.approx(0.88)


def test_text_chunk_to_evidence_score_clamping() -> None:
    doc = _make_document("Refunds are processed in 5-7 business days.")
    chunker = DocumentChunker()
    chunk = chunker.chunk_document(doc)[0]

    ev_high = chunk.to_evidence(relevance_score=1.5)
    assert ev_high.relevance_score == 1.0

    ev_low = chunk.to_evidence(relevance_score=-0.2)
    assert ev_low.relevance_score == 0.0

    ev_none = chunk.to_evidence(relevance_score=None)
    assert ev_none.relevance_score is None

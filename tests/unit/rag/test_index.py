"""Unit tests for M05 VectorIndex and FAISSIndex.

Tests adding chunks, similarity search, top-k ranking, dimension checks,
empty index handling, clear, and persistence.
"""

from __future__ import annotations

import tempfile

import numpy as np
import pytest

from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import DocumentMetadata
from eclair.rag.index import FAISSIndex, VectorIndex
from eclair.rag.models import TextChunk


def _make_chunk(text: str, doc_id: str = "doc-1", idx: int = 0) -> TextChunk:
    meta = DocumentMetadata(
        filename="policy.md",
        source="data/knowledge_base/policy.md",
        created_date="2026-01-01T00:00:00Z",
        modified_date="2026-01-02T00:00:00Z",
    )
    return TextChunk(text=text, doc_id=doc_id, metadata=meta, chunk_index=idx)


def test_empty_index_returns_empty_results() -> None:
    index = VectorIndex()
    assert len(index) == 0

    query_vec = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    # Search on uninitialized empty index returns []
    results = index.search(query_vec, top_k=5)
    assert results == []


def test_invalid_top_k_raises_module_error() -> None:
    index = VectorIndex()
    query_vec = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)

    with pytest.raises(ModuleError) as exc1:
        index.search(query_vec, top_k=0)
    assert exc1.value.code == "rag_invalid_top_k"

    with pytest.raises(ModuleError) as exc2:
        index.search(query_vec, top_k=-2)
    assert exc2.value.code == "rag_invalid_top_k"


def test_add_chunks_and_search_ranking() -> None:
    index = VectorIndex()

    c1 = _make_chunk("Chunk about returns and refunds", "doc-1", 0)
    c2 = _make_chunk("Chunk about shipping timelines", "doc-1", 1)
    c3 = _make_chunk("Chunk about account login security", "doc-2", 0)

    # Orthogonal or distinct 3D unit vectors
    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],  # matches query [1, 0, 0] perfectly
            [0.0, 1.0, 0.0],  # orthogonal
            [0.6, 0.8, 0.0],  # partial match (cos ~ 0.6)
        ],
        dtype=np.float32,
    )

    index.add_chunks([c1, c2, c3], embeddings)
    assert len(index) == 3
    assert index.dimension == 3

    query_vec = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    results = index.search(query_vec, top_k=3)

    assert len(results) == 3
    # First candidate should be c1 with score ~ 1.0
    assert results[0][0].text == "Chunk about returns and refunds"
    assert results[0][1] == pytest.approx(1.0, abs=1e-3)

    # Second candidate should be c3 with score ~ 0.6
    assert results[1][0].text == "Chunk about account login security"
    assert results[1][1] == pytest.approx(0.6, abs=1e-3)

    # Third candidate should be c2 with score ~ 0.0
    assert results[2][0].text == "Chunk about shipping timelines"
    assert results[2][1] == pytest.approx(0.0, abs=1e-3)


def test_top_k_bounds_respected() -> None:
    index = VectorIndex()
    chunks = [_make_chunk(f"Chunk {i}", f"doc-{i}", i) for i in range(10)]
    embeddings = np.zeros((10, 4), dtype=np.float32)
    for i in range(10):
        embeddings[i, i % 4] = 1.0

    index.add_chunks(chunks, embeddings)

    query_vec = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    results_top2 = index.search(query_vec, top_k=2)
    assert len(results_top2) == 2

    results_top5 = index.search(query_vec, top_k=5)
    assert len(results_top5) == 5

    # Requesting more than total available returns len(chunks)
    results_top20 = index.search(query_vec, top_k=20)
    assert len(results_top20) == 10


def test_dimension_mismatch_raises_error() -> None:
    index = VectorIndex()
    c1 = _make_chunk("Chunk 1")
    emb1 = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    index.add_chunks([c1], emb1)

    # Adding a chunk with 4 dimensions to a 3-dimension index
    c2 = _make_chunk("Chunk 2")
    emb2 = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    with pytest.raises(ModuleError) as exc1:
        index.add_chunks([c2], emb2)
    assert exc1.value.code == "rag_dimension_mismatch"

    # Searching with a 4-dimension query
    query_4d = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    with pytest.raises(ModuleError) as exc2:
        index.search(query_4d, top_k=3)
    assert exc2.value.code == "rag_dimension_mismatch"


def test_chunk_embedding_count_mismatch_raises_error() -> None:
    index = VectorIndex()
    c1 = _make_chunk("Chunk 1")
    c2 = _make_chunk("Chunk 2")
    emb = np.array([[1.0, 0.0]], dtype=np.float32)

    with pytest.raises(ModuleError) as exc:
        index.add_chunks([c1, c2], emb)
    assert exc.value.code == "rag_chunk_embedding_mismatch"


def test_clear_and_reindex() -> None:
    index = VectorIndex()
    c1 = _make_chunk("Chunk 1")
    index.add_chunks([c1], np.array([[1.0, 0.0]], dtype=np.float32))
    assert len(index) == 1

    index.clear()
    assert len(index) == 0
    assert len(index.chunks) == 0


def test_index_persistence_save_and_load() -> None:
    index = VectorIndex()
    c1 = _make_chunk("Chunk 1 text", "doc-1", 0)
    c2 = _make_chunk("Chunk 2 text", "doc-2", 0)
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    index.add_chunks([c1, c2], embeddings)

    with tempfile.TemporaryDirectory() as tmp_dir:
        index.save(tmp_dir)

        loaded_index = FAISSIndex()
        loaded_index.load(tmp_dir)

        assert len(loaded_index) == 2
        assert loaded_index.dimension == 2
        assert loaded_index.chunks[0].text == "Chunk 1 text"
        assert loaded_index.chunks[1].text == "Chunk 2 text"

        query_vec = np.array([[1.0, 0.0]], dtype=np.float32)
        results = loaded_index.search(query_vec, top_k=1)
        assert len(results) == 1
        assert results[0][0].text == "Chunk 1 text"
        assert results[0][1] == pytest.approx(1.0, abs=1e-3)

"""Unit tests for M05 EmbeddingGenerator.

Tests embedding generation, dimension consistency, query vs chunk symmetry,
normalization, and error handling using deterministic offline encoders.
"""

from __future__ import annotations

import numpy as np
import pytest

from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import DocumentMetadata
from eclair.rag.embeddings import EmbeddingGenerator
from eclair.rag.models import TextChunk


class DeterministicFakeEncoder:
    """Offline fake encoder mapping words to deterministic dense float vectors."""

    def __init__(self, dim: int = 8) -> None:
        self.dim = dim

    def encode(self, sentences: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for s in sentences:
            # Deterministic hash-based vector
            vec = [0.0] * self.dim
            for word in s.lower().split():
                idx = hash(word) % self.dim
                vec[idx] += 1.0
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            else:
                vec[0] = 1.0
            vectors.append(vec)
        return vectors


def _make_chunk(text: str, idx: int = 0) -> TextChunk:
    meta = DocumentMetadata(
        filename="test.md",
        source="data/test.md",
        created_date="2026-01-01T00:00:00Z",
        modified_date="2026-01-02T00:00:00Z",
    )
    return TextChunk(text=text, doc_id="doc-1", metadata=meta, chunk_index=idx)


def test_embed_texts_produces_normalized_numerical_arrays() -> None:
    encoder = DeterministicFakeEncoder(dim=16)
    generator = EmbeddingGenerator(encoder=encoder)

    texts = ["Refunds are available for 30 days.", "Invoices must be paid within 14 days."]
    embeddings = generator.embed_texts(texts)

    assert isinstance(embeddings, np.ndarray)
    assert embeddings.shape == (2, 16)
    assert embeddings.dtype == np.float32

    # Check normalization (unit norm)
    norms = np.linalg.norm(embeddings, axis=1)
    np.testing.assert_allclose(norms, [1.0, 1.0], rtol=1e-5)


def test_embed_chunks_consistent_dimensions() -> None:
    encoder = DeterministicFakeEncoder(dim=12)
    generator = EmbeddingGenerator(encoder=encoder)

    chunks = [
        _make_chunk("Chunk one text", 0),
        _make_chunk("Chunk two text", 1),
        _make_chunk("Chunk three text", 2),
    ]
    embeddings = generator.embed_chunks(chunks)

    assert embeddings.shape == (3, 12)


def test_query_and_chunk_embeddings_have_same_dimension() -> None:
    encoder = DeterministicFakeEncoder(dim=10)
    generator = EmbeddingGenerator(encoder=encoder)

    chunk = _make_chunk("Sample document chunk text")
    chunk_emb = generator.embed_chunks([chunk])
    query_emb = generator.embed_query("Sample search query")

    assert chunk_emb.shape[1] == query_emb.shape[1] == 10
    assert query_emb.shape == (1, 10)


def test_empty_text_sequence_returns_empty_array() -> None:
    encoder = DeterministicFakeEncoder(dim=8)
    generator = EmbeddingGenerator(encoder=encoder)

    empty_texts = generator.embed_texts([])
    assert empty_texts.shape == (0, 0)

    empty_chunks = generator.embed_chunks([])
    assert empty_chunks.shape == (0, 0)


def test_empty_or_whitespace_query_raises_error() -> None:
    encoder = DeterministicFakeEncoder()
    generator = EmbeddingGenerator(encoder=encoder)

    with pytest.raises(ModuleError) as exc1:
        generator.embed_query("")
    assert exc1.value.code == "rag_empty_input"

    with pytest.raises(ModuleError) as exc2:
        generator.embed_query("   \n\t  ")
    assert exc2.value.code == "rag_empty_input"


def test_empty_or_whitespace_text_in_list_raises_error() -> None:
    encoder = DeterministicFakeEncoder()
    generator = EmbeddingGenerator(encoder=encoder)

    with pytest.raises(ModuleError) as exc:
        generator.embed_texts(["Valid text", "   ", "Another valid"])
    assert exc.value.code == "rag_empty_input"


def test_malformed_encoder_output_raises_module_error() -> None:
    class BadEncoder:
        def encode(self, sentences: list[str]) -> object:
            return "not a list of vectors"

    generator = EmbeddingGenerator(encoder=BadEncoder())  # type: ignore[arg-type]
    with pytest.raises(ModuleError) as exc:
        generator.embed_texts(["Test sentence"])
    assert exc.value.code == "rag_bad_encoder_output"

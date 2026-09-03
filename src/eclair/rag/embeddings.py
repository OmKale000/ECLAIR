"""Embedding generation for M05 RAG / Evidence Retrieval.

Generates numerical vector embeddings for document chunks and queries using
SentenceTransformers (or an injected Encoder for deterministic offline testing).
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

import numpy as np

from eclair.exceptions import ModuleError
from eclair.rag.models import TextChunk

__all__ = ["Encoder", "EmbeddingGenerator", "DEFAULT_EMBEDDING_MODEL"]

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@runtime_checkable
class Encoder(Protocol):
    """Minimal embedding interface (satisfied by SentenceTransformer.encode)."""

    def encode(self, sentences: list[str]) -> object:
        """Return embedding vectors for a list of sentences."""
        ...


class EmbeddingGenerator:
    """Generates normalized dense embeddings for document chunks and queries."""

    def __init__(
        self,
        *,
        encoder: Encoder | None = None,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        normalize_embeddings: bool = True,
    ) -> None:
        self._encoder = encoder
        self._model_name = model_name
        self._normalize = normalize_embeddings
        self._dimension: int | None = None

    @property
    def model_name(self) -> str:
        """Name of the underlying embedding model."""
        return self._model_name

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        """Generate normalized 2D float32 vector embeddings for a sequence of texts.

        Args:
            texts: List or sequence of text strings to embed.

        Returns:
            A 2D numpy array of shape ``(len(texts), dimension)`` with dtype ``float32``.
        """
        if not texts:
            return np.empty((0, self._dimension or 0), dtype=np.float32)

        clean_texts = [t.strip() for t in texts]
        if any(not t for t in clean_texts):
            raise ModuleError(
                "Cannot generate embeddings for empty or whitespace-only text",
                code="rag_empty_input",
            )

        encoder = self._get_encoder()
        try:
            raw = encoder.encode(clean_texts)
        except Exception as exc:
            raise ModuleError(
                f"Embedding generation failed: {exc}",
                code="rag_embedding_error",
            ) from exc

        try:
            arr = np.asarray(raw, dtype=np.float32)
        except Exception as exc:
            raise ModuleError(
                "Encoder returned non-numeric or malformed embedding vectors",
                code="rag_bad_encoder_output",
            ) from exc

        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        if arr.ndim != 2:
            raise ModuleError(
                f"Expected 2D embedding array, got shape {arr.shape}",
                code="rag_bad_encoder_output",
            )

        if self._normalize:
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1e-12
            arr = arr / norms

        self._dimension = arr.shape[1]
        return arr

    def embed_chunks(self, chunks: Sequence[TextChunk]) -> np.ndarray:
        """Generate embeddings for a sequence of :class:`TextChunk` objects.

        Args:
            chunks: Sequence of document chunks.

        Returns:
            A 2D numpy array of shape ``(len(chunks), dimension)``.
        """
        if not chunks:
            return np.empty((0, self._dimension or 0), dtype=np.float32)

        texts = [chunk.text for chunk in chunks]
        return self.embed_texts(texts)

    def embed_query(self, query: str) -> np.ndarray:
        """Generate a normalized 1D or 2D vector embedding for a single search query.

        Args:
            query: The search query string.

        Returns:
            A 2D numpy array of shape ``(1, dimension)`` with dtype ``float32``.
        """
        clean_query = query.strip()
        if not clean_query:
            raise ModuleError(
                "Cannot embed empty or whitespace-only query",
                code="rag_empty_input",
            )

        return self.embed_texts([clean_query])

    def _get_encoder(self) -> Encoder:
        """Return the injected encoder or lazily construct a SentenceTransformer."""
        if self._encoder is not None:
            return self._encoder
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover
            raise ModuleError(
                "sentence-transformers is required for generating embeddings",
                code="rag_missing_dependency",
            ) from exc

        self._encoder = SentenceTransformer(self._model_name)
        return self._encoder

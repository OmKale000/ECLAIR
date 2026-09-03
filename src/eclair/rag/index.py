"""Vector indexing and similarity search for M05 RAG / Evidence Retrieval.

Provides FAISS-based vector similarity indexing (with an in-memory NumPy fallback
for environments without compiled FAISS binaries) mapping vector indices directly
to source :class:`TextChunk` objects and metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np

from eclair.exceptions import ModuleError
from eclair.rag.models import TextChunk

__all__ = ["VectorIndex", "FAISSIndex"]


class VectorIndex:
    """FAISS-powered vector index with source chunk tracking.

    Uses inner-product (cosine similarity on normalized vectors) for similarity
    ranking and maintains a 1-to-1 mapping between vector positions and :class:`TextChunk`
    objects.
    """

    def __init__(self, dimension: int | None = None) -> None:
        self._dimension = dimension
        self._chunks: list[TextChunk] = []
        self._embeddings: np.ndarray | None = None
        self._faiss_index: object | None = None
        self._use_faiss = self._try_init_faiss()

    @property
    def dimension(self) -> int | None:
        """Vector dimension of the index."""
        return self._dimension

    @property
    def chunks(self) -> list[TextChunk]:
        """List of indexed chunks."""
        return list(self._chunks)

    def __len__(self) -> int:
        return len(self._chunks)

    def _try_init_faiss(self) -> bool:
        """Check if FAISS is available and initialize if dimension is known."""
        try:
            import faiss

            if self._dimension is not None and self._dimension > 0:
                self._faiss_index = faiss.IndexFlatIP(self._dimension)
            return True
        except ImportError:
            self._faiss_index = None
            return False

    def add_chunks(self, chunks: Sequence[TextChunk], embeddings: np.ndarray) -> None:
        """Add chunks and their corresponding embedding vectors to the index.

        Args:
            chunks: Sequence of :class:`TextChunk` objects.
            embeddings: 2D float32 numpy array of shape ``(len(chunks), dimension)``.
        """
        if not chunks:
            return

        if len(chunks) != len(embeddings):
            raise ModuleError(
                f"Number of chunks ({len(chunks)}) must match number of embeddings ({len(embeddings)})",
                code="rag_chunk_embedding_mismatch",
            )

        arr = np.asarray(embeddings, dtype=np.float32)
        if arr.ndim != 2:
            raise ModuleError(
                f"Expected 2D embedding array, got shape {arr.shape}",
                code="rag_bad_vector_shape",
            )

        n_vectors, dim = arr.shape
        if self._dimension is None:
            self._dimension = dim
            if self._use_faiss and self._faiss_index is None:
                try:
                    import faiss

                    self._faiss_index = faiss.IndexFlatIP(self._dimension)
                except ImportError:  # pragma: no cover
                    self._use_faiss = False
        elif self._dimension != dim:
            raise ModuleError(
                f"Vector dimension mismatch: expected {self._dimension}, got {dim}",
                code="rag_dimension_mismatch",
            )

        # Append chunks
        self._chunks.extend(chunks)

        # Update embeddings array
        if self._embeddings is None:
            self._embeddings = arr
        else:
            self._embeddings = np.vstack([self._embeddings, arr])

        # Update FAISS index if active
        if self._use_faiss and self._faiss_index is not None:
            try:
                self._faiss_index.add(arr)  # type: ignore[attr-defined]
            except Exception as exc:  # pragma: no cover
                raise ModuleError(
                    f"FAISS index add failed: {exc}",
                    code="rag_index_error",
                ) from exc

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[tuple[TextChunk, float]]:
        """Search index for nearest candidate chunks.

        Args:
            query_vector: 1D or 2D numpy array containing the query embedding.
            top_k: Number of nearest candidates to return (must be >= 1).

        Returns:
            Ranked list of ``(chunk, similarity_score)`` tuples sorted in descending score order.
        """
        if top_k <= 0:
            raise ModuleError(
                f"top_k must be positive, got {top_k}",
                code="rag_invalid_top_k",
            )

        if len(self._chunks) == 0 or self._embeddings is None:
            return []

        q = np.asarray(query_vector, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)

        if q.shape[1] != self._dimension:
            raise ModuleError(
                f"Query vector dimension {q.shape[1]} does not match index dimension {self._dimension}",
                code="rag_dimension_mismatch",
            )

        k = min(top_k, len(self._chunks))

        # FAISS search if active
        if self._use_faiss and self._faiss_index is not None:
            try:
                distances, indices = self._faiss_index.search(q, k)  # type: ignore[attr-defined]
                results: list[tuple[TextChunk, float]] = []
                for score, idx in zip(distances[0], indices[0], strict=True):
                    if idx >= 0 and idx < len(self._chunks):
                        clamped_score = max(0.0, min(1.0, float(score)))
                        results.append((self._chunks[idx], clamped_score))
                return results
            except Exception:  # pragma: no cover
                # Fallback to NumPy exact dot product if FAISS throws
                pass

        # NumPy cosine similarity search
        scores = np.dot(self._embeddings, q.T).flatten()
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            clamped_score = max(0.0, min(1.0, score))
            results.append((self._chunks[idx], clamped_score))
        return results

    def clear(self) -> None:
        """Reset the index and remove all stored chunks."""
        self._chunks.clear()
        self._embeddings = None
        if self._use_faiss and self._dimension is not None:
            try:
                import faiss

                self._faiss_index = faiss.IndexFlatIP(self._dimension)
            except ImportError:  # pragma: no cover
                self._faiss_index = None

    def save(self, directory: str | Path) -> None:
        """Persist index chunks and vectors to disk.

        Args:
            directory: Directory path where index data should be saved.
        """
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        meta = {
            "dimension": self._dimension,
            "chunks": [chunk.model_dump() for chunk in self._chunks],
        }
        with open(dir_path / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        if self._embeddings is not None:
            np.save(dir_path / "embeddings.npy", self._embeddings)

    def load(self, directory: str | Path) -> None:
        """Load index chunks and vectors from disk.

        Args:
            directory: Directory path to load index data from.
        """
        dir_path = Path(directory)
        meta_file = dir_path / "metadata.json"
        emb_file = dir_path / "embeddings.npy"

        if not meta_file.exists():
            raise ModuleError(
                f"Index metadata file not found at {meta_file}",
                code="rag_index_not_found",
            )

        with open(meta_file, encoding="utf-8") as f:
            meta = json.load(f)

        self.clear()
        self._dimension = meta.get("dimension")
        self._chunks = [TextChunk.model_validate(c) for c in meta.get("chunks", [])]

        if emb_file.exists():
            self._embeddings = np.load(emb_file)
            if self._use_faiss and self._dimension:
                try:
                    import faiss

                    self._faiss_index = faiss.IndexFlatIP(self._dimension)
                    self._faiss_index.add(self._embeddings)
                except ImportError:  # pragma: no cover
                    pass


# Alias for explicit FAISS index reference
FAISSIndex = VectorIndex

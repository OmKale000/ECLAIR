"""Claim deduplication for M03 Claim Extraction.

Removes duplicate claims in two passes over the normalized claim texts:

1. **Exact duplicates** — collapsed via the normalizer's comparison key
   (case/punctuation/whitespace-insensitive).
2. **Semantic duplicates** — near-duplicate phrasings detected with
   sentence-transformers embeddings and cosine similarity above a threshold.

The embedding model is *injectable*: any object exposing
``encode(list[str]) -> sequence of vectors`` (the sentence-transformers
``SentenceTransformer.encode`` shape) satisfies :class:`Encoder`. When no encoder
is injected, a sentence-transformers model is lazily constructed on first use, so
unit tests can inject a fake encoder and run fully offline (no downloads/network).

Ordering is deterministic: the first occurrence of each claim is kept.
"""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from eclair.claims.normalizer import ClaimNormalizer
from eclair.exceptions import ModuleError

__all__ = ["Encoder", "ClaimDeduplicator", "DEFAULT_EMBEDDING_MODEL", "DEFAULT_SIMILARITY_THRESHOLD"]

#: Default sentence-transformers model used when no encoder is injected.
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

#: Cosine-similarity at/above which two claims are treated as semantic duplicates.
DEFAULT_SIMILARITY_THRESHOLD = 0.9


@runtime_checkable
class Encoder(Protocol):
    """Minimal embedding interface (satisfied by SentenceTransformer.encode)."""

    def encode(self, sentences: list[str]) -> object:
        """Return one embedding vector per input sentence."""
        ...


class ClaimDeduplicator:
    """Deduplicates normalized claim texts (exact + semantic)."""

    def __init__(
        self,
        *,
        encoder: Encoder | None = None,
        normalizer: ClaimNormalizer | None = None,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        self._encoder = encoder
        self._normalizer = normalizer or ClaimNormalizer()
        self._model_name = model_name
        self._similarity_threshold = similarity_threshold

    def deduplicate(self, texts: list[str]) -> list[str]:
        """Return ``texts`` with exact and semantic duplicates removed.

        The first occurrence of each unique claim is preserved in order.
        """
        # Pass 1: drop exact duplicates by comparison key.
        exact_unique: list[str] = []
        seen_keys: set[str] = set()
        for text in texts:
            key = self._normalizer.comparison_key(text)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            exact_unique.append(text)

        if len(exact_unique) < 2:
            return exact_unique

        # Pass 2: drop semantic near-duplicates.
        embeddings = self._embed(exact_unique)
        kept: list[str] = []
        kept_embeddings: list[list[float]] = []
        for text, embedding in zip(exact_unique, embeddings, strict=True):
            vector = [float(x) for x in embedding]
            if any(
                self._cosine_similarity(vector, existing) >= self._similarity_threshold
                for existing in kept_embeddings
            ):
                continue
            kept.append(text)
            kept_embeddings.append(vector)
        return kept

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Encode ``texts`` using the injected or lazily-built encoder."""
        encoder = self._get_encoder()
        raw = encoder.encode(texts)
        try:
            return [[float(x) for x in vector] for vector in raw]
        except TypeError as exc:
            raise ModuleError(
                "Encoder returned a value that is not a sequence of vectors",
                code="claims_bad_encoder_output",
            ) from exc

    def _get_encoder(self) -> Encoder:
        """Return the injected encoder or lazily construct a default one."""
        if self._encoder is not None:
            return self._encoder
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ModuleError(
                "sentence-transformers is required for semantic deduplication",
                code="claims_missing_dependency",
            ) from exc
        self._encoder = SentenceTransformer(self._model_name)
        return self._encoder

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two equal-length vectors (0.0 if degenerate)."""
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

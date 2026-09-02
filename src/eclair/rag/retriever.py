"""Retriever implementation for M05 RAG / Evidence Retrieval.

Implements the M01 ``Retriever`` protocol (``search(query, top_k=5) -> list[Evidence]``)
and provides end-to-end orchestration from query embedding and FAISS vector similarity
search to optional candidate reranking.
"""

from __future__ import annotations

from typing import Sequence

from eclair.contracts.evidence import Evidence
from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import Document
from eclair.rag.chunker import DocumentChunker
from eclair.rag.embeddings import EmbeddingGenerator
from eclair.rag.index import VectorIndex
from eclair.rag.models import TextChunk
from eclair.rag.reranker import NoOpReranker, Reranker

__all__ = ["Retriever", "DEFAULT_TOP_K"]

DEFAULT_TOP_K = 5


class Retriever:
    """Orchestrates document indexing and Top-K candidate evidence retrieval.

    Conforms to the M01 :class:`RetrieverProtocol` interface.
    """

    def __init__(
        self,
        *,
        index: VectorIndex | None = None,
        embedder: EmbeddingGenerator | None = None,
        reranker: Reranker | None = None,
        chunker: DocumentChunker | None = None,
        default_top_k: int = DEFAULT_TOP_K,
    ) -> None:
        self._index = index if index is not None else VectorIndex()
        self._embedder = embedder if embedder is not None else EmbeddingGenerator()
        self._reranker = reranker if reranker is not None else NoOpReranker()
        self._chunker = chunker if chunker is not None else DocumentChunker()
        self._default_top_k = default_top_k

    @property
    def index(self) -> VectorIndex:
        """The underlying vector index."""
        return self._index

    @property
    def embedder(self) -> EmbeddingGenerator:
        """The underlying embedding generator."""
        return self._embedder

    @property
    def reranker(self) -> Reranker:
        """The candidate evidence reranker."""
        return self._reranker

    @property
    def chunker(self) -> DocumentChunker:
        """The document chunker."""
        return self._chunker

    def index_documents(self, documents: Sequence[Document]) -> list[TextChunk]:
        """Chunk, embed, and index a collection of standardized M04 documents.

        Args:
            documents: Sequence of M04 standardized documents.

        Returns:
            The list of indexed :class:`TextChunk` objects.
        """
        if not documents:
            return []

        chunks = self._chunker.chunk_documents(documents)
        if not chunks:
            return []

        embeddings = self._embedder.embed_chunks(chunks)
        self._index.add_chunks(chunks, embeddings)
        return chunks

    def index_chunks(self, chunks: Sequence[TextChunk]) -> None:
        """Embed and index pre-chunked passages.

        Args:
            chunks: Sequence of :class:`TextChunk` objects.
        """
        if not chunks:
            return

        embeddings = self._embedder.embed_chunks(chunks)
        self._index.add_chunks(chunks, embeddings)

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[Evidence]:
        """Retrieve up to ``top_k`` candidate evidence items for the query.

        Conforms to the M01 ``Retriever`` protocol signature.

        Args:
            query: The search query or atomic claim text.
            top_k: Maximum number of candidate evidence items to return.

        Returns:
            Ranked list of :class:`Evidence` objects. Returns ``[]`` if the index
            is empty, no candidates exist, or the query is empty.
        """
        if top_k <= 0:
            raise ModuleError(
                f"top_k must be a positive integer, got {top_k}",
                code="rag_invalid_top_k",
            )

        clean_query = query.strip()
        if not clean_query:
            return []

        if len(self._index) == 0:
            return []

        # Generate query embedding
        query_vec = self._embedder.embed_query(clean_query)

        # Search FAISS / vector index
        scored_chunks = self._index.search(query_vec, top_k=top_k)
        if not scored_chunks:
            return []

        # Convert to M01 Evidence contracts
        candidate_evidence: list[Evidence] = []
        for chunk, score in scored_chunks:
            evidence = chunk.to_evidence(relevance_score=score)
            candidate_evidence.append(evidence)

        # Apply optional reranking
        final_evidence = self._reranker.rerank(clean_query, candidate_evidence)

        # Guarantee at most top_k returned
        return final_evidence[:top_k]

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[Evidence]:
        """Alias for :meth:`search` satisfying the ``retrieve(query, top_k)`` interface."""
        return self.search(query, top_k=top_k)

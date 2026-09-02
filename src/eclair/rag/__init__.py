"""ECLAIR RAG / Evidence Retrieval (M05).

Provides evidence retrieval over the controlled knowledge base:
- Document chunking (:class:`DocumentChunker`, :class:`TextChunk`)
- Dense embeddings (:class:`EmbeddingGenerator`, :class:`Encoder`)
- Vector indexing (:class:`VectorIndex`, :class:`FAISSIndex`)
- Candidate reranking (:class:`Reranker`, :class:`NoOpReranker`, :class:`SimilarityReranker`)
- Retrieval orchestration (:class:`Retriever`)

Public entry point is :class:`Retriever`.
"""

from __future__ import annotations

from eclair.rag.chunker import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, DocumentChunker
from eclair.rag.embeddings import DEFAULT_EMBEDDING_MODEL, EmbeddingGenerator, Encoder
from eclair.rag.index import FAISSIndex, VectorIndex
from eclair.rag.models import ScoredChunk, TextChunk
from eclair.rag.reranker import NoOpReranker, Reranker, SimilarityReranker
from eclair.rag.retriever import DEFAULT_TOP_K, Retriever

__all__ = [
    "DocumentChunker",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "TextChunk",
    "ScoredChunk",
    "EmbeddingGenerator",
    "Encoder",
    "DEFAULT_EMBEDDING_MODEL",
    "VectorIndex",
    "FAISSIndex",
    "Reranker",
    "NoOpReranker",
    "SimilarityReranker",
    "Retriever",
    "DEFAULT_TOP_K",
]

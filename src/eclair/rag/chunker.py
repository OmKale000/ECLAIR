"""Document chunking for M05 RAG / Evidence Retrieval.

Converts standardized M04 documents into searchable, metadata-preserving
:class:`TextChunk` objects suitable for embedding and indexing.
"""

from __future__ import annotations

import re
from typing import Sequence

from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import Document
from eclair.rag.models import TextChunk

__all__ = ["DocumentChunker", "DEFAULT_CHUNK_SIZE", "DEFAULT_CHUNK_OVERLAP"]

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
MIN_CHUNK_SIZE = 10


class DocumentChunker:
    """Chunks M04 standardized documents into smaller passage chunks.

    Preserves source document identifiers, page numbers, and all metadata
    required to construct valid M01 :class:`Evidence` objects.
    """

    def __init__(
        self,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE,
    ) -> None:
        if chunk_size <= 0:
            raise ModuleError(
                f"chunk_size must be positive, got {chunk_size}",
                code="rag_invalid_chunk_size",
            )
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ModuleError(
                f"chunk_overlap must be in [0, {chunk_size}), got {chunk_overlap}",
                code="rag_invalid_chunk_overlap",
            )

        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._min_chunk_size = min_chunk_size

    @property
    def chunk_size(self) -> int:
        """Configured maximum chunk size in characters."""
        return self._chunk_size

    @property
    def chunk_overlap(self) -> int:
        """Configured character overlap between consecutive chunks."""
        return self._chunk_overlap

    def chunk_document(self, document: Document) -> list[TextChunk]:
        """Split a single :class:`Document` into one or more :class:`TextChunk` objects.

        Args:
            document: The standardized M04 document.

        Returns:
            A list of :class:`TextChunk` objects preserving document metadata and source.
        """
        raw_text = document.text.strip()
        if not raw_text:
            return []

        # If text is smaller than or equal to chunk size, emit as a single chunk
        if len(raw_text) <= self._chunk_size:
            return [
                TextChunk(
                    text=raw_text,
                    doc_id=document.doc_id,
                    metadata=document.metadata,
                    chunk_index=0,
                )
            ]

        passages = self._split_text(raw_text)
        if not passages:
            # Fallback if splitting yielded nothing
            passages = [raw_text]

        chunks: list[TextChunk] = []
        for idx, passage in enumerate(passages):
            chunks.append(
                TextChunk(
                    text=passage,
                    doc_id=document.doc_id,
                    metadata=document.metadata,
                    chunk_index=idx,
                )
            )
        return chunks

    def chunk_documents(self, documents: Sequence[Document]) -> list[TextChunk]:
        """Split multiple :class:`Document` objects into chunks.

        Args:
            documents: A sequence of M04 standardized documents.

        Returns:
            A combined list of :class:`TextChunk` objects.
        """
        all_chunks: list[TextChunk] = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks

    def _split_text(self, text: str) -> list[str]:
        """Split text into overlapping windows honoring paragraph and sentence boundaries."""
        # Step 1: Split into paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        # Step 2: Break paragraphs into smaller units if they exceed chunk_size
        units: list[str] = []
        for p in paragraphs:
            if len(p) <= self._chunk_size:
                units.append(p)
            else:
                # Split large paragraph by sentence or line breaks
                sentences = [
                    s.strip()
                    for s in re.split(r"(?<=[.!?])\s+|\n+", p)
                    if s.strip()
                ]
                if not sentences:
                    sentences = [p]
                for s in sentences:
                    if len(s) <= self._chunk_size:
                        units.append(s)
                    else:
                        # Split by words if a single sentence is very long
                        words = s.split()
                        current_segment: list[str] = []
                        current_len = 0
                        for w in words:
                            w_len = len(w) + (1 if current_segment else 0)
                            if current_len + w_len > self._chunk_size and current_segment:
                                units.append(" ".join(current_segment))
                                current_segment = [w]
                                current_len = len(w)
                            else:
                                current_segment.append(w)
                                current_len += w_len
                        if current_segment:
                            units.append(" ".join(current_segment))

        # Step 3: Combine units into chunks with overlap
        chunks: list[str] = []
        current_chunk_parts: list[str] = []
        current_chunk_len = 0

        for unit in units:
            unit_len = len(unit) + (2 if current_chunk_parts else 0)
            if current_chunk_len + unit_len <= self._chunk_size:
                current_chunk_parts.append(unit)
                current_chunk_len += unit_len
            else:
                if current_chunk_parts:
                    chunk_str = "\n\n".join(current_chunk_parts).strip()
                    if len(chunk_str) >= self._min_chunk_size:
                        chunks.append(chunk_str)

                    # Build overlap from the tail of current_chunk_parts
                    overlap_parts: list[str] = []
                    overlap_len = 0
                    for part in reversed(current_chunk_parts):
                        if overlap_len + len(part) <= self._chunk_overlap:
                            overlap_parts.insert(0, part)
                            overlap_len += len(part) + 2
                        else:
                            break

                    current_chunk_parts = overlap_parts + [unit]
                    current_chunk_len = sum(len(p) for p in current_chunk_parts) + 2 * max(
                        0, len(current_chunk_parts) - 1
                    )
                else:
                    chunks.append(unit)
                    current_chunk_parts = []
                    current_chunk_len = 0

        if current_chunk_parts:
            final_str = "\n\n".join(current_chunk_parts).strip()
            if len(final_str) >= self._min_chunk_size:
                chunks.append(final_str)
            elif chunks:
                # Append short remainder to previous chunk if possible
                chunks[-1] = f"{chunks[-1]}\n\n{final_str}"
            else:
                chunks.append(final_str)

        return chunks

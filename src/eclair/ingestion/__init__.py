"""ECLAIR Document Ingestion (M04).

Converts knowledge sources (PDF, TXT, Markdown) into standardized ECLAIR
document/knowledge objects ready for M05 (RAG / Evidence Retrieval).

Public entry point is :class:`DocumentLoader` or format-specific loaders
(:class:`TextLoader`, :class:`MarkdownLoader`, :class:`PDFLoader`).
"""

from __future__ import annotations

from eclair.ingestion.loader import SUPPORTED_EXTENSIONS, DocumentLoader
from eclair.ingestion.markdown_loader import MarkdownLoader
from eclair.ingestion.metadata import (
    Document,
    DocumentMetadata,
    StandardizedDocument,
    extract_file_metadata,
)
from eclair.ingestion.pdf_loader import PDFLoader, PDFReader
from eclair.ingestion.text_loader import TextLoader

__all__ = [
    "DocumentLoader",
    "TextLoader",
    "MarkdownLoader",
    "PDFLoader",
    "PDFReader",
    "Document",
    "DocumentMetadata",
    "StandardizedDocument",
    "extract_file_metadata",
    "SUPPORTED_EXTENSIONS",
]

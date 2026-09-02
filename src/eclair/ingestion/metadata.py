"""Metadata and standardized document models for M04 Document Ingestion.

Defines the standardized document and metadata models produced by M04 and
consumed by M05 (RAG / Evidence Retrieval).

Every standardized document object carries all six required metadata fields:
    1. filename
    2. source
    3. created_date
    4. modified_date
    5. page_number
    6. document_version

This module implements no chunking, embedding, indexing, or retrieval logic
(COMMON_RULES sec.6, M04 non-responsibility). Errors use the shared M01
exception hierarchy (``eclair.exceptions``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

__all__ = [
    "DocumentMetadata",
    "Document",
    "StandardizedDocument",
    "extract_file_metadata",
]


class DocumentMetadata(BaseModel):
    """Standardized metadata containing all six required ECLAIR metadata fields."""

    model_config = {"extra": "forbid"}

    filename: str = Field(
        ...,
        min_length=1,
        description="Name of the file including extension (e.g. 'refund_policy.md').",
    )
    source: str = Field(
        ...,
        min_length=1,
        description="Origin or file path of the document (e.g. 'data/knowledge_base/refund_policy/refund_policy.md').",
    )
    created_date: str = Field(
        ...,
        min_length=1,
        description="Document creation date in ISO 8601 string format.",
    )
    modified_date: str = Field(
        ...,
        min_length=1,
        description="Document last modified date in ISO 8601 string format.",
    )
    page_number: int | None = Field(
        default=None,
        ge=1,
        description="1-indexed page number for multi-page documents (e.g. PDF), or None/1 for single-page documents.",
    )
    document_version: str = Field(
        default="1.0",
        min_length=1,
        description="Document version string (e.g. '1.0' or extracted from document frontmatter).",
    )


class Document(BaseModel):
    """A standardized knowledge/document object produced by M04 for M05 RAG indexing."""

    model_config = {"extra": "forbid"}

    doc_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Stable unique identifier for this document object.",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Extracted and normalized textual content of the document or page.",
    )
    metadata: DocumentMetadata = Field(
        ...,
        description="Standardized document metadata carrying all required metadata fields.",
    )


# Alias for explicit clarity in cross-module integration
StandardizedDocument = Document


def extract_file_metadata(
    file_path: str | Path,
    *,
    source: str | None = None,
    page_number: int | None = None,
    document_version: str = "1.0",
) -> DocumentMetadata:
    """Extract filesystem metadata and build a validated :class:`DocumentMetadata` object.

    Args:
        file_path: Path to the source file.
        source: Optional custom source string. Defaults to ``str(file_path)``.
        page_number: Optional 1-indexed page number.
        document_version: Version string for the document (defaults to "1.0").

    Returns:
        A populated and validated :class:`DocumentMetadata` instance.
    """
    path = Path(file_path)
    filename = path.name

    if path.exists() and path.is_file():
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        # st_birthtime is available on Windows/macOS; fallback to st_ctime on Unix
        ctime_val = getattr(stat, "st_birthtime", stat.st_ctime)
        ctime = datetime.fromtimestamp(ctime_val, tz=timezone.utc).isoformat()
    else:
        now_iso = datetime.now(timezone.utc).isoformat()
        ctime = now_iso
        mtime = now_iso

    resolved_source = source if source is not None else str(file_path).replace("\\", "/")

    return DocumentMetadata(
        filename=filename,
        source=resolved_source,
        created_date=ctime,
        modified_date=mtime,
        page_number=page_number,
        document_version=document_version,
    )

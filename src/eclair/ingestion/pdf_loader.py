"""PDF document loader for M04 Document Ingestion.

Extracts text from PDF files page-by-page using PyMuPDF (fitz) or an injected
reader, producing standardized :class:`Document` objects with page-level metadata.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import Document, DocumentMetadata, extract_file_metadata

__all__ = ["PDFLoader", "PDFReader"]

_CONSECUTIVE_BLANK_LINES_RE = re.compile(r"\n{3,}")


@runtime_checkable
class PDFReader(Protocol):
    """Protocol for extracting page-by-page text from PDF files."""

    def extract_pages(self, file_path: str | Path) -> list[tuple[int, str]]:
        """Extract pages from a PDF file.

        Args:
            file_path: Path to the PDF file.

        Returns:
            A list of tuples: (page_number_1_indexed, page_text).
        """
        ...


class DefaultPyMuPDFReader:
    """Default PDF reader using PyMuPDF (fitz)."""

    def extract_pages(self, file_path: str | Path) -> list[tuple[int, str]]:
        """Extract text from each page of a PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ModuleError(
                "PyMuPDF (fitz) is required for PDF document ingestion. "
                "Install with `pip install pymupdf`.",
                code="ingestion_missing_dependency",
            ) from exc

        path = Path(file_path)
        try:
            doc = fitz.open(path)
        except Exception as exc:
            raise ModuleError(
                f"Failed to open PDF file {path.name}: {exc}",
                code="ingestion_parse_failed",
            ) from exc

        pages: list[tuple[int, str]] = []
        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                text = page.get_text()
                pages.append((page_index + 1, text))
        except Exception as exc:
            raise ModuleError(
                f"Failed to extract text from PDF file {path.name}: {exc}",
                code="ingestion_parse_failed",
            ) from exc
        finally:
            doc.close()

        return pages


class PDFLoader:
    """Loader for Portable Document Format (.pdf) files."""

    def __init__(self, *, reader: PDFReader | None = None) -> None:
        """Initialize the PDF loader.

        Args:
            reader: Optional custom or fake PDF reader implementing :class:`PDFReader`.
                    Defaults to PyMuPDF (fitz).
        """
        self._reader = reader or DefaultPyMuPDFReader()

    def load(
        self,
        file_path: str | Path,
        *,
        source: str | None = None,
        version: str = "1.0",
    ) -> list[Document]:
        """Load a PDF file and produce one :class:`Document` per non-empty page.

        Args:
            file_path: Path to the .pdf file.
            source: Optional custom source identifier.
            version: Document version string (default: "1.0").

        Returns:
            A list of :class:`Document` objects, one per non-empty page, with page_number set.

        Raises:
            ModuleError: If the file does not exist, cannot be parsed, or contains no extractable text.
        """
        path = Path(file_path)
        if not path.exists():
            raise ModuleError(
                f"File not found: {file_path}",
                code="ingestion_file_not_found",
            )
        if not path.is_file():
            raise ModuleError(
                f"Expected a file but found directory: {file_path}",
                code="ingestion_not_a_file",
            )

        base_metadata = extract_file_metadata(
            file_path=path,
            source=source,
            page_number=None,
            document_version=version,
        )

        try:
            raw_pages = self._reader.extract_pages(path)
        except ModuleError:
            raise
        except Exception as exc:
            raise ModuleError(
                f"Failed to parse PDF file {path.name}: {exc}",
                code="ingestion_parse_failed",
            ) from exc

        documents: list[Document] = []
        for page_num, raw_text in raw_pages:
            cleaned = self._clean_pdf_text(raw_text)
            if not cleaned:
                continue

            page_meta = DocumentMetadata(
                filename=base_metadata.filename,
                source=base_metadata.source,
                created_date=base_metadata.created_date,
                modified_date=base_metadata.modified_date,
                page_number=page_num,
                document_version=base_metadata.document_version,
            )
            documents.append(Document(text=cleaned, metadata=page_meta))

        if not documents:
            raise ModuleError(
                f"PDF file {path.name} contains no readable text across any page",
                code="ingestion_empty_document",
            )

        return documents

    @staticmethod
    def _clean_pdf_text(text: str) -> str:
        """Clean and normalize extracted PDF text."""
        if not text:
            return ""

        # Normalize line endings
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        # Strip null bytes
        normalized = normalized.replace("\x00", "")

        # Collapse excessive blank lines
        normalized = _CONSECUTIVE_BLANK_LINES_RE.sub("\n\n", normalized)

        return normalized.strip()

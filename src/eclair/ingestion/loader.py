"""Unified document loader orchestrator for M04 Document Ingestion.

Dispatches document loading by file format (PDF, TXT, Markdown) and produces
standardized :class:`Document` objects ready for indexing by M05 (RAG).
"""

from __future__ import annotations

from pathlib import Path

from eclair.exceptions import ModuleError
from eclair.ingestion.markdown_loader import MarkdownLoader
from eclair.ingestion.metadata import Document
from eclair.ingestion.pdf_loader import PDFLoader
from eclair.ingestion.text_loader import TextLoader

__all__ = ["DocumentLoader", "SUPPORTED_EXTENSIONS"]

#: File extensions supported by M04 Document Ingestion (frozen per Spec §M04).
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".txt", ".md", ".markdown"})


class DocumentLoader:
    """Main entry point for ingesting knowledge base documents into standardized objects.

    Dispatches file loading to dedicated format loaders:
    - ``.txt`` -> :class:`TextLoader`
    - ``.md``, ``.markdown`` -> :class:`MarkdownLoader`
    - ``.pdf`` -> :class:`PDFLoader`

    Rejects unsupported file types and surfaces all parsing/loading failures
    via the shared M01 :class:`ModuleError`.
    """

    def __init__(
        self,
        *,
        text_loader: TextLoader | None = None,
        markdown_loader: MarkdownLoader | None = None,
        pdf_loader: PDFLoader | None = None,
    ) -> None:
        """Initialize DocumentLoader with optional custom/mocked format loaders."""
        self._text_loader = text_loader or TextLoader()
        self._markdown_loader = markdown_loader or MarkdownLoader()
        self._pdf_loader = pdf_loader or PDFLoader()

    def load_file(
        self,
        file_path: str | Path,
        *,
        source: str | None = None,
        version: str = "1.0",
    ) -> list[Document]:
        """Load a single document file and produce standardized Document objects.

        Args:
            file_path: Path to the target document.
            source: Optional custom source identifier.
            version: Document version string (default: "1.0").

        Returns:
            A list of validated :class:`Document` objects.

        Raises:
            ModuleError: If the file does not exist, has an unsupported extension,
                         or fails during extraction.
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

        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            supported_str = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ModuleError(
                f"Unsupported file format {ext!r} for file {path.name}; "
                f"supported formats: {supported_str}",
                code="ingestion_unsupported_format",
            )

        if ext == ".txt":
            return self._text_loader.load(path, source=source, version=version)
        if ext in {".md", ".markdown"}:
            return self._markdown_loader.load(path, source=source, version=version)
        if ext == ".pdf":
            return self._pdf_loader.load(path, source=source, version=version)

        # Defensive fallback
        raise ModuleError(
            f"Unsupported file format: {ext}",
            code="ingestion_unsupported_format",
        )

    def load_directory(
        self,
        dir_path: str | Path,
        *,
        recursive: bool = True,
        source: str | None = None,
        version: str = "1.0",
    ) -> list[Document]:
        """Ingest all supported document files in a directory.

        Args:
            dir_path: Path to the knowledge base directory.
            recursive: Whether to scan subdirectories recursively (default: True).
            source: Optional source prefix/override.
            version: Document version string.

        Returns:
            A list of all ingested :class:`Document` objects sorted deterministically.

        Raises:
            ModuleError: If the directory does not exist or is not a directory.
        """
        path = Path(dir_path)
        if not path.exists():
            raise ModuleError(
                f"Directory not found: {dir_path}",
                code="ingestion_directory_not_found",
            )
        if not path.is_dir():
            raise ModuleError(
                f"Expected a directory but found file: {dir_path}",
                code="ingestion_not_a_directory",
            )

        pattern = "**/*" if recursive else "*"
        all_paths = sorted(path.glob(pattern))

        documents: list[Document] = []
        for file_p in all_paths:
            if not file_p.is_file():
                continue
            # Skip hidden files and .gitkeep
            if file_p.name.startswith(".") or file_p.name == ".gitkeep":
                continue

            if file_p.suffix.lower() in SUPPORTED_EXTENSIONS:
                docs = self.load_file(file_p, source=source, version=version)
                documents.extend(docs)

        return documents

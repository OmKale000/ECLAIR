"""Text document loader for M04 Document Ingestion.

Loads and normalizes plain text (.txt) files into standardized :class:`Document`
objects with required metadata.
"""

from __future__ import annotations

import re
from pathlib import Path

from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import Document, extract_file_metadata

__all__ = ["TextLoader"]

_CONSECUTIVE_BLANK_LINES_RE = re.compile(r"\n{3,}")


class TextLoader:
    """Loader for plain text (.txt) files."""

    def load(
        self,
        file_path: str | Path,
        *,
        source: str | None = None,
        version: str = "1.0",
    ) -> list[Document]:
        """Load a plain text file, clean its content, and return standardized Document objects.

        Args:
            file_path: Path to the .txt file.
            source: Optional custom source identifier.
            version: Document version string (default: "1.0").

        Returns:
            A list containing one :class:`Document` object.

        Raises:
            ModuleError: If the file does not exist, cannot be read, or contains no readable text.
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

        try:
            content = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = path.read_bytes().decode("latin-1")
            except Exception as exc:
                raise ModuleError(
                    f"Failed to decode text file {file_path}: {exc}",
                    code="ingestion_read_error",
                ) from exc
        except Exception as exc:
            raise ModuleError(
                f"Failed to read file {file_path}: {exc}",
                code="ingestion_read_error",
            ) from exc

        cleaned = self._clean_text(content)
        if not cleaned:
            raise ModuleError(
                f"Text file {path.name} contains no readable text",
                code="ingestion_empty_document",
            )

        metadata = extract_file_metadata(
            file_path=path,
            source=source,
            page_number=1,
            document_version=version,
        )

        return [Document(text=cleaned, metadata=metadata)]

    def load_text(
        self,
        text: str,
        *,
        filename: str = "document.txt",
        source: str = "direct_input",
        version: str = "1.0",
    ) -> Document:
        """Create a :class:`Document` from an in-memory text string.

        Args:
            text: Raw input text.
            filename: Virtual filename for metadata.
            source: Source origin string.
            version: Document version string.

        Returns:
            A standardized :class:`Document` instance.

        Raises:
            ModuleError: If the text is empty after cleaning.
        """
        cleaned = self._clean_text(text)
        if not cleaned:
            raise ModuleError(
                f"Provided text for {filename} contains no readable text",
                code="ingestion_empty_document",
            )

        metadata = extract_file_metadata(
            file_path=filename,
            source=source,
            page_number=1,
            document_version=version,
        )

        return Document(text=cleaned, metadata=metadata)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize plain text.

        - Converts all newline styles (CRLF, CR) to standard LF (\\n).
        - Removes null bytes (\\x00).
        - Collapses 3 or more consecutive blank lines into at most 2.
        - Trims leading and trailing whitespace.
        """
        if not text:
            return ""

        # Normalize line endings
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")

        # Strip null bytes
        normalized = normalized.replace("\x00", "")

        # Collapse excess blank lines
        normalized = _CONSECUTIVE_BLANK_LINES_RE.sub("\n\n", normalized)

        return normalized.strip()

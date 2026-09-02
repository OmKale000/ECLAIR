"""Markdown document loader for M04 Document Ingestion.

Loads, cleans, and standardizes Markdown (.md, .markdown) files into
:class:`Document` objects with required metadata and frontmatter parsing.
"""

from __future__ import annotations

import re
from pathlib import Path

from eclair.exceptions import ModuleError
from eclair.ingestion.metadata import Document, extract_file_metadata

__all__ = ["MarkdownLoader"]

_CONSECUTIVE_BLANK_LINES_RE = re.compile(r"\n{3,}")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_VERSION_FIELD_RE = re.compile(r"^(?:version|doc_version|document_version)\s*:\s*[\"']?([^\"'\n]+)[\"']?", re.MULTILINE | re.IGNORECASE)


class MarkdownLoader:
    """Loader for Markdown (.md, .markdown) files."""

    def load(
        self,
        file_path: str | Path,
        *,
        source: str | None = None,
        version: str = "1.0",
    ) -> list[Document]:
        """Load a Markdown file, parse frontmatter, clean text, and return a Document.

        Args:
            file_path: Path to the markdown file.
            source: Optional custom source identifier.
            version: Default document version string if not found in frontmatter.

        Returns:
            A list containing one :class:`Document` object.

        Raises:
            ModuleError: If the file does not exist, cannot be read, or is empty.
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
                    f"Failed to decode Markdown file {file_path}: {exc}",
                    code="ingestion_read_error",
                ) from exc
        except Exception as exc:
            raise ModuleError(
                f"Failed to read file {file_path}: {exc}",
                code="ingestion_read_error",
            ) from exc

        body, extracted_version = self._parse_markdown(content, default_version=version)
        cleaned = self._clean_markdown(body)

        if not cleaned:
            raise ModuleError(
                f"Markdown file {path.name} contains no readable text",
                code="ingestion_empty_document",
            )

        metadata = extract_file_metadata(
            file_path=path,
            source=source,
            page_number=1,
            document_version=extracted_version,
        )

        return [Document(text=cleaned, metadata=metadata)]

    def load_markdown(
        self,
        content: str,
        *,
        filename: str = "document.md",
        source: str = "direct_input",
        version: str = "1.0",
    ) -> Document:
        """Create a :class:`Document` from an in-memory Markdown string.

        Args:
            content: Raw Markdown text.
            filename: Virtual filename for metadata.
            source: Source origin string.
            version: Default document version.

        Returns:
            A standardized :class:`Document` instance.

        Raises:
            ModuleError: If the markdown is empty after cleaning.
        """
        body, extracted_version = self._parse_markdown(content, default_version=version)
        cleaned = self._clean_markdown(body)

        if not cleaned:
            raise ModuleError(
                f"Provided Markdown for {filename} contains no readable text",
                code="ingestion_empty_document",
            )

        metadata = extract_file_metadata(
            file_path=filename,
            source=source,
            page_number=1,
            document_version=extracted_version,
        )

        return Document(text=cleaned, metadata=metadata)

    @classmethod
    def _parse_markdown(cls, content: str, default_version: str) -> tuple[str, str]:
        """Extract frontmatter version if present, and return (body, version)."""
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        match = _FRONTMATTER_RE.match(normalized)
        if not match:
            return normalized, default_version

        frontmatter_text = match.group(1)
        body = normalized[match.end():]

        version = default_version
        version_match = _VERSION_FIELD_RE.search(frontmatter_text)
        if version_match:
            version = version_match.group(1).strip()

        return body, version

    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Clean and normalize markdown body text."""
        if not text:
            return ""

        # Remove null bytes
        normalized = text.replace("\x00", "")

        # Collapse excess blank lines
        normalized = _CONSECUTIVE_BLANK_LINES_RE.sub("\n\n", normalized)

        return normalized.strip()

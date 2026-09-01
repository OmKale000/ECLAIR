"""Unit tests for M04 Document Ingestion.

Tests document ingestion for PDF, TXT, and Markdown files, metadata extraction,
text cleaning, error handling, and standardized object creation.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from eclair.exceptions import ModuleError
from eclair.ingestion import (
    SUPPORTED_EXTENSIONS,
    Document,
    DocumentLoader,
    DocumentMetadata,
    MarkdownLoader,
    PDFLoader,
    PDFReader,
    TextLoader,
    extract_file_metadata,
)


class FakePDFReader:
    """Deterministic fake PDF reader for offline unit testing."""

    def __init__(self, pages: list[tuple[int, str]] | None = None, *, should_fail: bool = False) -> None:
        self._pages = pages if pages is not None else [(1, "Page 1 sample content"), (2, "Page 2 sample content")]
        self._should_fail = should_fail

    def extract_pages(self, file_path: str | Path) -> list[tuple[int, str]]:
        if self._should_fail:
            raise RuntimeError("Corrupted PDF structure")
        return self._pages


# --- Metadata & Model Tests ------------------------------------------------


def test_document_metadata_all_six_fields() -> None:
    meta = DocumentMetadata(
        filename="refund_policy.md",
        source="data/knowledge_base/refund_policy/refund_policy.md",
        created_date="2026-01-01T00:00:00Z",
        modified_date="2026-01-02T00:00:00Z",
        page_number=1,
        document_version="1.0",
    )
    assert meta.filename == "refund_policy.md"
    assert meta.source == "data/knowledge_base/refund_policy/refund_policy.md"
    assert meta.created_date == "2026-01-01T00:00:00Z"
    assert meta.modified_date == "2026-01-02T00:00:00Z"
    assert meta.page_number == 1
    assert meta.document_version == "1.0"


def test_document_metadata_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        DocumentMetadata(
            filename="doc.txt",
            source="src",
            created_date="2026-01-01T00:00:00Z",
            modified_date="2026-01-02T00:00:00Z",
            unapproved_extra_field="invalid",  # type: ignore[call-arg]
        )


def test_document_model_creation() -> None:
    meta = DocumentMetadata(
        filename="terms.txt",
        source="terms.txt",
        created_date="2026-01-01T00:00:00Z",
        modified_date="2026-01-02T00:00:00Z",
        page_number=1,
        document_version="1.0",
    )
    doc = Document(text="Valid terms and conditions text.", metadata=meta)
    assert doc.doc_id is not None
    assert len(doc.doc_id) > 0
    assert doc.text == "Valid terms and conditions text."
    assert doc.metadata.filename == "terms.txt"


def test_document_empty_text_forbidden() -> None:
    meta = DocumentMetadata(
        filename="empty.txt",
        source="empty.txt",
        created_date="2026-01-01T00:00:00Z",
        modified_date="2026-01-02T00:00:00Z",
    )
    with pytest.raises(ValidationError):
        Document(text="", metadata=meta)


# --- TextLoader Tests -------------------------------------------------------


def test_text_loader_valid_file() -> None:
    loader = TextLoader()
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "sample_policy.txt"
        file_path.write_bytes(b"Customers may return items within 30 days.\r\nFull refund is guaranteed.")

        docs = loader.load(file_path, version="2.0")
        assert len(docs) == 1
        doc = docs[0]
        assert doc.text == "Customers may return items within 30 days.\nFull refund is guaranteed."
        assert doc.metadata.filename == "sample_policy.txt"
        assert doc.metadata.document_version == "2.0"
        assert doc.metadata.page_number == 1
        assert doc.metadata.created_date is not None
        assert doc.metadata.modified_date is not None


def test_text_loader_cleaning_and_normalization() -> None:
    loader = TextLoader()
    raw = "   \n\nLine 1\r\n\r\n\r\n\r\nLine 2 with null\x00 byte\n\n\n  "
    doc = loader.load_text(raw, filename="test.txt", version="1.1")
    assert doc.text == "Line 1\n\nLine 2 with null byte"
    assert doc.metadata.filename == "test.txt"
    assert doc.metadata.document_version == "1.1"


def test_text_loader_empty_file_raises_error() -> None:
    loader = TextLoader()
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "empty.txt"
        file_path.write_text("   \n\n  ", encoding="utf-8")

        with pytest.raises(ModuleError) as exc_info:
            loader.load(file_path)
        assert exc_info.value.code == "ingestion_empty_document"


def test_text_loader_file_not_found() -> None:
    loader = TextLoader()
    with pytest.raises(ModuleError) as exc_info:
        loader.load("non_existent_file.txt")
    assert exc_info.value.code == "ingestion_file_not_found"


# --- MarkdownLoader Tests --------------------------------------------------


def test_markdown_loader_valid_file() -> None:
    loader = MarkdownLoader()
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "refund_policy.md"
        content = (
            "# Refund Policy\n\n"
            "## Standard Returns\n"
            "Items can be returned within 30 days for a full refund."
        )
        file_path.write_text(content, encoding="utf-8")

        docs = loader.load(file_path)
        assert len(docs) == 1
        doc = docs[0]
        assert "# Refund Policy" in doc.text
        assert "Items can be returned within 30 days" in doc.text
        assert doc.metadata.filename == "refund_policy.md"
        assert doc.metadata.document_version == "1.0"
        assert doc.metadata.page_number == 1


def test_markdown_loader_frontmatter_version_parsing() -> None:
    loader = MarkdownLoader()
    content = (
        "---\n"
        "title: Product Return Guide\n"
        "version: 3.2.1\n"
        "author: Operations\n"
        "---\n\n"
        "# Returns\n"
        "Defective items can be exchanged within 90 days."
    )
    doc = loader.load_markdown(content, filename="guide.md")
    assert doc.metadata.document_version == "3.2.1"
    assert "---" not in doc.text
    assert "Defective items can be exchanged within 90 days." in doc.text


def test_markdown_loader_empty_raises_error() -> None:
    loader = MarkdownLoader()
    with pytest.raises(ModuleError) as exc_info:
        loader.load_markdown("---\nversion: 1.0\n---\n   ", filename="empty.md")
    assert exc_info.value.code == "ingestion_empty_document"


# --- PDFLoader Tests -------------------------------------------------------


def test_pdf_loader_multi_page_extraction_with_injected_reader() -> None:
    fake_reader = FakePDFReader([
        (1, "Page 1: Invoicing rules and payment terms."),
        (2, "Page 2: Overdue interest rates and penalties."),
    ])
    loader = PDFLoader(reader=fake_reader)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "invoice_policy.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 dummy content")

        docs = loader.load(pdf_path, version="1.5")
        assert len(docs) == 2
        assert docs[0].text == "Page 1: Invoicing rules and payment terms."
        assert docs[0].metadata.page_number == 1
        assert docs[0].metadata.filename == "invoice_policy.pdf"
        assert docs[0].metadata.document_version == "1.5"

        assert docs[1].text == "Page 2: Overdue interest rates and penalties."
        assert docs[1].metadata.page_number == 2
        assert docs[1].metadata.filename == "invoice_policy.pdf"


def test_pdf_loader_skips_blank_pages() -> None:
    fake_reader = FakePDFReader([
        (1, "Page 1: Content."),
        (2, "   \n\n  "),
        (3, "Page 3: Content."),
    ])
    loader = PDFLoader(reader=fake_reader)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 dummy")

        docs = loader.load(pdf_path)
        assert len(docs) == 2
        assert docs[0].metadata.page_number == 1
        assert docs[1].metadata.page_number == 3


def test_pdf_loader_all_empty_pages_raises_error() -> None:
    fake_reader = FakePDFReader([
        (1, "   "),
        (2, "   \n  "),
    ])
    loader = PDFLoader(reader=fake_reader)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "scanned_empty.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 dummy")

        with pytest.raises(ModuleError) as exc_info:
            loader.load(pdf_path)
        assert exc_info.value.code == "ingestion_empty_document"


def test_pdf_loader_corrupted_file_raises_error() -> None:
    fake_reader = FakePDFReader(should_fail=True)
    loader = PDFLoader(reader=fake_reader)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "corrupt.pdf"
        pdf_path.write_bytes(b"garbage")

        with pytest.raises(ModuleError) as exc_info:
            loader.load(pdf_path)
        assert exc_info.value.code == "ingestion_parse_failed"


# --- DocumentLoader Orchestrator Tests -------------------------------------


def test_document_loader_supported_extensions_constant() -> None:
    assert SUPPORTED_EXTENSIONS == {".pdf", ".txt", ".md", ".markdown"}


def test_document_loader_dispatch_by_extension() -> None:
    fake_reader = FakePDFReader([(1, "PDF content")])
    pdf_loader = PDFLoader(reader=fake_reader)
    doc_loader = DocumentLoader(pdf_loader=pdf_loader)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        txt_file = tmp_path / "doc.txt"
        txt_file.write_text("Text content", encoding="utf-8")

        md_file = tmp_path / "doc.md"
        md_file.write_text("# Markdown content", encoding="utf-8")

        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        txt_docs = doc_loader.load_file(txt_file)
        assert len(txt_docs) == 1
        assert txt_docs[0].text == "Text content"

        md_docs = doc_loader.load_file(md_file)
        assert len(md_docs) == 1
        assert "# Markdown content" in md_docs[0].text

        pdf_docs = doc_loader.load_file(pdf_file)
        assert len(pdf_docs) == 1
        assert pdf_docs[0].text == "PDF content"


def test_document_loader_unsupported_extensions_rejected() -> None:
    loader = DocumentLoader()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        unsupported_files = ["data.json", "sheet.csv", "page.html", "doc.docx", "script.py"]
        for fname in unsupported_files:
            p = tmp_path / fname
            p.write_text("dummy content", encoding="utf-8")
            with pytest.raises(ModuleError) as exc_info:
                loader.load_file(p)
            assert exc_info.value.code == "ingestion_unsupported_format"


def test_document_loader_load_directory() -> None:
    fake_reader = FakePDFReader([(1, "Policy PDF text")])
    pdf_loader = PDFLoader(reader=fake_reader)
    doc_loader = DocumentLoader(pdf_loader=pdf_loader)

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sub1 = root / "refund_policy"
        sub2 = root / "customer_policy"
        sub1.mkdir()
        sub2.mkdir()

        (sub1 / "refund.md").write_text("# Refund Policy", encoding="utf-8")
        (sub1 / ".gitkeep").write_text("", encoding="utf-8")
        (sub2 / "customer.txt").write_text("Customer guidelines", encoding="utf-8")
        (sub2 / "policy.pdf").write_bytes(b"%PDF-1.4")
        (sub2 / "ignore.csv").write_text("a,b,c", encoding="utf-8")  # should be ignored

        docs = doc_loader.load_directory(root, recursive=True)
        assert len(docs) == 3

        filenames = [d.metadata.filename for d in docs]
        assert "refund.md" in filenames
        assert "customer.txt" in filenames
        assert "policy.pdf" in filenames
        assert "ignore.csv" not in filenames


def test_document_loader_nonexistent_directory() -> None:
    loader = DocumentLoader()
    with pytest.raises(ModuleError) as exc_info:
        loader.load_directory("nonexistent_directory_12345")
    assert exc_info.value.code == "ingestion_directory_not_found"

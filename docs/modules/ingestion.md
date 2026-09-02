# M04 — Document Ingestion

> Module documentation (Spec §4.8). Derived only from the Spec (§M04, §4.7) and the repo.
> Authoritative rules: `rules/M04_document_ingestion.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M04
- **Name:** Document Ingestion
- **Folder:** `src/eclair/ingestion/`
- **Tests:** `tests/unit/ingestion/`

## Purpose (Spec §M04)
Convert knowledge sources into searchable, standardized ECLAIR knowledge objects.

## Responsibility
Load documents (PDF, TXT, Markdown), normalize/clean text, extract metadata, and produce standardized `Document` objects ready for indexing and evidence retrieval by M05 (RAG).

## Non-responsibility
- Does NOT chunk, embed, index, or retrieve (that is M05 RAG).
- Does NOT score evidence quality (M06) or verify claims (M07).
- Does NOT perform LLM calls, confidence calculation, or risk assessment.

## Files (Spec §M04)
```text
src/eclair/ingestion/
├── __init__.py           # Exports DocumentLoader, format loaders, and models
├── metadata.py           # DocumentMetadata, Document (StandardizedDocument), extract_file_metadata
├── text_loader.py        # TextLoader (plain text ingestion and cleaning)
├── markdown_loader.py    # MarkdownLoader (markdown cleaning and frontmatter parsing)
├── pdf_loader.py         # PDFLoader (PyMuPDF page-by-page extraction and protocol)
└── loader.py             # DocumentLoader orchestrator and format dispatcher
```

## Technology (Spec §M04)
Python 3.12, PyMuPDF (fitz), Pydantic v2.

## Processing Pipeline
```text
Raw Document (PDF / TXT / MD)
       ↓
File Type Validation (SUPPORTED_EXTENSIONS)
       ↓
Dedicated Format Loader (PDFLoader / TextLoader / MarkdownLoader)
       ↓
Text Extraction & Cleaning (Line ending normalization, null byte removal)
       ↓
Metadata Extraction (6 required fields)
       ↓
Standardized Document Object (Document)
       ↓
M05 RAG (Chunking, Embedding, Indexing)
```

## Supported Formats
Only the following extensions are supported:
- Plain Text: `.txt`
- Markdown: `.md`, `.markdown`
- Portable Document Format: `.pdf`

All other formats (e.g. `.docx`, `.json`, `.csv`, `.html`) are strictly rejected.

## Standardized Metadata Fields
Every standardized `Document` object carries a `metadata: DocumentMetadata` containing all six required fields:
1. `filename` (`str`): File name with extension (e.g. `refund_policy.md`).
2. `source` (`str`): File system path or source URI.
3. `created_date` (`str`): ISO 8601 creation timestamp.
4. `modified_date` (`str`): ISO 8601 modification timestamp.
5. `page_number` (`int | None`): 1-indexed page number for multi-page documents (PDF), or 1/None for single-page documents.
6. `document_version` (`str`): Version string (extracted from frontmatter or default `"1.0"`).

## Standardized Document Model
```python
class DocumentMetadata(BaseModel):
    filename: str
    source: str
    created_date: str
    modified_date: str
    page_number: int | None = None
    document_version: str = "1.0"

class Document(BaseModel):
    doc_id: str
    text: str
    metadata: DocumentMetadata
```

## Error Handling
All errors use the shared M01 exception hierarchy (`eclair.exceptions.ModuleError`) with specific error codes:
- `ingestion_unsupported_format`: Raised when an unsupported file type is provided.
- `ingestion_file_not_found`: Raised when target file does not exist.
- `ingestion_directory_not_found`: Raised when target directory does not exist.
- `ingestion_empty_document`: Raised when a document contains no readable text.
- `ingestion_read_error`: Raised on file I/O or decoding failure.
- `ingestion_parse_failed`: Raised when a document (e.g. PDF) is corrupted.
- `ingestion_missing_dependency`: Raised when PyMuPDF (`fitz`) is required but not installed.

## Sample Input / Output

### Sample Input
File: `data/knowledge_base/refund_policy/refund_policy.md`
```markdown
---
title: Product Refund Policy
version: 2.1
---

# Refund Policy

Customers may return defective items within 30 days of purchase.
All refunds are processed to the original payment method within 5-7 business days.
```

### Sample Output (Python Object / JSON)
```json
{
  "doc_id": "a3f8902be71a4f02882199b9cfec0601",
  "text": "# Refund Policy\n\nCustomers may return defective items within 30 days of purchase.\nAll refunds are processed to the original payment method within 5-7 business days.",
  "metadata": {
    "filename": "refund_policy.md",
    "source": "data/knowledge_base/refund_policy/refund_policy.md",
    "created_date": "2026-09-01T12:00:00+00:00",
    "modified_date": "2026-09-01T12:00:00+00:00",
    "page_number": 1,
    "document_version": "2.1"
  }
}
```

## Consumer Integration
Consumed directly by **M05 (RAG / Evidence Retrieval)**:
```python
from eclair.ingestion import DocumentLoader

loader = DocumentLoader()
# Load entire knowledge base directory
documents = loader.load_directory("data/knowledge_base")
# documents: list[Document] passed to M05 chunker/indexer
```

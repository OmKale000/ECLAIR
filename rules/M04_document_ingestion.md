# M04 — Document Ingestion — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M04 — Document Ingestion
IDENTIFIER: M04

PURPOSE:
  Convert knowledge sources into searchable, standardized ECLAIR knowledge objects.

RESPONSIBILITY:
  - Support PDF, TXT and Markdown sources.
  - Extract text and capture metadata: filename, source, created date, modified date,
    page number, document version.

NON-RESPONSIBILITY:
  - Does NOT chunk/embed/index/retrieve (that is M05 RAG).
  - Does NOT score evidence quality (M06) or verify (M07).

LOCATION:
  src/eclair/ingestion/
EXISTING FOLDERS USED:
  src/eclair/ingestion/  (loader.py, pdf_loader.py, text_loader.py, markdown_loader.py, metadata.py)
  tests/unit/ingestion/
  data/knowledge_base/   (controlled knowledge base source, read-only input)
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 config/exceptions (and contracts if a shared document type exists).
  External: PyMuPDF, Python document parsers.
  Configuration: via M01 config.

INPUTS:
  Source: files under data/knowledge_base/ (refund_policy, customer_policy, invoice_policy,
    product_policy, company_policy) per Spec §4.7.
  Format: PDF, TXT, Markdown files.
  Validation: reject unsupported types; capture required metadata fields.

PROCESSING:
  New logic: document -> text extraction -> cleaning -> metadata -> standardized document object.

OUTPUTS:
  Format: standardized knowledge/document objects suitable for indexing.
  Destination: consumed by M05 RAG.

CONSUMERS:
  Module/service: M05 RAG (chunking/embedding/indexing).
  Expected contract: standardized document objects with the metadata fields above.

INTEGRATION POINTS:
  APIs used: none. APIs exposed: internal loader interface.
  Database: none. Events/Queues: none. Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; surface parse failures; no invented fallback.
VALIDATION RULES: only PDF/TXT/Markdown; metadata must include the six listed fields.
INTEGRATION REQUIREMENTS: output must be directly indexable by M05.

DO NOT CHANGE: M01 contracts; M05 folder; any other module.
REUSE RULES: reuse PyMuPDF; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only loading + metadata standardization.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: raw documents -> standardized knowledge objects.
  Does NOT handle: chunking, embeddings, retrieval, scoring, verification.

VERIFICATION BEFORE COMPLETE:
  - PDF/TXT/Markdown load into standardized objects with required metadata.
  - tests/unit/ingestion/ pass; sample input/output; docs/modules/ingestion.md written.
```

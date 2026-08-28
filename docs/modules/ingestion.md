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
Load documents and produce standardized document objects with metadata, ready for indexing and
evidence retrieval.

## Non-responsibility
- Does NOT chunk, embed, index, or retrieve (that is M05 RAG).
- Does NOT score evidence quality (M06) or verify (M07).

## Files (Spec §M04)
```
src/eclair/ingestion/  loader.py  pdf_loader.py  text_loader.py  markdown_loader.py  metadata.py
```

## Technology (Spec §M04)
PyMuPDF, Python, document parsers.

## Method (Spec §M04)
Document → text extraction → cleaning → metadata → document object.

## Required functionality (Spec §M04)
- Support PDF, TXT and Markdown.
- Capture: filename, source, created date, modified date, page number, document version.

## Inputs / Outputs
- **Input:** knowledge-source files from the controlled knowledge base `data/knowledge_base/`
  (refund_policy, customer_policy, invoice_policy, product_policy, company_policy — Spec §4.7) and
  `data/raw/`.
- **Output:** standardized document objects (with the metadata fields above).
- **Consumers:** M05 RAG (chunking / embedding / indexing).

## Controlled knowledge base (Spec §4.7)
Prototype v1 begins with a deterministic controlled knowledge base rather than live web search, to
keep demonstrations reproducible, benchmarkable and easy to debug. Do not add live web-search
dependence in v1.

## Error handling
Use M01 exceptions. Validate supported file types; do not silently skip parse failures.

## Do not change
M01 contracts; the knowledge-base folder layout; any other module folder.

## Expected outcome (Spec §M04)
Raw documents become standardized knowledge objects suitable for indexing and evidence retrieval.

## Verification before complete (Spec §4.8)
- PDF, TXT and Markdown files load into standardized objects with all required metadata.
- `tests/unit/ingestion/` pass; sample input/output provided.

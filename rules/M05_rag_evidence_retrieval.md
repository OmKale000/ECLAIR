# M05 — RAG / Evidence Retrieval — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M05 — RAG / Evidence Retrieval
IDENTIFIER: M05

PURPOSE:
  Retrieve evidence relevant to each claim.

RESPONSIBILITY:
  - Chunk, embed, index, retrieve and optionally rerank relevant evidence.
  - Provide retrieve(query, top_k=5) returning ranked evidence.
  - Support controlled knowledge-base retrieval.

NON-RESPONSIBILITY:
  - Does NOT judge evidence quality/conflict (M06) or verify claims (M07).
  - Retrieval is NOT proof (Spec §4.5).
  - Does NOT ingest raw documents (M04).

LOCATION:
  src/eclair/rag/
EXISTING FOLDERS USED:
  src/eclair/rag/  (chunker.py, embeddings.py, index.py, retriever.py, reranker.py, models.py)
  tests/unit/rag/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts (Evidence, Query/Claim); M04 standardized documents.
  External: SentenceTransformers, FAISS, NumPy.
  Configuration: via M01 config (index paths, top_k defaults, model names).

INPUTS:
  Source: standardized documents from M04; a query/claim text from the engine.
  Format: query text + top_k; documents from M04.
  Validation: validate query and top_k.

PROCESSING:
  New logic: chunking -> embeddings -> FAISS similarity search -> Top-K retrieval ->
    optional reranking.

OUTPUTS:
  Format: list[Evidence] (M01 contract), ranked.
  Destination: consumed by M06 Evidence Quality and M07 Verification.

CONSUMERS:
  Module/service: M06, M07, M12 Reflection, engine.
  Expected contract: list[Evidence] ranked; empty list is a valid result.

INTEGRATION POINTS:
  APIs used: none external. APIs exposed: Retriever.search(query, top_k)->list[Evidence].
  Database: none (FAISS index files via config). Events/Queues: none.
  Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; empty retrieval is valid (not an error); no invented proof.
VALIDATION RULES: top_k bounds; evidence objects must be valid M01 contracts.
INTEGRATION REQUIREMENTS: per claim, return ranked candidate evidence only.

DO NOT CHANGE: M01 Evidence contract; M04 folder; any other module.
REUSE RULES: reuse FAISS + SentenceTransformers; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only chunk/embed/index/retrieve/rerank.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: retrieval of ranked candidate evidence.
  Does NOT handle: quality scoring, verification, confidence, decisions.

VERIFICATION BEFORE COMPLETE:
  - retrieve(query, top_k) returns ranked list[Evidence] from the controlled KB.
  - Optional reranking supported.
  - tests/unit/rag/ pass; sample input/output; docs/modules/rag.md written.
```

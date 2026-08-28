# M05 — RAG / Evidence Retrieval

> Module documentation (Spec §4.8). Derived only from the Spec (§M05, §4.5, §4.7) and the repo.
> Authoritative rules: `rules/M05_rag_evidence_retrieval.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M05
- **Name:** RAG / Evidence Retrieval
- **Folder:** `src/eclair/rag/`
- **Tests:** `tests/unit/rag/`

## Purpose (Spec §M05)
Retrieve evidence relevant to each claim.

## Responsibility
Chunk, embed, index, retrieve and optionally rerank relevant evidence over the controlled knowledge
base.

## Non-responsibility
- Does NOT decide whether evidence supports a claim — **RAG is not verification (Spec §4.5)**.
- Does NOT score evidence quality/conflict (M06) or verify (M07).

## Files (Spec §M05)
```
src/eclair/rag/  chunker.py  embeddings.py  index.py  retriever.py  reranker.py  models.py
```

## Technology (Spec §M05)
sentence-transformers, FAISS, NumPy.

## Method (Spec §M05)
Chunking → embeddings → FAISS similarity search → Top-K retrieval → optional reranking.

## Required functionality (Spec §M05)
- `retrieve(query, top_k=5)` — interface: `Retriever.search(query, top_k=5) -> list[Evidence]`
  (Spec §4.1, §4.3).
- Return ranked evidence.
- Support controlled knowledge-base retrieval.
- Optionally rerank retrieved candidates.

## Inputs / Outputs
- **Input:** a claim/query (`str`), typically per-claim from M03, plus indexed documents from M04.
- **Output:** `list[Evidence]` (M01 contract), ranked candidate evidence.
- **Consumers:** M06 Evidence Quality (scores it), M07 Verification (verifies against it), engine.

## Dependencies
- Internal: M01 contracts (`Evidence`); M04 standardized documents.
- External: FAISS, sentence-transformers, NumPy.

## Reliability semantic (Spec §4.5)
"I found this document" ≠ "this document supports the claim." Retrieval produces *candidate*
evidence only; verification (M07) is a separate explicit step. RAG retrieval itself is never treated
as proof.

## Error handling
Use M01 exceptions. Returning zero evidence is valid; do not fabricate evidence.

## Do not change
M01 `Evidence` contract; M04 document format; any other module folder.

## Expected outcome (Spec §M05)
For each claim, ECLAIR returns ranked candidate evidence. RAG retrieval itself is not treated as proof.

## Verification before complete (Spec §4.8)
- `retrieve(query, top_k=5)` returns ranked `Evidence` from the controlled KB; optional reranking works.
- `tests/unit/rag/` pass; sample input/output provided.

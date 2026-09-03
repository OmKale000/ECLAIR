# M05 — RAG / Evidence Retrieval

> Module documentation (Spec §4.8). Derived only from the Spec (§M05, §4.5, §4.7) and the repo.
> Authoritative rules: `rules/M05_rag_evidence_retrieval.md`, `rules/COMMON_RULES.md`.

## 1. Identity
- **ID:** M05
- **Name:** RAG / Evidence Retrieval
- **Folder:** `src/eclair/rag/`
- **Tests:** `tests/unit/rag/`

## 2. Purpose (Spec §M05)
Retrieve candidate evidence relevant to each extracted atomic claim from the controlled knowledge base.

## 3. Module Responsibilities
- Chunk standardized documents produced by M04 Document Ingestion into searchable passage chunks.
- Generate numerical dense embeddings using SentenceTransformers (`sentence-transformers/all-MiniLM-L6-v2`) for document chunks and queries with matching vector dimensions.
- Build and maintain FAISS vector indices mapping vector positions directly to chunks and parent document metadata.
- Provide the frozen M01 retrieval interface: `Retriever.search(query: str, top_k: int = 5) -> list[Evidence]` (and alias `retrieve(query, top_k)`).
- Return candidate evidence ranked in descending order of similarity score.
- Support optional candidate reranking (`Reranker`, `SimilarityReranker`, `NoOpReranker`) without altering core contract fields.
- Gracefully handle empty knowledge bases and zero-evidence queries by returning `[]`.

## 4. Non-Responsibilities
- Does NOT ingest raw document files (responsibility of M04).
- Does NOT judge evidence quality, credibility, or conflict (responsibility of M06).
- Does NOT verify claims or determine truth values — **RAG is not verification (Spec §4.5)**.
- Does NOT calculate calibrated ECS or final confidence (responsibility of M10 / M11).
- Does NOT make decision actions (responsibility of M13).
- Does NOT fabricate evidence when search yields no matches.

## 5. Architecture & Components
```text
src/eclair/rag/
  ├── models.py       # TextChunk and ScoredChunk data models
  ├── chunker.py      # DocumentChunker splitting M04 documents into passage chunks
  ├── embeddings.py   # EmbeddingGenerator and Encoder protocol
  ├── index.py        # VectorIndex and FAISSIndex with NumPy fallback
  ├── reranker.py     # Reranker protocol, NoOpReranker, SimilarityReranker
  ├── retriever.py    # Retriever orchestrator implementing M01 Retriever protocol
  └── __init__.py     # Module public exports
```

### Component Details
1. **`DocumentChunker` (`chunker.py`)**:
   - Takes M04 `Document` / `StandardizedDocument` objects.
   - Splits text into passage chunks honoring paragraph breaks (`\n\n`), sentence boundaries, and character bounds (`chunk_size=500`, `chunk_overlap=50`).
   - Preserves `doc_id`, `source`, `filename`, `created_date`, `modified_date`, `page_number`, and `document_version`.
2. **`EmbeddingGenerator` (`embeddings.py`)**:
   - Encodes document chunks and queries into normalized float32 embeddings.
   - Uses `all-MiniLM-L6-v2` by default with injectable `Encoder` for offline unit testing.
   - Ensures identical embedding dimension between queries and indexed passages.
3. **`VectorIndex` / `FAISSIndex` (`index.py`)**:
   - Maintains a 1-to-1 index mapping from vector IDs to `TextChunk` objects.
   - Performs inner product (cosine similarity) search.
   - Supports disk serialization via `save()` and `load()`.
4. **`Reranker` (`reranker.py`)**:
   - `NoOpReranker`: Pass-through default.
   - `SimilarityReranker`: Lexical/hybrid candidate re-scoring and re-ordering.
5. **`Retriever` (`retriever.py`)**:
   - Conforms to the frozen M01 `Retriever` protocol (`search(query, top_k=5) -> list[Evidence]`).
   - Converts scored chunks into standard M01 `Evidence` instances with `relevance_score` in `[0.0, 1.0]`.

## 6. M04 → M05 → M06 / M07 Integration Flow
```text
M04 Standardized Documents
           ↓
M05 DocumentChunker
           ↓
M05 EmbeddingGenerator
           ↓
M05 FAISS VectorIndex
           ↓  ← [Query / Claim from M03 / Engine]
M05 Retriever.search(query, top_k)
           ↓
M05 Optional Reranking
           ↓
M01 ranked list[Evidence]
           ↓
M06 Evidence Quality → M07 Claim Verification → Engine
```

## 7. Reliability Boundary & Semantics (Spec §4.5)
- **Retrieved evidence ≠ proof:** Finding a related document does not mean the claim is factual or verified.
- **Similarity score ≠ truth:** High cosine similarity only denotes semantic proximity, not truth or agreement.
- **No evidence → `[]`:** Absence of matching documents produces an empty list `[]`, which verification (M07) maps to `UNKNOWN` (never `SUPPORTED`, Spec §4.9).
- M05 outputs unverified candidate evidence only.

## 8. Sample Input and Output

### Input: M04 Standardized Document
```python
from eclair.ingestion.metadata import Document, DocumentMetadata

doc = Document(
    doc_id="doc-refund-001",
    text=(
        "# Refund Policy\n\n"
        "Customers may request a full refund within 30 calendar days of initial purchase.\n\n"
        "Refunds are credited back to the original payment method within 5-7 business days."
    ),
    metadata=DocumentMetadata(
        filename="refund_policy.md",
        source="data/knowledge_base/refund_policy/refund_policy.md",
        created_date="2026-01-01T00:00:00Z",
        modified_date="2026-01-02T00:00:00Z",
        page_number=1,
        document_version="1.0",
    ),
)
```

### Execution: Indexing & Retrieval
```python
from eclair.rag import Retriever

retriever = Retriever()
retriever.index_documents([doc])

# Query derived from an atomic claim extracted by M03
query = "Refunds can be requested within 30 days"
results = retriever.search(query, top_k=1)
```

### Output: M01 Evidence Contract
```python
[
    Evidence(
        evidence_id="a1b2c3d4e5f67890",
        text="Customers may request a full refund within 30 calendar days of initial purchase.",
        source="data/knowledge_base/refund_policy/refund_policy.md",
        relevance_score=0.912,
    )
]
```

"""Integration tests between M04 Ingestion, M05 RAG Retrieval, and M06 Evidence Quality.

Tests that M05 retrieved Evidence contracts are seamlessly ingested, scored,
and quality-annotated by M06 without contract drift.
"""

from __future__ import annotations

from eclair.contracts.evidence import Evidence
from eclair.evidence.models import EvidenceQualityReport
from eclair.evidence.scorer import EvidenceScorer
from eclair.ingestion.metadata import Document, DocumentMetadata
from eclair.rag.embeddings import EmbeddingGenerator
from eclair.rag.index import VectorIndex
from eclair.rag.retriever import Retriever


class DeterministicWordEncoder:
    """Deterministic offline word encoder for fast integration testing."""

    def __init__(self, dim: int = 16) -> None:
        self.dim = dim

    def encode(self, sentences: list[str]) -> list[list[float]]:
        vecs: list[list[float]] = []
        for s in sentences:
            v = [0.0] * self.dim
            for w in s.lower().replace(".", "").replace(",", "").split():
                idx = abs(hash(w)) % self.dim
                v[idx] += 1.0
            norm = sum(x * x for x in v) ** 0.5
            if norm > 0:
                v = [x / norm for x in v]
            else:
                v[0] = 1.0
            vecs.append(v)
        return vecs


def test_m05_retrieval_to_m06_quality_scoring_pipeline() -> None:
    # 1. M04 Ingestion document
    doc = Document(
        doc_id="doc-refund-001",
        text=(
            "Customers may request a full refund within 30 calendar days of initial purchase. "
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

    # 2. M05 RAG indexing and retrieval
    encoder = DeterministicWordEncoder(dim=16)
    embedder = EmbeddingGenerator(encoder=encoder)
    index = VectorIndex(dimension=16)
    retriever = Retriever(index=index, embedder=embedder)

    retriever.index_documents([doc])

    query = "Refunds within 30 days"
    retrieved_evidence: list[Evidence] = retriever.search(query, top_k=2)

    assert len(retrieved_evidence) >= 1
    ev = retrieved_evidence[0]
    assert isinstance(ev, Evidence)
    assert ev.relevance_score is not None

    # 3. M06 Evidence Quality assessment
    scorer = EvidenceScorer()
    report: EvidenceQualityReport = scorer.score_evidence(
        retrieved_evidence,
        claim_text=query,
    )

    assert isinstance(report, EvidenceQualityReport)
    assert len(report.items) == len(retrieved_evidence)
    assert report.is_insufficient is False
    assert report.average_quality >= 0.70

    scored_item = report.items[0]
    assert scored_item.evidence.evidence_id == ev.evidence_id
    assert scored_item.signals.authority_score == 1.0  # Controlled KB path
    assert scored_item.signals.freshness_score >= 0.70
    assert scored_item.signals.overall_score >= 0.70

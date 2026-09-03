"""Integration tests for M04 -> M05 pipeline.

Tests the full data flow:
M04 StandardizedDocument / DocumentLoader -> M05 Chunker -> M05 Embeddings
-> M05 FAISS/Vector Index -> M05 Retriever -> M01 Evidence[] -> Downstream readiness.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from eclair.contracts.evidence import Evidence
from eclair.ingestion import DocumentLoader, MarkdownLoader, TextLoader
from eclair.rag import (
    DocumentChunker,
    EmbeddingGenerator,
    Retriever,
    VectorIndex,
)


class PipelineDeterministicEncoder:
    """Offline encoder for integration tests."""

    def __init__(self, dim: int = 16) -> None:
        self.dim = dim

    def encode(self, sentences: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for s in sentences:
            v = [0.0] * self.dim
            for word in s.lower().replace(".", "").replace(",", "").split():
                idx = abs(hash(word)) % self.dim
                v[idx] += 1.0
            norm = sum(x * x for x in v) ** 0.5
            if norm > 0:
                v = [x / norm for x in v]
            else:
                v[0] = 1.0
            out.append(v)
        return out


def test_m04_to_m05_end_to_end_integration() -> None:
    # 1. Ingest files using M04 loaders
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        policy_file = tmp_path / "refund_policy.md"
        policy_file.write_text(
            "# Company Refund Policy\n\n"
            "Customers may request a full refund within 30 calendar days of initial purchase.\n\n"
            "Refunds are credited back to the original payment method within 5-7 business days.",
            encoding="utf-8",
        )

        terms_file = tmp_path / "terms.txt"
        terms_file.write_text(
            "Terms of Service\n\n"
            "All accounts must maintain valid contact email addresses.",
            encoding="utf-8",
        )

        md_loader = MarkdownLoader()
        txt_loader = TextLoader()

        docs_md = md_loader.load(policy_file)
        docs_txt = txt_loader.load(terms_file)

        assert len(docs_md) == 1
        assert len(docs_txt) == 1
        assert docs_md[0].metadata.filename == "refund_policy.md"
        assert docs_txt[0].metadata.filename == "terms.txt"

        # 2. Build M05 RAG Pipeline
        encoder = PipelineDeterministicEncoder(dim=16)
        embedder = EmbeddingGenerator(encoder=encoder)
        index = VectorIndex(dimension=16)
        chunker = DocumentChunker(chunk_size=150, chunk_overlap=20)
        retriever = Retriever(index=index, embedder=embedder, chunker=chunker)

        # 3. Index documents
        indexed_chunks = retriever.index_documents(docs_md + docs_txt)
        assert len(indexed_chunks) >= 2
        assert len(retriever.index) == len(indexed_chunks)

        # 4. Search and retrieve candidate evidence for an atomic claim / query
        query = "refund thirty days purchase"
        results = retriever.retrieve(query, top_k=5)

        assert len(results) >= 1
        assert isinstance(results, list)
        for ev in results:
            assert isinstance(ev, Evidence)
            assert isinstance(ev.evidence_id, str)
            assert len(ev.evidence_id) > 0
            assert len(ev.text) > 0
            assert ev.source is not None
            assert ev.relevance_score is not None
            assert 0.0 <= ev.relevance_score <= 1.0

        # Top result should contain refund information
        top_evidence = results[0]
        assert "refund" in top_evidence.text.lower()
        assert "refund_policy.md" in (top_evidence.source or "")


def test_m04_loader_directory_to_m05_pipeline() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / "faq.txt").write_text(
            "FAQ: Password resets take effect immediately across all sessions.",
            encoding="utf-8",
        )
        (tmp_path / "shipping.md").write_text(
            "Standard shipping takes 3-5 business days domestically.",
            encoding="utf-8",
        )

        loader = DocumentLoader()
        documents = loader.load_directory(tmp_path)
        assert len(documents) == 2

        encoder = PipelineDeterministicEncoder(dim=16)
        embedder = EmbeddingGenerator(encoder=encoder)
        retriever = Retriever(embedder=embedder)

        retriever.index_documents(documents)
        assert len(retriever.index) == 2

        # Search for shipping
        shipping_results = retriever.search("shipping business days", top_k=1)
        assert len(shipping_results) == 1
        assert "shipping" in shipping_results[0].text.lower()

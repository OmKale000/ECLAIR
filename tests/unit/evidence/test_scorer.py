"""Unit tests for M06 EvidenceScorer orchestration engine."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from eclair.contracts.evidence import Evidence
from eclair.exceptions import ContractValidationError
from eclair.evidence.models import EvidenceQualityReport, ScoredEvidence
from eclair.evidence.scorer import (
    EvidenceScorer,
    EvidenceScorerConfig,
    score_completeness,
)


def test_score_completeness() -> None:
    # Empty
    assert score_completeness("") == 0.0
    # Very short
    assert score_completeness("Hi") == 0.25
    # Medium
    assert score_completeness("This is a short statement about returns.") == 0.50
    # Complete well-formed passage
    assert score_completeness(
        "Customers may request a full refund within 30 calendar days of initial purchase, "
        "provided the product remains in its original packaging."
    ) == 1.0
    # Truncation ellipsis penalized
    score_trunc = score_completeness("The refund policy states that items must be returned within...")
    assert score_trunc <= 0.85


def test_score_single_item_all_signals_present() -> None:
    scorer = EvidenceScorer()
    ref = datetime(2026, 6, 1, tzinfo=timezone.utc)

    ev = Evidence(
        evidence_id="ev-100",
        text="Customers may request a full refund within 30 calendar days of initial purchase.",
        source="data/knowledge_base/refund_policy.md",
        relevance_score=0.95,
    )
    meta = {
        "modified_date": "2026-05-15T00:00:00Z",
    }

    scored = scorer.score_item(
        ev,
        metadata=meta,
        reference_date=ref,
    )

    assert isinstance(scored, ScoredEvidence)
    sig = scored.signals
    assert sig.evidence_id == "ev-100"
    assert sig.relevance_score == 0.95
    assert sig.authority_score == 1.0
    assert sig.freshness_score == 1.0
    assert sig.completeness_score >= 0.80
    assert sig.conflict_score == 0.0
    assert sig.overall_score >= 0.85
    assert not sig.is_outdated
    assert not sig.is_duplicate
    assert not sig.is_conflicting
    assert not sig.is_low_quality
    assert sig.flags == []


def test_score_single_item_lexical_relevance_fallback() -> None:
    scorer = EvidenceScorer()
    # Evidence without relevance_score; compute from claim_text
    ev = Evidence(
        evidence_id="ev-1",
        text="Refunds for damaged items are processed immediately upon receipt.",
        source="kb/refund.md",
    )
    scored = scorer.score_item(
        ev,
        claim_text="Damaged items receive immediate refund processing",
    )
    assert scored.signals.relevance_score >= 0.70


def test_custom_scorer_configuration_weights() -> None:
    # Custom config weighting freshness and authority heavily
    custom_cfg = EvidenceScorerConfig(
        weight_relevance=0.20,
        weight_authority=0.40,
        weight_freshness=0.30,
        weight_completeness=0.10,
        weight_conflict_penalty=0.10,
    )
    scorer = EvidenceScorer(config=custom_cfg)
    assert scorer.config.weight_authority == 0.40


def test_insufficient_evidence_empty_list_returns_signal_no_crash() -> None:
    scorer = EvidenceScorer()
    report = scorer.score_evidence([])

    assert isinstance(report, EvidenceQualityReport)
    assert report.is_insufficient is True
    assert report.items == []
    assert report.average_quality == 0.0
    assert "NO_EVIDENCE" in report.summary_flags
    assert "INSUFFICIENT_EVIDENCE" in report.summary_flags


def test_insufficient_evidence_all_low_quality() -> None:
    scorer = EvidenceScorer()
    ev = Evidence(
        evidence_id="ev-bad",
        text="bad.",
        source="untrusted_spam.com",
        relevance_score=0.1,
    )
    report = scorer.score_evidence([ev])

    assert report.is_insufficient is True
    assert "INSUFFICIENT_QUALITY" in report.summary_flags
    assert "ev-bad" in report.low_quality_ids


def test_batch_scoring_with_conflicts_and_duplicates() -> None:
    scorer = EvidenceScorer()

    ev1 = Evidence(
        evidence_id="ev-1",
        text="Full refunds are issued within 30 days of purchase.",
        source="data/knowledge_base/refund_policy.md",
        relevance_score=0.90,
    )
    ev2 = Evidence(
        evidence_id="ev-2",
        text="Full refunds are issued within 30 days of purchase.",
        source="data/knowledge_base/refund_policy.md",
        relevance_score=0.90,
    )
    ev3 = Evidence(
        evidence_id="ev-3",
        text="Full refunds are issued within 10 days of purchase.",
        source="data/knowledge_base/refund_policy.md",
        relevance_score=0.90,
    )

    report = scorer.evaluate([ev1, ev2, ev3])

    assert len(report.items) == 3
    assert report.has_conflicts is True
    assert len(report.conflicts) >= 1
    assert "ev-2" in report.duplicate_ids
    assert "HAS_CONFLICTS" in report.summary_flags
    assert "HAS_DUPLICATES" in report.summary_flags


def test_validation_rejects_invalid_inputs() -> None:
    scorer = EvidenceScorer()
    with pytest.raises(ContractValidationError):
        scorer.score_item("not_an_evidence_object")  # type: ignore[arg-type]

    with pytest.raises(ContractValidationError):
        scorer.score_evidence(["invalid_element"])  # type: ignore[list-item]

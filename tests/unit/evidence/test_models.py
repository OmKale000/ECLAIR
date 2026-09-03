"""Unit tests for M06 data models in models.py.

Tests field bounds, extra attribute rejection, default values, and helper properties.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair.contracts.evidence import Evidence
from eclair.evidence.models import (
    ConflictDetail,
    EvidenceQualityReport,
    EvidenceQualitySignals,
    ScoredEvidence,
)


def test_evidence_quality_signals_defaults_and_validation() -> None:
    signals = EvidenceQualitySignals(evidence_id="ev-1")
    assert signals.evidence_id == "ev-1"
    assert signals.relevance_score == 0.5
    assert signals.authority_score == 0.5
    assert signals.freshness_score == 0.5
    assert signals.completeness_score == 0.5
    assert signals.conflict_score == 0.0
    assert signals.overall_score == 0.5
    assert not signals.is_outdated
    assert not signals.is_duplicate
    assert not signals.is_conflicting
    assert not signals.is_low_quality
    assert signals.flags == []
    assert signals.metadata == {}


def test_evidence_quality_signals_bounds_validation() -> None:
    # Scores must be within [0.0, 1.0]
    with pytest.raises(ValidationError):
        EvidenceQualitySignals(evidence_id="ev-1", relevance_score=-0.1)

    with pytest.raises(ValidationError):
        EvidenceQualitySignals(evidence_id="ev-1", authority_score=1.5)

    with pytest.raises(ValidationError):
        EvidenceQualitySignals(evidence_id="ev-1", freshness_score=2.0)

    with pytest.raises(ValidationError):
        EvidenceQualitySignals(evidence_id="ev-1", completeness_score=-0.01)

    with pytest.raises(ValidationError):
        EvidenceQualitySignals(evidence_id="ev-1", conflict_score=1.01)

    with pytest.raises(ValidationError):
        EvidenceQualitySignals(evidence_id="ev-1", overall_score=-1.0)


def test_evidence_quality_signals_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        EvidenceQualitySignals(evidence_id="ev-1", invalid_extra_field=True)  # type: ignore[call-arg]


def test_conflict_detail_fields_and_bounds() -> None:
    detail = ConflictDetail(
        evidence_id_a="ev-1",
        evidence_id_b="ev-2",
        conflict_score=0.85,
        conflict_type="numerical",
        reason="30 days vs 14 days",
        passage_a_snippet="Return in 30 days.",
        passage_b_snippet="Return in 14 days.",
    )
    assert detail.evidence_id_a == "ev-1"
    assert detail.evidence_id_b == "ev-2"
    assert detail.conflict_score == 0.85
    assert detail.conflict_type == "numerical"
    assert detail.reason == "30 days vs 14 days"

    with pytest.raises(ValidationError):
        ConflictDetail(
            evidence_id_a="ev-1",
            evidence_id_b="ev-2",
            conflict_score=1.5,
            reason="Invalid",
        )


def test_scored_evidence_container() -> None:
    ev = Evidence(
        evidence_id="ev-100",
        text="All returns are subject to a 10% restocking fee.",
        source="data/knowledge_base/refund_policy.md",
        relevance_score=0.92,
    )
    signals = EvidenceQualitySignals(
        evidence_id="ev-100",
        relevance_score=0.92,
        authority_score=1.0,
        freshness_score=0.95,
        completeness_score=0.85,
        conflict_score=0.0,
        overall_score=0.94,
    )
    scored = ScoredEvidence(evidence=ev, signals=signals)
    assert scored.evidence.evidence_id == "ev-100"
    assert scored.signals.overall_score == 0.94


def test_evidence_quality_report_properties() -> None:
    ev1 = Evidence(evidence_id="ev-1", text="Refund within 30 days.")
    sig1 = EvidenceQualitySignals(evidence_id="ev-1", overall_score=0.9)
    scored1 = ScoredEvidence(evidence=ev1, signals=sig1)

    ev2 = Evidence(evidence_id="ev-2", text="No refunds for software.")
    sig2 = EvidenceQualitySignals(evidence_id="ev-2", overall_score=0.8)
    scored2 = ScoredEvidence(evidence=ev2, signals=sig2)

    report = EvidenceQualityReport(
        items=[scored1, scored2],
        average_quality=0.85,
        is_insufficient=False,
        has_conflicts=False,
        conflicts=[],
        duplicate_ids=[],
        outdated_ids=[],
        low_quality_ids=[],
        summary_flags=["HIGH_QUALITY"],
    )

    assert len(report.evidence_list) == 2
    assert report.evidence_list[0].evidence_id == "ev-1"
    assert len(report.signals_list) == 2
    assert report.signals_list[1].evidence_id == "ev-2"
    assert report.average_quality == 0.85
    assert not report.is_insufficient

"""Unit tests for M06 FreshnessScorer and obsolescence detection."""

from __future__ import annotations

from datetime import datetime, timezone

from eclair.evidence.freshness import (
    FreshnessScorer,
    is_outdated_evidence,
    score_freshness,
)


def test_recent_date_full_freshness() -> None:
    ref = datetime(2026, 6, 1, tzinfo=timezone.utc)
    scorer = FreshnessScorer(reference_date=ref)

    # 10 days old
    meta = {"modified_date": "2026-05-22T00:00:00Z"}
    assert scorer.score(metadata=meta) == 1.0
    assert not scorer.is_outdated(metadata=meta)


def test_age_decay_intervals() -> None:
    ref = datetime(2026, 6, 1, tzinfo=timezone.utc)
    scorer = FreshnessScorer(reference_date=ref)

    # 60 days old -> ~0.95
    score_60d = scorer.score(metadata={"modified_date": "2026-04-02T00:00:00Z"})
    assert score_60d == 0.95

    # 150 days old -> ~0.85
    score_150d = scorer.score(metadata={"modified_date": "2026-01-02T00:00:00Z"})
    assert score_150d == 0.85

    # 300 days old -> ~0.75
    score_300d = scorer.score(metadata={"modified_date": "2025-08-05T00:00:00Z"})
    assert score_300d == 0.75

    # 600 days old -> ~0.55
    score_600d = scorer.score(metadata={"modified_date": "2024-10-09T00:00:00Z"})
    assert score_600d == 0.55

    # 1200 days old (>2 years) -> decayed towards 0.1
    score_old = scorer.score(metadata={"modified_date": "2023-01-01T00:00:00Z"})
    assert score_old < 0.40
    assert scorer.is_outdated(metadata={"modified_date": "2023-01-01T00:00:00Z"})


def test_deprecation_keywords_trigger_outdated() -> None:
    scorer = FreshnessScorer()

    # Even with no date, deprecation in text or source penalizes score heavily
    score_dep = scorer.score(text="This refund rule is deprecated as of last quarter.")
    assert score_dep <= 0.25
    assert scorer.is_outdated(text="This refund rule is deprecated as of last quarter.")

    score_obs = scorer.score(source="kb/obsolete_policy_2020.md")
    assert score_obs <= 0.25
    assert scorer.is_outdated(source="kb/obsolete_policy_2020.md")


def test_year_extraction_from_text() -> None:
    ref = datetime(2026, 6, 1, tzinfo=timezone.utc)
    scorer = FreshnessScorer(reference_date=ref)

    # Text mentioning old year
    text_2021 = "Effective from 2021, all sales are final."
    assert scorer.is_outdated(text=text_2021)

    # Text mentioning current year
    text_2026 = "Updated guidelines for 2026 operations."
    assert not scorer.is_outdated(text=text_2026)


def test_default_freshness_for_controlled_kb_without_dates() -> None:
    scorer = FreshnessScorer()
    score = scorer.score(source="data/knowledge_base/refund_policy.md", text="Active standard policy.")
    assert score == 0.85
    assert not scorer.is_outdated(source="data/knowledge_base/refund_policy.md", text="Active standard policy.")


def test_metadata_freshness_override() -> None:
    scorer = FreshnessScorer()
    meta = {"freshness_score": 0.99}
    assert scorer.score(metadata=meta) == 0.99


def test_convenience_functions() -> None:
    ref = datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert score_freshness(metadata={"modified_date": "2026-05-30T00:00:00Z"}, reference_date=ref) == 1.0
    assert is_outdated_evidence(text="Deprecated legacy policy.", reference_date=ref)

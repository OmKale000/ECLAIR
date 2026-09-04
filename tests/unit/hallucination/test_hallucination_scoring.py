"""Unit tests for M08 Hallucination Detection scoring and reason generation."""

from __future__ import annotations

import pytest

from eclair.hallucination.models import (
    HallucinationReason,
    HallucinationSignals,
)
from eclair.hallucination.scoring import (
    HallucinationScorer,
    HallucinationScorerConfig,
)


def test_scorer_default_weights() -> None:
    scorer = HallucinationScorer()
    signals = HallucinationSignals(
        no_evidence_score=0.0,
        contradiction_score=0.0,
        low_semantic_support_score=0.0,
        model_disagreement_score=0.0,
        numerical_inconsistency_score=0.0,
    )
    prob = scorer.compute_probability(signals)
    assert prob == 0.0
    assert scorer.is_flagged(prob) is False


def test_scorer_all_ones() -> None:
    scorer = HallucinationScorer()
    signals = HallucinationSignals(
        no_evidence_score=1.0,
        contradiction_score=1.0,
        low_semantic_support_score=1.0,
        model_disagreement_score=1.0,
        numerical_inconsistency_score=1.0,
    )
    prob = scorer.compute_probability(signals)
    assert prob == 1.0
    assert scorer.is_flagged(prob) is True


def test_scorer_contradiction_override() -> None:
    scorer = HallucinationScorer()
    signals = HallucinationSignals(
        no_evidence_score=0.0,
        contradiction_score=1.0,
        low_semantic_support_score=0.1,
        model_disagreement_score=0.0,
        numerical_inconsistency_score=0.0,
        details={"contradiction": {"reason": "Evidence contradicts claim"}},
    )
    prob = scorer.compute_probability(signals)
    assert prob >= 0.85
    assert scorer.is_flagged(prob) is True

    _, flagged, reasons = scorer.score(signals)
    assert flagged is True
    assert any(HallucinationReason.CONTRADICTORY_EVIDENCE.value in r for r in reasons)


def test_scorer_no_evidence_high_override() -> None:
    scorer = HallucinationScorer()
    signals = HallucinationSignals(
        no_evidence_score=1.0,
        contradiction_score=0.0,
        low_semantic_support_score=0.8,
        model_disagreement_score=0.0,
        numerical_inconsistency_score=0.0,
        details={"no_evidence": {"reason": "Zero evidence passages found"}},
    )
    prob, flagged, reasons = scorer.score(signals)
    assert prob >= 0.70
    assert flagged is True
    assert any(HallucinationReason.NO_EVIDENCE.value in r for r in reasons)


def test_scorer_numerical_inconsistency_override() -> None:
    scorer = HallucinationScorer()
    signals = HallucinationSignals(
        no_evidence_score=0.9,
        contradiction_score=0.0,
        low_semantic_support_score=0.5,
        model_disagreement_score=0.0,
        numerical_inconsistency_score=0.9,
        details={"numerical_inconsistency": {"reason": "Numbers do not match"}},
    )
    prob, flagged, reasons = scorer.score(signals)
    assert prob >= 0.80
    assert flagged is True
    assert any(HallucinationReason.NUMERICAL_INCONSISTENCY.value in r for r in reasons)


def test_scorer_bounds_guarantee() -> None:
    scorer = HallucinationScorer()
    for no_ev in [0.0, 0.5, 1.0]:
        for contra in [0.0, 0.5, 1.0]:
            for sem in [0.0, 0.5, 1.0]:
                for dis in [0.0, 0.5, 1.0]:
                    for num in [0.0, 0.5, 1.0]:
                        signals = HallucinationSignals(
                            no_evidence_score=no_ev,
                            contradiction_score=contra,
                            low_semantic_support_score=sem,
                            model_disagreement_score=dis,
                            numerical_inconsistency_score=num,
                        )
                        prob = scorer.compute_probability(signals)
                        assert 0.0 <= prob <= 1.0


def test_scorer_custom_config() -> None:
    custom_cfg = HallucinationScorerConfig(
        weight_no_evidence=0.50,
        weight_contradiction=0.50,
        weight_low_semantic_support=0.0,
        weight_model_disagreement=0.0,
        weight_numerical_inconsistency=0.0,
        hallucination_threshold=0.60,
    )
    scorer = HallucinationScorer(config=custom_cfg)
    signals = HallucinationSignals(
        no_evidence_score=0.8,
        contradiction_score=0.2,
    )
    prob = scorer.compute_probability(signals)
    assert prob == pytest.approx(0.50, abs=1e-2)
    assert scorer.is_flagged(prob) is False


def test_reasons_non_empty_when_flagged() -> None:
    scorer = HallucinationScorer(
        config=HallucinationScorerConfig(
            hallucination_threshold=0.30,
            signal_reason_threshold=0.80,
        )
    )
    signals = HallucinationSignals(
        no_evidence_score=0.40,
        contradiction_score=0.40,
        low_semantic_support_score=0.40,
    )
    prob, flagged, reasons = scorer.score(signals)
    assert flagged is True
    assert len(reasons) >= 1
    assert "Elevated composite hallucination probability" in reasons[0]

"""Unit tests for M10 Confidence Estimation weighted fusion and aggregation."""

from __future__ import annotations

from eclair.confidence.fusion import ConfidenceFuser
from eclair.confidence.models import (
    ClaimConfidenceResult,
    ConfidenceBreakdown,
    ConfidenceFusionConfig,
    ConfidenceSignals,
)


def test_fusion_all_signals_present() -> None:
    """Verify weighted linear fusion with all 5 signals present."""
    config = ConfidenceFusionConfig(
        weight_verification=0.35,
        weight_evidence=0.25,
        weight_agreement=0.15,
        weight_consistency=0.15,
        weight_model_confidence=0.10,
    )
    fuser = ConfidenceFuser(config)
    signals = ConfidenceSignals(
        verification_score=1.0,
        evidence_score=0.8,
        agreement_score=0.9,
        consistency_score=1.0,
        model_confidence_score=0.7,
    )
    raw_conf, breakdown = fuser.fuse(signals)

    # Expected: 0.35*1.0 + 0.25*0.8 + 0.15*0.9 + 0.15*1.0 + 0.10*0.7
    # = 0.35 + 0.20 + 0.135 + 0.15 + 0.07 = 0.905
    expected = 0.905
    assert abs(raw_conf - expected) < 1e-3
    assert breakdown.total_raw_confidence == raw_conf
    assert len(breakdown.available_signals) == 5
    assert len(breakdown.missing_signals) == 0
    assert abs(sum(breakdown.effective_weights.values()) - 1.0) < 1e-4


def test_fusion_missing_signals_renormalization() -> None:
    """Verify weight renormalization when signals are missing."""
    config = ConfidenceFusionConfig(
        weight_verification=0.40,
        weight_evidence=0.40,
        weight_agreement=0.10,
        weight_consistency=0.05,
        weight_model_confidence=0.05,
    )
    fuser = ConfidenceFuser(config)
    # Only verification (0.40) and evidence (0.40) present -> sum = 0.80 -> effective = 0.50 each
    signals = ConfidenceSignals(
        verification_score=0.90,
        evidence_score=0.70,
        agreement_score=None,
        consistency_score=None,
        model_confidence_score=None,
    )
    raw_conf, breakdown = fuser.fuse(signals)

    # Expected: 0.50 * 0.90 + 0.50 * 0.70 = 0.80
    assert abs(raw_conf - 0.80) < 1e-3
    assert breakdown.effective_weights["verification"] == 0.50
    assert breakdown.effective_weights["evidence"] == 0.50
    assert len(breakdown.missing_signals) == 3


def test_fusion_single_signal() -> None:
    """Verify single available signal receives effective weight of 1.0."""
    fuser = ConfidenceFuser()
    signals = ConfidenceSignals(verification_score=0.85)
    raw_conf, breakdown = fuser.fuse(signals)
    assert raw_conf == 0.85
    assert breakdown.effective_weights["verification"] == 1.0


def test_fusion_no_signals_available() -> None:
    """Verify behavior when zero signals are available."""
    fuser = ConfidenceFuser()
    signals = ConfidenceSignals()
    raw_conf, breakdown = fuser.fuse(signals)
    assert raw_conf == 0.0
    assert len(breakdown.missing_signals) == 5
    assert len(breakdown.available_signals) == 0


def test_fusion_extreme_values() -> None:
    """Verify lower and upper bounds of fusion."""
    fuser = ConfidenceFuser()

    zeros = ConfidenceSignals(
        verification_score=0.0,
        evidence_score=0.0,
        agreement_score=0.0,
        consistency_score=0.0,
        model_confidence_score=0.0,
    )
    raw_0, _ = fuser.fuse(zeros)
    assert raw_0 == 0.0

    ones = ConfidenceSignals(
        verification_score=1.0,
        evidence_score=1.0,
        agreement_score=1.0,
        consistency_score=1.0,
        model_confidence_score=1.0,
    )
    raw_1, _ = fuser.fuse(ones)
    assert raw_1 == 1.0


def test_aggregate_claim_confidences_mean() -> None:
    """Verify mean aggregation across claims."""
    fuser = ConfidenceFuser()
    c1 = ClaimConfidenceResult(
        claim_id="1",
        raw_confidence=0.80,
        signals=ConfidenceSignals(),
        breakdown=ConfidenceBreakdown(total_raw_confidence=0.80),
    )
    c2 = ClaimConfidenceResult(
        claim_id="2",
        raw_confidence=0.60,
        signals=ConfidenceSignals(),
        breakdown=ConfidenceBreakdown(total_raw_confidence=0.60),
    )
    agg = fuser.aggregate_claim_confidences([c1, c2], method="mean")
    assert agg == 0.70


def test_aggregate_claim_confidences_min() -> None:
    """Verify min (weakest-link) aggregation across claims."""
    fuser = ConfidenceFuser()
    c1 = ClaimConfidenceResult(
        claim_id="1",
        raw_confidence=0.90,
        signals=ConfidenceSignals(),
        breakdown=ConfidenceBreakdown(total_raw_confidence=0.90),
    )
    c2 = ClaimConfidenceResult(
        claim_id="2",
        raw_confidence=0.40,
        signals=ConfidenceSignals(),
        breakdown=ConfidenceBreakdown(total_raw_confidence=0.40),
    )
    agg = fuser.aggregate_claim_confidences([c1, c2], method="min")
    assert agg == 0.40


def test_aggregate_claim_confidences_empty() -> None:
    """Verify empty list aggregation returns 0.0."""
    fuser = ConfidenceFuser()
    agg = fuser.aggregate_claim_confidences([], method="mean")
    assert agg == 0.0

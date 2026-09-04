"""Unit tests for M08 Hallucination Detection models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair.hallucination.models import (
    HallucinationReason,
    HallucinationResult,
    HallucinationSignals,
    ResponseHallucinationResult,
)


def test_hallucination_signals_valid() -> None:
    signals = HallucinationSignals(
        no_evidence_score=0.2,
        contradiction_score=0.1,
        low_semantic_support_score=0.3,
        model_disagreement_score=0.4,
        numerical_inconsistency_score=0.0,
        details={"info": "test"},
    )
    assert signals.no_evidence_score == 0.2
    assert signals.contradiction_score == 0.1
    assert signals.low_semantic_support_score == 0.3
    assert signals.model_disagreement_score == 0.4
    assert signals.numerical_inconsistency_score == 0.0
    assert signals.details == {"info": "test"}


def test_hallucination_signals_boundary_validation() -> None:
    with pytest.raises(ValidationError):
        HallucinationSignals(no_evidence_score=1.5)

    with pytest.raises(ValidationError):
        HallucinationSignals(contradiction_score=-0.1)


def test_hallucination_signals_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        HallucinationSignals(no_evidence_score=0.5, unknown_field=123)  # type: ignore[call-arg]


def test_hallucination_result_valid() -> None:
    signals = HallucinationSignals(
        no_evidence_score=0.8,
        contradiction_score=0.0,
        low_semantic_support_score=0.7,
        model_disagreement_score=0.0,
        numerical_inconsistency_score=0.0,
    )
    result = HallucinationResult(
        claim_id="claim-001",
        hallucination_probability=0.75,
        is_hallucination=True,
        reasons=[HallucinationReason.NO_EVIDENCE.value],
        signals=signals,
    )
    assert result.claim_id == "claim-001"
    assert result.hallucination_probability == 0.75
    assert result.is_hallucination is True
    assert len(result.reasons) == 1
    assert result.signals.no_evidence_score == 0.8


def test_hallucination_result_probability_bounds() -> None:
    signals = HallucinationSignals()
    with pytest.raises(ValidationError):
        HallucinationResult(
            claim_id="c1",
            hallucination_probability=1.2,
            is_hallucination=True,
            signals=signals,
        )

    with pytest.raises(ValidationError):
        HallucinationResult(
            claim_id="c1",
            hallucination_probability=-0.5,
            is_hallucination=False,
            signals=signals,
        )


def test_response_hallucination_result() -> None:
    signals = HallucinationSignals(no_evidence_score=0.9)
    claim_res = HallucinationResult(
        claim_id="c1",
        hallucination_probability=0.85,
        is_hallucination=True,
        reasons=["No evidence found"],
        signals=signals,
    )
    response_res = ResponseHallucinationResult(
        claim_results=[claim_res],
        overall_hallucination_probability=0.85,
        has_hallucination=True,
        hallucinated_claim_ids=["c1"],
        summary_reasons=["No evidence found"],
    )
    assert response_res.has_hallucination is True
    assert response_res.hallucinated_claim_ids == ["c1"]
    assert len(response_res.claim_results) == 1

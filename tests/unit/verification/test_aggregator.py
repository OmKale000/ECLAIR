"""Unit tests for M07 EvidenceAggregator."""

from __future__ import annotations

import pytest

from eclair.contracts import Claim, VerificationResult, VerificationStatus
from eclair.exceptions import ContractValidationError
from eclair.verification import (
    EvidenceAggregator,
    EvidenceVerification,
    NLILabel,
    NLIPrediction,
    VerificationDetail,
)


def test_aggregator_no_evidence_returns_unknown_and_empty_evidence_ids() -> None:
    aggregator = EvidenceAggregator()
    claim = Claim(text="Sample claim")

    result, detail = aggregator.aggregate(claim, [])

    assert isinstance(result, VerificationResult)
    assert isinstance(detail, VerificationDetail)
    assert result.status is VerificationStatus.UNKNOWN
    assert result.evidence_ids == []
    assert detail.support_score == 0.0
    assert detail.contradiction_score == 0.0
    assert detail.supporting_evidence_ids == []
    assert detail.contradicting_evidence_ids == []


def test_aggregator_supported_evidence() -> None:
    aggregator = EvidenceAggregator()
    claim = Claim(text="Sample claim")

    pred = NLIPrediction(
        label=NLILabel.ENTAILMENT,
        entailment_score=0.92,
        contradiction_score=0.03,
        neutral_score=0.05,
    )
    ev_eval = EvidenceVerification(
        evidence_id="ev_1",
        status=VerificationStatus.SUPPORTED,
        support_score=0.92,
        contradiction_score=0.03,
        nli_prediction=pred,
    )

    result, detail = aggregator.aggregate(claim, [ev_eval])

    assert result.status is VerificationStatus.SUPPORTED
    assert result.evidence_ids == ["ev_1"]
    assert detail.supporting_evidence_ids == ["ev_1"]
    assert detail.support_score == 0.92


def test_aggregator_contradicted_evidence() -> None:
    aggregator = EvidenceAggregator()
    claim = Claim(text="Sample claim")

    ev_eval = EvidenceVerification(
        evidence_id="ev_contra",
        status=VerificationStatus.CONTRADICTED,
        support_score=0.04,
        contradiction_score=0.91,
    )

    result, detail = aggregator.aggregate(claim, [ev_eval])

    assert result.status is VerificationStatus.CONTRADICTED
    assert result.evidence_ids == ["ev_contra"]
    assert detail.contradicting_evidence_ids == ["ev_contra"]
    assert detail.contradiction_score == 0.91


def test_aggregator_type_validation() -> None:
    aggregator = EvidenceAggregator()

    with pytest.raises(ContractValidationError):
        aggregator.aggregate("not a claim", [])  # type: ignore[arg-type]

    with pytest.raises(ContractValidationError):
        aggregator.aggregate(Claim(text="test"), "not a list")  # type: ignore[arg-type]

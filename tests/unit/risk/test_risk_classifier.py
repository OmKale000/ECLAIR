"""Unit tests for M13 RiskClassifier (Spec sec.M13)."""

from __future__ import annotations

import pytest

from eclair.contracts.enums import VerificationStatus
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.risk.classifier import RiskClassifier
from eclair.risk.models import RiskSignals
from eclair.risk.thresholds import RiskThresholds


def test_classifier_high_ecs_low_risk() -> None:
    """Verify high calibrated ECS with no adverse signals results in low risk."""
    classifier = RiskClassifier()
    signals = RiskSignals(
        calibrated_ecs=0.92,
        verifications=[
            VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED, evidence_ids=["e1"]),
        ],
        hallucination_probability=0.05,
        agreement_score=0.95,
    )

    result = classifier.classify(signals)
    assert isinstance(result, RiskResult)
    assert result.risk_level == "low"
    assert result.risk_score < 0.20


def test_classifier_low_ecs_increases_risk() -> None:
    """Verify low calibrated ECS significantly raises the risk score."""
    classifier = RiskClassifier()
    signals = RiskSignals(
        calibrated_ecs=0.20,
        verifications=[
            VerificationResult(claim_id="c1", status=VerificationStatus.UNKNOWN, evidence_ids=[]),
        ],
    )

    result = classifier.classify(signals)
    assert result.risk_level in {"high", "critical", "medium"}
    assert result.risk_score > 0.40


def test_classifier_contradictions_raise_risk() -> None:
    """Verify contradicted claims significantly increase risk score."""
    classifier = RiskClassifier()
    signals = RiskSignals(
        calibrated_ecs=0.80,
        verifications=[
            VerificationResult(claim_id="c1", status=VerificationStatus.CONTRADICTED, evidence_ids=["e1"]),
            VerificationResult(claim_id="c2", status=VerificationStatus.CONTRADICTED, evidence_ids=["e2"]),
        ],
    )

    result, reasons = classifier.classify_with_reasons(signals)
    assert any("contradicted by evidence" in r for r in reasons)
    assert result.risk_score > 0.30


def test_classifier_hallucination_raises_risk() -> None:
    """Verify elevated hallucination probability increases risk score."""
    classifier = RiskClassifier()
    signals = RiskSignals(
        calibrated_ecs=0.75,
        hallucination_probability=0.85,
        is_hallucination=True,
    )

    result, reasons = classifier.classify_with_reasons(signals)
    assert any("hallucination" in r.lower() for r in reasons)
    assert result.risk_score > 0.30


def test_classifier_unsafe_action_critical_risk() -> None:
    """Verify unsafe action flag produces maximum risk score 1.0 and critical level."""
    classifier = RiskClassifier()
    signals = RiskSignals(
        calibrated_ecs=0.99,
        unsafe_action=True,
    )

    result, reasons = classifier.classify_with_reasons(signals)
    assert result.risk_level == "critical"
    assert result.risk_score == 1.0
    assert any("Unsafe action" in r for r in reasons)


def test_classifier_escalate_to_human_flag() -> None:
    """Verify escalate_to_human flag forces risk level to at least HIGH."""
    classifier = RiskClassifier()
    signals = RiskSignals(
        calibrated_ecs=0.90,
        escalate_to_human=True,
    )

    result, reasons = classifier.classify_with_reasons(signals)
    assert result.risk_level in {"high", "critical"}
    assert result.risk_score >= classifier.thresholds.high_risk_threshold
    assert any("human review" in r.lower() for r in reasons)


def test_classifier_accepts_dictionary_input() -> None:
    """Verify dictionary inputs are accepted and normalized."""
    classifier = RiskClassifier()
    signal_dict = {
        "calibrated_ecs": 0.88,
        "agreement_score": 0.90,
    }

    result = classifier.classify(signal_dict)
    assert isinstance(result, RiskResult)
    assert result.risk_level == "low"


def test_classifier_malformed_dictionary_raises() -> None:
    """Verify malformed dictionary inputs raise ContractValidationError."""
    classifier = RiskClassifier()
    with pytest.raises(ContractValidationError):
        classifier.classify({"calibrated_ecs": 2.5})


def test_classifier_unsupported_type_raises() -> None:
    """Verify non-dict non-RiskSignals inputs raise ModuleError."""
    classifier = RiskClassifier()
    with pytest.raises(ModuleError):
        classifier.classify("invalid_string_signal")  # type: ignore[arg-type]


def test_classifier_custom_thresholds_honored() -> None:
    """Verify custom thresholds alter risk level boundaries."""
    strict_thresh = RiskThresholds(
        medium_risk_threshold=0.15,
        high_risk_threshold=0.25,
        critical_risk_threshold=0.50,
    )
    classifier = RiskClassifier(thresholds=strict_thresh)
    signals = RiskSignals(calibrated_ecs=0.55)

    result = classifier.classify(signals)
    assert result.risk_score >= 0.25
    assert result.risk_level in {"high", "critical"}

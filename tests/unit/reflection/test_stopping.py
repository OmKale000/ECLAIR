"""Unit tests for M12 StoppingController."""

from __future__ import annotations

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.verification import VerificationResult
from eclair.reflection.models import ReflectionConfig
from eclair.reflection.stopping import StoppingController


def test_should_trigger_on_low_confidence() -> None:
    stopping = StoppingController()
    cfg = ReflectionConfig(low_confidence_threshold=0.70)

    c1 = Claim(claim_id="c1", text="Sample claim.")
    v1 = VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED)

    # Raw confidence below threshold
    conf = ConfidenceResult(raw_confidence=0.50)
    triggered, reason = stopping.should_trigger([c1], [v1], confidence=conf, config=cfg)
    assert triggered is True
    assert "below_threshold" in reason

    # Calibrated ECS below threshold
    conf_ecs = ConfidenceResult(raw_confidence=0.80, calibrated_ecs=0.45)
    triggered, reason = stopping.should_trigger([c1], [v1], confidence=conf_ecs, config=cfg)
    assert triggered is True
    assert "below_threshold" in reason


def test_should_trigger_on_contradicted_claim() -> None:
    stopping = StoppingController()
    c1 = Claim(claim_id="c1", text="Contradicted claim.")
    v1 = VerificationResult(claim_id="c1", status=VerificationStatus.CONTRADICTED)

    conf = ConfidenceResult(raw_confidence=0.95, calibrated_ecs=0.90)
    triggered, reason = stopping.should_trigger([c1], [v1], confidence=conf)
    assert triggered is True
    assert "contradicted" in reason


def test_should_trigger_on_unknown_claim() -> None:
    stopping = StoppingController()
    c1 = Claim(claim_id="c1", text="Unsupported claim.")
    v1 = VerificationResult(claim_id="c1", status=VerificationStatus.UNKNOWN)

    conf = ConfidenceResult(raw_confidence=0.95, calibrated_ecs=0.90)
    triggered, reason = stopping.should_trigger([c1], [v1], confidence=conf)
    assert triggered is True
    assert "unsupported" in reason


def test_should_not_trigger_when_all_supported_and_confident() -> None:
    stopping = StoppingController()
    cfg = ReflectionConfig(low_confidence_threshold=0.60)
    c1 = Claim(claim_id="c1", text="Supported claim.")
    v1 = VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED)
    conf = ConfidenceResult(raw_confidence=0.85, calibrated_ecs=0.80)

    triggered, reason = stopping.should_trigger([c1], [v1], confidence=conf, config=cfg)
    assert triggered is False
    assert reason == "all_claims_supported_and_confident"


def test_stop_on_identical_answer() -> None:
    stopping = StoppingController()
    cfg = ReflectionConfig(max_iterations=3)

    v1 = [VerificationResult(claim_id="c1", status=VerificationStatus.UNKNOWN)]

    should_stop, reason, improved = stopping.check_stopping_condition(
        iteration=1,
        config=cfg,
        current_verifications=v1,
        previous_verifications=v1,
        current_confidence=None,
        previous_confidence=None,
        new_answer="Same answer text.",
        previous_answer="Same answer text.",
    )
    assert should_stop is True
    assert reason == "regeneration_unchanged"
    assert improved is False


def test_stop_when_all_claims_supported() -> None:
    stopping = StoppingController()
    cfg = ReflectionConfig(max_iterations=3)

    v_prev = [VerificationResult(claim_id="c1", status=VerificationStatus.CONTRADICTED)]
    v_curr = [VerificationResult(claim_id="c2", status=VerificationStatus.SUPPORTED)]

    should_stop, reason, improved = stopping.check_stopping_condition(
        iteration=1,
        config=cfg,
        current_verifications=v_curr,
        previous_verifications=v_prev,
        current_confidence=None,
        previous_confidence=None,
        new_answer="Fully supported answer.",
        previous_answer="Flawed answer.",
    )
    assert should_stop is True
    assert reason == "all_claims_supported"
    assert improved is True


def test_stop_when_confidence_improves() -> None:
    stopping = StoppingController()
    cfg = ReflectionConfig(max_iterations=3, low_confidence_threshold=0.75, min_improvement_margin=0.05)

    v = [VerificationResult(claim_id="c1", status=VerificationStatus.UNKNOWN)]

    prev_conf = ConfidenceResult(raw_confidence=0.50, calibrated_ecs=0.45)
    curr_conf = ConfidenceResult(raw_confidence=0.85, calibrated_ecs=0.80)

    should_stop, reason, improved = stopping.check_stopping_condition(
        iteration=1,
        config=cfg,
        current_verifications=v,
        previous_verifications=v,
        current_confidence=curr_conf,
        previous_confidence=prev_conf,
        new_answer="Improved answer.",
        previous_answer="Low confidence answer.",
    )
    assert should_stop is True
    assert "confidence_improved" in reason
    assert improved is True


def test_stop_on_max_iterations_reached() -> None:
    stopping = StoppingController()
    cfg = ReflectionConfig(max_iterations=2)

    v_curr = [VerificationResult(claim_id="c1", status=VerificationStatus.UNKNOWN)]
    v_prev = [VerificationResult(claim_id="c1", status=VerificationStatus.UNKNOWN)]

    should_stop, reason, _improved = stopping.check_stopping_condition(
        iteration=2,
        config=cfg,
        current_verifications=v_curr,
        previous_verifications=v_prev,
        current_confidence=None,
        previous_confidence=None,
        new_answer="Still weak answer.",
        previous_answer="First weak answer.",
    )
    assert should_stop is True
    assert reason == "max_iterations_reached"

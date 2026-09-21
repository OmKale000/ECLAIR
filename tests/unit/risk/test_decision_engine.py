"""Unit tests for M13 DecisionEngine service and protocol conformance (Spec sec.M13, sec.4.3)."""

from __future__ import annotations

import pytest

from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import DecisionAction, VerificationStatus
from eclair.contracts.interfaces import DecisionEngine as DecisionEngineProtocol
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.risk.decision import DecisionEngine, RiskDecisionEngine
from eclair.risk.models import RiskAssessmentResult, RiskSignals
from eclair.risk.thresholds import RiskThresholds


def test_decision_engine_protocol_conformance() -> None:
    """Verify RiskDecisionEngine conforms to M01 DecisionEngine Protocol."""
    engine = RiskDecisionEngine()
    assert isinstance(engine, DecisionEngineProtocol)

    alias_engine = DecisionEngine()
    assert isinstance(alias_engine, DecisionEngineProtocol)


def test_decide_from_risk_signals() -> None:
    """Verify decide() with RiskSignals returns valid DecisionResult."""
    engine = RiskDecisionEngine()
    signals = RiskSignals(
        calibrated_ecs=0.88,
        verifications=[
            VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED, evidence_ids=["e1"]),
        ],
    )

    decision = engine.decide(signals)
    assert isinstance(decision, DecisionResult)
    assert decision.action is DecisionAction.RETURN
    assert decision.reason is not None


def test_decide_from_confidence_result_contract() -> None:
    """Verify decide() directly consumes an M01 ConfidenceResult contract."""
    engine = RiskDecisionEngine()
    conf = ConfidenceResult(raw_confidence=0.90, calibrated_ecs=0.85)

    decision = engine.decide(conf)
    assert isinstance(decision, DecisionResult)
    assert decision.action is DecisionAction.RETURN


def test_decide_from_dict_and_kwargs() -> None:
    """Verify decide() accepts dictionary input and keyword arguments."""
    engine = RiskDecisionEngine()

    # Dictionary input
    d1 = engine.decide({"calibrated_ecs": 0.25, "iteration_count": 3})
    assert isinstance(d1, DecisionResult)
    assert d1.action is DecisionAction.ABSTAIN

    # Kwargs input
    d2 = engine.decide(calibrated_ecs=0.92)
    assert isinstance(d2, DecisionResult)
    assert d2.action is DecisionAction.RETURN


def test_decide_from_numeric_ecs_signal() -> None:
    """Verify decide() accepts a direct numeric float representing calibrated ECS."""
    engine = RiskDecisionEngine()
    decision = engine.decide(0.85)
    assert isinstance(decision, DecisionResult)
    assert decision.action is DecisionAction.RETURN


def test_decide_out_of_bounds_numeric_raises() -> None:
    """Verify out-of-bounds numeric signal raises ModuleError."""
    engine = RiskDecisionEngine()
    with pytest.raises(ModuleError, match="must be in \\[0.0, 1.0\\]"):
        engine.decide(1.5)


def test_decide_unsupported_type_raises() -> None:
    """Verify unsupported input type raises ModuleError."""
    engine = RiskDecisionEngine()
    with pytest.raises(ModuleError):
        engine.decide(["invalid_list_signal"])


def test_decide_malformed_dict_raises() -> None:
    """Verify malformed dict raises ContractValidationError."""
    engine = RiskDecisionEngine()
    with pytest.raises(ContractValidationError):
        engine.decide({"calibrated_ecs": -0.5})


def test_classify_risk_method() -> None:
    """Verify classify_risk returns structured RiskResult."""
    engine = RiskDecisionEngine()
    risk = engine.classify_risk(calibrated_ecs=0.85)

    assert isinstance(risk, RiskResult)
    assert risk.risk_level == "low"
    assert 0.0 <= risk.risk_score <= 1.0


def test_evaluate_comprehensive_result() -> None:
    """Verify evaluate() produces combined RiskAssessmentResult."""
    engine = RiskDecisionEngine()
    res = engine.evaluate(calibrated_ecs=0.95)

    assert isinstance(res, RiskAssessmentResult)
    assert isinstance(res.risk, RiskResult)
    assert isinstance(res.decision, DecisionResult)
    assert isinstance(res.signals, RiskSignals)
    assert res.decision.action is DecisionAction.RETURN
    assert res.policy_rule == "RETURN"


def test_all_six_decision_actions_producible() -> None:
    """Verify all six frozen DecisionAction members can be selected under respective conditions."""
    engine = RiskDecisionEngine()

    # 1. RETURN
    res_return = engine.decide(calibrated_ecs=0.88)
    assert res_return.action is DecisionAction.RETURN

    # 2. VERIFY_MORE
    res_verify = engine.decide(
        calibrated_ecs=0.55,
        verifications=[VerificationResult(claim_id="c1", status=VerificationStatus.UNKNOWN, evidence_ids=[])],
        iteration_count=0,
    )
    assert res_verify.action is DecisionAction.VERIFY_MORE

    # 3. REGENERATE
    res_regen = engine.decide(
        calibrated_ecs=0.45,
        verifications=[VerificationResult(claim_id="c1", status=VerificationStatus.CONTRADICTED, evidence_ids=["e1"])],
        iteration_count=1,
    )
    assert res_regen.action is DecisionAction.REGENERATE

    # 4. ABSTAIN
    res_abstain = engine.decide(
        calibrated_ecs=0.25,
        iteration_count=3,
    )
    assert res_abstain.action is DecisionAction.ABSTAIN

    # 5. HUMAN_REVIEW
    res_review = engine.decide(
        calibrated_ecs=0.75,
        escalate_to_human=True,
    )
    assert res_review.action is DecisionAction.HUMAN_REVIEW

    # 6. BLOCK_ACTION
    res_block = engine.decide(
        calibrated_ecs=0.90,
        unsafe_action=True,
    )
    assert res_block.action is DecisionAction.BLOCK_ACTION


def test_no_unsupported_decision_actions() -> None:
    """Verify no decision outside the six defined frozen actions can ever be returned."""
    allowed_actions = {a.value for a in DecisionAction}
    engine = RiskDecisionEngine()

    test_inputs = [
        {"calibrated_ecs": 0.95},
        {"calibrated_ecs": 0.10},
        {"calibrated_ecs": 0.50, "iteration_count": 0},
        {"calibrated_ecs": 0.50, "iteration_count": 3},
        {"unsafe_action": True},
        {"escalate_to_human": True},
    ]

    for inp in test_inputs:
        decision = engine.decide(**inp)
        assert decision.action.value in allowed_actions


def test_m13_does_not_calculate_or_alter_ecs() -> None:
    """Verify M13 does NOT modify or recompute the incoming calibrated ECS."""
    engine = RiskDecisionEngine()
    original_ecs = 0.777
    conf = ConfidenceResult(raw_confidence=0.888, calibrated_ecs=original_ecs)

    assessment = engine.evaluate(confidence_result=conf)
    # The signal evaluated must match exactly the upstream calibrated ECS
    assert assessment.signals.effective_ecs == original_ecs
    assert assessment.signals.raw_confidence == 0.888


def test_custom_thresholds_passed_to_engine() -> None:
    """Verify custom RiskThresholds alter decision boundaries as expected."""
    custom_thresholds = RiskThresholds(high_ecs_threshold=0.90)
    engine = RiskDecisionEngine(thresholds=custom_thresholds)

    # 0.85 would normally RETURN with default 0.70 threshold, but with 0.90 threshold it triggers REGENERATE
    decision = engine.decide(calibrated_ecs=0.85, iteration_count=0)
    assert decision.action is DecisionAction.REGENERATE

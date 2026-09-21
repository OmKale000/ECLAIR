"""Unit tests for M13 DecisionPolicy (Spec sec.M13, sec.5)."""

from __future__ import annotations

from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import DecisionAction, VerificationStatus
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.risk.models import RiskSignals
from eclair.risk.policy import DecisionPolicy
from eclair.risk.thresholds import RiskThresholds


def test_policy_returns_valid_decision_result() -> None:
    """Verify policy evaluation returns a valid DecisionResult using DecisionAction enum."""
    policy = DecisionPolicy()
    signals = RiskSignals(calibrated_ecs=0.85)
    risk = RiskResult(risk_level="low", risk_score=0.10)

    decision = policy.evaluate(signals, risk)
    assert isinstance(decision, DecisionResult)
    assert isinstance(decision.action, DecisionAction)
    assert decision.reason is not None


def test_policy_action_return_high_ecs() -> None:
    """Verify high calibrated ECS with low risk yields RETURN (Spec sec.5)."""
    policy = DecisionPolicy()
    signals = RiskSignals(
        calibrated_ecs=0.88,
        verifications=[
            VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED, evidence_ids=["e1"]),
        ],
    )
    risk = RiskResult(risk_level="low", risk_score=0.08)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.RETURN
    assert "satisfies high threshold" in decision.reason


def test_policy_action_verify_more_unknown_claims() -> None:
    """Verify unverified/unknown claims request VERIFY_MORE on initial run."""
    policy = DecisionPolicy()
    signals = RiskSignals(
        calibrated_ecs=0.55,
        verifications=[
            VerificationResult(claim_id="c1", status=VerificationStatus.UNKNOWN, evidence_ids=[]),
            VerificationResult(claim_id="c2", status=VerificationStatus.UNKNOWN, evidence_ids=[]),
        ],
        iteration_count=0,
    )
    risk = RiskResult(risk_level="medium", risk_score=0.35)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.VERIFY_MORE
    assert "unverified status" in decision.reason


def test_policy_action_regenerate_on_low_ecs_within_iterations() -> None:
    """Verify low ECS within iteration limit yields REGENERATE (Spec sec.M12)."""
    policy = DecisionPolicy()
    signals = RiskSignals(
        calibrated_ecs=0.45,
        verifications=[
            VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED, evidence_ids=["e1"]),
        ],
        iteration_count=1,
    )
    risk = RiskResult(risk_level="medium", risk_score=0.40)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.REGENERATE
    assert "Reflection triggered by" in decision.reason


def test_policy_action_regenerate_on_contradiction() -> None:
    """Verify contradicted claim within iteration limit triggers REGENERATE."""
    policy = DecisionPolicy()
    signals = RiskSignals(
        calibrated_ecs=0.60,
        verifications=[
            VerificationResult(claim_id="c1", status=VerificationStatus.CONTRADICTED, evidence_ids=["e1"]),
        ],
        iteration_count=0,
    )
    risk = RiskResult(risk_level="medium", risk_score=0.45)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.REGENERATE
    assert "contradicted" in decision.reason.lower()


def test_policy_action_abstain_when_iterations_exhausted() -> None:
    """Verify low ECS after maximum reflection iterations yields ABSTAIN (Spec sec.5)."""
    policy = DecisionPolicy()
    signals = RiskSignals(
        calibrated_ecs=0.35,
        iteration_count=3,  # Reached max_reflection_iterations (3)
    )
    risk = RiskResult(risk_level="medium", risk_score=0.50)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.ABSTAIN
    assert "maximum reflection iterations" in decision.reason


def test_policy_action_human_review_on_escalate_flag() -> None:
    """Verify explicit escalation flag yields HUMAN_REVIEW."""
    policy = DecisionPolicy()
    signals = RiskSignals(
        calibrated_ecs=0.85,
        escalate_to_human=True,
    )
    risk = RiskResult(risk_level="high", risk_score=0.65)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.HUMAN_REVIEW
    assert "human review requested" in decision.reason.lower()


def test_policy_action_human_review_on_high_risk() -> None:
    """Verify high risk level yields HUMAN_REVIEW."""
    policy = DecisionPolicy()
    signals = RiskSignals(calibrated_ecs=0.60)
    risk = RiskResult(risk_level="high", risk_score=0.65)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.HUMAN_REVIEW
    assert "warrants human oversight" in decision.reason


def test_policy_action_block_action_on_unsafe_flag() -> None:
    """Verify unsafe action flag yields BLOCK_ACTION."""
    policy = DecisionPolicy()
    signals = RiskSignals(
        calibrated_ecs=0.99,
        unsafe_action=True,
    )
    risk = RiskResult(risk_level="critical", risk_score=1.0)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.BLOCK_ACTION
    assert "Unsafe action" in decision.reason


def test_policy_action_block_action_on_critical_risk() -> None:
    """Verify critical risk level yields BLOCK_ACTION."""
    policy = DecisionPolicy()
    signals = RiskSignals(calibrated_ecs=0.20)
    risk = RiskResult(risk_level="critical", risk_score=0.85)

    decision = policy.evaluate(signals, risk)
    assert decision.action is DecisionAction.BLOCK_ACTION
    assert "Critical risk score" in decision.reason


def test_policy_ecs_threshold_boundaries() -> None:
    """Verify threshold boundary behavior at high_ecs_threshold (0.70)."""
    policy = DecisionPolicy(thresholds=RiskThresholds(high_ecs_threshold=0.70))
    risk_low = RiskResult(risk_level="low", risk_score=0.10)

    # Exactly at threshold: 0.70 -> RETURN
    at_thresh = RiskSignals(calibrated_ecs=0.70)
    assert policy.evaluate(at_thresh, risk_low).action is DecisionAction.RETURN

    # Slightly above threshold: 0.7001 -> RETURN
    above_thresh = RiskSignals(calibrated_ecs=0.7001)
    assert policy.evaluate(above_thresh, risk_low).action is DecisionAction.RETURN

    # Slightly below threshold: 0.6999 -> REGENERATE (iteration_count=0)
    below_thresh = RiskSignals(calibrated_ecs=0.6999, iteration_count=0)
    assert policy.evaluate(below_thresh, risk_low).action is DecisionAction.REGENERATE

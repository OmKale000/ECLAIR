"""Configurable risk decision policy for M13 Risk & Decision Engine.

Applies the configured threshold-based risk policy to calibrated ECS and reliability
signals, mapping them deterministically to exactly one of the six frozen DecisionAction
members in M01 DecisionResult.

Reliability invariants (Spec sec.5, sec.M13, SHARED_CONTRACTS_REFERENCE sec.2):
- Allowed actions strictly limited to:
  RETURN, VERIFY_MORE, REGENERATE, ABSTAIN, HUMAN_REVIEW, BLOCK_ACTION.
- HIGH ECS -> RETURN (Spec sec.5).
- LOW ECS -> Reflection (REGENERATE / VERIFY_MORE) -> ACCEPT / ABSTAIN.
- Escalation -> HUMAN_REVIEW; unsafe action -> BLOCK_ACTION.
- Never invents new decision actions or states.
"""

from __future__ import annotations

from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import DecisionAction
from eclair.contracts.risk import RiskResult
from eclair.risk.models import RiskLevel, RiskSignals
from eclair.risk.thresholds import RiskThresholds

__all__ = [
    "DecisionPolicy",
]


class DecisionPolicy:
    """Evaluates calibrated ECS and risk signals against configured thresholds to select a decision."""

    def __init__(self, thresholds: RiskThresholds | None = None) -> None:
        self.thresholds = thresholds or RiskThresholds()

    def evaluate(
        self,
        signals: RiskSignals,
        risk: RiskResult,
    ) -> DecisionResult:
        """Apply risk-based policy and select one of the six frozen DecisionAction members.

        Evaluation cascade follows the established Spec §5 & §M13 decision branches:
        1. Critical Risk / Safety Violation -> BLOCK_ACTION
        2. Explicit Escalation -> HUMAN_REVIEW
        3. Reflection Iterations Exhausted with Low ECS / Issues -> ABSTAIN
        4. High Risk (prior to iteration exhaustion) -> HUMAN_REVIEW
        5. High Calibrated ECS & Low Risk -> RETURN
        6. Unverified Claims / Missing Evidence -> VERIFY_MORE
        7. Low ECS / Hallucination / Contradiction within Iteration Limit -> REGENERATE

        Args:
            signals: Normalized RiskSignals container.
            risk: Validated RiskResult produced by RiskClassifier.

        Returns:
            DecisionResult with one of the six valid DecisionAction values and explanation.
        """
        ecs = signals.effective_ecs
        is_critical_risk = risk.risk_level == RiskLevel.CRITICAL.value
        is_high_risk = risk.risk_level == RiskLevel.HIGH.value

        # --- Branch 1: Safety & Block Action ---
        if signals.unsafe_action or is_critical_risk:
            reason = (
                "Unsafe action or critical safety policy breach detected; blocking action."
                if signals.unsafe_action
                else f"Critical risk score ({risk.risk_score:.2f} >= "
                f"{self.thresholds.critical_risk_threshold:.2f}); blocking action."
            )
            return DecisionResult(
                action=DecisionAction.BLOCK_ACTION,
                reason=reason,
            )

        # --- Branch 2: Explicit Escalation to Human Review ---
        if signals.escalate_to_human:
            return DecisionResult(
                action=DecisionAction.HUMAN_REVIEW,
                reason="Explicit escalation to human review requested.",
            )

        iterations_exhausted = (
            signals.iteration_count >= self.thresholds.max_reflection_iterations
        )
        has_contradictions = (
            signals.contradicted_claims_count > self.thresholds.max_contradicted_claims
        )
        is_hallucinating = bool(
            signals.is_hallucination
            or (
                signals.hallucination_probability is not None
                and signals.hallucination_probability
                >= self.thresholds.hallucination_threshold
            )
        )
        needs_evidence = (
            signals.total_claims_count > 0
            and (
                signals.unknown_ratio > self.thresholds.max_unknown_ratio
                or (
                    signals.unknown_claims_count > 0
                    and signals.supported_claims_count == 0
                    and not has_contradictions
                )
            )
        )

        # --- Branch 3: Reflection Iterations Exhausted -> ABSTAIN ---
        # Spec sec.5, sec.M13: remains LOW after reflection -> ABSTAIN
        if iterations_exhausted:
            if (
                (ecs is not None and ecs < self.thresholds.high_ecs_threshold)
                or has_contradictions
                or is_hallucinating
                or needs_evidence
                or is_high_risk
            ):
                abstain_reasons: list[str] = [
                    f"maximum reflection iterations ({self.thresholds.max_reflection_iterations}) reached"
                ]
                if ecs is not None and ecs < self.thresholds.low_ecs_threshold:
                    abstain_reasons.append(
                        f"calibrated ECS ({ecs:.2f}) remains below low threshold "
                        f"({self.thresholds.low_ecs_threshold:.2f})"
                    )
                if has_contradictions:
                    abstain_reasons.append(f"{signals.contradicted_claims_count} claim(s) contradicted")
                if needs_evidence:
                    abstain_reasons.append("claims remain unsupported by evidence")

                return DecisionResult(
                    action=DecisionAction.ABSTAIN,
                    reason=f"Abstaining from response: {'; '.join(abstain_reasons)}.",
                )

        # --- Branch 4: High Risk (before iterations exhausted) -> HUMAN_REVIEW ---
        if is_high_risk:
            return DecisionResult(
                action=DecisionAction.HUMAN_REVIEW,
                reason=(
                    f"High risk classification ({risk.risk_level}, score {risk.risk_score:.2f}) "
                    "warrants human oversight before taking action."
                ),
            )

        # --- Branch 5: High ECS & Low Risk -> RETURN ---
        # Spec sec.5: HIGH ECS -> RETURN
        if (
            ecs is not None
            and ecs >= self.thresholds.high_ecs_threshold
            and risk.risk_level == RiskLevel.LOW.value
            and not has_contradictions
            and not is_hallucinating
        ):
            return DecisionResult(
                action=DecisionAction.RETURN,
                reason=(
                    f"Calibrated ECS ({ecs:.2f}) satisfies high threshold "
                    f"({self.thresholds.high_ecs_threshold:.2f}) with low risk."
                ),
            )

        # --- Branch 6: Verification Needed -> VERIFY_MORE ---
        # When claims have UNKNOWN status without severe contradiction on first iteration
        if needs_evidence and signals.iteration_count == 0 and not has_contradictions:
            return DecisionResult(
                action=DecisionAction.VERIFY_MORE,
                reason=(
                    f"Claims have unverified status (unknown ratio {signals.unknown_ratio:.2f}); "
                    "additional evidence retrieval and verification required."
                ),
            )

        # --- Branch 7: Reflection & Regeneration -> REGENERATE ---
        # Spec sec.5, sec.M12: LOW ECS -> enter reflection loop within iteration limit
        if not iterations_exhausted:
            trigger_reason = (
                "contradicted claims"
                if has_contradictions
                else (
                    "hallucination detected"
                    if is_hallucinating
                    else f"calibrated ECS ({ecs:.2f} < {self.thresholds.high_ecs_threshold:.2f})"
                    if ecs is not None
                    else "uncertainty"
                )
            )
            return DecisionResult(
                action=DecisionAction.REGENERATE,
                reason=(
                    f"Reflection triggered by {trigger_reason}; "
                    f"iteration {signals.iteration_count + 1} of "
                    f"{self.thresholds.max_reflection_iterations}."
                ),
            )

        # Fallback: ABSTAIN
        return DecisionResult(
            action=DecisionAction.ABSTAIN,
            reason="Reliability criteria not met; abstaining from untrusted answer.",
        )

"""Risk classifier for M13 Risk & Decision Engine.

Responsible only for risk classification behavior. Evaluates calibrated ECS and
available reliability signals (verifications, hallucinations, agreement, conflict)
to produce a structured M01 RiskResult.

Reliability invariant (Spec sec.4.4, SHARED_CONTRACTS_REFERENCE sec.6):
Does NOT calculate raw confidence (M10) or calibrated ECS (M11).
Does NOT calibrate confidence or modify ECS values.
Consumes pre-computed calibrated ECS and upstream reliability signals.
"""

from __future__ import annotations

from typing import Any

from eclair.contracts.risk import RiskResult
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.risk.models import RiskLevel, RiskSignals
from eclair.risk.thresholds import RiskThresholds

__all__ = [
    "RiskClassifier",
]


class RiskClassifier:
    """Classifies risk level and numeric risk score from calibrated ECS and reliability signals."""

    def __init__(self, thresholds: RiskThresholds | None = None) -> None:
        self.thresholds = thresholds or RiskThresholds()

    def classify(self, signals: RiskSignals | dict[str, Any]) -> RiskResult:
        """Evaluate input reliability signals and produce a validated RiskResult.

        Args:
            signals: Either a RiskSignals instance or a dictionary of signal values.

        Returns:
            RiskResult with risk_level ("low", "medium", "high", "critical")
            and numeric risk_score in [0.0, 1.0].

        Raises:
            ContractValidationError: if signal dictionary or data is structurally invalid.
            ModuleError: if required signals are missing or out of range.
        """
        norm_signals = self._normalize_signals(signals)
        risk_score, reasons = self._calculate_risk_score(norm_signals)
        risk_level = self._determine_risk_level(risk_score, norm_signals)

        return RiskResult(
            risk_level=risk_level,
            risk_score=round(risk_score, 4),
        )

    def classify_with_reasons(
        self, signals: RiskSignals | dict[str, Any]
    ) -> tuple[RiskResult, list[str]]:
        """Evaluate risk and return both the RiskResult and explanatory reasons."""
        norm_signals = self._normalize_signals(signals)
        risk_score, reasons = self._calculate_risk_score(norm_signals)
        risk_level = self._determine_risk_level(risk_score, norm_signals)

        return (
            RiskResult(risk_level=risk_level, risk_score=round(risk_score, 4)),
            reasons,
        )

    def _normalize_signals(self, signals: RiskSignals | dict[str, Any]) -> RiskSignals:
        """Validate and normalize inputs into a RiskSignals instance."""
        if isinstance(signals, RiskSignals):
            return signals

        if isinstance(signals, dict):
            try:
                return RiskSignals(**signals)
            except Exception as exc:
                raise ContractValidationError(
                    f"Malformed signal dictionary for RiskClassifier: {exc}",
                    code="risk_contract_invalid",
                ) from exc

        raise ModuleError(
            f"Unsupported signals type for RiskClassifier: {type(signals).__name__}",
            code="risk_unsupported_type",
        )

    def _calculate_risk_score(self, signals: RiskSignals) -> tuple[float, list[str]]:
        """Calculate weighted numeric risk score in [0.0, 1.0] and gather explanatory reasons."""
        reasons: list[str] = []

        # Explicit unsafe action flag overrides all signals with maximum risk
        if signals.unsafe_action:
            reasons.append("Unsafe action or critical safety breach detected.")
            return 1.0, reasons

        # Weighted risk component accumulation
        total_risk = 0.0
        total_weight = 0.0

        # Component 1: Calibrated ECS deficiency (weight 0.40)
        # Higher ECS -> Lower Risk; Lower ECS -> Higher Risk
        ecs = signals.effective_ecs
        if ecs is not None:
            ecs_risk = 1.0 - ecs
            w_ecs = 0.40
            total_risk += ecs_risk * w_ecs
            total_weight += w_ecs
            if ecs < self.thresholds.low_ecs_threshold:
                reasons.append(
                    f"Low calibrated ECS ({ecs:.2f} < {self.thresholds.low_ecs_threshold:.2f})."
                )
        elif signals.raw_confidence is not None:
            # Fallback to raw confidence if calibrated ECS was not provided
            raw_risk = 1.0 - signals.raw_confidence
            w_raw = 0.30
            total_risk += raw_risk * w_raw
            total_weight += w_raw
            if signals.raw_confidence < self.thresholds.low_ecs_threshold:
                reasons.append(
                    f"Low raw confidence ({signals.raw_confidence:.2f})."
                )

        # Component 2: Verification contradictions and unverified claims (weight 0.30)
        if signals.verifications:
            w_verif = 0.30
            c_count = signals.contradicted_claims_count
            u_ratio = signals.unknown_ratio
            verif_risk = 0.0

            if c_count > self.thresholds.max_contradicted_claims:
                # Contradictions contribute to risk (up to 0.60 scaled by fraction)
                verif_risk += 0.60 * min(1.0, c_count / max(1, signals.total_claims_count))
                reasons.append(f"{c_count} claim(s) contradicted by evidence.")

            if u_ratio > self.thresholds.max_unknown_ratio:
                verif_risk += 0.30 * u_ratio
                reasons.append(
                    f"High unknown claim ratio ({u_ratio:.2f} > {self.thresholds.max_unknown_ratio:.2f})."
                )

            verif_risk = min(1.0, verif_risk)
            total_risk += verif_risk * w_verif
            total_weight += w_verif

        # Component 3: Hallucination signals (weight 0.20)
        halluc_prob = signals.hallucination_probability
        if halluc_prob is not None:
            w_halluc = 0.20
            total_risk += halluc_prob * w_halluc
            total_weight += w_halluc
            if halluc_prob >= self.thresholds.hallucination_threshold:
                reasons.append(
                    f"Elevated hallucination probability ({halluc_prob:.2f} >= "
                    f"{self.thresholds.hallucination_threshold:.2f})."
                )
        elif signals.is_hallucination:
            w_halluc = 0.20
            total_risk += 0.80 * w_halluc
            total_weight += w_halluc
            reasons.append("Response flagged as hallucination by M08.")

        # Component 4: Multi-model disagreement (weight 0.10)
        if signals.agreement_score is not None:
            w_agree = 0.10
            disagreement = 1.0 - signals.agreement_score
            total_risk += disagreement * w_agree
            total_weight += w_agree
            if signals.agreement_score < self.thresholds.min_agreement_threshold:
                reasons.append(
                    f"Low model consensus agreement ({signals.agreement_score:.2f} < "
                    f"{self.thresholds.min_agreement_threshold:.2f})."
                )

        # Component 5: Evidence conflict / quality (weight 0.10)
        if signals.evidence_conflict_score is not None:
            w_conf = 0.10
            total_risk += signals.evidence_conflict_score * w_conf
            total_weight += w_conf
            if signals.evidence_conflict_score > 0.3:
                reasons.append(
                    f"Evidence source conflict detected ({signals.evidence_conflict_score:.2f})."
                )

        # Explicit human review requested
        if signals.escalate_to_human:
            reasons.append("Manual escalation to human review requested.")

        # If no signals provided, base risk score is 0.5 (unknown)
        if total_weight <= 0.0:
            return 0.5, ["No reliability signals provided for risk classification."]

        # Renormalize across active weights
        normalized_score = total_risk / total_weight
        bounded_score = max(0.0, min(1.0, normalized_score))

        # If human escalation was requested, ensure risk score is at least high_risk_threshold
        if signals.escalate_to_human:
            bounded_score = max(bounded_score, self.thresholds.high_risk_threshold)

        return bounded_score, reasons

    def _determine_risk_level(self, risk_score: float, signals: RiskSignals) -> str:
        """Map numeric risk score and critical conditions to qualitative RiskLevel."""
        if signals.unsafe_action or risk_score >= self.thresholds.critical_risk_threshold:
            return RiskLevel.CRITICAL.value

        if signals.escalate_to_human or risk_score >= self.thresholds.high_risk_threshold:
            return RiskLevel.HIGH.value

        if risk_score >= self.thresholds.medium_risk_threshold:
            return RiskLevel.MEDIUM.value

        return RiskLevel.LOW.value

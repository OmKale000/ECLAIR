"""Decision Engine implementation for M13 Risk & Decision Engine.

Conforms to the frozen M01 ``DecisionEngine`` Protocol:
    ``DecisionEngine.decide(signals: Any) -> DecisionResult``

Coordinates risk classification and policy evaluation to select exactly one
valid DecisionResult action (RETURN, VERIFY_MORE, REGENERATE, ABSTAIN,
HUMAN_REVIEW, or BLOCK_ACTION).

Reliability invariants (Spec sec.4.4, sec.M13):
- Does NOT compute raw confidence (M10) or calibrated ECS (M11).
- Strictly consumes calibrated ECS and upstream reliability signals.
- Returns only contracts from M01 (DecisionResult, RiskResult).
- Does NOT persist decisions (M14).
- Does NOT execute reflection loops (M12).
"""

from __future__ import annotations

from typing import Any

from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.risk import RiskResult
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.risk.classifier import RiskClassifier
from eclair.risk.models import RiskAssessmentResult, RiskSignals
from eclair.risk.policy import DecisionPolicy
from eclair.risk.thresholds import RiskThresholds

__all__ = [
    "DecisionEngine",
    "RiskDecisionEngine",
]


class RiskDecisionEngine:
    """Risk & Decision Engine service conforming to the M01 DecisionEngine Protocol."""

    def __init__(
        self,
        thresholds: RiskThresholds | None = None,
        classifier: RiskClassifier | None = None,
        policy: DecisionPolicy | None = None,
    ) -> None:
        self.thresholds = thresholds or RiskThresholds()
        self.classifier = classifier or RiskClassifier(self.thresholds)
        self.policy = policy or DecisionPolicy(self.thresholds)

    def decide(self, signals: Any = None, **kwargs: Any) -> DecisionResult:
        """Select a decision action from reliability signals.

        Conforms to ``eclair.contracts.interfaces.DecisionEngine.decide``.

        Args:
            signals: RiskSignals instance, ConfidenceResult, dictionary of signals, or None.
            **kwargs: Signal fields passed as keyword arguments.

        Returns:
            DecisionResult with one of the six frozen DecisionAction values.

        Raises:
            ContractValidationError: if signal data fails contract validation.
            ModuleError: if input types are invalid or required data cannot be parsed.
        """
        assessment = self.evaluate(signals, **kwargs)
        return assessment.decision

    def classify_risk(self, signals: Any = None, **kwargs: Any) -> RiskResult:
        """Evaluate and return only the RiskResult for the provided signals."""
        assessment = self.evaluate(signals, **kwargs)
        return assessment.risk

    def evaluate(self, signals: Any = None, **kwargs: Any) -> RiskAssessmentResult:
        """Perform full evaluation returning both RiskResult and DecisionResult."""
        norm_signals = self._normalize_input(signals, kwargs)

        risk_result, reasons = self.classifier.classify_with_reasons(norm_signals)
        decision_result = self.policy.evaluate(norm_signals, risk_result)

        return RiskAssessmentResult(
            risk=risk_result,
            decision=decision_result,
            signals=norm_signals,
            reasons=reasons,
            policy_rule=decision_result.action.value,
        )

    def _normalize_input(self, signals: Any, kwargs: dict[str, Any]) -> RiskSignals:
        """Normalize various input representations into a valid RiskSignals instance."""
        # Case 1: kwargs provided with signals is None
        if signals is None and kwargs:
            try:
                return RiskSignals(**kwargs)
            except Exception as exc:
                raise ContractValidationError(
                    f"Invalid signal keyword arguments: {exc}",
                    code="risk_contract_invalid",
                ) from exc

        # Case 2: RiskSignals instance passed directly
        if isinstance(signals, RiskSignals):
            if kwargs:
                # Merge kwargs into the instance
                data = signals.model_dump()
                data.update(kwargs)
                return RiskSignals(**data)
            return signals

        # Case 3: ConfidenceResult contract passed directly
        if isinstance(signals, ConfidenceResult):
            fields: dict[str, Any] = {
                "calibrated_ecs": signals.calibrated_ecs,
                "raw_confidence": signals.raw_confidence,
                "confidence_result": signals,
            }
            fields.update(kwargs)
            return RiskSignals(**fields)

        # Case 4: Dictionary of signals passed
        if isinstance(signals, dict):
            merged = dict(signals)
            merged.update(kwargs)
            try:
                return RiskSignals(**merged)
            except Exception as exc:
                raise ContractValidationError(
                    f"Invalid signal dictionary structure: {exc}",
                    code="risk_contract_invalid",
                ) from exc

        # Case 5: Direct numeric float (interpreted as calibrated_ecs)
        if isinstance(signals, (int, float)):
            val = float(signals)
            if not 0.0 <= val <= 1.0:
                raise ModuleError(
                    f"Numeric ECS signal value must be in [0.0, 1.0], got {val}",
                    code="risk_out_of_bounds",
                )
            fields = {"calibrated_ecs": val}
            fields.update(kwargs)
            return RiskSignals(**fields)

        # Case 6: Nothing provided
        if signals is None and not kwargs:
            return RiskSignals()

        raise ModuleError(
            f"Unsupported signals input type for DecisionEngine: {type(signals).__name__}",
            code="risk_unsupported_type",
        )


# Alias DecisionEngine to RiskDecisionEngine for contract and protocol consistency
DecisionEngine = RiskDecisionEngine

"""M13 — Risk & Decision Engine module for ECLAIR (Spec sec.M13, sec.4.1, sec.5).

Determines the action ECLAIR should take after reliability analysis by evaluating
calibrated ECS and reliability signals against a configurable, threshold-based risk policy.

Selects one of the six frozen DecisionAction members:
- RETURN: calibrated ECS satisfies high threshold with low risk.
- VERIFY_MORE: unverified claims require additional evidence retrieval.
- REGENERATE: low ECS, contradiction, or hallucination requires reflection loop.
- ABSTAIN: low ECS or ungrounded claims persist after iteration limit.
- HUMAN_REVIEW: high risk or explicit escalation requires human oversight.
- BLOCK_ACTION: unsafe action or critical safety breach blocked.

Reliability invariants (Spec sec.4.4, sec.M13, SHARED_CONTRACTS_REFERENCE sec.6):
- M13 does NOT compute raw confidence (M10) or calibrated ECS (M11).
- M13 does NOT execute self-reflection loops (M12).
- M13 does NOT persist decisions or manage database storage (M14).
- M13 produces M01 RiskResult and DecisionResult contracts.
"""

from __future__ import annotations

from eclair.risk.classifier import RiskClassifier
from eclair.risk.decision import DecisionEngine, RiskDecisionEngine
from eclair.risk.models import (
    RiskAssessmentResult,
    RiskLevel,
    RiskSignals,
)
from eclair.risk.policy import DecisionPolicy
from eclair.risk.thresholds import (
    DEFAULT_CRITICAL_RISK_THRESHOLD,
    DEFAULT_HALLUCINATION_THRESHOLD,
    DEFAULT_HIGH_ECS_THRESHOLD,
    DEFAULT_HIGH_RISK_THRESHOLD,
    DEFAULT_LOW_ECS_THRESHOLD,
    DEFAULT_MAX_CONTRADICTED_CLAIMS,
    DEFAULT_MAX_REFLECTION_ITERATIONS,
    DEFAULT_MAX_UNKNOWN_RATIO,
    DEFAULT_MEDIUM_RISK_THRESHOLD,
    DEFAULT_MIN_AGREEMENT_THRESHOLD,
    RiskThresholds,
    load_risk_thresholds,
)

__all__ = [
    # Main Engine / Service
    "DecisionEngine",
    "RiskDecisionEngine",
    # Classifier & Policy
    "RiskClassifier",
    "DecisionPolicy",
    # Thresholds & Configuration
    "RiskThresholds",
    "load_risk_thresholds",
    "DEFAULT_HIGH_ECS_THRESHOLD",
    "DEFAULT_LOW_ECS_THRESHOLD",
    "DEFAULT_HALLUCINATION_THRESHOLD",
    "DEFAULT_CRITICAL_RISK_THRESHOLD",
    "DEFAULT_HIGH_RISK_THRESHOLD",
    "DEFAULT_MEDIUM_RISK_THRESHOLD",
    "DEFAULT_MIN_AGREEMENT_THRESHOLD",
    "DEFAULT_MAX_UNKNOWN_RATIO",
    "DEFAULT_MAX_CONTRADICTED_CLAIMS",
    "DEFAULT_MAX_REFLECTION_ITERATIONS",
    # Models
    "RiskLevel",
    "RiskSignals",
    "RiskAssessmentResult",
]

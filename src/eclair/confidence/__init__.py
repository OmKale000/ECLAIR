"""M10 Confidence Estimation module.

Estimates raw confidence from available reliability signals (verification,
evidence, agreement, consistency, model-confidence) using configurable weighted fusion.

Reliability invariants (Spec sec.4.4, SHARED_CONTRACTS_REFERENCE sec.6):
- M10 produces RAW confidence only.
- Raw confidence is NOT calibrated ECS.
- Only M11 may convert raw confidence into calibrated ECS.
- Absence of evidence must never be treated as support.
- Model agreement is a reliability signal, not proof of truth.
"""

from __future__ import annotations

from eclair.confidence.estimator import ConfidenceEstimator
from eclair.confidence.fusion import ConfidenceFuser
from eclair.confidence.models import (
    DEFAULT_WEIGHT_AGREEMENT,
    DEFAULT_WEIGHT_CONSISTENCY,
    DEFAULT_WEIGHT_EVIDENCE,
    DEFAULT_WEIGHT_MODEL_CONFIDENCE,
    DEFAULT_WEIGHT_VERIFICATION,
    ClaimConfidenceResult,
    ConfidenceBreakdown,
    ConfidenceFusionConfig,
    ConfidenceSignals,
    ResponseConfidenceResult,
    SignalContribution,
)
from eclair.confidence.signals import (
    extract_agreement_signal,
    extract_claim_signals,
    extract_consistency_signal,
    extract_evidence_signal,
    extract_model_confidence_signal,
    extract_response_signals,
    extract_verification_signal,
)

__all__ = [
    # Main Service & Fuser
    "ConfidenceEstimator",
    "ConfidenceFuser",
    # Config & Constants
    "ConfidenceFusionConfig",
    "DEFAULT_WEIGHT_VERIFICATION",
    "DEFAULT_WEIGHT_EVIDENCE",
    "DEFAULT_WEIGHT_AGREEMENT",
    "DEFAULT_WEIGHT_CONSISTENCY",
    "DEFAULT_WEIGHT_MODEL_CONFIDENCE",
    # Models
    "ConfidenceSignals",
    "SignalContribution",
    "ConfidenceBreakdown",
    "ClaimConfidenceResult",
    "ResponseConfidenceResult",
    # Signal Extraction Helpers
    "extract_verification_signal",
    "extract_evidence_signal",
    "extract_agreement_signal",
    "extract_consistency_signal",
    "extract_model_confidence_signal",
    "extract_claim_signals",
    "extract_response_signals",
]

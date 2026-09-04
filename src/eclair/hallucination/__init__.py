"""ECLAIR Hallucination Detection (M08).

Provides multi-signal hallucination detection and scoring over atomic claims and responses:
- Combines 5 core reliability signals: no evidence, contradictory evidence,
  low semantic support, model disagreement, and numerical inconsistency.
- Produces structured HallucinationResult with bounded probability in [0.0, 1.0],
  threshold-based boolean flag, and non-empty explanatory reasons when flagged.
- Exposes HallucinationDetector for single claim or full response batch analysis.
"""

from __future__ import annotations

from eclair.hallucination.detector import HallucinationDetector
from eclair.hallucination.models import (
    HallucinationReason,
    HallucinationResult,
    HallucinationSignals,
    ResponseHallucinationResult,
)
from eclair.hallucination.scoring import (
    DEFAULT_HALLUCINATION_THRESHOLD,
    HallucinationScorer,
    HallucinationScorerConfig,
)
from eclair.hallucination.signals import (
    extract_contradiction_signal,
    extract_hallucination_signals,
    extract_model_disagreement_signal,
    extract_no_evidence_signal,
    extract_numerical_inconsistency_signal,
    extract_semantic_support_signal,
)

__all__ = [
    # Models
    "HallucinationReason",
    "HallucinationSignals",
    "HallucinationResult",
    "ResponseHallucinationResult",
    # Signals
    "extract_no_evidence_signal",
    "extract_contradiction_signal",
    "extract_semantic_support_signal",
    "extract_model_disagreement_signal",
    "extract_numerical_inconsistency_signal",
    "extract_hallucination_signals",
    # Scoring
    "DEFAULT_HALLUCINATION_THRESHOLD",
    "HallucinationScorerConfig",
    "HallucinationScorer",
    # Detector
    "HallucinationDetector",
]

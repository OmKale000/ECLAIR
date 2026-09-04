"""Scoring and probability fusion logic for M08 Hallucination Detection.

Combines the 5 hallucination signals into a bounded probability score in [0.0, 1.0],
evaluates threshold-based flagging, and generates explanatory reasons.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from eclair.hallucination.models import (
    HallucinationReason,
    HallucinationSignals,
)

__all__ = [
    "DEFAULT_HALLUCINATION_THRESHOLD",
    "HallucinationScorerConfig",
    "HallucinationScorer",
]

DEFAULT_HALLUCINATION_THRESHOLD = 0.50
DEFAULT_SIGNAL_REASON_THRESHOLD = 0.35


class HallucinationScorerConfig(BaseModel):
    """Configuration for hallucination signal fusion weights and thresholds."""

    model_config = {"frozen": True, "extra": "forbid"}

    weight_no_evidence: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for absence of supporting evidence signal.",
    )
    weight_contradiction: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Weight for contradictory evidence signal.",
    )
    weight_low_semantic_support: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for low semantic support signal.",
    )
    weight_model_disagreement: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for cross-model disagreement signal.",
    )
    weight_numerical_inconsistency: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for numerical / entity disparity signal.",
    )
    hallucination_threshold: float = Field(
        default=DEFAULT_HALLUCINATION_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Probability threshold above which a claim is flagged as hallucination.",
    )
    signal_reason_threshold: float = Field(
        default=DEFAULT_SIGNAL_REASON_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Signal value threshold above which a reason is included in output.",
    )


class HallucinationScorer:
    """Combines hallucination signals into a structured probability and generates reasons."""

    def __init__(self, config: HallucinationScorerConfig | None = None) -> None:
        self.config = config or HallucinationScorerConfig()

    def compute_probability(self, signals: HallucinationSignals) -> float:
        """Compute the composite hallucination probability bounded in [0.0, 1.0]."""
        cfg = self.config

        # High-severity override: direct strong contradiction is a severe risk indicator
        if signals.contradiction_score >= 0.85:
            base_prob = max(
                0.85,
                signals.contradiction_score * 0.9 + signals.numerical_inconsistency_score * 0.1,
            )
            return max(0.0, min(1.0, round(base_prob, 4)))

        # High-severity override: strong numerical disparity on factual quantities
        if signals.numerical_inconsistency_score >= 0.80:
            base_prob = max(
                0.70,
                signals.numerical_inconsistency_score * 0.70
                + signals.no_evidence_score * 0.20
                + signals.low_semantic_support_score * 0.10,
            )
            return max(0.0, min(1.0, round(base_prob, 4)))

        # High-severity override: zero evidence with low semantic support
        if signals.no_evidence_score >= 0.9:
            if signals.low_semantic_support_score >= 0.7:
                base_prob = 0.70 + 0.15 * signals.model_disagreement_score
                return max(0.0, min(1.0, round(base_prob, 4)))

        # Weighted linear combination
        total_weight = (
            cfg.weight_no_evidence
            + cfg.weight_contradiction
            + cfg.weight_low_semantic_support
            + cfg.weight_model_disagreement
            + cfg.weight_numerical_inconsistency
        )
        if total_weight <= 0.0:
            total_weight = 1.0

        raw_prob = (
            signals.no_evidence_score * cfg.weight_no_evidence
            + signals.contradiction_score * cfg.weight_contradiction
            + signals.low_semantic_support_score * cfg.weight_low_semantic_support
            + signals.model_disagreement_score * cfg.weight_model_disagreement
            + signals.numerical_inconsistency_score * cfg.weight_numerical_inconsistency
        ) / total_weight

        return max(0.0, min(1.0, round(raw_prob, 4)))

    def is_flagged(self, probability: float) -> bool:
        """Determine if a calculated probability exceeds the hallucination threshold."""
        return probability >= self.config.hallucination_threshold

    def generate_reasons(
        self,
        signals: HallucinationSignals,
        probability: float,
        is_flagged: bool,
    ) -> list[str]:
        """Generate human-readable reasons explaining active hallucination signals.

        Guaranteed to produce at least one non-empty reason if is_flagged is True.
        """
        reasons: list[str] = []
        thresh = self.config.signal_reason_threshold

        if signals.contradiction_score >= thresh:
            contra_det = signals.details.get("contradiction", {}).get("reason")
            reason_text = (
                f"{HallucinationReason.CONTRADICTORY_EVIDENCE.value} ({contra_det})"
                if contra_det
                else HallucinationReason.CONTRADICTORY_EVIDENCE.value
            )
            reasons.append(reason_text)

        if signals.no_evidence_score >= thresh:
            no_ev_det = signals.details.get("no_evidence", {}).get("reason")
            reason_text = (
                f"{HallucinationReason.NO_EVIDENCE.value} ({no_ev_det})"
                if no_ev_det
                else HallucinationReason.NO_EVIDENCE.value
            )
            reasons.append(reason_text)

        if signals.numerical_inconsistency_score >= thresh:
            num_det = signals.details.get("numerical_inconsistency", {}).get("reason")
            reason_text = (
                f"{HallucinationReason.NUMERICAL_INCONSISTENCY.value} ({num_det})"
                if num_det
                else HallucinationReason.NUMERICAL_INCONSISTENCY.value
            )
            reasons.append(reason_text)

        if signals.low_semantic_support_score >= thresh:
            sem_det = signals.details.get("low_semantic_support", {}).get("reason")
            reason_text = (
                f"{HallucinationReason.LOW_SEMANTIC_SUPPORT.value} ({sem_det})"
                if sem_det
                else HallucinationReason.LOW_SEMANTIC_SUPPORT.value
            )
            reasons.append(reason_text)

        if signals.model_disagreement_score >= thresh:
            dis_det = signals.details.get("model_disagreement", {}).get("reason")
            reason_text = (
                f"{HallucinationReason.MODEL_DISAGREEMENT.value} ({dis_det})"
                if dis_det
                else HallucinationReason.MODEL_DISAGREEMENT.value
            )
            reasons.append(reason_text)

        if is_flagged and not reasons:
            reasons.append(
                f"Elevated composite hallucination probability ({probability:.2f} >= "
                f"{self.config.hallucination_threshold:.2f})"
            )

        return reasons

    def score(self, signals: HallucinationSignals) -> tuple[float, bool, list[str]]:
        """Score a set of hallucination signals.

        Returns:
            tuple of (hallucination_probability, is_hallucination_flag, reasons_list).
        """
        prob = self.compute_probability(signals)
        flagged = self.is_flagged(prob)
        reasons = self.generate_reasons(signals, prob, flagged)
        return prob, flagged, reasons

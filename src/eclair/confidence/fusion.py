"""Weighted fusion and aggregation logic for M10 Confidence Estimation.

Fuses the 5 reliability signals (verification, evidence, agreement, consistency,
model-confidence) into bounded RAW confidence in [0.0, 1.0] using configurable weights.

Reliability invariant (Spec sec.4.4, SHARED_CONTRACTS_REFERENCE sec.6):
M10 produces RAW confidence only. It does NOT calibrate confidence into ECS.
Calibration into ECS is strictly performed by M11.
"""

from __future__ import annotations

import numpy as np

from eclair.confidence.models import (
    ClaimConfidenceResult,
    ConfidenceBreakdown,
    ConfidenceFusionConfig,
    ConfidenceSignals,
    SignalContribution,
)

__all__ = [
    "ConfidenceFuser",
]

_SIGNAL_NAMES = [
    "verification",
    "evidence",
    "agreement",
    "consistency",
    "model_confidence",
]


class ConfidenceFuser:
    """Combines reliability signals into raw confidence scores with transparent breakdowns."""

    def __init__(self, config: ConfidenceFusionConfig | None = None) -> None:
        self.config = config or ConfidenceFusionConfig()

    def _get_configured_weight(self, signal_name: str) -> float:
        """Retrieve nominal configured weight for a specific signal."""
        cfg = self.config
        if signal_name == "verification":
            return cfg.weight_verification
        if signal_name == "evidence":
            return cfg.weight_evidence
        if signal_name == "agreement":
            return cfg.weight_agreement
        if signal_name == "consistency":
            return cfg.weight_consistency
        if signal_name == "model_confidence":
            return cfg.weight_model_confidence
        return 0.0

    def fuse(self, signals: ConfidenceSignals) -> tuple[float, ConfidenceBreakdown]:
        """Fuse available reliability signals into a single bounded RAW confidence score.

        When some signals are missing, weights are renormalized over the available signals
        to ensure full attribution without inventing unobserved signal values.

        Returns:
            tuple of (raw_confidence, confidence_breakdown).
        """
        available = signals.available_signals
        missing = signals.missing_signals

        if not available:
            # Zero signals available
            breakdown = ConfidenceBreakdown(
                contributions={
                    name: SignalContribution(
                        signal_name=name,
                        raw_value=None,
                        configured_weight=self._get_configured_weight(name),
                        effective_weight=0.0,
                        weighted_contribution=0.0,
                        is_available=False,
                    )
                    for name in _SIGNAL_NAMES
                },
                effective_weights={},
                total_raw_confidence=0.0,
                available_signals=[],
                missing_signals=_SIGNAL_NAMES.copy(),
            )
            return 0.0, breakdown

        # Calculate sum of weights for available signals
        available_names = list(available.keys())
        nominal_weights = [self._get_configured_weight(k) for k in available_names]
        weight_sum = sum(nominal_weights)

        effective_weights: dict[str, float] = {}
        if weight_sum > 0.0 and self.config.renormalize_missing:
            for k, w in zip(available_names, nominal_weights, strict=False):
                effective_weights[k] = w / weight_sum
        else:
            # Equal weighting fallback if all available weights are zero
            equal_w = 1.0 / len(available_names)
            for k in available_names:
                effective_weights[k] = equal_w

        # Compute weighted linear combination using NumPy
        sig_values = np.array([available[k] for k in available_names], dtype=np.float64)
        eff_w_values = np.array([effective_weights[k] for k in available_names], dtype=np.float64)
        raw_conf_val = float(np.dot(sig_values, eff_w_values))

        # Enforce strict bounds in [0.0, 1.0]
        raw_confidence = max(0.0, min(1.0, round(raw_conf_val, 4)))

        # Build detailed contribution records for all 5 signals
        contributions: dict[str, SignalContribution] = {}
        for name in _SIGNAL_NAMES:
            cfg_w = self._get_configured_weight(name)
            is_avail = name in available
            raw_val = available.get(name)
            eff_w = effective_weights.get(name, 0.0)
            weighted_contrib = (
                round(eff_w * raw_val, 4) if (is_avail and raw_val is not None) else 0.0
            )

            contributions[name] = SignalContribution(
                signal_name=name,
                raw_value=raw_val,
                configured_weight=cfg_w,
                effective_weight=round(eff_w, 4),
                weighted_contribution=weighted_contrib,
                is_available=is_avail,
            )

        breakdown = ConfidenceBreakdown(
            contributions=contributions,
            effective_weights={k: round(v, 4) for k, v in effective_weights.items()},
            total_raw_confidence=raw_confidence,
            available_signals=available_names,
            missing_signals=missing,
        )

        return raw_confidence, breakdown

    def aggregate_claim_confidences(
        self,
        claim_results: list[ClaimConfidenceResult],
        method: str | None = None,
    ) -> float:
        """Aggregate a collection of claim-level raw confidences into a response-level score.

        Supported methods:
            - 'mean': Arithmetic mean of claim confidences (default).
            - 'min': Minimum claim confidence (weakest-link reliability).
            - 'weighted': Mean weighted by inverse variance / position.
            - 'median': Median claim confidence.

        Returns:
            Bounded float in [0.0, 1.0].
        """
        if not claim_results:
            return 0.0

        agg_method = method or self.config.response_aggregation
        conf_array = np.array([cr.raw_confidence for cr in claim_results], dtype=np.float64)

        if agg_method == "min":
            result = float(np.min(conf_array))
        elif agg_method == "median":
            result = float(np.median(conf_array))
        elif agg_method == "weighted":
            # Linear decay weighting: earlier claims receive slightly higher priority
            n = len(conf_array)
            weights = np.linspace(1.0, 0.8, n)
            result = float(np.average(conf_array, weights=weights))
        else:
            # Default to arithmetic mean
            result = float(np.mean(conf_array))

        return max(0.0, min(1.0, round(result, 4)))

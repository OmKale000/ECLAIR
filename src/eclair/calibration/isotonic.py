"""Isotonic regression calibration for M11 ECS Calibration (Spec sec.M11).

Implements non-parametric monotonic calibration using isotonic regression from scikit-learn.

Reliability invariant (Spec sec.4.4):
Raw confidence is NOT calibrated ECS. Calibration requires fitting against empirical
observed correctness labels.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from sklearn.isotonic import IsotonicRegression

from eclair.calibration.metrics import evaluate_calibration, validate_calibration_inputs
from eclair.calibration.models import CalibrationMetrics
from eclair.exceptions import ContractValidationError, ModuleError

__all__ = ["IsotonicCalibrator"]


class IsotonicCalibrator:
    """Non-parametric isotonic regression calibrator for mapping raw confidence to ECS."""

    def __init__(self, y_min: float = 0.0, y_max: float = 1.0) -> None:
        """Initialize the isotonic calibrator.

        Args:
            y_min: Minimum calibrated output probability (default 0.0).
            y_max: Maximum calibrated output probability (default 1.0).
        """
        self._y_min = y_min
        self._y_max = y_max
        self._regressor = IsotonicRegression(
            y_min=self._y_min,
            y_max=self._y_max,
            out_of_bounds="clip",
            increasing=True,
        )
        self._is_fitted: bool = False
        self._sample_count: int = 0

    @property
    def is_fitted(self) -> bool:
        """Whether the calibrator has been fitted with observed correctness."""
        return self._is_fitted

    @property
    def sample_count(self) -> int:
        """Number of training samples used during fitting."""
        return self._sample_count

    def fit(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
    ) -> IsotonicCalibrator:
        """Fit the isotonic regression model on observed (confidence, correctness) pairs.

        Args:
            confidences: Sequence of raw confidence scores in [0.0, 1.0].
            labels: Sequence of binary observed correctness outcomes.

        Returns:
            Self (fitted instance).

        Raises:
            ContractValidationError: If inputs are invalid or mismatched.
        """
        confs_arr, labels_arr = validate_calibration_inputs(confidences, labels)

        # Fit isotonic regression
        self._regressor.fit(confs_arr, labels_arr)
        self._is_fitted = True
        self._sample_count = len(confs_arr)
        return self

    def calibrate(self, raw_confidence: float) -> float:
        """Calibrate a single raw confidence score into a calibrated ECS.

        Args:
            raw_confidence: Raw confidence score in [0.0, 1.0].

        Returns:
            Calibrated Epistemic Confidence Score in [0.0, 1.0].

        Raises:
            ModuleError: If called before the model is fitted with observed correctness.
            ContractValidationError: If raw_confidence is not a valid float in [0.0, 1.0].
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot calibrate confidence: IsotonicCalibrator is not fitted with observed correctness (Spec sec.4.4).",
                code="calibrator_not_fitted",
            )

        if not isinstance(raw_confidence, (int, float, np.number)) or isinstance(raw_confidence, bool):
            raise ContractValidationError(
                f"raw_confidence must be a float, got {type(raw_confidence).__name__} ({raw_confidence!r}).",
                code="invalid_confidence_type",
            )

        val = float(raw_confidence)
        if np.isnan(val) or np.isinf(val) or val < 0.0 or val > 1.0:
            raise ContractValidationError(
                f"raw_confidence must be in [0.0, 1.0], got {raw_confidence}.",
                code="invalid_confidence_range",
            )

        calibrated = float(self._regressor.predict([val])[0])
        return float(np.clip(calibrated, 0.0, 1.0))

    def calibrate_batch(self, raw_confidences: Sequence[float]) -> list[float]:
        """Calibrate a batch of raw confidence scores.

        Args:
            raw_confidences: Sequence of raw confidence scores in [0.0, 1.0].

        Returns:
            List of calibrated ECS values in [0.0, 1.0].

        Raises:
            ModuleError: If called before the model is fitted.
            ContractValidationError: If any confidence score is invalid.
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot calibrate confidence: IsotonicCalibrator is not fitted with observed correctness (Spec sec.4.4).",
                code="calibrator_not_fitted",
            )

        if raw_confidences is None:
            raise ContractValidationError("raw_confidences cannot be None.", code="input_none")

        clean_confs: list[float] = []
        for idx, c in enumerate(raw_confidences):
            if not isinstance(c, (int, float, np.number)) or isinstance(c, bool):
                raise ContractValidationError(
                    f"raw_confidence at index {idx} must be a float, got {type(c).__name__} ({c!r}).",
                    code="invalid_confidence_type",
                )
            val = float(c)
            if np.isnan(val) or np.isinf(val) or val < 0.0 or val > 1.0:
                raise ContractValidationError(
                    f"raw_confidence at index {idx} must be in [0.0, 1.0], got {c}.",
                    code="invalid_confidence_range",
                )
            clean_confs.append(val)

        if not clean_confs:
            return []

        preds = self._regressor.predict(clean_confs)
        return [float(np.clip(p, 0.0, 1.0)) for p in preds]

    def evaluate(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """Evaluate calibration performance on a test/validation set.

        Args:
            confidences: Sequence of raw confidence scores.
            labels: Sequence of binary observed correctness outcomes.
            n_bins: Number of bins for ECE/MCE computation.

        Returns:
            CalibrationMetrics evaluated on the calibrated probabilities.
        """
        calibrated_confs = self.calibrate_batch(confidences)
        return evaluate_calibration(
            confidences=calibrated_confs,
            labels=labels,
            n_bins=n_bins,
            method="isotonic",
            details={
                "training_sample_count": self._sample_count,
            },
        )

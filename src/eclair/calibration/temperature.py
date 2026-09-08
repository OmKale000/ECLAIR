"""Parametric calibration (Platt/Sigmoid scaling and Temperature scaling) for M11 (Spec sec.M11).

Implements:
- Platt scaling (Sigmoid calibration via Logistic Regression / Platt parameters)
- Temperature scaling (Single temperature parameter optimization over logits)

Reliability invariant (Spec sec.4.4):
Raw confidence is NOT calibrated ECS. Calibration requires fitting against empirical
observed correctness labels.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression

from eclair.calibration.metrics import evaluate_calibration, validate_calibration_inputs
from eclair.calibration.models import CalibrationMetrics
from eclair.exceptions import ContractValidationError, ModuleError

__all__ = ["PlattCalibrator", "SigmoidCalibrator", "TemperatureCalibrator"]


def _safe_logit(p: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """Compute numerical logit = ln(p / (1 - p)) with clipping to avoid infinities."""
    p_clipped = np.clip(p, eps, 1.0 - eps)
    return np.log(p_clipped / (1.0 - p_clipped))


def _sigmoid(z: np.ndarray | float) -> np.ndarray | float:
    """Numerically stable sigmoid function."""
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


class PlattCalibrator:
    """Platt / Sigmoid scaling calibrator.

    Fits a logistic sigmoid model mapping raw confidence / logits to calibrated probabilities:
        P(y = 1 | p) = sigmoid(a * logit(p) + b)
    """

    def __init__(self) -> None:
        self._model = LogisticRegression(solver="lbfgs", C=1.0)
        self._is_fitted: bool = False
        self._sample_count: int = 0
        self._a: float = 1.0
        self._b: float = 0.0

    @property
    def is_fitted(self) -> bool:
        """Whether the calibrator has been fitted with observed correctness."""
        return self._is_fitted

    @property
    def sample_count(self) -> int:
        """Number of training samples used during fitting."""
        return self._sample_count

    @property
    def slope(self) -> float:
        """Learned slope parameter a."""
        return self._a

    @property
    def intercept(self) -> float:
        """Learned intercept parameter b."""
        return self._b

    def fit(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
    ) -> PlattCalibrator:
        """Fit Platt scaling model on observed (confidence, correctness) pairs.

        Args:
            confidences: Sequence of raw confidence scores in [0.0, 1.0].
            labels: Sequence of binary observed correctness outcomes.

        Returns:
            Self (fitted instance).

        Raises:
            ContractValidationError: If inputs are invalid or mismatched.
        """
        confs_arr, labels_arr = validate_calibration_inputs(confidences, labels)

        # If all labels are of single class, handle deterministically
        unique_labels = np.unique(labels_arr)
        if len(unique_labels) < 2:
            # Single class: constant predictor
            single_val = float(unique_labels[0])
            self._a = 0.0
            self._b = -10.0 if single_val == 0.0 else 10.0
            self._is_fitted = True
            self._sample_count = len(confs_arr)
            return self

        # Transform confidences to logit space
        logits = _safe_logit(confs_arr).reshape(-1, 1)

        self._model.fit(logits, labels_arr)
        self._a = float(self._model.coef_[0][0])
        self._b = float(self._model.intercept_[0])
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
            ModuleError: If called before the model is fitted.
            ContractValidationError: If raw_confidence is invalid.
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot calibrate confidence: PlattCalibrator is not fitted with observed correctness (Spec sec.4.4).",
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

        logit = float(_safe_logit(np.array([val]))[0])
        calibrated = float(_sigmoid(self._a * logit + self._b))
        return float(np.clip(calibrated, 0.0, 1.0))

    def calibrate_batch(self, raw_confidences: Sequence[float]) -> list[float]:
        """Calibrate a batch of raw confidence scores.

        Args:
            raw_confidences: Sequence of raw confidence scores in [0.0, 1.0].

        Returns:
            List of calibrated ECS values in [0.0, 1.0].
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot calibrate confidence: PlattCalibrator is not fitted with observed correctness (Spec sec.4.4).",
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

        logits = _safe_logit(np.array(clean_confs, dtype=np.float64))
        calibrated = _sigmoid(self._a * logits + self._b)
        return [float(np.clip(p, 0.0, 1.0)) for p in calibrated]

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
            method="platt",
            details={
                "a_slope": self._a,
                "b_intercept": self._b,
                "training_sample_count": self._sample_count,
            },
        )


# Alias SigmoidCalibrator to PlattCalibrator
SigmoidCalibrator = PlattCalibrator


class TemperatureCalibrator:
    """Temperature scaling calibrator.

    Scales confidence logits by a single learned positive temperature parameter T:
        P_cal(p) = sigmoid(logit(p) / T)
    """

    def __init__(self) -> None:
        self._temperature: float = 1.0
        self._is_fitted: bool = False
        self._sample_count: int = 0

    @property
    def is_fitted(self) -> bool:
        """Whether the calibrator has been fitted with observed correctness."""
        return self._is_fitted

    @property
    def temperature(self) -> float:
        """Learned temperature parameter T (> 0)."""
        return self._temperature

    @property
    def sample_count(self) -> int:
        """Number of training samples used during fitting."""
        return self._sample_count

    def fit(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
    ) -> TemperatureCalibrator:
        """Fit the temperature parameter T by minimizing negative log-likelihood (NLL).

        Args:
            confidences: Sequence of raw confidence scores in [0.0, 1.0].
            labels: Sequence of binary observed correctness outcomes.

        Returns:
            Self (fitted instance).

        Raises:
            ContractValidationError: If inputs are invalid or mismatched.
        """
        confs_arr, labels_arr = validate_calibration_inputs(confidences, labels)
        logits = _safe_logit(confs_arr)

        # Optimize T > 0 by grid search / line search over log(T)
        best_t = 1.0
        best_nll = float("inf")
        eps = 1e-7

        # Grid search over candidate temperatures in [0.05, 10.0]
        candidates = np.logspace(-1.3, 1.0, 100)
        for t in candidates:
            scaled_logits = logits / t
            probs = _sigmoid(scaled_logits)
            probs = np.clip(probs, eps, 1.0 - eps)
            # Binary cross entropy / NLL
            nll = -float(np.mean(labels_arr * np.log(probs) + (1 - labels_arr) * np.log(1.0 - probs)))
            if nll < best_nll:
                best_nll = nll
                best_t = float(t)

        self._temperature = best_t
        self._is_fitted = True
        self._sample_count = len(confs_arr)
        return self

    def calibrate(self, raw_confidence: float) -> float:
        """Calibrate a single raw confidence score using learned temperature.

        Args:
            raw_confidence: Raw confidence score in [0.0, 1.0].

        Returns:
            Calibrated Epistemic Confidence Score in [0.0, 1.0].
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot calibrate confidence: TemperatureCalibrator is not fitted with observed correctness (Spec sec.4.4).",
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

        logit = float(_safe_logit(np.array([val]))[0])
        calibrated = float(_sigmoid(logit / self._temperature))
        return float(np.clip(calibrated, 0.0, 1.0))

    def calibrate_batch(self, raw_confidences: Sequence[float]) -> list[float]:
        """Calibrate a batch of raw confidence scores."""
        if not self._is_fitted:
            raise ModuleError(
                "Cannot calibrate confidence: TemperatureCalibrator is not fitted with observed correctness (Spec sec.4.4).",
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

        logits = _safe_logit(np.array(clean_confs, dtype=np.float64))
        calibrated = _sigmoid(logits / self._temperature)
        return [float(np.clip(p, 0.0, 1.0)) for p in calibrated]

    def evaluate(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """Evaluate calibration performance on a test/validation set."""
        calibrated_confs = self.calibrate_batch(confidences)
        return evaluate_calibration(
            confidences=calibrated_confs,
            labels=labels,
            n_bins=n_bins,
            method="temperature",
            details={
                "temperature": self._temperature,
                "training_sample_count": self._sample_count,
            },
        )

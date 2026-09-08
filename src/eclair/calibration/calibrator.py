"""ECS Calibrator facade for M11 (Spec sec.M11, sec.4.4).

Provides the unified, high-level calibrator for converting M10 raw confidence
into a statistically meaningful Epistemic Confidence Score (ECS), evaluating
ECE and Brier scores, and generating reliability diagrams.

Reliability invariant (Spec sec.4.4, SHARED_CONTRACTS_REFERENCE sec.6):
Raw confidence is NOT calibrated ECS. Calibrated ECS is produced ONLY by M11
after calibration against observed correctness. If no observed correctness
training data is provided, calibration cannot be claimed.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from eclair.calibration.isotonic import IsotonicCalibrator
from eclair.calibration.metrics import (
    compute_brier_score,
    compute_ece,
    compute_mce,
    validate_calibration_inputs,
)
from eclair.calibration.models import (
    CalibrationMethod,
    CalibrationMetrics,
    ECSCalibrationResult,
    ReliabilityDiagramData,
)
from eclair.calibration.reliability import compute_reliability_diagram_data
from eclair.calibration.temperature import PlattCalibrator, TemperatureCalibrator
from eclair.contracts.confidence import ConfidenceResult
from eclair.exceptions import ContractValidationError, ModuleError

__all__ = ["ECSCalibrator"]


class ECSCalibrator:
    """High-level Epistemic Confidence Score (ECS) Calibrator."""

    def __init__(
        self,
        method: str | CalibrationMethod = CalibrationMethod.PLATT,
    ) -> None:
        """Initialize the ECS Calibrator.

        Args:
            method: Calibration method ('platt', 'sigmoid', 'isotonic', 'temperature').
                Default is 'platt'.
        """
        self._method_str = (
            method.value if isinstance(method, CalibrationMethod) else str(method).lower()
        )
        self._calibrator = self._create_inner_calibrator(self._method_str)
        self._is_fitted: bool = False
        self._training_sample_count: int = 0

    @property
    def method(self) -> str:
        """The active calibration method name."""
        return self._method_str

    @property
    def is_fitted(self) -> bool:
        """Whether the calibrator has been fitted with observed correctness."""
        return self._is_fitted

    @property
    def sample_count(self) -> int:
        """Number of training samples used during fitting."""
        return self._training_sample_count

    def _create_inner_calibrator(self, method: str) -> Any:
        """Instantiate the underlying calibration algorithm."""
        if method in ("platt", "sigmoid"):
            return PlattCalibrator()
        elif method == "isotonic":
            return IsotonicCalibrator()
        elif method == "temperature":
            return TemperatureCalibrator()
        else:
            raise ContractValidationError(
                f"Unsupported calibration method: {method!r}. Supported methods: 'platt', 'isotonic', 'temperature'.",
                code="unsupported_calibration_method",
            )

    def fit(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
        method: str | CalibrationMethod | None = None,
    ) -> ECSCalibrator:
        """Fit the calibration model on paired confidence scores and observed correctness labels.

        Args:
            confidences: Sequence of raw confidence scores in [0.0, 1.0].
            labels: Sequence of binary observed correctness outcomes (1 for correct, 0 for incorrect).
            method: Optional override for the calibration method.

        Returns:
            Self (fitted ECSCalibrator instance).

        Raises:
            ContractValidationError: If inputs are invalid, empty, or mismatched.
        """
        if method is not None:
            self._method_str = (
                method.value if isinstance(method, CalibrationMethod) else str(method).lower()
            )
            self._calibrator = self._create_inner_calibrator(self._method_str)

        confs_arr, labels_arr = validate_calibration_inputs(confidences, labels)
        self._calibrator.fit(confs_arr, labels_arr)
        self._is_fitted = True
        self._training_sample_count = len(confs_arr)
        return self

    def calibrate(
        self,
        confidence: float | Any,
    ) -> ECSCalibrationResult:
        """Convert raw confidence into a calibrated Epistemic Confidence Score (ECS).

        Accepts:
            - float: Raw confidence value in [0.0, 1.0].
            - ConfidenceResult: Canonical M01 contract.
            - ClaimConfidenceResult: M10 claim-level result.
            - ResponseConfidenceResult: M10 response-level result.

        Returns:
            An :class:`ECSCalibrationResult` containing both raw confidence and calibrated ECS.

        Raises:
            ModuleError: If called before fitting with observed correctness.
            ContractValidationError: If confidence input is invalid.
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot claim calibrated ECS without observed correctness data (Spec sec.4.4). "
                "Calibrator must be fitted before calibration.",
                code="calibrator_not_fitted",
            )

        claim_id: str | None = None
        raw_val: float

        # Handle various input formats
        if isinstance(confidence, (int, float, np.number)) and not isinstance(confidence, bool):
            raw_val = float(confidence)
        elif hasattr(confidence, "raw_confidence"):
            raw_val = float(confidence.raw_confidence)
            if hasattr(confidence, "claim_id"):
                claim_id = getattr(confidence, "claim_id")
        else:
            raise ContractValidationError(
                f"Unsupported confidence input type: {type(confidence).__name__} ({confidence!r}).",
                code="invalid_confidence_input",
            )

        if np.isnan(raw_val) or np.isinf(raw_val) or raw_val < 0.0 or raw_val > 1.0:
            raise ContractValidationError(
                f"Raw confidence must be in [0.0, 1.0], got {raw_val}.",
                code="invalid_confidence_range",
            )

        calibrated_ecs = self._calibrator.calibrate(raw_val)
        calibrated_ecs = float(np.clip(calibrated_ecs, 0.0, 1.0))

        return ECSCalibrationResult(
            raw_confidence=raw_val,
            calibrated_ecs=calibrated_ecs,
            method=self._method_str,
            is_calibrated=True,
            claim_id=claim_id,
            details={
                "training_sample_count": self._training_sample_count,
                "delta": float(calibrated_ecs - raw_val),
            },
        )

    def calibrate_result(self, confidence_result: ConfidenceResult) -> ConfidenceResult:
        """Calibrate an M01 ConfidenceResult and return a new instance with calibrated_ecs populated.

        Args:
            confidence_result: M01 ConfidenceResult with raw_confidence.

        Returns:
            A new ConfidenceResult with both raw_confidence and calibrated_ecs populated.

        Raises:
            ModuleError: If called before fitting.
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot claim calibrated ECS without observed correctness data (Spec sec.4.4).",
                code="calibrator_not_fitted",
            )

        if not isinstance(confidence_result, ConfidenceResult):
            raise ContractValidationError(
                f"Expected ConfidenceResult, got {type(confidence_result).__name__}",
                code="invalid_contract_type",
            )

        calibrated_ecs = self._calibrator.calibrate(confidence_result.raw_confidence)
        return ConfidenceResult(
            raw_confidence=confidence_result.raw_confidence,
            calibrated_ecs=float(np.clip(calibrated_ecs, 0.0, 1.0)),
        )

    def calibrate_batch(self, raw_confidences: Sequence[float]) -> list[float]:
        """Calibrate a batch of raw confidence scores into calibrated ECS values.

        Args:
            raw_confidences: Sequence of raw confidence scores.

        Returns:
            List of calibrated ECS floats in [0.0, 1.0].
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot claim calibrated ECS without observed correctness data (Spec sec.4.4).",
                code="calibrator_not_fitted",
            )

        return self._calibrator.calibrate_batch(raw_confidences)

    def evaluate(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """Evaluate calibration quality (ECE, Brier score, MCE) on a test/validation dataset.

        Args:
            confidences: Sequence of raw confidence scores.
            labels: Sequence of binary observed correctness outcomes.
            n_bins: Number of bins for ECE and MCE computation.

        Returns:
            A validated :class:`CalibrationMetrics` object.
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot evaluate calibration: Calibrator is not fitted with observed correctness (Spec sec.4.4).",
                code="calibrator_not_fitted",
            )

        calibrated_scores = self.calibrate_batch(confidences)
        ece = compute_ece(calibrated_scores, labels, n_bins=n_bins)
        brier = compute_brier_score(calibrated_scores, labels)
        mce = compute_mce(calibrated_scores, labels, n_bins=n_bins)

        # Uncalibrated baseline for comparison
        raw_ece = compute_ece(confidences, labels, n_bins=n_bins)
        raw_brier = compute_brier_score(confidences, labels)

        return CalibrationMetrics(
            ece=ece,
            brier_score=brier,
            mce=mce,
            sample_count=len(confidences),
            bin_count=n_bins,
            method=self._method_str,
            details={
                "raw_ece": raw_ece,
                "raw_brier_score": raw_brier,
                "ece_improvement": float(raw_ece - ece),
                "brier_improvement": float(raw_brier - brier),
                "training_sample_count": self._training_sample_count,
            },
        )

    def get_reliability_data(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
        n_bins: int = 10,
    ) -> ReliabilityDiagramData:
        """Generate structured reliability diagram data for the calibrated predictions.

        Args:
            confidences: Sequence of raw confidence scores.
            labels: Sequence of binary observed correctness outcomes.
            n_bins: Number of confidence bins.

        Returns:
            A :class:`ReliabilityDiagramData` instance.
        """
        if not self._is_fitted:
            raise ModuleError(
                "Cannot generate reliability data: Calibrator is not fitted with observed correctness (Spec sec.4.4).",
                code="calibrator_not_fitted",
            )

        calibrated_scores = self.calibrate_batch(confidences)
        return compute_reliability_diagram_data(calibrated_scores, labels, n_bins=n_bins)

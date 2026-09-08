"""M11 — ECS Calibration module for ECLAIR (Spec sec.M11, sec.4.4).

Converts raw fused confidence from M10 into a statistically meaningful
Epistemic Confidence Score (ECS), calculates Expected Calibration Error (ECE)
and Brier Score, and produces reliability diagrams.

Reliability invariant (Spec sec.4.4):
Raw confidence is NOT calibrated ECS. Calibrated ECS is produced only by M11
after calibration against observed correctness.
"""

from __future__ import annotations

from eclair.calibration.calibrator import ECSCalibrator
from eclair.calibration.isotonic import IsotonicCalibrator
from eclair.calibration.metrics import (
    compute_brier_score,
    compute_ece,
    compute_mce,
    evaluate_calibration,
    validate_calibration_inputs,
)
from eclair.calibration.models import (
    CalibrationBin,
    CalibrationDataset,
    CalibrationMethod,
    CalibrationMetrics,
    ECSCalibrationResult,
    ReliabilityDiagramData,
)
from eclair.calibration.reliability import (
    ReliabilityAnalyzer,
    compute_reliability_diagram_data,
    plot_reliability_diagram,
)
from eclair.calibration.temperature import (
    PlattCalibrator,
    SigmoidCalibrator,
    TemperatureCalibrator,
)

__all__ = [
    "CalibrationMethod",
    "CalibrationBin",
    "CalibrationMetrics",
    "ReliabilityDiagramData",
    "ECSCalibrationResult",
    "CalibrationDataset",
    "ECSCalibrator",
    "IsotonicCalibrator",
    "PlattCalibrator",
    "SigmoidCalibrator",
    "TemperatureCalibrator",
    "ReliabilityAnalyzer",
    "compute_brier_score",
    "compute_ece",
    "compute_mce",
    "evaluate_calibration",
    "compute_reliability_diagram_data",
    "plot_reliability_diagram",
    "validate_calibration_inputs",
]

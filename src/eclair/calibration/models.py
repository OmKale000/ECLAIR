"""Data models for M11 ECS Calibration.

Defines the data structures for calibration methods, calibration bins,
calibration metrics (ECE, Brier score, MCE), reliability diagrams,
calibrated ECS results, and calibration datasets.

Reliability invariant (Spec sec.4.4, SHARED_CONTRACTS_REFERENCE sec.6):
Raw confidence is NOT calibrated ECS. Calibrated ECS is produced ONLY by M11
after calibration against observed correctness.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from eclair.contracts.confidence import ConfidenceResult

__all__ = [
    "CalibrationMethod",
    "CalibrationBin",
    "CalibrationMetrics",
    "ReliabilityDiagramData",
    "ECSCalibrationResult",
    "CalibrationDataset",
]


class CalibrationMethod(str, Enum):
    """Supported calibration algorithms in M11."""

    PLATT = "platt"
    SIGMOID = "sigmoid"
    ISOTONIC = "isotonic"
    TEMPERATURE = "temperature"


class CalibrationBin(BaseModel):
    """A single confidence bin in a calibration/reliability diagram."""

    model_config = {"extra": "forbid"}

    bin_index: int = Field(
        ...,
        ge=0,
        description="Zero-based index of this bin.",
    )
    lower_bound: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Lower confidence threshold for this bin (inclusive, or > 0 for non-first bins).",
    )
    upper_bound: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Upper confidence threshold for this bin (inclusive).",
    )
    sample_count: int = Field(
        ...,
        ge=0,
        description="Number of samples falling into this confidence bin.",
    )
    mean_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average predicted/calibrated confidence of samples in this bin.",
    )
    accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Empirical accuracy (fraction of positive observed correctness) in this bin.",
    )
    calibration_error: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Absolute calibration error |accuracy - mean_confidence| for this bin.",
    )


class CalibrationMetrics(BaseModel):
    """Comprehensive calibration evaluation metrics (Spec sec.M11, sec.M18)."""

    model_config = {"extra": "forbid"}

    ece: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Expected Calibration Error across all bins.",
    )
    brier_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Brier Score (mean squared error between confidence and correctness).",
    )
    mce: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Maximum Calibration Error across all non-empty bins.",
    )
    sample_count: int = Field(
        ...,
        ge=0,
        description="Total number of evaluated samples.",
    )
    bin_count: int = Field(
        ...,
        ge=1,
        description="Number of bins used for ECE and MCE computation.",
    )
    method: str = Field(
        ...,
        description="Calibration method used ('platt', 'isotonic', 'temperature', 'uncalibrated', etc.).",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional diagnostic and configuration metadata.",
    )


class ReliabilityDiagramData(BaseModel):
    """Structured data required to render reliability diagrams and calibration curves."""

    model_config = {"extra": "forbid"}

    bins: list[CalibrationBin] = Field(
        default_factory=list,
        description="Detailed per-bin calibration statistics.",
    )
    bin_edges: list[float] = Field(
        default_factory=list,
        description="Boundary edges defining the confidence bins in [0.0, 1.0].",
    )
    bin_accuracies: list[float] = Field(
        default_factory=list,
        description="Empirical accuracy for each bin.",
    )
    bin_confidences: list[float] = Field(
        default_factory=list,
        description="Mean confidence for each bin.",
    )
    bin_counts: list[int] = Field(
        default_factory=list,
        description="Sample count in each bin.",
    )
    ece: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Expected Calibration Error for this diagram.",
    )
    brier_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Brier score for this diagram.",
    )
    mce: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Maximum Calibration Error for this diagram.",
    )
    overall_accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall empirical accuracy across all samples.",
    )
    overall_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall mean confidence across all samples.",
    )
    sample_count: int = Field(
        ...,
        ge=0,
        description="Total sample count represented in the diagram.",
    )


class ECSCalibrationResult(BaseModel):
    """Result of calibrating raw confidence into an Epistemic Confidence Score (ECS)."""

    model_config = {"extra": "forbid"}

    raw_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Original raw confidence from M10.",
    )
    calibrated_ecs: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calibrated Epistemic Confidence Score produced by M11.",
    )
    method: str = Field(
        ...,
        description="Calibration algorithm applied ('platt', 'isotonic', 'temperature', etc.).",
    )
    is_calibrated: bool = Field(
        default=True,
        description="Whether calibration was actually performed against observed correctness.",
    )
    claim_id: str | None = Field(
        default=None,
        description="Optional claim identifier if calibrating a claim-level score.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic metadata (e.g. model parameters, raw-to-calibrated delta).",
    )

    def to_confidence_result(self) -> ConfidenceResult:
        """Convert to the canonical M01 ConfidenceResult contract.

        Populates both ``raw_confidence`` and ``calibrated_ecs``.
        """
        return ConfidenceResult(
            raw_confidence=self.raw_confidence,
            calibrated_ecs=self.calibrated_ecs,
        )


class CalibrationDataset(BaseModel):
    """Validated dataset of paired confidence scores and observed correctness labels."""

    model_config = {"extra": "forbid"}

    confidences: list[float] = Field(
        ...,
        description="List of raw or predicted confidence scores in [0.0, 1.0].",
    )
    labels: list[int] = Field(
        ...,
        description="List of binary observed correctness labels (1 for correct, 0 for incorrect).",
    )

    @field_validator("confidences")
    @classmethod
    def validate_confidences(cls, v: list[float]) -> list[float]:
        if not v:
            raise ValueError("Confidences list cannot be empty.")
        for i, val in enumerate(v):
            if not isinstance(val, (int, float)):
                raise ValueError(f"Confidence at index {i} is not a number: {val!r}")
            if val < 0.0 or val > 1.0:
                raise ValueError(f"Confidence at index {i} must be in [0.0, 1.0], got {val}")
        return [float(x) for x in v]

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("Labels list cannot be empty.")
        for i, val in enumerate(v):
            if val not in (0, 1):
                raise ValueError(f"Label at index {i} must be binary 0 or 1, got {val!r}")
        return v

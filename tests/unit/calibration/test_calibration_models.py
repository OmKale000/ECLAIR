"""Unit tests for M11 calibration data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair.calibration.models import (
    CalibrationBin,
    CalibrationDataset,
    CalibrationMethod,
    CalibrationMetrics,
    ECSCalibrationResult,
    ReliabilityDiagramData,
)
from eclair.contracts.confidence import ConfidenceResult


def test_calibration_method_enum() -> None:
    assert CalibrationMethod.PLATT == "platt"
    assert CalibrationMethod.SIGMOID == "sigmoid"
    assert CalibrationMethod.ISOTONIC == "isotonic"
    assert CalibrationMethod.TEMPERATURE == "temperature"


def test_calibration_bin_valid() -> None:
    bin_obj = CalibrationBin(
        bin_index=0,
        lower_bound=0.0,
        upper_bound=0.1,
        sample_count=5,
        mean_confidence=0.05,
        accuracy=0.2,
        calibration_error=0.15,
    )
    assert bin_obj.bin_index == 0
    assert bin_obj.sample_count == 5
    assert bin_obj.calibration_error == pytest.approx(0.15)


def test_calibration_bin_validation_failures() -> None:
    with pytest.raises(ValidationError):
        CalibrationBin(
            bin_index=-1,  # negative index
            lower_bound=0.0,
            upper_bound=0.1,
            sample_count=5,
            mean_confidence=0.05,
            accuracy=0.2,
            calibration_error=0.15,
        )

    with pytest.raises(ValidationError):
        CalibrationBin(
            bin_index=0,
            lower_bound=-0.1,  # out of bounds
            upper_bound=0.1,
            sample_count=5,
            mean_confidence=0.05,
            accuracy=0.2,
            calibration_error=0.15,
        )


def test_calibration_metrics() -> None:
    metrics = CalibrationMetrics(
        ece=0.05,
        brier_score=0.12,
        mce=0.15,
        sample_count=100,
        bin_count=10,
        method="platt",
        details={"info": "test"},
    )
    assert metrics.ece == 0.05
    assert metrics.brier_score == 0.12
    assert metrics.sample_count == 100
    assert metrics.method == "platt"


def test_reliability_diagram_data() -> None:
    data = ReliabilityDiagramData(
        bins=[],
        bin_edges=[0.0, 0.5, 1.0],
        bin_accuracies=[0.4, 0.8],
        bin_confidences=[0.3, 0.85],
        bin_counts=[10, 15],
        ece=0.07,
        brier_score=0.14,
        mce=0.10,
        overall_accuracy=0.64,
        overall_confidence=0.63,
        sample_count=25,
    )
    assert data.sample_count == 25
    assert len(data.bin_edges) == 3


def test_ecs_calibration_result_conversion() -> None:
    res = ECSCalibrationResult(
        raw_confidence=0.90,
        calibrated_ecs=0.73,
        method="platt",
        is_calibrated=True,
        claim_id="claim-001",
        details={"delta": -0.17},
    )
    assert res.raw_confidence == 0.90
    assert res.calibrated_ecs == 0.73
    assert res.claim_id == "claim-001"

    conf_contract = res.to_confidence_result()
    assert isinstance(conf_contract, ConfidenceResult)
    assert conf_contract.raw_confidence == 0.90
    assert conf_contract.calibrated_ecs == 0.73


def test_calibration_dataset_valid() -> None:
    ds = CalibrationDataset(
        confidences=[0.1, 0.5, 0.9],
        labels=[0, 1, 1],
    )
    assert ds.confidences == [0.1, 0.5, 0.9]
    assert ds.labels == [0, 1, 1]


def test_calibration_dataset_invalid() -> None:
    with pytest.raises(ValidationError):
        CalibrationDataset(confidences=[], labels=[])

    with pytest.raises(ValidationError):
        CalibrationDataset(confidences=[1.5], labels=[1])

    with pytest.raises(ValidationError):
        CalibrationDataset(confidences=[0.5], labels=[2])

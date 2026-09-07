"""Unit tests for Platt (Sigmoid) scaling and Temperature scaling."""

from __future__ import annotations

import pytest

from eclair.calibration.temperature import PlattCalibrator, SigmoidCalibrator, TemperatureCalibrator
from eclair.exceptions import ContractValidationError, ModuleError


def test_platt_calibrator_unfitted_raises() -> None:
    cal = PlattCalibrator()
    assert not cal.is_fitted

    with pytest.raises(ModuleError, match="not fitted"):
        cal.calibrate(0.7)

    with pytest.raises(ModuleError, match="not fitted"):
        cal.calibrate_batch([0.7])


def test_platt_calibrator_fit_and_calibrate() -> None:
    cal = PlattCalibrator()
    confs = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
    labels = [0, 0, 0, 1, 1, 1]

    cal.fit(confs, labels)
    assert cal.is_fitted
    assert cal.sample_count == 6

    ecs_low = cal.calibrate(0.2)
    ecs_high = cal.calibrate(0.8)

    assert 0.0 <= ecs_low <= 1.0
    assert 0.0 <= ecs_high <= 1.0
    assert ecs_low < ecs_high


def test_sigmoid_calibrator_alias() -> None:
    assert SigmoidCalibrator is PlattCalibrator
    cal = SigmoidCalibrator()
    cal.fit([0.2, 0.8], [0, 1])
    assert cal.is_fitted


def test_temperature_calibrator_fit_and_calibrate() -> None:
    cal = TemperatureCalibrator()
    assert not cal.is_fitted

    with pytest.raises(ModuleError, match="not fitted"):
        cal.calibrate(0.8)

    # Overconfident model predictions: extreme confidences but mixed accuracy
    confs = [0.05, 0.1, 0.2, 0.8, 0.9, 0.95]
    labels = [0, 0, 1, 0, 1, 1]

    cal.fit(confs, labels)
    assert cal.is_fitted
    assert cal.sample_count == 6
    assert cal.temperature > 0.0

    calibrated_val = cal.calibrate(0.9)
    assert 0.0 <= calibrated_val <= 1.0


def test_parametric_calibrators_validation() -> None:
    platt = PlattCalibrator()
    platt.fit([0.2, 0.8], [0, 1])

    with pytest.raises(ContractValidationError):
        platt.calibrate(-0.5)

    with pytest.raises(ContractValidationError):
        platt.calibrate(1.5)

    temp = TemperatureCalibrator()
    temp.fit([0.2, 0.8], [0, 1])

    with pytest.raises(ContractValidationError):
        temp.calibrate(-0.5)

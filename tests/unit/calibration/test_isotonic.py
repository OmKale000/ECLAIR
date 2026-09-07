"""Unit tests for Isotonic regression calibration."""

from __future__ import annotations

import pytest

from eclair.calibration.isotonic import IsotonicCalibrator
from eclair.exceptions import ContractValidationError, ModuleError


def test_isotonic_calibrator_unfitted_raises() -> None:
    calibrator = IsotonicCalibrator()
    assert not calibrator.is_fitted
    assert calibrator.sample_count == 0

    with pytest.raises(ModuleError, match="not fitted"):
        calibrator.calibrate(0.8)

    with pytest.raises(ModuleError, match="not fitted"):
        calibrator.calibrate_batch([0.8, 0.9])


def test_isotonic_calibrator_fit_and_calibrate() -> None:
    calibrator = IsotonicCalibrator()

    # Synthetic overconfident predictions: raw confidence is higher than true accuracy
    confs = [0.2, 0.4, 0.6, 0.8, 0.9]
    labels = [0, 0, 1, 1, 1]

    calibrator.fit(confs, labels)
    assert calibrator.is_fitted
    assert calibrator.sample_count == 5

    # Calibrate single value
    ecs_low = calibrator.calibrate(0.2)
    ecs_high = calibrator.calibrate(0.9)

    assert 0.0 <= ecs_low <= 1.0
    assert 0.0 <= ecs_high <= 1.0
    assert ecs_low <= ecs_high  # Monotonicity property of isotonic regression


def test_isotonic_calibrator_batch() -> None:
    calibrator = IsotonicCalibrator()
    confs = [0.1, 0.3, 0.5, 0.7, 0.9]
    labels = [0, 0, 0, 1, 1]

    calibrator.fit(confs, labels)
    batch_out = calibrator.calibrate_batch([0.2, 0.5, 0.8])
    assert len(batch_out) == 3
    assert all(0.0 <= x <= 1.0 for x in batch_out)
    assert batch_out[0] <= batch_out[1] <= batch_out[2]


def test_isotonic_calibrator_invalid_input() -> None:
    calibrator = IsotonicCalibrator()
    confs = [0.1, 0.5, 0.9]
    labels = [0, 1, 1]
    calibrator.fit(confs, labels)

    with pytest.raises(ContractValidationError):
        calibrator.calibrate(-0.1)

    with pytest.raises(ContractValidationError):
        calibrator.calibrate(1.1)

    with pytest.raises(ContractValidationError):
        calibrator.calibrate_batch([-0.1])


def test_isotonic_evaluate() -> None:
    calibrator = IsotonicCalibrator()
    confs = [0.1, 0.3, 0.6, 0.8, 0.9]
    labels = [0, 0, 1, 1, 1]
    calibrator.fit(confs, labels)

    metrics = calibrator.evaluate(confs, labels, n_bins=5)
    assert metrics.method == "isotonic"
    assert metrics.sample_count == 5
    assert 0.0 <= metrics.ece <= 1.0
    assert 0.0 <= metrics.brier_score <= 1.0

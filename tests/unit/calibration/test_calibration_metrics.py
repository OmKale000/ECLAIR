"""Unit tests for calibration metrics (ECE, Brier score, MCE)."""

from __future__ import annotations

import pytest

from eclair.calibration.metrics import (
    compute_brier_score,
    compute_ece,
    compute_mce,
    evaluate_calibration,
    validate_calibration_inputs,
)
from eclair.exceptions import ContractValidationError


def test_validate_calibration_inputs_valid() -> None:
    confs, labels = validate_calibration_inputs([0.0, 0.5, 1.0], [0, 1, 1])
    assert len(confs) == 3
    assert len(labels) == 3
    assert confs.dtype.name == "float64"
    assert labels.dtype.name == "int32"


def test_validate_calibration_inputs_boolean_labels() -> None:
    confs, labels = validate_calibration_inputs([0.2, 0.8], [False, True])
    assert list(labels) == [0, 1]


def test_validate_calibration_inputs_errors() -> None:
    with pytest.raises(ContractValidationError):
        validate_calibration_inputs([], [])

    with pytest.raises(ContractValidationError):
        validate_calibration_inputs([0.5], [1, 0])

    with pytest.raises(ContractValidationError):
        validate_calibration_inputs([-0.1, 0.5], [0, 1])

    with pytest.raises(ContractValidationError):
        validate_calibration_inputs([1.1, 0.5], [0, 1])

    with pytest.raises(ContractValidationError):
        validate_calibration_inputs([0.5, 0.5], [0, 2])

    with pytest.raises(ContractValidationError):
        validate_calibration_inputs([0.5, float("nan")], [0, 1])


def test_compute_brier_score_perfect() -> None:
    # Confidences match labels perfectly -> Brier = 0.0
    confs = [1.0, 0.0, 1.0, 0.0]
    labels = [1, 0, 1, 0]
    assert compute_brier_score(confs, labels) == 0.0


def test_compute_brier_score_worst() -> None:
    # Completely wrong predictions -> Brier = 1.0
    confs = [1.0, 1.0, 0.0, 0.0]
    labels = [0, 0, 1, 1]
    assert compute_brier_score(confs, labels) == 1.0


def test_compute_brier_score_intermediate() -> None:
    confs = [0.8, 0.2]
    labels = [1, 0]
    # (0.8-1)^2 = 0.04, (0.2-0)^2 = 0.04 -> mean = 0.04
    assert compute_brier_score(confs, labels) == pytest.approx(0.04)


def test_compute_ece_perfect() -> None:
    # 10 samples with confidence 0.8 where 8 are positive -> perfect bin accuracy
    confs = [0.8] * 10
    labels = [1] * 8 + [0] * 2
    assert compute_ece(confs, labels, n_bins=10) == pytest.approx(0.0)


def test_compute_ece_miscalibrated() -> None:
    # 10 samples with confidence 0.9, but only 5 are positive (50% accuracy) -> error = 0.4
    confs = [0.9] * 10
    labels = [1] * 5 + [0] * 5
    assert compute_ece(confs, labels, n_bins=10) == pytest.approx(0.4)


def test_compute_mce() -> None:
    confs = [0.1] * 5 + [0.9] * 5
    # Bin 1 (conf 0.1): 1 positive -> acc = 0.2 -> error = 0.1
    # Bin 2 (conf 0.9): 1 positive -> acc = 0.2 -> error = 0.7
    labels = [1, 0, 0, 0, 0] + [1, 0, 0, 0, 0]
    mce = compute_mce(confs, labels, n_bins=10)
    assert mce == pytest.approx(0.7)


def test_evaluate_calibration_comprehensive() -> None:
    confs = [0.1, 0.2, 0.7, 0.8, 0.9]
    labels = [0, 0, 1, 1, 1]
    metrics = evaluate_calibration(confs, labels, n_bins=5, method="platt")
    assert metrics.sample_count == 5
    assert metrics.bin_count == 5
    assert metrics.method == "platt"
    assert 0.0 <= metrics.ece <= 1.0
    assert 0.0 <= metrics.brier_score <= 1.0
    assert 0.0 <= metrics.mce <= 1.0

"""Unit tests for the high-level ECSCalibrator facade."""

from __future__ import annotations

import pytest

from eclair.calibration.calibrator import ECSCalibrator
from eclair.calibration.models import (
    CalibrationMethod,
    CalibrationMetrics,
    ECSCalibrationResult,
    ReliabilityDiagramData,
)
from eclair.confidence.models import (
    ClaimConfidenceResult,
    ConfidenceBreakdown,
    ConfidenceSignals,
    ResponseConfidenceResult,
)
from eclair.contracts.confidence import ConfidenceResult
from eclair.exceptions import ContractValidationError, ModuleError


def test_calibrator_unfitted_raises() -> None:
    calibrator = ECSCalibrator()
    assert not calibrator.is_fitted
    assert calibrator.sample_count == 0

    with pytest.raises(ModuleError, match="Cannot claim calibrated ECS"):
        calibrator.calibrate(0.8)

    with pytest.raises(ModuleError, match="Cannot claim calibrated ECS"):
        calibrator.calibrate_result(ConfidenceResult(raw_confidence=0.8))

    with pytest.raises(ModuleError, match="Cannot claim calibrated ECS"):
        calibrator.calibrate_batch([0.8])

    with pytest.raises(ModuleError, match="not fitted"):
        calibrator.evaluate([0.8], [1])

    with pytest.raises(ModuleError, match="not fitted"):
        calibrator.get_reliability_data([0.8], [1])


def test_calibrator_fit_and_calibrate_float() -> None:
    calibrator = ECSCalibrator(method="platt")
    confs = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
    labels = [0, 0, 0, 1, 1, 1]

    calibrator.fit(confs, labels)
    assert calibrator.is_fitted
    assert calibrator.sample_count == 6

    res = calibrator.calibrate(0.90)
    assert isinstance(res, ECSCalibrationResult)
    assert res.raw_confidence == 0.90
    assert 0.0 <= res.calibrated_ecs <= 1.0
    assert res.is_calibrated is True
    assert res.method == "platt"


def test_calibrator_calibrate_confidence_result_contract() -> None:
    calibrator = ECSCalibrator(method="isotonic")
    confs = [0.1, 0.3, 0.5, 0.7, 0.9]
    labels = [0, 0, 1, 1, 1]
    calibrator.fit(confs, labels)

    raw_contract = ConfidenceResult(raw_confidence=0.85)
    assert raw_contract.calibrated_ecs is None

    calibrated_contract = calibrator.calibrate_result(raw_contract)
    assert isinstance(calibrated_contract, ConfidenceResult)
    assert calibrated_contract.raw_confidence == 0.85
    assert calibrated_contract.calibrated_ecs is not None
    assert 0.0 <= calibrated_contract.calibrated_ecs <= 1.0


def test_calibrator_with_m10_models() -> None:
    calibrator = ECSCalibrator(method=CalibrationMethod.PLATT)
    confs = [0.1, 0.2, 0.8, 0.9]
    labels = [0, 0, 1, 1]
    calibrator.fit(confs, labels)

    # Test with M10 ClaimConfidenceResult
    claim_conf = ClaimConfidenceResult(
        claim_id="claim-123",
        raw_confidence=0.85,
        signals=ConfidenceSignals(verification_score=0.9),
        breakdown=ConfidenceBreakdown(total_raw_confidence=0.85),
    )
    res_claim = calibrator.calibrate(claim_conf)
    assert res_claim.claim_id == "claim-123"
    assert res_claim.raw_confidence == 0.85
    assert 0.0 <= res_claim.calibrated_ecs <= 1.0

    # Test with M10 ResponseConfidenceResult
    resp_conf = ResponseConfidenceResult(
        raw_confidence=0.75,
        claim_confidences=[claim_conf],
    )
    res_resp = calibrator.calibrate(resp_conf)
    assert res_resp.raw_confidence == 0.75
    assert 0.0 <= res_resp.calibrated_ecs <= 1.0


def test_calibrator_batch_and_evaluation() -> None:
    calibrator = ECSCalibrator(method="platt")
    train_confs = [0.1, 0.2, 0.4, 0.6, 0.8, 0.9]
    train_labels = [0, 0, 0, 1, 1, 1]
    calibrator.fit(train_confs, train_labels)

    batch_res = calibrator.calibrate_batch([0.2, 0.5, 0.8])
    assert len(batch_res) == 3
    assert all(0.0 <= x <= 1.0 for x in batch_res)

    test_confs = [0.15, 0.35, 0.75, 0.85]
    test_labels = [0, 0, 1, 1]
    metrics = calibrator.evaluate(test_confs, test_labels, n_bins=5)
    assert isinstance(metrics, CalibrationMetrics)
    assert metrics.sample_count == 4
    assert 0.0 <= metrics.ece <= 1.0
    assert 0.0 <= metrics.brier_score <= 1.0

    diag_data = calibrator.get_reliability_data(test_confs, test_labels, n_bins=5)
    assert isinstance(diag_data, ReliabilityDiagramData)
    assert len(diag_data.bins) == 5


def test_calibrator_unsupported_method() -> None:
    with pytest.raises(ContractValidationError, match="Unsupported calibration method"):
        ECSCalibrator(method="unsupported_method")


def test_calibrator_invalid_inputs() -> None:
    calibrator = ECSCalibrator()
    calibrator.fit([0.2, 0.8], [0, 1])

    with pytest.raises(ContractValidationError):
        calibrator.calibrate("invalid_string")

    with pytest.raises(ContractValidationError):
        calibrator.calibrate(-0.5)

    with pytest.raises(ContractValidationError):
        calibrator.calibrate_result("not_a_contract")  # type: ignore[arg-type]

"""Calibration evaluation metrics for M11 ECS Calibration (Spec sec.M11, sec.M18).

Implements standard calibration error metrics:
- Expected Calibration Error (ECE)
- Brier Score
- Maximum Calibration Error (MCE)
- Comprehensive calibration evaluation

Reliability invariant (Spec sec.4.4):
ECE and Brier score must be calculated only on valid, paired confidence values and
observed binary correctness labels.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from eclair.calibration.models import CalibrationMetrics
from eclair.exceptions import ContractValidationError

__all__ = [
    "validate_calibration_inputs",
    "compute_brier_score",
    "compute_ece",
    "compute_mce",
    "evaluate_calibration",
]


def validate_calibration_inputs(
    confidences: Sequence[float],
    labels: Sequence[int | bool | float],
) -> tuple[np.ndarray, np.ndarray]:
    """Validate and sanitize confidence scores and observed correctness labels.

    Args:
        confidences: Sequence of predicted/calibrated confidence scores in [0.0, 1.0].
        labels: Sequence of observed correctness labels (1/True for correct, 0/False for incorrect).

    Returns:
        Tuple of (confidences_array, labels_array) as 1D float64 and int32 numpy arrays.

    Raises:
        ContractValidationError: If inputs are empty, lengths mismatch, values are non-numeric,
            confidences are outside [0.0, 1.0], or labels are not binary {0, 1}.
    """
    if confidences is None or labels is None:
        raise ContractValidationError(
            "Confidence scores and correctness labels cannot be None.",
            code="calibration_input_none",
        )

    try:
        conf_len = len(confidences)
        lab_len = len(labels)
    except TypeError as exc:
        raise ContractValidationError(
            f"Inputs must be sequences, got {type(confidences).__name__} and {type(labels).__name__}",
            code="calibration_input_type",
        ) from exc

    if conf_len == 0 or lab_len == 0:
        raise ContractValidationError(
            "Confidence scores and correctness labels cannot be empty.",
            code="calibration_input_empty",
        )

    if conf_len != lab_len:
        raise ContractValidationError(
            f"Length mismatch between confidences ({conf_len}) and labels ({lab_len}).",
            code="calibration_length_mismatch",
        )

    # Convert to numeric arrays and validate individual values
    clean_confs: list[float] = []
    for idx, c in enumerate(confidences):
        if not isinstance(c, (int, float, np.number)) or isinstance(c, bool):
            raise ContractValidationError(
                f"Confidence at index {idx} must be a float, got {type(c).__name__} ({c!r}).",
                code="invalid_confidence_type",
            )
        val = float(c)
        if np.isnan(val) or np.isinf(val):
            raise ContractValidationError(
                f"Confidence at index {idx} is NaN or Inf: {c!r}.",
                code="invalid_confidence_value",
            )
        if val < 0.0 or val > 1.0:
            raise ContractValidationError(
                f"Confidence at index {idx} must be in [0.0, 1.0], got {val}.",
                code="invalid_confidence_range",
            )
        clean_confs.append(val)

    clean_labels: list[int] = []
    for idx, y in enumerate(labels):
        if isinstance(y, bool):
            clean_labels.append(1 if y else 0)
        elif isinstance(y, (int, np.integer)):
            if int(y) not in (0, 1):
                raise ContractValidationError(
                    f"Correctness label at index {idx} must be binary 0 or 1, got {y!r}.",
                    code="invalid_label_value",
                )
            clean_labels.append(int(y))
        elif isinstance(y, (float, np.floating)):
            if float(y) == 0.0:
                clean_labels.append(0)
            elif float(y) == 1.0:
                clean_labels.append(1)
            else:
                raise ContractValidationError(
                    f"Correctness label at index {idx} must be binary 0 or 1, got {y!r}.",
                    code="invalid_label_value",
                )
        else:
            raise ContractValidationError(
                f"Correctness label at index {idx} must be binary, got {type(y).__name__} ({y!r}).",
                code="invalid_label_type",
            )

    return np.array(clean_confs, dtype=np.float64), np.array(clean_labels, dtype=np.int32)


def compute_brier_score(
    confidences: Sequence[float],
    labels: Sequence[int | bool | float],
) -> float:
    """Compute the Brier Score for confidence predictions against observed correctness.

    Brier score measures the mean squared difference between predicted confidence
    and observed binary outcomes:
        Brier = (1 / N) * sum((p_i - y_i)^2)

    A lower Brier score indicates better calibrated and more accurate probabilities.

    Args:
        confidences: Sequence of confidence scores in [0.0, 1.0].
        labels: Sequence of binary observed correctness outcomes.

    Returns:
        Brier score as a float in [0.0, 1.0].
    """
    confs_arr, labels_arr = validate_calibration_inputs(confidences, labels)
    brier = float(np.mean((confs_arr - labels_arr) ** 2))
    return float(np.clip(brier, 0.0, 1.0))


def compute_ece(
    confidences: Sequence[float],
    labels: Sequence[int | bool | float],
    n_bins: int = 10,
    strategy: str = "uniform",
) -> float:
    """Compute the Expected Calibration Error (ECE).

    ECE partitions the confidence range into M bins and calculates the weighted
    average difference between empirical accuracy and average confidence:
        ECE = sum_{m=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|

    Args:
        confidences: Sequence of confidence scores in [0.0, 1.0].
        labels: Sequence of binary observed correctness outcomes.
        n_bins: Number of confidence bins (default 10). Must be >= 1.
        strategy: Binning strategy, 'uniform' (equal width) or 'quantile' (equal frequency).

    Returns:
        ECE as a float in [0.0, 1.0].
    """
    if n_bins < 1:
        raise ContractValidationError(
            f"n_bins must be >= 1, got {n_bins}.",
            code="invalid_n_bins",
        )

    confs_arr, labels_arr = validate_calibration_inputs(confidences, labels)
    n_samples = len(confs_arr)

    if strategy == "quantile":
        # Quantile bin edges
        quantiles = np.linspace(0.0, 1.0, n_bins + 1)
        bin_edges = np.percentile(confs_arr, quantiles * 100.0)
        bin_edges[0] = 0.0
        bin_edges[-1] = 1.0
    else:
        # Uniform equal-width bin edges
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)

    ece = 0.0
    for m in range(n_bins):
        low = bin_edges[m]
        high = bin_edges[m + 1]

        if m == 0:
            mask = (confs_arr >= low) & (confs_arr <= high)
        else:
            mask = (confs_arr > low) & (confs_arr <= high)

        bin_count = int(np.sum(mask))
        if bin_count > 0:
            bin_acc = float(np.mean(labels_arr[mask]))
            bin_conf = float(np.mean(confs_arr[mask]))
            weight = bin_count / n_samples
            ece += weight * abs(bin_acc - bin_conf)

    return float(np.clip(ece, 0.0, 1.0))


def compute_mce(
    confidences: Sequence[float],
    labels: Sequence[int | bool | float],
    n_bins: int = 10,
) -> float:
    """Compute the Maximum Calibration Error (MCE).

    MCE measures the worst-case calibration error across all non-empty bins:
        MCE = max_{m: |B_m| > 0} |acc(B_m) - conf(B_m)|

    Args:
        confidences: Sequence of confidence scores in [0.0, 1.0].
        labels: Sequence of binary observed correctness outcomes.
        n_bins: Number of confidence bins (default 10). Must be >= 1.

    Returns:
        MCE as a float in [0.0, 1.0].
    """
    if n_bins < 1:
        raise ContractValidationError(
            f"n_bins must be >= 1, got {n_bins}.",
            code="invalid_n_bins",
        )

    confs_arr, labels_arr = validate_calibration_inputs(confidences, labels)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)

    max_error = 0.0
    for m in range(n_bins):
        low = bin_edges[m]
        high = bin_edges[m + 1]

        if m == 0:
            mask = (confs_arr >= low) & (confs_arr <= high)
        else:
            mask = (confs_arr > low) & (confs_arr <= high)

        bin_count = int(np.sum(mask))
        if bin_count > 0:
            bin_acc = float(np.mean(labels_arr[mask]))
            bin_conf = float(np.mean(confs_arr[mask]))
            error = abs(bin_acc - bin_conf)
            if error > max_error:
                max_error = error

    return float(np.clip(max_error, 0.0, 1.0))


def evaluate_calibration(
    confidences: Sequence[float],
    labels: Sequence[int | bool | float],
    n_bins: int = 10,
    method: str = "unknown",
    details: dict[str, Any] | None = None,
) -> CalibrationMetrics:
    """Perform a full evaluation of confidence calibration against observed correctness.

    Args:
        confidences: Sequence of confidence scores in [0.0, 1.0].
        labels: Sequence of binary observed correctness outcomes.
        n_bins: Number of bins for ECE and MCE computation.
        method: Calibration method name.
        details: Optional diagnostic dictionary.

    Returns:
        A validated :class:`CalibrationMetrics` object.
    """
    confs_arr, _ = validate_calibration_inputs(confidences, labels)
    ece = compute_ece(confidences, labels, n_bins=n_bins)
    brier = compute_brier_score(confidences, labels)
    mce = compute_mce(confidences, labels, n_bins=n_bins)

    return CalibrationMetrics(
        ece=ece,
        brier_score=brier,
        mce=mce,
        sample_count=len(confs_arr),
        bin_count=n_bins,
        method=method,
        details=details or {},
    )

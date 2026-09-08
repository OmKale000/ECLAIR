"""Reliability diagrams and calibration curve analysis for M11 (Spec sec.M11).

Provides structured data generation and visual plotting helpers for reliability
diagrams (calibration curves) to inspect how predicted/calibrated confidence
relates to empirical observed correctness.

Reliability invariant (Spec sec.4.4):
Produces calibration analysis data to inspect calibration quality; does NOT embed
Streamlit or dashboard UI logic inside M11.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from eclair.calibration.metrics import (
    compute_brier_score,
    compute_ece,
    compute_mce,
    validate_calibration_inputs,
)
from eclair.calibration.models import CalibrationBin, ReliabilityDiagramData
from eclair.exceptions import ContractValidationError

__all__ = [
    "compute_reliability_diagram_data",
    "plot_reliability_diagram",
    "ReliabilityAnalyzer",
]


def compute_reliability_diagram_data(
    confidences: Sequence[float],
    labels: Sequence[int | bool | float],
    n_bins: int = 10,
) -> ReliabilityDiagramData:
    """Compute structured binning statistics for a reliability diagram / calibration curve.

    Args:
        confidences: Sequence of confidence scores in [0.0, 1.0].
        labels: Sequence of binary observed correctness outcomes.
        n_bins: Number of equal-width bins in [0.0, 1.0]. Default is 10.

    Returns:
        A validated :class:`ReliabilityDiagramData` instance.

    Raises:
        ContractValidationError: If inputs are invalid or n_bins < 1.
    """
    if n_bins < 1:
        raise ContractValidationError(
            f"n_bins must be >= 1, got {n_bins}.",
            code="invalid_n_bins",
        )

    confs_arr, labels_arr = validate_calibration_inputs(confidences, labels)
    n_samples = len(confs_arr)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1).tolist()
    bins: list[CalibrationBin] = []
    bin_accuracies: list[float] = []
    bin_confidences: list[float] = []
    bin_counts: list[int] = []

    for m in range(n_bins):
        low = bin_edges[m]
        high = bin_edges[m + 1]

        if m == 0:
            mask = (confs_arr >= low) & (confs_arr <= high)
        else:
            mask = (confs_arr > low) & (confs_arr <= high)

        count = int(np.sum(mask))
        bin_counts.append(count)

        if count > 0:
            acc = float(np.mean(labels_arr[mask]))
            conf = float(np.mean(confs_arr[mask]))
        else:
            acc = 0.0
            conf = (low + high) / 2.0

        bin_accuracies.append(acc)
        bin_confidences.append(conf)
        cal_err = abs(acc - conf) if count > 0 else 0.0

        bins.append(
            CalibrationBin(
                bin_index=m,
                lower_bound=low,
                upper_bound=high,
                sample_count=count,
                mean_confidence=conf,
                accuracy=acc,
                calibration_error=cal_err,
            )
        )

    ece = compute_ece(confidences, labels, n_bins=n_bins)
    brier = compute_brier_score(confidences, labels)
    mce = compute_mce(confidences, labels, n_bins=n_bins)
    overall_acc = float(np.mean(labels_arr))
    overall_conf = float(np.mean(confs_arr))

    return ReliabilityDiagramData(
        bins=bins,
        bin_edges=bin_edges,
        bin_accuracies=bin_accuracies,
        bin_confidences=bin_confidences,
        bin_counts=bin_counts,
        ece=ece,
        brier_score=brier,
        mce=mce,
        overall_accuracy=overall_acc,
        overall_confidence=overall_conf,
        sample_count=n_samples,
    )


def plot_reliability_diagram(
    diagram_data: ReliabilityDiagramData,
    title: str = "Reliability Diagram",
    save_path: str | None = None,
) -> Any:
    """Render a Matplotlib reliability diagram figure from structured diagram data.

    Args:
        diagram_data: Computed :class:`ReliabilityDiagramData`.
        title: Title of the chart.
        save_path: Optional file path to save the generated figure.

    Returns:
        The generated Matplotlib Figure object, or None if matplotlib is not available.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(7, 8), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
    )

    # Main calibration plot
    bin_centers = [
        (diagram_data.bin_edges[i] + diagram_data.bin_edges[i + 1]) / 2.0
        for i in range(len(diagram_data.bin_edges) - 1)
    ]
    width = 1.0 / len(bin_centers)

    # Plot empirical accuracy bars
    ax1.bar(
        bin_centers,
        diagram_data.bin_accuracies,
        width=width * 0.85,
        alpha=0.7,
        color="#2563eb",
        edgecolor="#1d4ed8",
        label="Observed Accuracy",
    )

    # Plot perfect calibration diagonal
    ax1.plot([0, 1], [0, 1], linestyle="--", color="#dc2626", label="Perfect Calibration")

    ax1.set_xlim(0.0, 1.0)
    ax1.set_ylim(0.0, 1.0)
    ax1.set_ylabel("Accuracy")
    ax1.set_title(f"{title} (ECE: {diagram_data.ece:.3f}, Brier: {diagram_data.brier_score:.3f})")
    ax1.legend(loc="upper left")
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Frequency / sample count histogram below
    ax2.bar(
        bin_centers,
        diagram_data.bin_counts,
        width=width * 0.85,
        color="#64748b",
        edgecolor="#475569",
    )
    ax2.set_xlabel("Confidence")
    ax2.set_ylabel("Count")
    ax2.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


class ReliabilityAnalyzer:
    """Analyzer providing high-level reliability diagram and curve generation."""

    def __init__(self, default_bins: int = 10) -> None:
        self.default_bins = default_bins

    def analyze(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
        n_bins: int | None = None,
    ) -> ReliabilityDiagramData:
        """Analyze calibration curve and return structured diagram data."""
        bins = n_bins if n_bins is not None else self.default_bins
        return compute_reliability_diagram_data(confidences, labels, n_bins=bins)

    def plot(
        self,
        confidences: Sequence[float],
        labels: Sequence[int | bool | float],
        title: str = "Reliability Diagram",
        n_bins: int | None = None,
        save_path: str | None = None,
    ) -> Any:
        """Analyze and plot a reliability diagram."""
        data = self.analyze(confidences, labels, n_bins=n_bins)
        return plot_reliability_diagram(data, title=title, save_path=save_path)

"""Unit tests for reliability diagram generation and curve analysis."""

from __future__ import annotations

import pytest

from eclair.calibration.models import ReliabilityDiagramData
from eclair.calibration.reliability import (
    ReliabilityAnalyzer,
    compute_reliability_diagram_data,
    plot_reliability_diagram,
)
from eclair.exceptions import ContractValidationError


def test_compute_reliability_diagram_data() -> None:
    confs = [0.05, 0.15, 0.25, 0.75, 0.85, 0.95]
    labels = [0, 0, 0, 1, 1, 1]

    data = compute_reliability_diagram_data(confs, labels, n_bins=5)
    assert isinstance(data, ReliabilityDiagramData)
    assert len(data.bins) == 5
    assert len(data.bin_edges) == 6
    assert data.sample_count == 6
    assert data.overall_accuracy == pytest.approx(0.5)
    assert 0.0 <= data.ece <= 1.0
    assert 0.0 <= data.brier_score <= 1.0


def test_compute_reliability_diagram_invalid_bins() -> None:
    with pytest.raises(ContractValidationError):
        compute_reliability_diagram_data([0.5, 0.8], [0, 1], n_bins=0)


def test_reliability_analyzer() -> None:
    analyzer = ReliabilityAnalyzer(default_bins=10)
    confs = [0.1, 0.2, 0.3, 0.8, 0.9]
    labels = [0, 0, 0, 1, 1]

    diag_data = analyzer.analyze(confs, labels)
    assert diag_data.sample_count == 5
    assert len(diag_data.bins) == 10


def test_plot_reliability_diagram_execution() -> None:
    confs = [0.1, 0.2, 0.3, 0.8, 0.9]
    labels = [0, 0, 0, 1, 1]
    diag_data = compute_reliability_diagram_data(confs, labels, n_bins=5)

    # Calling plot should either produce a Figure or None without crashing
    fig = plot_reliability_diagram(diag_data, title="Test Diagram")
    # If matplotlib is installed, fig is a Figure object; otherwise None
    if fig is not None:
        import matplotlib.pyplot as plt
        plt.close(fig)

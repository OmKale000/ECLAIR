"""Unit tests for M06 ConflictDetector (duplicates and contradictions)."""

from __future__ import annotations

from eclair.contracts.evidence import Evidence
from eclair.evidence.conflict import (
    ConflictDetector,
    detect_conflicts,
    detect_duplicates,
)


def test_duplicate_detection_exact_and_fuzzy() -> None:
    detector = ConflictDetector()

    ev1 = Evidence(evidence_id="ev-1", text="Customers may request a full refund within 30 days.")
    ev2 = Evidence(evidence_id="ev-2", text="Customers may request a full refund within 30 days.")
    ev3 = Evidence(evidence_id="ev-3", text="Customers can request a full refund within 30 days.")
    ev4 = Evidence(evidence_id="ev-4", text="Completely different passage regarding invoice payment methods.")

    dups, clusters = detector.detect_duplicates([ev1, ev2, ev3, ev4])
    assert "ev-2" in dups
    assert "ev-3" in dups
    assert "ev-4" not in dups
    assert len(clusters) == 1
    assert clusters[0] == ["ev-1", "ev-2", "ev-3"]


def test_numerical_conflict_detection() -> None:
    detector = ConflictDetector()

    ev1 = Evidence(
        evidence_id="ev-1",
        text="Customers may request a refund within 30 days of initial purchase.",
    )
    ev2 = Evidence(
        evidence_id="ev-2",
        text="Customers may request a refund within 14 days of initial purchase.",
    )

    conflicts = detector.detect_conflicts([ev1, ev2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "numerical"
    assert conflicts[0].conflict_score >= 0.85
    assert "30" in conflicts[0].reason and "14" in conflicts[0].reason


def test_polarity_conflict_detection() -> None:
    detector = ConflictDetector()

    ev1 = Evidence(
        evidence_id="ev-1",
        text="Returns for opened digital software products are permitted.",
    )
    ev2 = Evidence(
        evidence_id="ev-2",
        text="Returns for opened digital software products are prohibited.",
    )

    conflicts = detector.detect_conflicts([ev1, ev2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "polarity"
    assert conflicts[0].conflict_score >= 0.80


def test_antonym_conflict_detection() -> None:
    detector = ConflictDetector()

    ev1 = Evidence(
        evidence_id="ev-1",
        text="Identity verification is mandatory for international customer accounts.",
    )
    ev2 = Evidence(
        evidence_id="ev-2",
        text="Identity verification is optional for international customer accounts.",
    )

    conflicts = detector.detect_conflicts([ev1, ev2])
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "policy"
    assert conflicts[0].conflict_score >= 0.80


def test_unrelated_evidence_has_no_conflict() -> None:
    detector = ConflictDetector()

    ev1 = Evidence(
        evidence_id="ev-1",
        text="Invoices must be settled in USD currency via wire transfer.",
    )
    ev2 = Evidence(
        evidence_id="ev-2",
        text="The company annual holiday calendar lists twelve observed holidays.",
    )

    conflicts = detector.detect_conflicts([ev1, ev2])
    assert len(conflicts) == 0


def test_score_conflicts_attributes_scores_to_items() -> None:
    detector = ConflictDetector()

    ev1 = Evidence(
        evidence_id="ev-1",
        text="Refund processing time is 5 business days.",
    )
    ev2 = Evidence(
        evidence_id="ev-2",
        text="Refund processing time is 10 business days.",
    )
    ev3 = Evidence(
        evidence_id="ev-3",
        text="Company headquarters is located in San Francisco.",
    )

    scores, conflicts = detector.score_conflicts([ev1, ev2, ev3])
    assert scores["ev-1"] >= 0.85
    assert scores["ev-2"] >= 0.85
    assert scores["ev-3"] == 0.0
    assert len(conflicts) == 1


def test_convenience_functions() -> None:
    ev1 = Evidence(evidence_id="ev-1", text="All returns allowed.")
    ev2 = Evidence(evidence_id="ev-2", text="All returns allowed.")
    ev3 = Evidence(evidence_id="ev-3", text="No returns allowed.")

    dups, _ = detect_duplicates([ev1, ev2])
    assert "ev-2" in dups

    confs = detect_conflicts([ev1, ev3])
    assert len(confs) >= 1

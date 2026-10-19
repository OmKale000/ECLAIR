"""Unit tests for AuditReconstructor and DecisionPath."""

from __future__ import annotations

import pytest

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import ClaimType, DecisionAction, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.query import Query
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.database.database import create_db_engine, init_db
from eclair.database.session import DatabaseSessionManager
from eclair.exceptions import ModuleError
from eclair.provenance.audit import AuditReconstructor
from eclair.provenance.tracker import ProvenanceTracker


@pytest.fixture
def session_manager():
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    mgr = DatabaseSessionManager(engine=engine)
    yield mgr
    engine.dispose()


def test_audit_reconstruction_complete(session_manager):
    with session_manager.session() as session:
        tracker = ProvenanceTracker(session)
        tracker.record_query(
            Query(query_id="q-audit-comp", question="Can I cancel within 14 days?"),
            final_answer="Yes, cancellations are permitted within 14 days.",
        )
        tracker.record_claims(
            "q-audit-comp",
            [
                Claim(claim_id="c-1", text="Cancellation period is 14 days.", claim_type=ClaimType.FACTUAL),
                Claim(claim_id="c-2", text="Full refund is issued.", claim_type=ClaimType.FACTUAL),
            ],
        )
        tracker.record_evidence(
            "q-audit-comp",
            [
                Evidence(evidence_id="e-1", text="Customer may cancel within 14 days for a full refund.", source="customer_policy.md", relevance_score=0.98),
            ],
        )
        tracker.record_verifications(
            "q-audit-comp",
            [
                VerificationResult(claim_id="c-1", status=VerificationStatus.SUPPORTED, evidence_ids=["e-1"]),
                VerificationResult(claim_id="c-2", status=VerificationStatus.SUPPORTED, evidence_ids=["e-1"]),
            ],
        )
        tracker.record_confidence(
            "q-audit-comp",
            ConfidenceResult(raw_confidence=0.92, calibrated_ecs=0.94),
        )
        tracker.record_risk(
            "q-audit-comp",
            RiskResult(risk_level="LOW", risk_score=0.08),
        )
        tracker.record_decision(
            "q-audit-comp",
            DecisionResult(action=DecisionAction.RETURN, reason="All claims supported with high confidence."),
        )
        tracker.record_consensus(
            "q-audit-comp",
            agreement_score=1.0,
            consensus_level="FULL",
            majority_answer="14 days full refund",
        )
        tracker.record_feedback(
            "q-audit-comp",
            rating=5.0,
            feedback_text="Clear and accurate",
        )

    # Reconstruct in separate session
    with session_manager.session() as session:
        reconstructor = AuditReconstructor(session)
        path = reconstructor.reconstruct("q-audit-comp")

        assert path.query_id == "q-audit-comp"
        assert path.question == "Can I cancel within 14 days?"
        assert path.final_answer == "Yes, cancellations are permitted within 14 days."
        assert len(path.claims) == 2
        assert len(path.evidence) == 1
        assert len(path.verifications) == 2
        assert path.confidence is not None
        assert path.confidence["raw_confidence"] == 0.92
        assert path.confidence["calibrated_ecs"] == 0.94
        assert path.consensus is not None
        assert path.consensus["consensus_level"] == "FULL"
        assert path.risk is not None
        assert path.risk["risk_level"] == "LOW"
        assert path.decision is not None
        assert path.decision["action"] == "RETURN"
        assert len(path.feedback) == 1
        assert path.is_complete is True

        # Check narrative explanation
        assert "Query: 'Can I cancel within 14 days?'" in path.explanation
        assert "Extracted 2 claim(s)" in path.explanation
        assert "2 SUPPORTED, 0 CONTRADICTED, 0 UNKNOWN" in path.explanation
        assert "Confidence: raw=0.9200, calibrated_ecs=0.9400" in path.explanation
        assert "Risk: level=LOW" in path.explanation
        assert "Decision action: RETURN" in path.explanation

        # Test to_dict serialization
        path_dict = path.to_dict()
        assert isinstance(path_dict, dict)
        assert path_dict["query_id"] == "q-audit-comp"


def test_audit_reconstruction_partial_lineage(session_manager):
    with session_manager.session() as session:
        tracker = ProvenanceTracker(session)
        tracker.record_query(
            Query(query_id="q-audit-partial", question="Incomplete pipeline question"),
        )
        # Only claims recorded, no verifications, confidence, risk, or decision

    with session_manager.session() as session:
        reconstructor = AuditReconstructor(session)
        path = reconstructor.reconstruct("q-audit-partial")

        assert path.query_id == "q-audit-partial"
        assert path.is_complete is False
        assert "Note: Audit trail is partial" in path.explanation


def test_audit_reconstruction_unknown_query(session_manager):
    with session_manager.session() as session:
        reconstructor = AuditReconstructor(session)
        with pytest.raises(ModuleError) as exc_info:
            reconstructor.reconstruct("unknown-query-id")
        assert exc_info.value.code == "query_not_found"

        with pytest.raises(ModuleError) as exc_info:
            reconstructor.reconstruct("   ")
        assert exc_info.value.code == "empty_query_id"

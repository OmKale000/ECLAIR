"""Unit tests for M14 SQLAlchemy ORM models."""

from __future__ import annotations

import pytest

from eclair.database.database import create_db_engine, init_db
from eclair.database.models import (
    AuditModel,
    ClaimModel,
    ConfidenceModel,
    ConsensusModel,
    DecisionModel,
    EvidenceModel,
    FeedbackModel,
    QueryModel,
    RiskModel,
    VerificationModel,
)
from eclair.database.session import DatabaseSessionManager


@pytest.fixture
def session_manager():
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    mgr = DatabaseSessionManager(engine=engine)
    yield mgr
    engine.dispose()


def test_models_persistence_and_relationships(session_manager):
    with session_manager.session() as session:
        # Create Query
        query = QueryModel(
            query_id="q-full-1",
            question="Is product return policy 30 days?",
            final_answer="Yes, the return policy is 30 days.",
        )
        session.add(query)
        session.flush()

        # Add Claim
        claim = ClaimModel(
            claim_id="c-1",
            query_id="q-full-1",
            text="Return policy is 30 days.",
            claim_type="FACTUAL",
            position=0,
        )
        session.add(claim)

        # Add Evidence
        evidence = EvidenceModel(
            evidence_id="e-1",
            query_id="q-full-1",
            text="Items may be returned within 30 days of purchase.",
            source="refund_policy.md",
            relevance_score=0.95,
        )
        session.add(evidence)

        # Add Verification
        verification = VerificationModel(
            query_id="q-full-1",
            claim_id="c-1",
            status="SUPPORTED",
            evidence_ids=["e-1"],
        )
        session.add(verification)

        # Add Confidence
        confidence = ConfidenceModel(
            query_id="q-full-1",
            raw_confidence=0.88,
            calibrated_ecs=0.91,
        )
        session.add(confidence)

        # Add Consensus
        consensus = ConsensusModel(
            query_id="q-full-1",
            agreement_score=1.0,
            consensus_level="FULL",
            majority_answer="30 days",
            details={"voters": 3},
        )
        session.add(consensus)

        # Add Risk
        risk = RiskModel(
            query_id="q-full-1",
            risk_level="LOW",
            risk_score=0.10,
        )
        session.add(risk)

        # Add Decision
        decision = DecisionModel(
            query_id="q-full-1",
            action="RETURN",
            reason="High confidence and verified evidence.",
        )
        session.add(decision)

        # Add Feedback
        feedback = FeedbackModel(
            feedback_id="fb-1",
            query_id="q-full-1",
            rating=5.0,
            feedback_text="Very helpful answer",
            user_id="user-42",
        )
        session.add(feedback)

        # Add Audit
        audit = AuditModel(
            audit_id="audit-1",
            query_id="q-full-1",
            final_answer="Yes, the return policy is 30 days.",
            decision_action="RETURN",
            summary={"claims": 1, "supported": 1},
        )
        session.add(audit)

    # Verify retrieval and relationships
    with session_manager.session() as session:
        loaded_query = session.get(QueryModel, "q-full-1")
        assert loaded_query is not None
        assert len(loaded_query.claims) == 1
        assert loaded_query.claims[0].claim_id == "c-1"
        assert len(loaded_query.evidence) == 1
        assert loaded_query.evidence[0].evidence_id == "e-1"
        assert len(loaded_query.verifications) == 1
        assert loaded_query.verifications[0].status == "SUPPORTED"
        assert loaded_query.verifications[0].evidence_ids == ["e-1"]
        assert loaded_query.confidence is not None
        assert loaded_query.confidence.raw_confidence == 0.88
        assert loaded_query.confidence.calibrated_ecs == 0.91
        assert loaded_query.consensus is not None
        assert loaded_query.consensus.consensus_level == "FULL"
        assert loaded_query.risk is not None
        assert loaded_query.risk.risk_level == "LOW"
        assert loaded_query.decision is not None
        assert loaded_query.decision.action == "RETURN"
        assert len(loaded_query.feedbacks) == 1
        assert loaded_query.feedbacks[0].rating == 5.0
        assert loaded_query.audit is not None
        assert loaded_query.audit.decision_action == "RETURN"


def test_cascade_delete(session_manager):
    with session_manager.session() as session:
        query = QueryModel(query_id="q-del-1", question="To be deleted")
        session.add(query)
        session.flush()

        claim = ClaimModel(claim_id="c-del-1", query_id="q-del-1", text="Claim to be deleted")
        evidence = EvidenceModel(evidence_id="e-del-1", query_id="q-del-1", text="Evidence to be deleted")
        session.add_all([claim, evidence])

    with session_manager.session() as session:
        query = session.get(QueryModel, "q-del-1")
        session.delete(query)

    with session_manager.session() as session:
        assert session.get(ClaimModel, "c-del-1") is None
        assert session.get(EvidenceModel, "e-del-1") is None

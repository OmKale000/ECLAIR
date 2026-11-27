"""Unit tests for ProvenanceTracker."""

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
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.provenance.tracker import ProvenanceTracker


@pytest.fixture
def session_manager():
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    mgr = DatabaseSessionManager(engine=engine)
    yield mgr
    engine.dispose()


def test_tracker_record_query_success_and_validation(session_manager):
    with session_manager.session() as session:
        tracker = ProvenanceTracker(session)

        # Success
        q = Query(query_id="q-trk-1", question="What is the refund period?")
        model = tracker.record_query(q, final_answer="30 days")
        assert model.query_id == "q-trk-1"
        assert model.question == "What is the refund period?"
        assert model.final_answer == "30 days"

        # Invalid contract type raises ContractValidationError
        with pytest.raises(ContractValidationError):
            tracker.record_query("not a query object")  # type: ignore


def test_tracker_record_claims_and_ordering(session_manager):
    with session_manager.session() as session:
        tracker = ProvenanceTracker(session)
        tracker.record_query(Query(query_id="q-trk-claims", question="Test Q"))

        claims = [
            Claim(claim_id="c-1", text="First statement", claim_type=ClaimType.FACTUAL),
            Claim(claim_id="c-2", text="Second statement", claim_type=ClaimType.NUMERIC),
        ]
        models = tracker.record_claims("q-trk-claims", claims)
        assert len(models) == 2
        assert models[0].position == 0
        assert models[1].position == 1

        # Non-existent query raises ModuleError
        with pytest.raises(ModuleError) as exc_info:
            tracker.record_claims("non-existent-query", claims)
        assert exc_info.value.code == "query_not_found"

        # Invalid claim type raises ContractValidationError
        with pytest.raises(ContractValidationError):
            tracker.record_claims("q-trk-claims", ["not a claim"])  # type: ignore


def test_tracker_record_evidence_and_verifications(session_manager):
    with session_manager.session() as session:
        tracker = ProvenanceTracker(session)
        tracker.record_query(Query(query_id="q-trk-ev", question="Evidence Q"))

        ev_list = [
            Evidence(evidence_id="e-1", text="Evidence passage", source="policy.md", relevance_score=0.92)
        ]
        ev_models = tracker.record_evidence("q-trk-ev", ev_list)
        assert len(ev_models) == 1
        assert ev_models[0].source == "policy.md"

        ver_list = [
            VerificationResult(
                claim_id="c-1",
                status=VerificationStatus.SUPPORTED,
                evidence_ids=["e-1"],
            )
        ]
        ver_models = tracker.record_verifications("q-trk-ev", ver_list)
        assert len(ver_models) == 1
        assert ver_models[0].status == "SUPPORTED"

        # Invalid verifications
        with pytest.raises(ContractValidationError):
            tracker.record_verifications("q-trk-ev", ["invalid"])  # type: ignore


def test_tracker_record_confidence_risk_decision(session_manager):
    with session_manager.session() as session:
        tracker = ProvenanceTracker(session)
        tracker.record_query(Query(query_id="q-trk-eval", question="Eval Q"))

        conf = ConfidenceResult(raw_confidence=0.82, calibrated_ecs=0.87)
        conf_model = tracker.record_confidence("q-trk-eval", conf)
        assert conf_model.raw_confidence == 0.82
        assert conf_model.calibrated_ecs == 0.87

        risk = RiskResult(risk_level="MEDIUM", risk_score=0.45)
        risk_model = tracker.record_risk("q-trk-eval", risk)
        assert risk_model.risk_level == "MEDIUM"
        assert risk_model.risk_score == 0.45

        dec = DecisionResult(action=DecisionAction.RETURN, reason="Passed thresholds")
        dec_model = tracker.record_decision("q-trk-eval", dec)
        assert dec_model.action == "RETURN"

        # Consensus
        consensus_model = tracker.record_consensus(
            "q-trk-eval",
            agreement_score=0.90,
            consensus_level="FULL",
            majority_answer="Answer text",
        )
        assert consensus_model.consensus_level == "FULL"

        # Final answer update
        updated_query = tracker.record_final_answer("q-trk-eval", "Final answer updated")
        assert updated_query.final_answer == "Final answer updated"

        # Feedback
        fb_model = tracker.record_feedback("q-trk-eval", rating=4.5, feedback_text="Helpful")
        assert fb_model.rating == 4.5

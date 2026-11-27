"""Unit tests for ProvenanceService facade."""

from __future__ import annotations

import pytest

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import ClaimType, DecisionAction, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.query import Query
from eclair.contracts.result import EclairResult
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.database.database import create_db_engine, init_db
from eclair.database.session import DatabaseSessionManager
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.provenance.service import ProvenanceService


@pytest.fixture
def service():
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    mgr = DatabaseSessionManager(engine=engine)
    srv = ProvenanceService(session_manager=mgr)
    yield srv
    engine.dispose()


def test_service_record_result_complete(service):
    # Construct complete EclairResult
    result = EclairResult(
        query_id="q-srv-comp-1",
        answer="Invoices are due in 30 calendar days.",
        claims=[
            Claim(claim_id="c-inv-1", text="Invoice due date is 30 days.", claim_type=ClaimType.FACTUAL),
        ],
        evidence=[
            Evidence(evidence_id="e-inv-1", text="Payment terms: net 30 days.", source="invoice_policy.md", relevance_score=0.96),
        ],
        verifications=[
            VerificationResult(claim_id="c-inv-1", status=VerificationStatus.SUPPORTED, evidence_ids=["e-inv-1"]),
        ],
        confidence=ConfidenceResult(raw_confidence=0.88, calibrated_ecs=0.91),
        risk=RiskResult(risk_level="LOW", risk_score=0.12),
        decision=DecisionResult(action=DecisionAction.RETURN, reason="Verified against policy."),
    )

    class DummyConsensus:
        agreement_score = 0.95
        consensus_level = "FULL"
        majority_answer = "30 days"
        details = {"method": "voting"}

    saved_id = service.record_result(
        result=result,
        question="When is invoice payment due?",
        consensus=DummyConsensus(),
    )
    assert saved_id == "q-srv-comp-1"

    # Verify audit trail can be retrieved
    trail = service.get_audit_trail("q-srv-comp-1")
    assert trail.query_id == "q-srv-comp-1"
    assert trail.question == "When is invoice payment due?"
    assert trail.final_answer == "Invoices are due in 30 calendar days."
    assert len(trail.claims) == 1
    assert len(trail.evidence) == 1
    assert len(trail.verifications) == 1
    assert trail.confidence["raw_confidence"] == 0.88
    assert trail.confidence["calibrated_ecs"] == 0.91
    assert trail.consensus["consensus_level"] == "FULL"
    assert trail.risk["risk_level"] == "LOW"
    assert trail.decision["action"] == "RETURN"
    assert trail.is_complete is True

    # Verify raw lineage
    lineage = service.get_lineage("q-srv-comp-1")
    assert lineage["query_id"] == "q-srv-comp-1"
    assert lineage["audit"]["decision_action"] == "RETURN"


def test_service_record_result_validation(service):
    # Non-EclairResult raises ContractValidationError
    with pytest.raises(ContractValidationError):
        service.record_result("not a result")  # type: ignore

    # Empty query_id
    class DummyInvalidResult(EclairResult):
        model_config = {"extra": "allow"}

    # Validation on empty string query_id handled directly
    with pytest.raises(ContractValidationError):
        service.record_result(EclairResult(query_id="   ", answer="Some answer"))


def test_service_record_feedback(service):
    # Record query first
    query = Query(query_id="q-fb-srv", question="How to return a product?")
    service.record_query(query)

    fb_id = service.record_feedback(
        query_id="q-fb-srv",
        rating=4.0,
        feedback_text="Helpful response",
        user_id="user-123",
    )
    assert fb_id is not None

    lineage = service.get_lineage("q-fb-srv")
    assert len(lineage["feedback"]) == 1
    assert lineage["feedback"][0]["feedback_id"] == fb_id
    assert lineage["feedback"][0]["rating"] == 4.0

    # Non-existent query raises ModuleError
    with pytest.raises(ModuleError) as exc_info:
        service.record_feedback(query_id="non-existent-query", rating=1.0)
    assert exc_info.value.code == "query_not_found"


def test_service_transaction_rollback_prevents_partial_writes(service):
    # If an error happens midway through record_result, no partial records remain
    class FaultyConfidence:
        pass  # Will trigger ContractValidationError in tracker.record_confidence

    result = EclairResult(
        query_id="q-rollback-atomic",
        answer="Some answer",
        claims=[Claim(claim_id="c-rb-1", text="Claim to rollback")],
    )
    # Inject faulty confidence that violates validation
    result.__dict__["confidence"] = "faulty_confidence"

    with pytest.raises(ContractValidationError):
        service.record_result(result, question="Rollback test")

    # Verify query was NOT persisted
    with pytest.raises(ModuleError) as exc_info:
        service.get_audit_trail("q-rollback-atomic")
    assert exc_info.value.code == "query_not_found"

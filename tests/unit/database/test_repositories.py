"""Unit tests for M14 database repository implementations."""

from __future__ import annotations

import pytest

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import ClaimType, DecisionAction, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.database.database import create_db_engine, init_db
from eclair.database.repositories import (
    AuditRepository,
    ClaimRepository,
    ConfidenceRepository,
    DecisionRepository,
    EvidenceRepository,
    QueryRepository,
    VerificationRepository,
)
from eclair.database.session import DatabaseSessionManager
from eclair.exceptions import ModuleError


@pytest.fixture
def session_manager():
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    mgr = DatabaseSessionManager(engine=engine)
    yield mgr
    engine.dispose()


def test_query_repository(session_manager):
    with session_manager.session() as session:
        repo = QueryRepository(session)
        created = repo.create("q-repo-1", "What is the policy?", final_answer="Policy answer")
        assert created.query_id == "q-repo-1"

        # Duplicate query_id raises
        with pytest.raises(ModuleError) as exc_info:
            repo.create("q-repo-1", "Duplicate question")
        assert exc_info.value.code == "duplicate_query_id"

        # Retrieval
        fetched = repo.get_by_id("q-repo-1")
        assert fetched is not None
        assert fetched.question == "What is the policy?"

        # Update final answer
        updated = repo.update_final_answer("q-repo-1", "New final answer")
        assert updated is not None
        assert updated.final_answer == "New final answer"

        # List
        queries = repo.list_queries(limit=10)
        assert len(queries) == 1

        # Delete
        assert repo.delete("q-repo-1") is True
        assert repo.get_by_id("q-repo-1") is None
        assert repo.delete("q-non-existent") is False


def test_claim_repository(session_manager):
    with session_manager.session() as session:
        QueryRepository(session).create("q-claim-test", "Question")
        repo = ClaimRepository(session)

        claims = [
            Claim(claim_id="c-1", text="First claim", claim_type=ClaimType.FACTUAL),
            Claim(claim_id="c-2", text="Second claim", claim_type=ClaimType.NUMERIC),
        ]
        created = repo.create_many(claims, "q-claim-test")
        assert len(created) == 2
        assert created[0].position == 0
        assert created[1].position == 1

        retrieved = repo.get_by_query_id("q-claim-test")
        assert len(retrieved) == 2
        assert retrieved[0].claim_id == "c-1"
        assert retrieved[1].claim_id == "c-2"
        assert retrieved[1].claim_type == "NUMERIC"


def test_evidence_repository(session_manager):
    with session_manager.session() as session:
        QueryRepository(session).create("q-ev-test", "Question")
        repo = EvidenceRepository(session)

        ev_list = [
            Evidence(evidence_id="e-1", text="Evidence 1", source="doc1.txt", relevance_score=0.9),
            Evidence(evidence_id="e-2", text="Evidence 2", source="doc2.txt", relevance_score=0.8),
        ]
        created = repo.create_many(ev_list, "q-ev-test")
        assert len(created) == 2

        retrieved = repo.get_by_query_id("q-ev-test")
        assert len(retrieved) == 2
        assert repo.get_by_id("e-1") is not None


def test_verification_repository(session_manager):
    with session_manager.session() as session:
        QueryRepository(session).create("q-ver-test", "Question")
        repo = VerificationRepository(session)

        ver_list = [
            VerificationResult(
                claim_id="c-1",
                status=VerificationStatus.SUPPORTED,
                evidence_ids=["e-1"],
            ),
            VerificationResult(
                claim_id="c-2",
                status=VerificationStatus.UNKNOWN,
                evidence_ids=[],
            ),
        ]
        repo.create_many(ver_list, "q-ver-test")

        retrieved = repo.get_by_query_id("q-ver-test")
        assert len(retrieved) == 2

        v1 = repo.get_by_claim_id("q-ver-test", "c-1")
        assert v1 is not None
        assert v1.status == "SUPPORTED"
        assert v1.evidence_ids == ["e-1"]


def test_confidence_and_decision_repository(session_manager):
    with session_manager.session() as session:
        QueryRepository(session).create("q-conf-test", "Question")

        conf_repo = ConfidenceRepository(session)
        conf_contract = ConfidenceResult(raw_confidence=0.85, calibrated_ecs=0.89)
        conf_repo.save_contract("q-conf-test", conf_contract)

        retrieved_conf = conf_repo.get_by_query_id("q-conf-test")
        assert retrieved_conf is not None
        assert retrieved_conf.raw_confidence == 0.85
        assert retrieved_conf.calibrated_ecs == 0.89

        dec_repo = DecisionRepository(session)
        dec_contract = DecisionResult(action=DecisionAction.RETURN, reason="Verified evidence")
        dec_repo.save_contract("q-conf-test", dec_contract)

        retrieved_dec = dec_repo.get_by_query_id("q-conf-test")
        assert retrieved_dec is not None
        assert retrieved_dec.action == "RETURN"
        assert retrieved_dec.reason == "Verified evidence"

        risk_contract = RiskResult(risk_level="LOW", risk_score=0.15)
        dec_repo.save_risk_contract("q-conf-test", risk_contract)

        retrieved_risk = dec_repo.get_risk_by_query_id("q-conf-test")
        assert retrieved_risk is not None
        assert retrieved_risk.risk_level == "LOW"


def test_audit_repository_and_full_lineage(session_manager):
    with session_manager.session() as session:
        QueryRepository(session).create("q-audit-test", "Query for audit", final_answer="Answer")
        ClaimRepository(session).create("c-10", "q-audit-test", "Claim text")
        EvidenceRepository(session).create("e-10", "q-audit-test", "Evidence text")
        VerificationRepository(session).create("q-audit-test", "c-10", "SUPPORTED", ["e-10"])
        ConfidenceRepository(session).create_or_update("q-audit-test", 0.92, 0.94)
        DecisionRepository(session).create_or_update("q-audit-test", "RETURN", "Solid")
        DecisionRepository(session).create_or_update_risk("q-audit-test", "LOW", 0.05)

        audit_repo = AuditRepository(session)
        audit_repo.record_consensus("q-audit-test", 1.0, "FULL", "Answer", {"voters": 3})
        audit_repo.record_feedback("q-audit-test", rating=5.0, feedback_text="Great answer")
        audit_repo.create("q-audit-test", final_answer="Answer", decision_action="RETURN", summary={"status": "ok"})

        # Test get_full_lineage
        lineage = audit_repo.get_full_lineage("q-audit-test")
        assert lineage is not None
        assert lineage["query_id"] == "q-audit-test"
        assert len(lineage["claims"]) == 1
        assert len(lineage["evidence"]) == 1
        assert len(lineage["verifications"]) == 1
        assert lineage["confidence"]["raw_confidence"] == 0.92
        assert lineage["consensus"]["consensus_level"] == "FULL"
        assert lineage["risk"]["risk_level"] == "LOW"
        assert lineage["decision"]["action"] == "RETURN"
        assert len(lineage["feedback"]) == 1
        assert lineage["audit"]["decision_action"] == "RETURN"

        # Non-existent query lineage
        assert audit_repo.get_full_lineage("q-unknown") is None

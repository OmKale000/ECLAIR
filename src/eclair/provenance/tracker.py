"""Provenance tracker for recording pipeline stage outputs (M14 Provenance & Database)."""

from __future__ import annotations

from typing import Any, Dict, Sequence

from sqlalchemy.orm import Session

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.evidence import Evidence
from eclair.contracts.query import Query
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.database.models.claim import ClaimModel
from eclair.database.models.confidence import ConfidenceModel
from eclair.database.models.consensus import ConsensusModel
from eclair.database.models.decision import DecisionModel
from eclair.database.models.evidence import EvidenceModel
from eclair.database.models.feedback import FeedbackModel
from eclair.database.models.query import QueryModel
from eclair.database.models.risk import RiskModel
from eclair.database.models.verification import VerificationModel
from eclair.database.repositories.audit_repository import AuditRepository
from eclair.database.repositories.claim_repository import ClaimRepository
from eclair.database.repositories.confidence_repository import ConfidenceRepository
from eclair.database.repositories.decision_repository import DecisionRepository
from eclair.database.repositories.evidence_repository import EvidenceRepository
from eclair.database.repositories.query_repository import QueryRepository
from eclair.database.repositories.verification_repository import VerificationRepository
from eclair.exceptions import ContractValidationError, ModuleError


class ProvenanceTracker:
    """Records query-to-decision lineage stage-by-stage into the database.

    Ensures strict validation of domain contracts and maintains ordering and relationships.
    Never silently drops records or swallows persistence errors.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.query_repo = QueryRepository(session)
        self.claim_repo = ClaimRepository(session)
        self.evidence_repo = EvidenceRepository(session)
        self.verification_repo = VerificationRepository(session)
        self.confidence_repo = ConfidenceRepository(session)
        self.decision_repo = DecisionRepository(session)
        self.audit_repo = AuditRepository(session)

    def record_query(self, query: Query, final_answer: str | None = None) -> QueryModel:
        """Record a Query entry.

        Args:
            query: Query domain contract.
            final_answer: Optional final answer text.

        Returns:
            Created or retrieved QueryModel.

        Raises:
            ContractValidationError: If query is invalid.
        """
        if not isinstance(query, Query):
            raise ContractValidationError("Expected Query domain contract", code="invalid_contract")
        if not query.query_id or not query.query_id.strip():
            raise ContractValidationError("Query must contain a non-empty query_id", code="empty_query_id")

        existing = self.query_repo.get_by_id(query.query_id)
        if existing is not None:
            if final_answer is not None:
                existing.final_answer = final_answer
                self.session.flush()
            return existing

        return self.query_repo.create(
            query_id=query.query_id,
            question=query.question,
            final_answer=final_answer,
        )

    def record_claims(self, query_id: str, claims: Sequence[Claim]) -> list[ClaimModel]:
        """Record extracted claims for a query.

        Args:
            query_id: Parent query identifier.
            claims: Sequence of Claim contracts.

        Returns:
            List of created ClaimModel records.

        Raises:
            ContractValidationError: If any item is not a Claim contract.
        """
        self._ensure_query_exists(query_id)
        for c in claims:
            if not isinstance(c, Claim):
                raise ContractValidationError("Items must be Claim domain contracts", code="invalid_contract")
        return self.claim_repo.create_many(claims, query_id)

    def record_evidence(self, query_id: str, evidence: Sequence[Evidence]) -> list[EvidenceModel]:
        """Record retrieved evidence passages for a query.

        Args:
            query_id: Parent query identifier.
            evidence: Sequence of Evidence contracts.

        Returns:
            List of created EvidenceModel records.

        Raises:
            ContractValidationError: If any item is not an Evidence contract.
        """
        self._ensure_query_exists(query_id)
        for ev in evidence:
            if not isinstance(ev, Evidence):
                raise ContractValidationError("Items must be Evidence domain contracts", code="invalid_contract")
        return self.evidence_repo.create_many(evidence, query_id)

    def record_verifications(
        self,
        query_id: str,
        verifications: Sequence[VerificationResult],
    ) -> list[VerificationModel]:
        """Record claim verification outcomes for a query.

        Args:
            query_id: Parent query identifier.
            verifications: Sequence of VerificationResult contracts.

        Returns:
            List of created VerificationModel records.

        Raises:
            ContractValidationError: If any item is not a VerificationResult contract.
        """
        self._ensure_query_exists(query_id)
        for v in verifications:
            if not isinstance(v, VerificationResult):
                raise ContractValidationError(
                    "Items must be VerificationResult domain contracts",
                    code="invalid_contract",
                )
        return self.verification_repo.create_many(verifications, query_id)

    def record_confidence(
        self,
        query_id: str,
        confidence: ConfidenceResult,
    ) -> ConfidenceModel:
        """Record raw confidence and calibrated ECS for a query.

        Args:
            query_id: Parent query identifier.
            confidence: ConfidenceResult contract.

        Returns:
            Created or updated ConfidenceModel.

        Raises:
            ContractValidationError: If confidence is not a ConfidenceResult contract.
        """
        self._ensure_query_exists(query_id)
        if not isinstance(confidence, ConfidenceResult):
            raise ContractValidationError(
                "Expected ConfidenceResult domain contract",
                code="invalid_contract",
            )
        return self.confidence_repo.save_contract(query_id, confidence)

    def record_risk(self, query_id: str, risk: RiskResult) -> RiskModel:
        """Record risk assessment for a query.

        Args:
            query_id: Parent query identifier.
            risk: RiskResult contract.

        Returns:
            Created or updated RiskModel.

        Raises:
            ContractValidationError: If risk is not a RiskResult contract.
        """
        self._ensure_query_exists(query_id)
        if not isinstance(risk, RiskResult):
            raise ContractValidationError("Expected RiskResult domain contract", code="invalid_contract")
        return self.decision_repo.save_risk_contract(query_id, risk)

    def record_decision(self, query_id: str, decision: DecisionResult) -> DecisionModel:
        """Record decision action and reason for a query.

        Args:
            query_id: Parent query identifier.
            decision: DecisionResult contract.

        Returns:
            Created or updated DecisionModel.

        Raises:
            ContractValidationError: If decision is not a DecisionResult contract.
        """
        self._ensure_query_exists(query_id)
        if not isinstance(decision, DecisionResult):
            raise ContractValidationError("Expected DecisionResult domain contract", code="invalid_contract")
        return self.decision_repo.save_contract(query_id, decision)

    def record_consensus(
        self,
        query_id: str,
        agreement_score: float,
        consensus_level: str,
        majority_answer: str | None = None,
        details: Dict[str, Any] | None = None,
    ) -> ConsensusModel:
        """Record multi-model consensus evaluation for a query.

        Args:
            query_id: Parent query identifier.
            agreement_score: Agreement score in [0.0, 1.0].
            consensus_level: ConsensusLevel string.
            majority_answer: Plurality answer text.
            details: Optional diagnostics.

        Returns:
            Created or updated ConsensusModel.
        """
        self._ensure_query_exists(query_id)
        return self.audit_repo.record_consensus(
            query_id=query_id,
            agreement_score=agreement_score,
            consensus_level=consensus_level,
            majority_answer=majority_answer,
            details=details,
        )

    def record_final_answer(self, query_id: str, final_answer: str) -> QueryModel:
        """Update the final answer for a query.

        Args:
            query_id: Parent query identifier.
            final_answer: Final answer text.

        Returns:
            Updated QueryModel.
        """
        record = self.query_repo.update_final_answer(query_id, final_answer)
        if record is None:
            raise ModuleError(f"Query {query_id!r} not found", code="query_not_found")
        return record

    def record_feedback(
        self,
        query_id: str,
        rating: float | None = None,
        feedback_text: str | None = None,
        user_id: str | None = None,
    ) -> FeedbackModel:
        """Record user feedback for a query.

        Args:
            query_id: Target query identifier.
            rating: Rating value.
            feedback_text: Feedback comment.
            user_id: Optional user identifier.

        Returns:
            Created FeedbackModel.
        """
        self._ensure_query_exists(query_id)
        return self.audit_repo.record_feedback(
            query_id=query_id,
            rating=rating,
            feedback_text=feedback_text,
            user_id=user_id,
        )

    def _ensure_query_exists(self, query_id: str) -> None:
        """Verify that the query exists before attaching lineage elements."""
        if not query_id or not str(query_id).strip():
            raise ContractValidationError("query_id cannot be empty", code="empty_query_id")
        existing = self.query_repo.get_by_id(query_id)
        if existing is None:
            raise ModuleError(
                f"Query with id {query_id!r} does not exist. Persist the query before its lineage.",
                code="query_not_found",
            )

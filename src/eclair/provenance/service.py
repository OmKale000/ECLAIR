"""High-level service coordinating provenance tracking and audit reconstruction."""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import Engine

from eclair.contracts.query import Query
from eclair.contracts.result import EclairResult
from eclair.database.database import create_db_engine
from eclair.database.session import DatabaseSessionManager
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.provenance.audit import AuditReconstructor, DecisionPath
from eclair.provenance.tracker import ProvenanceTracker


class ProvenanceService:
    """Service facade for provenance persistence and audit reconstruction.

    Provides transaction-safe entry points for engine outputs (EclairResult),
    user feedback, and audit decision path retrieval.
    """

    def __init__(
        self,
        session_manager: DatabaseSessionManager | None = None,
        engine: Engine | None = None,
    ) -> None:
        """Initialize ProvenanceService.

        Args:
            session_manager: Optional DatabaseSessionManager instance.
            engine: Optional SQLAlchemy Engine. If neither is passed, creates default engine.
        """
        if session_manager is not None:
            self.session_manager = session_manager
        elif engine is not None:
            self.session_manager = DatabaseSessionManager(engine=engine)
        else:
            self.session_manager = DatabaseSessionManager(engine=create_db_engine())

    def record_query(self, query: Query, final_answer: str | None = None) -> str:
        """Record or update a Query entry.

        Args:
            query: Query domain contract.
            final_answer: Optional final answer text.

        Returns:
            The query_id string.
        """
        with self.session_manager.session() as session:
            tracker = ProvenanceTracker(session)
            model = tracker.record_query(query, final_answer=final_answer)
            return model.query_id

    def record_result(
        self,
        result: EclairResult,
        question: str | None = None,
        consensus: Any | None = None,
    ) -> str:
        """Atomically persist complete pipeline outputs from an EclairResult.

        Coordinates writes across queries, claims, evidence, verifications,
        confidence, risk, decision, consensus, and generates an audit log entry.
        All operations run in a single transaction; failure rolls back completely.

        Args:
            result: Aggregate EclairResult contract from the engine.
            question: Optional user question text (used if Query not previously recorded).
            consensus: Optional consensus evaluation (e.g. M09 ConsensusResult or dict).

        Returns:
            The query_id string.

        Raises:
            ContractValidationError: If input result is not an EclairResult.
            ModuleError: If database persistence fails.
        """
        if not isinstance(result, EclairResult):
            raise ContractValidationError(
                "result must be an instance of EclairResult",
                code="invalid_contract",
            )
        if not result.query_id or not str(result.query_id).strip():
            raise ContractValidationError(
                "result.query_id cannot be empty",
                code="empty_query_id",
            )

        with self.session_manager.session() as session:
            tracker = ProvenanceTracker(session)

            # Ensure query row exists
            query_contract = Query(
                query_id=result.query_id,
                question=question or f"Query {result.query_id}",
            )
            tracker.record_query(query_contract, final_answer=result.answer)

            # Persist stage outputs
            if result.claims:
                tracker.record_claims(result.query_id, result.claims)

            if result.evidence:
                tracker.record_evidence(result.query_id, result.evidence)

            if result.verifications:
                tracker.record_verifications(result.query_id, result.verifications)

            if result.confidence is not None:
                tracker.record_confidence(result.query_id, result.confidence)

            if result.risk is not None:
                tracker.record_risk(result.query_id, result.risk)

            if result.decision is not None:
                tracker.record_decision(result.query_id, result.decision)

            # Record consensus if provided
            if consensus is not None:
                self._record_consensus_object(tracker, result.query_id, consensus)

            # Generate structured audit log entry
            decision_action = (
                result.decision.action.value
                if result.decision and hasattr(result.decision.action, "value")
                else (str(result.decision.action) if result.decision else None)
            )

            summary: dict[str, Any] = {
                "claims_count": len(result.claims),
                "evidence_count": len(result.evidence),
                "verifications_count": len(result.verifications),
                "raw_confidence": (
                    result.confidence.raw_confidence if result.confidence else None
                ),
                "calibrated_ecs": (
                    result.confidence.calibrated_ecs if result.confidence else None
                ),
                "risk_level": result.risk.risk_level if result.risk else None,
                "decision_action": decision_action,
            }

            tracker.audit_repo.create(
                query_id=result.query_id,
                final_answer=result.answer,
                decision_action=decision_action,
                summary=summary,
            )

            return result.query_id

    def record_feedback(
        self,
        query_id: str,
        rating: float | None = None,
        feedback_text: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Record user feedback for an existing query.

        Args:
            query_id: Target query identifier.
            rating: Optional rating score.
            feedback_text: Optional user comments.
            user_id: Optional user identifier.

        Returns:
            Created feedback_id string.

        Raises:
            ModuleError: If query_id does not exist.
        """
        with self.session_manager.session() as session:
            tracker = ProvenanceTracker(session)
            model = tracker.record_feedback(
                query_id=query_id,
                rating=rating,
                feedback_text=feedback_text,
                user_id=user_id,
            )
            return model.feedback_id

    def get_audit_trail(self, query_id: str) -> DecisionPath:
        """Retrieve and reconstruct the decision path for a query.

        Args:
            query_id: Query identifier.

        Returns:
            DecisionPath reconstructed from persisted records.

        Raises:
            ModuleError: If query_id is not found.
        """
        with self.session_manager.session() as session:
            reconstructor = AuditReconstructor(session)
            return reconstructor.reconstruct(query_id)

    def get_lineage(self, query_id: str) -> Dict[str, Any]:
        """Retrieve raw lineage dictionary for a query.

        Args:
            query_id: Query identifier.

        Returns:
            Dictionary containing complete lineage tables.

        Raises:
            ModuleError: If query_id is not found.
        """
        with self.session_manager.session() as session:
            tracker = ProvenanceTracker(session)
            lineage = tracker.audit_repo.get_full_lineage(query_id)
            if lineage is None:
                raise ModuleError(
                    f"Query {query_id!r} not found",
                    code="query_not_found",
                )
            return lineage

    def _record_consensus_object(
        self,
        tracker: ProvenanceTracker,
        query_id: str,
        consensus: Any,
    ) -> None:
        """Extract attributes from consensus object and record them."""
        agreement_score = getattr(consensus, "agreement_score", 0.0)
        consensus_level_raw = getattr(consensus, "consensus_level", "PARTIAL")
        consensus_level = (
            consensus_level_raw.value
            if hasattr(consensus_level_raw, "value")
            else str(consensus_level_raw)
        )
        majority_answer = getattr(consensus, "majority_answer", None)
        details = getattr(consensus, "details", None)

        tracker.record_consensus(
            query_id=query_id,
            agreement_score=agreement_score,
            consensus_level=consensus_level,
            majority_answer=majority_answer,
            details=details if isinstance(details, dict) else None,
        )

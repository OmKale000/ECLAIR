"""Repository for audit logs, full lineage retrieval, feedback, and consensus."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from eclair.database.models.audit import AuditModel
from eclair.database.models.consensus import ConsensusModel
from eclair.database.models.feedback import FeedbackModel
from eclair.database.models.query import QueryModel


class AuditRepository:
    """Repository operations for AuditModel, full query lineage, feedback, and consensus."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        query_id: str,
        final_answer: str | None = None,
        decision_action: str | None = None,
        summary: Dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> AuditModel:
        """Create or update an AuditModel log for a query.

        Args:
            query_id: Unique query identifier.
            final_answer: Optional final answer text.
            decision_action: Selected decision action.
            summary: Optional structured summary dictionary.
            timestamp: Audit timestamp. Defaults to UTC now.

        Returns:
            Created or updated AuditModel.
        """
        record = self.get_by_query_id(query_id)
        ts = timestamp or datetime.now(timezone.utc)
        if record is None:
            record = AuditModel(
                query_id=query_id,
                final_answer=final_answer,
                decision_action=decision_action,
                summary=summary,
                timestamp=ts,
            )
            self.session.add(record)
        else:
            record.final_answer = final_answer
            record.decision_action = decision_action
            record.summary = summary
            record.timestamp = ts
        self.session.flush()
        return record

    def get_by_query_id(self, query_id: str) -> AuditModel | None:
        """Retrieve AuditModel by query_id.

        Args:
            query_id: Query identifier.

        Returns:
            AuditModel or None.
        """
        stmt = select(AuditModel).where(AuditModel.query_id == query_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def record_consensus(
        self,
        query_id: str,
        agreement_score: float,
        consensus_level: str,
        majority_answer: str | None = None,
        details: Dict[str, Any] | None = None,
    ) -> ConsensusModel:
        """Create or update a ConsensusModel record for a query.

        Args:
            query_id: Query identifier.
            agreement_score: Numeric agreement score.
            consensus_level: ConsensusLevel string.
            majority_answer: Plurality answer text.
            details: Optional diagnostic dictionary.

        Returns:
            Created or updated ConsensusModel.
        """
        stmt = select(ConsensusModel).where(ConsensusModel.query_id == query_id)
        record = self.session.execute(stmt).scalar_one_or_none()
        if record is None:
            record = ConsensusModel(
                query_id=query_id,
                agreement_score=agreement_score,
                consensus_level=consensus_level,
                majority_answer=majority_answer,
                details=details,
            )
            self.session.add(record)
        else:
            record.agreement_score = agreement_score
            record.consensus_level = consensus_level
            record.majority_answer = majority_answer
            record.details = details
        self.session.flush()
        return record

    def get_consensus_by_query_id(self, query_id: str) -> ConsensusModel | None:
        """Retrieve ConsensusModel for a query.

        Args:
            query_id: Query identifier.

        Returns:
            ConsensusModel or None.
        """
        stmt = select(ConsensusModel).where(ConsensusModel.query_id == query_id)
        return self.session.execute(stmt).scalar_one_or_none()

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
            feedback_text: User comment text.
            user_id: Optional user identifier.

        Returns:
            Created FeedbackModel.
        """
        record = FeedbackModel(
            query_id=query_id,
            rating=rating,
            feedback_text=feedback_text,
            user_id=user_id,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_feedback_by_query_id(self, query_id: str) -> Sequence[FeedbackModel]:
        """Retrieve all feedback entries for a query.

        Args:
            query_id: Query identifier.

        Returns:
            Sequence of FeedbackModel records.
        """
        stmt = (
            select(FeedbackModel)
            .where(FeedbackModel.query_id == query_id)
            .order_by(FeedbackModel.created_at.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_full_lineage(self, query_id: str) -> Dict[str, Any] | None:
        """Retrieve complete lineage graph for a query with all associations.

        Args:
            query_id: Query identifier.

        Returns:
            Dictionary containing all lineage tables data or None if query not found.
        """
        stmt = (
            select(QueryModel)
            .where(QueryModel.query_id == query_id)
            .options(
                joinedload(QueryModel.claims),
                joinedload(QueryModel.evidence),
                joinedload(QueryModel.verifications),
                joinedload(QueryModel.confidence),
                joinedload(QueryModel.consensus),
                joinedload(QueryModel.risk),
                joinedload(QueryModel.decision),
                joinedload(QueryModel.feedbacks),
                joinedload(QueryModel.audit),
            )
        )
        query = self.session.execute(stmt).unique().scalar_one_or_none()
        if query is None:
            return None

        return {
            "query_id": query.query_id,
            "question": query.question,
            "final_answer": query.final_answer,
            "created_at": query.created_at.isoformat() if query.created_at else None,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "text": c.text,
                    "claim_type": c.claim_type,
                    "position": c.position,
                }
                for c in query.claims
            ],
            "evidence": [
                {
                    "evidence_id": e.evidence_id,
                    "text": e.text,
                    "source": e.source,
                    "relevance_score": e.relevance_score,
                }
                for e in query.evidence
            ],
            "verifications": [
                {
                    "claim_id": v.claim_id,
                    "status": v.status,
                    "evidence_ids": v.evidence_ids,
                }
                for v in query.verifications
            ],
            "confidence": (
                {
                    "raw_confidence": query.confidence.raw_confidence,
                    "calibrated_ecs": query.confidence.calibrated_ecs,
                }
                if query.confidence
                else None
            ),
            "consensus": (
                {
                    "agreement_score": query.consensus.agreement_score,
                    "consensus_level": query.consensus.consensus_level,
                    "majority_answer": query.consensus.majority_answer,
                    "details": query.consensus.details,
                }
                if query.consensus
                else None
            ),
            "risk": (
                {
                    "risk_level": query.risk.risk_level,
                    "risk_score": query.risk.risk_score,
                }
                if query.risk
                else None
            ),
            "decision": (
                {
                    "action": query.decision.action,
                    "reason": query.decision.reason,
                }
                if query.decision
                else None
            ),
            "feedback": [
                {
                    "feedback_id": f.feedback_id,
                    "rating": f.rating,
                    "feedback_text": f.feedback_text,
                    "user_id": f.user_id,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in query.feedbacks
            ],
            "audit": (
                {
                    "audit_id": query.audit.audit_id,
                    "timestamp": query.audit.timestamp.isoformat() if query.audit.timestamp else None,
                    "final_answer": query.audit.final_answer,
                    "decision_action": query.audit.decision_action,
                    "summary": query.audit.summary,
                }
                if query.audit
                else None
            ),
        }

"""ORM model for user queries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eclair.database.models import Base

if TYPE_CHECKING:
    from eclair.database.models.audit import AuditModel
    from eclair.database.models.claim import ClaimModel
    from eclair.database.models.confidence import ConfidenceModel
    from eclair.database.models.consensus import ConsensusModel
    from eclair.database.models.decision import DecisionModel
    from eclair.database.models.evidence import EvidenceModel
    from eclair.database.models.feedback import FeedbackModel
    from eclair.database.models.risk import RiskModel
    from eclair.database.models.verification import VerificationModel


class QueryModel(Base):
    """Database representation of an ECLAIR query and its lineage anchor."""

    __tablename__ = "queries"

    query_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships to lineage elements
    claims: Mapped[List[ClaimModel]] = relationship(
        "ClaimModel",
        back_populates="query",
        cascade="all, delete-orphan",
        order_by="ClaimModel.position",
    )
    evidence: Mapped[List[EvidenceModel]] = relationship(
        "EvidenceModel",
        back_populates="query",
        cascade="all, delete-orphan",
    )
    verifications: Mapped[List[VerificationModel]] = relationship(
        "VerificationModel",
        back_populates="query",
        cascade="all, delete-orphan",
    )
    confidence: Mapped[ConfidenceModel | None] = relationship(
        "ConfidenceModel",
        back_populates="query",
        uselist=False,
        cascade="all, delete-orphan",
    )
    consensus: Mapped[ConsensusModel | None] = relationship(
        "ConsensusModel",
        back_populates="query",
        uselist=False,
        cascade="all, delete-orphan",
    )
    risk: Mapped[RiskModel | None] = relationship(
        "RiskModel",
        back_populates="query",
        uselist=False,
        cascade="all, delete-orphan",
    )
    decision: Mapped[DecisionModel | None] = relationship(
        "DecisionModel",
        back_populates="query",
        uselist=False,
        cascade="all, delete-orphan",
    )
    feedbacks: Mapped[List[FeedbackModel]] = relationship(
        "FeedbackModel",
        back_populates="query",
        cascade="all, delete-orphan",
    )
    audit: Mapped[AuditModel | None] = relationship(
        "AuditModel",
        back_populates="query",
        uselist=False,
        cascade="all, delete-orphan",
    )

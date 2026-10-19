"""ORM model for query audit trail entries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from eclair.database.models import Base

if TYPE_CHECKING:
    from eclair.database.models.query import QueryModel


class AuditModel(Base):
    """Database representation of an audit record summarizing query lineage."""

    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: uuid4().hex,
        index=True,
    )
    query_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("queries.query_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary: Mapped[Dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    query: Mapped[QueryModel] = relationship("QueryModel", back_populates="audit")

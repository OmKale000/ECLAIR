"""ORM model for retrieved evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eclair.database.models import Base

if TYPE_CHECKING:
    from eclair.database.models.query import QueryModel


class EvidenceModel(Base):
    """Database representation of retrieved evidence passages."""

    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    query_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("queries.query_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    query: Mapped[QueryModel] = relationship("QueryModel", back_populates="evidence")

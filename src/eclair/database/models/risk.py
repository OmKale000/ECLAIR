"""ORM model for risk classification results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eclair.database.models import Base

if TYPE_CHECKING:
    from eclair.database.models.query import QueryModel


class RiskModel(Base):
    """Database representation of risk assessment for a query."""

    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("queries.query_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    query: Mapped[QueryModel] = relationship("QueryModel", back_populates="risk")

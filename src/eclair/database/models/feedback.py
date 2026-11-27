"""ORM model for user feedback."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eclair.database.models import Base

if TYPE_CHECKING:
    from eclair.database.models.query import QueryModel


class FeedbackModel(Base):
    """Database representation of user feedback for a query."""

    __tablename__ = "feedbacks"

    feedback_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: uuid4().hex,
        index=True,
    )
    query_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("queries.query_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    query: Mapped[QueryModel] = relationship("QueryModel", back_populates="feedbacks")

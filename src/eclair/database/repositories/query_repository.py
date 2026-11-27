"""Repository for querying and persisting query entries."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from eclair.database.models.query import QueryModel
from eclair.exceptions import ModuleError


class QueryRepository:
    """Repository operations for QueryModel."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        query_id: str,
        question: str,
        final_answer: str | None = None,
    ) -> QueryModel:
        """Create a new QueryModel record.

        Args:
            query_id: Unique query identifier.
            question: User question text.
            final_answer: Optional final answer text.

        Returns:
            Created QueryModel.

        Raises:
            ModuleError: If query_id already exists or persistence fails.
        """
        existing = self.get_by_id(query_id)
        if existing is not None:
            raise ModuleError(
                f"Query with id {query_id!r} already exists",
                code="duplicate_query_id",
            )
        record = QueryModel(
            query_id=query_id,
            question=question,
            final_answer=final_answer,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_by_id(self, query_id: str) -> QueryModel | None:
        """Retrieve QueryModel by query_id.

        Args:
            query_id: Query identifier.

        Returns:
            QueryModel or None if not found.
        """
        stmt = select(QueryModel).where(QueryModel.query_id == query_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def update_final_answer(self, query_id: str, final_answer: str) -> QueryModel | None:
        """Update final answer text for an existing query.

        Args:
            query_id: Query identifier.
            final_answer: Generated answer text.

        Returns:
            Updated QueryModel or None if query not found.
        """
        record = self.get_by_id(query_id)
        if record is None:
            return None
        record.final_answer = final_answer
        self.session.flush()
        return record

    def list_queries(self, limit: int = 50, offset: int = 0) -> Sequence[QueryModel]:
        """List queries ordered by creation time descending.

        Args:
            limit: Maximum count to return.
            offset: Offset index.

        Returns:
            Sequence of QueryModel records.
        """
        stmt = (
            select(QueryModel)
            .order_by(QueryModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return self.session.execute(stmt).scalars().all()

    def delete(self, query_id: str) -> bool:
        """Delete a query and its cascaded lineage records.

        Args:
            query_id: Query identifier.

        Returns:
            True if deleted, False if query was not found.
        """
        record = self.get_by_id(query_id)
        if record is None:
            return False
        self.session.delete(record)
        self.session.flush()
        return True

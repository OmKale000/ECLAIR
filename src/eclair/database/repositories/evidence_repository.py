"""Repository for persisting and querying retrieved evidence records."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from eclair.contracts.evidence import Evidence
from eclair.database.models.evidence import EvidenceModel


class EvidenceRepository:
    """Repository operations for EvidenceModel."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        evidence_id: str,
        query_id: str,
        text: str,
        source: str | None = None,
        relevance_score: float | None = None,
    ) -> EvidenceModel:
        """Create a single EvidenceModel record.

        Args:
            evidence_id: Unique evidence identifier.
            query_id: Parent query identifier.
            text: Evidence passage text.
            source: Source document name or origin.
            relevance_score: Optional retrieval/quality score.

        Returns:
            Created EvidenceModel.
        """
        record = EvidenceModel(
            evidence_id=evidence_id,
            query_id=query_id,
            text=text,
            source=source,
            relevance_score=relevance_score,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def create_many(
        self,
        evidence_list: Sequence[Evidence],
        query_id: str,
    ) -> list[EvidenceModel]:
        """Persist a list of M01 Evidence contracts.

        Args:
            evidence_list: Sequence of Evidence domain contracts.
            query_id: Parent query identifier.

        Returns:
            List of created EvidenceModel records.
        """
        records: list[EvidenceModel] = []
        for ev in evidence_list:
            record = EvidenceModel(
                evidence_id=ev.evidence_id,
                query_id=query_id,
                text=ev.text,
                source=ev.source,
                relevance_score=ev.relevance_score,
            )
            self.session.add(record)
            records.append(record)
        self.session.flush()
        return records

    def get_by_query_id(self, query_id: str) -> Sequence[EvidenceModel]:
        """Retrieve all evidence passages for a query.

        Args:
            query_id: Query identifier.

        Returns:
            Sequence of EvidenceModel records.
        """
        stmt = (
            select(EvidenceModel)
            .where(EvidenceModel.query_id == query_id)
            .order_by(EvidenceModel.created_at.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_by_id(self, evidence_id: str) -> EvidenceModel | None:
        """Retrieve EvidenceModel by evidence_id.

        Args:
            evidence_id: Evidence identifier.

        Returns:
            EvidenceModel or None.
        """
        stmt = select(EvidenceModel).where(EvidenceModel.evidence_id == evidence_id)
        return self.session.execute(stmt).scalar_one_or_none()

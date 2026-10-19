"""Repository for persisting and querying atomic claim records."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from eclair.contracts.claim import Claim
from eclair.database.models.claim import ClaimModel


class ClaimRepository:
    """Repository operations for ClaimModel."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        claim_id: str,
        query_id: str,
        text: str,
        claim_type: str = "OTHER",
        position: int = 0,
    ) -> ClaimModel:
        """Create a single ClaimModel record.

        Args:
            claim_id: Unique claim identifier.
            query_id: Parent query identifier.
            text: Claim text.
            claim_type: String representation of ClaimType.
            position: Ordering index within the query claims.

        Returns:
            Created ClaimModel.
        """
        record = ClaimModel(
            claim_id=claim_id,
            query_id=query_id,
            text=text,
            claim_type=claim_type,
            position=position,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def create_many(
        self,
        claims: Sequence[Claim],
        query_id: str,
    ) -> list[ClaimModel]:
        """Persist a list of M01 Claim contracts preserving order.

        Args:
            claims: Sequence of Claim domain contracts.
            query_id: Parent query identifier.

        Returns:
            List of created ClaimModel records.
        """
        records: list[ClaimModel] = []
        for idx, c in enumerate(claims):
            claim_type_str = c.claim_type.value if hasattr(c.claim_type, "value") else str(c.claim_type)
            record = ClaimModel(
                claim_id=c.claim_id,
                query_id=query_id,
                text=c.text,
                claim_type=claim_type_str,
                position=idx,
            )
            self.session.add(record)
            records.append(record)
        self.session.flush()
        return records

    def get_by_query_id(self, query_id: str) -> Sequence[ClaimModel]:
        """Retrieve all claims for a given query ordered by position.

        Args:
            query_id: Query identifier.

        Returns:
            Sequence of ClaimModel records.
        """
        stmt = (
            select(ClaimModel)
            .where(ClaimModel.query_id == query_id)
            .order_by(ClaimModel.position.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_by_id(self, claim_id: str) -> ClaimModel | None:
        """Retrieve ClaimModel by claim_id.

        Args:
            claim_id: Claim identifier.

        Returns:
            ClaimModel or None.
        """
        stmt = select(ClaimModel).where(ClaimModel.claim_id == claim_id)
        return self.session.execute(stmt).scalar_one_or_none()

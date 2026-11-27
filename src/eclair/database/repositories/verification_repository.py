"""Repository for persisting and querying claim verification records."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from eclair.contracts.verification import VerificationResult
from eclair.database.models.verification import VerificationModel


class VerificationRepository:
    """Repository operations for VerificationModel."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        query_id: str,
        claim_id: str,
        status: str,
        evidence_ids: list[str] | None = None,
    ) -> VerificationModel:
        """Create a single VerificationModel record.

        Args:
            query_id: Parent query identifier.
            claim_id: Verified claim identifier.
            status: Verification status string (e.g. SUPPORTED, CONTRADICTED, UNKNOWN).
            evidence_ids: List of evidence identifier strings.

        Returns:
            Created VerificationModel.
        """
        record = VerificationModel(
            query_id=query_id,
            claim_id=claim_id,
            status=status,
            evidence_ids=evidence_ids or [],
        )
        self.session.add(record)
        self.session.flush()
        return record

    def create_many(
        self,
        verifications: Sequence[VerificationResult],
        query_id: str,
    ) -> list[VerificationModel]:
        """Persist a list of M01 VerificationResult contracts.

        Args:
            verifications: Sequence of VerificationResult domain contracts.
            query_id: Parent query identifier.

        Returns:
            List of created VerificationModel records.
        """
        records: list[VerificationModel] = []
        for v in verifications:
            status_str = v.status.value if hasattr(v.status, "value") else str(v.status)
            record = VerificationModel(
                query_id=query_id,
                claim_id=v.claim_id,
                status=status_str,
                evidence_ids=list(v.evidence_ids),
            )
            self.session.add(record)
            records.append(record)
        self.session.flush()
        return records

    def get_by_query_id(self, query_id: str) -> Sequence[VerificationModel]:
        """Retrieve all verification records for a query.

        Args:
            query_id: Query identifier.

        Returns:
            Sequence of VerificationModel records.
        """
        stmt = (
            select(VerificationModel)
            .where(VerificationModel.query_id == query_id)
            .order_by(VerificationModel.created_at.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def get_by_claim_id(self, query_id: str, claim_id: str) -> VerificationModel | None:
        """Retrieve verification record for a specific claim within a query.

        Args:
            query_id: Query identifier.
            claim_id: Claim identifier.

        Returns:
            VerificationModel or None.
        """
        stmt = select(VerificationModel).where(
            VerificationModel.query_id == query_id,
            VerificationModel.claim_id == claim_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

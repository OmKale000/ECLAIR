"""Repository for persisting and querying confidence estimation records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from eclair.contracts.confidence import ConfidenceResult
from eclair.database.models.confidence import ConfidenceModel


class ConfidenceRepository:
    """Repository operations for ConfidenceModel."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_or_update(
        self,
        query_id: str,
        raw_confidence: float,
        calibrated_ecs: float | None = None,
    ) -> ConfidenceModel:
        """Create or update a ConfidenceModel for a query.

        Args:
            query_id: Parent query identifier.
            raw_confidence: Raw fused confidence value.
            calibrated_ecs: Optional calibrated ECS score.

        Returns:
            Created or updated ConfidenceModel.
        """
        record = self.get_by_query_id(query_id)
        if record is None:
            record = ConfidenceModel(
                query_id=query_id,
                raw_confidence=raw_confidence,
                calibrated_ecs=calibrated_ecs,
            )
            self.session.add(record)
        else:
            record.raw_confidence = raw_confidence
            if calibrated_ecs is not None:
                record.calibrated_ecs = calibrated_ecs
        self.session.flush()
        return record

    def save_contract(
        self,
        query_id: str,
        confidence: ConfidenceResult,
    ) -> ConfidenceModel:
        """Persist an M01 ConfidenceResult domain contract.

        Args:
            query_id: Parent query identifier.
            confidence: ConfidenceResult domain contract.

        Returns:
            Created or updated ConfidenceModel.
        """
        return self.create_or_update(
            query_id=query_id,
            raw_confidence=confidence.raw_confidence,
            calibrated_ecs=confidence.calibrated_ecs,
        )

    def get_by_query_id(self, query_id: str) -> ConfidenceModel | None:
        """Retrieve ConfidenceModel for a query.

        Args:
            query_id: Query identifier.

        Returns:
            ConfidenceModel or None.
        """
        stmt = select(ConfidenceModel).where(ConfidenceModel.query_id == query_id)
        return self.session.execute(stmt).scalar_one_or_none()

"""Repository for persisting and querying decision and risk records."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from eclair.contracts.decision import DecisionResult
from eclair.contracts.risk import RiskResult
from eclair.database.models.decision import DecisionModel
from eclair.database.models.risk import RiskModel


class DecisionRepository:
    """Repository operations for DecisionModel and RiskModel."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_or_update(
        self,
        query_id: str,
        action: str,
        reason: str | None = None,
    ) -> DecisionModel:
        """Create or update a DecisionModel for a query.

        Args:
            query_id: Parent query identifier.
            action: Decision action name.
            reason: Optional justification text.

        Returns:
            Created or updated DecisionModel.
        """
        record = self.get_by_query_id(query_id)
        if record is None:
            record = DecisionModel(
                query_id=query_id,
                action=action,
                reason=reason,
            )
            self.session.add(record)
        else:
            record.action = action
            record.reason = reason
        self.session.flush()
        return record

    def save_contract(
        self,
        query_id: str,
        decision: DecisionResult,
    ) -> DecisionModel:
        """Persist an M01 DecisionResult domain contract.

        Args:
            query_id: Parent query identifier.
            decision: DecisionResult domain contract.

        Returns:
            Created or updated DecisionModel.
        """
        action_str = decision.action.value if hasattr(decision.action, "value") else str(decision.action)
        return self.create_or_update(
            query_id=query_id,
            action=action_str,
            reason=decision.reason,
        )

    def get_by_query_id(self, query_id: str) -> DecisionModel | None:
        """Retrieve DecisionModel for a query.

        Args:
            query_id: Query identifier.

        Returns:
            DecisionModel or None.
        """
        stmt = select(DecisionModel).where(DecisionModel.query_id == query_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_or_update_risk(
        self,
        query_id: str,
        risk_level: str,
        risk_score: float | None = None,
    ) -> RiskModel:
        """Create or update a RiskModel for a query.

        Args:
            query_id: Parent query identifier.
            risk_level: Risk level string.
            risk_score: Optional numeric risk score.

        Returns:
            Created or updated RiskModel.
        """
        stmt = select(RiskModel).where(RiskModel.query_id == query_id)
        record = self.session.execute(stmt).scalar_one_or_none()
        if record is None:
            record = RiskModel(
                query_id=query_id,
                risk_level=risk_level,
                risk_score=risk_score,
            )
            self.session.add(record)
        else:
            record.risk_level = risk_level
            record.risk_score = risk_score
        self.session.flush()
        return record

    def save_risk_contract(
        self,
        query_id: str,
        risk: RiskResult,
    ) -> RiskModel:
        """Persist an M01 RiskResult domain contract.

        Args:
            query_id: Parent query identifier.
            risk: RiskResult domain contract.

        Returns:
            Created or updated RiskModel.
        """
        return self.create_or_update_risk(
            query_id=query_id,
            risk_level=risk.risk_level,
            risk_score=risk.risk_score,
        )

    def get_risk_by_query_id(self, query_id: str) -> RiskModel | None:
        """Retrieve RiskModel for a query.

        Args:
            query_id: Query identifier.

        Returns:
            RiskModel or None.
        """
        stmt = select(RiskModel).where(RiskModel.query_id == query_id)
        return self.session.execute(stmt).scalar_one_or_none()

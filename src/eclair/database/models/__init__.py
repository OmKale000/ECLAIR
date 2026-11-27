"""SQLAlchemy ORM base and models for M14 Provenance & Database."""

# ruff: noqa: E402

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all ECLAIR ORM models."""

    pass


from eclair.database.models.audit import AuditModel
from eclair.database.models.claim import ClaimModel
from eclair.database.models.confidence import ConfidenceModel
from eclair.database.models.consensus import ConsensusModel
from eclair.database.models.decision import DecisionModel
from eclair.database.models.evidence import EvidenceModel
from eclair.database.models.feedback import FeedbackModel
from eclair.database.models.query import QueryModel
from eclair.database.models.risk import RiskModel
from eclair.database.models.verification import VerificationModel

__all__ = [
    "Base",
    "QueryModel",
    "ClaimModel",
    "EvidenceModel",
    "VerificationModel",
    "ConfidenceModel",
    "ConsensusModel",
    "RiskModel",
    "DecisionModel",
    "FeedbackModel",
    "AuditModel",
]

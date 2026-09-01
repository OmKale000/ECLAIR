"""Shared ECLAIR contracts (M01 Foundation).

Single import surface for the frozen shared contracts, enums, and interfaces
used by all modules M02-M18. Only M01 may define or change anything here.
"""

from __future__ import annotations

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import ClaimType, ConsensusLevel, DecisionAction, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.interfaces import (
    ClaimExtractor,
    ConfidenceEstimator,
    DecisionEngine,
    LLMProvider,
    Retriever,
    Verifier,
)
from eclair.contracts.query import Query
from eclair.contracts.result import EclairResult
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult

__all__ = [
    # Contracts
    "Query",
    "Claim",
    "Evidence",
    "VerificationResult",
    "ConfidenceResult",
    "RiskResult",
    "DecisionResult",
    "EclairResult",
    # Enums
    "VerificationStatus",
    "DecisionAction",
    "ConsensusLevel",
    "ClaimType",
    # Interfaces
    "LLMProvider",
    "ClaimExtractor",
    "Retriever",
    "Verifier",
    "ConfidenceEstimator",
    "DecisionEngine",
]

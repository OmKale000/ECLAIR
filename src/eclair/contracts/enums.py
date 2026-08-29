"""Frozen enumerations shared across ECLAIR contracts (M01 Foundation).

These enum members are FROZEN by the Spec / SHARED_CONTRACTS_REFERENCE.md sec.2.
No module may add, rename, or remove members.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["VerificationStatus", "DecisionAction", "ConsensusLevel"]


class VerificationStatus(str, Enum):
    """Claim verification status (Spec sec.M07, sec.4.9).

    NLI mapping: ENTAILMENT -> SUPPORTED, CONTRADICTION -> CONTRADICTED,
    NEUTRAL -> UNKNOWN. Absence of evidence MUST map to UNKNOWN, never SUPPORTED.
    """

    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class DecisionAction(str, Enum):
    """Decision actions selectable by the Risk & Decision Engine (Spec sec.M13)."""

    RETURN = "RETURN"
    VERIFY_MORE = "VERIFY_MORE"
    REGENERATE = "REGENERATE"
    ABSTAIN = "ABSTAIN"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK_ACTION = "BLOCK_ACTION"


class ConsensusLevel(str, Enum):
    """Multi-model consensus level (Spec sec.M09).

    A full or partial consensus label; the numeric agreement score is carried
    separately on the contract that uses this enum.
    """

    FULL = "FULL"
    PARTIAL = "PARTIAL"

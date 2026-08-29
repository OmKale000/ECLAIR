"""DecisionResult contract (M01 Foundation).

The action selected by M13 (Risk & Decision Engine) for a response
(Spec sec.4.1, sec.M13). The action is one of the frozen DecisionAction members.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from eclair.contracts.enums import DecisionAction

__all__ = ["DecisionResult"]


class DecisionResult(BaseModel):
    """The decision taken for a response."""

    model_config = {"extra": "forbid"}

    action: DecisionAction = Field(
        ...,
        description="One of RETURN/VERIFY_MORE/REGENERATE/ABSTAIN/HUMAN_REVIEW/BLOCK_ACTION.",
    )
    reason: str | None = Field(
        default=None,
        description="Optional human-readable justification for the decision.",
    )

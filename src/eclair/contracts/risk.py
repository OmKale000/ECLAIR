"""RiskResult contract (M01 Foundation).

Risk classification for a response, produced by M13 (Risk & Decision Engine)
alongside the DecisionResult (Spec sec.4.1, sec.M13).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["RiskResult"]


class RiskResult(BaseModel):
    """Risk assessment for a response."""

    model_config = {"extra": "forbid"}

    risk_level: str = Field(
        ...,
        min_length=1,
        description="Risk classification label assigned by M13.",
    )
    risk_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional numeric risk score assigned by M13.",
    )

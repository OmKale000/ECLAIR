"""ConfidenceResult contract (M01 Foundation).

Carries confidence information for a response. Produced by M10 (raw confidence)
and later populated with a calibrated Epistemic Confidence Score by M11
(Spec sec.4.1, sec.4.4).

Reliability invariant (Spec sec.4.4): raw confidence is NOT a calibrated ECS.
This contract keeps them as separate fields so M10 emits only ``raw_confidence``
and M11 populates ``calibrated_ecs``. M01 computes neither.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["ConfidenceResult"]


class ConfidenceResult(BaseModel):
    """Raw and (optionally) calibrated confidence for a response."""

    model_config = {"extra": "forbid"}

    raw_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Raw fused confidence produced by M10 (NOT calibrated).",
    )
    calibrated_ecs: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Calibrated Epistemic Confidence Score, produced only by M11.",
    )

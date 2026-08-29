"""Claim contract (M01 Foundation).

An atomic factual claim extracted from a generated answer. Produced by M03
(Claim Extraction) as ``list[Claim]`` and consumed by M05/M07/M08/M09/M10 and
the engine (Spec sec.4.1).
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

__all__ = ["Claim"]


class Claim(BaseModel):
    """A normalized, atomic factual statement to be verified."""

    model_config = {"extra": "forbid"}

    claim_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Stable identifier for this claim within a query lineage.",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="The atomic factual claim text.",
    )

"""Query contract (M01 Foundation).

The entry-point contract produced at the API / engine boundary (Spec sec.4.1).
Carries the user question and its identity used for provenance lineage
(Spec sec.M14, keyed by ``query_id``).
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

__all__ = ["Query"]


class Query(BaseModel):
    """A single reliability request entering the pipeline."""

    model_config = {"extra": "forbid"}

    query_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Stable identifier used to key the full provenance lineage.",
    )
    question: str = Field(
        ...,
        min_length=1,
        description="The user/application question to be answered reliably.",
    )

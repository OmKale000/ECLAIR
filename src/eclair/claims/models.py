"""Module-local interim types for M03 Claim Extraction.

These are *internal* structures used between the extraction pipeline stages
(raw LLM output -> normalized -> deduplicated -> classified). They are NOT
shared contracts. The shared, cross-module output type is ``Claim`` (with its
``ClaimType``), owned by M01 and imported from :mod:`eclair.contracts`; this
module never redefines or duplicates it (COMMON_RULES sec.2, sec.16).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["ExtractionResult"]


class ExtractionResult(BaseModel):
    """Interim container for the parsed LLM structured-extraction output.

    The extractor requests structured JSON from the LLM Gateway (M02) of the form
    ``{"claims": ["claim one", "claim two"]}`` and parses it into this container
    before the deterministic normalize -> deduplicate -> classify stages run.
    Interim only: NOT a shared contract (the shared output type is ``Claim``).
    """

    model_config = {"extra": "forbid"}

    claims: list[str] = Field(
        default_factory=list,
        description="Raw atomic claim strings parsed from the LLM structured output.",
    )

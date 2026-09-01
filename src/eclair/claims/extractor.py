"""Claim extraction orchestration for M03 Claim Extraction.

Implements the M01 ``ClaimExtractor`` protocol: ``extract(text) -> list[Claim]``.
One generated answer is broken into atomic factual claims via the pipeline:

    LLM structured extraction (M02) -> normalize -> deduplicate -> classify -> assign IDs

This module never calls LLM providers directly; it goes through the M02 LLM
Gateway (an ``LLMRouter``-shaped client injected at construction). It performs no
retrieval, verification, confidence, or decision logic (COMMON_RULES sec.6, M03
non-responsibility). Errors use the shared M01 ``ModuleError``; failures from the
LLM Gateway propagate unchanged (not swallowed).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import ValidationError

from eclair.claims.classifier import ClaimClassifier
from eclair.claims.deduplicator import ClaimDeduplicator
from eclair.claims.models import ExtractionResult
from eclair.claims.normalizer import ClaimNormalizer
from eclair.contracts import Claim
from eclair.exceptions import ModuleError
from eclair.llm import LLMRequest

__all__ = ["LLMClient", "ClaimExtractor", "EXTRACTION_PROMPT_TEMPLATE"]

#: Prompt asking the LLM to split an answer into atomic claims as JSON.
EXTRACTION_PROMPT_TEMPLATE = (
    "Break the following answer into atomic, self-contained factual claims. "
    "Return ONLY JSON of the form {{\"claims\": [\"claim one\", \"claim two\"]}} "
    "with one string per atomic claim and no other text.\n\nAnswer:\n{answer}"
)


@runtime_checkable
class LLMClient(Protocol):
    """Minimal LLM Gateway interface (satisfied by M02 ``LLMRouter``)."""

    def generate(self, request: Any) -> Any:
        """Generate a response for an ``LLMRequest`` (returns an ``LLMResponse``)."""
        ...


class ClaimExtractor:
    """Extract atomic :class:`Claim` objects from a generated answer.

    Conforms to the M01 ``ClaimExtractor`` protocol. Collaborators are injected so
    the module is unit-testable offline (fake LLM client + fake encoder).
    """

    def __init__(
        self,
        llm: LLMClient,
        *,
        normalizer: ClaimNormalizer | None = None,
        deduplicator: ClaimDeduplicator | None = None,
        classifier: ClaimClassifier | None = None,
    ) -> None:
        self._llm = llm
        self._normalizer = normalizer or ClaimNormalizer()
        self._deduplicator = deduplicator or ClaimDeduplicator(normalizer=self._normalizer)
        self._classifier = classifier or ClaimClassifier()

    def extract(self, text: str) -> list[Claim]:
        """Extract atomic factual claims from answer ``text``.

        Returns an empty list for empty/whitespace-only input. Otherwise requests
        a structured claim list from the LLM Gateway, then normalizes, deduplicates,
        classifies, and builds validated ``Claim`` objects (with auto IDs).

        Raises:
            ModuleError: if the LLM response cannot be parsed into the expected
                structured shape. LLM Gateway failures propagate as ``ModuleError``.
        """
        if not text or not text.strip():
            return []

        raw_claims = self._request_claims(text)

        normalized: list[str] = []
        for raw in raw_claims:
            cleaned = self._normalizer.normalize(raw)
            if cleaned:
                normalized.append(cleaned)

        unique = self._deduplicator.deduplicate(normalized)

        claims: list[Claim] = []
        for claim_text in unique:
            claim_type = self._classifier.classify(claim_text)
            try:
                claims.append(Claim(text=claim_text, claim_type=claim_type))
            except ValidationError as exc:
                raise ModuleError(
                    f"Extracted claim failed Claim contract validation: {exc}",
                    code="claims_invalid_claim",
                ) from exc
        return claims

    def _request_claims(self, text: str) -> list[str]:
        """Call the LLM Gateway and parse its structured output into claim strings."""
        request = LLMRequest(
            prompt=EXTRACTION_PROMPT_TEMPLATE.format(answer=text),
            json_mode=True,
        )
        response = self._llm.generate(request)

        structured = getattr(response, "structured", None)
        if structured is None:
            raise ModuleError(
                "LLM Gateway did not return structured JSON for claim extraction",
                code="claims_no_structured_output",
            )

        try:
            parsed = ExtractionResult.model_validate(structured)
        except ValidationError as exc:
            raise ModuleError(
                f"LLM structured output did not match the expected shape: {exc}",
                code="claims_bad_extraction_shape",
            ) from exc
        return list(parsed.claims)

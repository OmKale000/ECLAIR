"""Optional secondary LLM verifier for M07 Claim Verification.

Provides an LLM-based secondary verification method consuming the abstract
``LLMProvider`` Protocol from M01 / M02. Does not hard-code providers and does
not replace the primary NLI verifier (Spec sec.M07).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from eclair.contracts.claim import Claim
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.interfaces import LLMProvider
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.llm.base import LLMRequest, LLMResponse
from eclair.verification.models import LLMVerificationResult

__all__ = ["LLMVerifier"]

logger = logging.getLogger(__name__)

VERIFICATION_SYSTEM_PROMPT = """You are a rigorous factual claim verifier.
Evaluate whether the provided evidence SUPPORTS, CONTRADICTS, or is INSUFFICIENT/NEUTRAL (UNKNOWN) with respect to the given factual claim.

Respond ONLY with a valid JSON object matching this schema:
{
  "status": "SUPPORTED" | "CONTRADICTED" | "UNKNOWN",
  "support_score": float between 0.0 and 1.0,
  "contradiction_score": float between 0.0 and 1.0,
  "reasoning": "brief explanation"
}
"""


class LLMVerifier:
    """Secondary claim verifier using the M02 LLM Gateway."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        """Initialize the LLM verifier with an abstract LLM provider.

        Args:
            provider: Concrete provider implementing LLMProvider protocol.
        """
        self._provider = provider

    def verify_claim_evidence(
        self, claim: Claim, evidence: Evidence
    ) -> LLMVerificationResult:
        """Verify a single claim against a single evidence passage via LLM.

        Args:
            claim: Factual claim to verify.
            evidence: Evidence passage.

        Returns:
            LLMVerificationResult with status, scores, and optional reasoning.

        Raises:
            ContractValidationError: If inputs are invalid.
            ModuleError: If provider fails or is unconfigured.
        """
        if not isinstance(claim, Claim):
            raise ContractValidationError(
                f"Expected Claim instance, got {type(claim).__name__}",
                code="verification_invalid_claim",
            )
        if not isinstance(evidence, Evidence):
            raise ContractValidationError(
                f"Expected Evidence instance, got {type(evidence).__name__}",
                code="verification_invalid_evidence",
            )

        if self._provider is None:
            raise ModuleError(
                "LLMVerifier requires a configured LLMProvider",
                code="llm_verifier_unconfigured",
            )

        prompt = (
            f"{VERIFICATION_SYSTEM_PROMPT}\n\n"
            f"CLAIM: {claim.text}\n"
            f"EVIDENCE: {evidence.text}\n"
        )

        request = LLMRequest(
            prompt=prompt,
            temperature=0.0,
            json_mode=True,
        )

        try:
            response: LLMResponse = self._provider.generate(request)
        except Exception as exc:
            logger.warning("LLM verification call failed: %s", exc)
            return LLMVerificationResult(
                status=VerificationStatus.UNKNOWN,
                support_score=0.0,
                contradiction_score=0.0,
                reasoning=f"LLM call failed: {exc}",
            )

        return self._parse_response(response)

    def _parse_response(self, response: LLMResponse) -> LLMVerificationResult:
        """Parse structured LLM output into an LLMVerificationResult."""
        structured_data: Any = response.structured
        if structured_data is None:
            try:
                structured_data = json.loads(response.text)
            except Exception:
                structured_data = None

        if not isinstance(structured_data, dict):
            return LLMVerificationResult(
                status=VerificationStatus.UNKNOWN,
                support_score=0.0,
                contradiction_score=0.0,
                reasoning="Could not parse structured JSON from LLM response",
            )

        raw_status = str(structured_data.get("status", "UNKNOWN")).upper().strip()
        if raw_status == "SUPPORTED":
            status = VerificationStatus.SUPPORTED
        elif raw_status == "CONTRADICTED":
            status = VerificationStatus.CONTRADICTED
        else:
            status = VerificationStatus.UNKNOWN

        try:
            support_score = max(
                0.0, min(1.0, float(structured_data.get("support_score", 0.0)))
            )
        except (ValueError, TypeError):
            support_score = 0.0

        try:
            contradiction_score = max(
                0.0, min(1.0, float(structured_data.get("contradiction_score", 0.0)))
            )
        except (ValueError, TypeError):
            contradiction_score = 0.0

        reasoning = structured_data.get("reasoning")
        if reasoning is not None:
            reasoning = str(reasoning)

        return LLMVerificationResult(
            status=status,
            support_score=round(support_score, 4),
            contradiction_score=round(contradiction_score, 4),
            reasoning=reasoning,
        )

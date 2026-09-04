"""Claim Verifier implementation for M07 Claim Verification.

Implements the frozen M01 ``Verifier`` Protocol:
    ``Verifier.verify(claim: Claim, evidence: list[Evidence]) -> VerificationResult``

Follows Spec sec.M07, sec.4.5, sec.4.9:
    * Explicit verification: RAG retrieval alone is not verification.
    * Absence of evidence (evidence = []) MUST return ``VerificationStatus.UNKNOWN``
      with ``evidence_ids=[]``, never ``SUPPORTED``.
    * NLI mapping: ENTAILMENT -> SUPPORTED, CONTRADICTION -> CONTRADICTED,
      NEUTRAL -> UNKNOWN.
    * Uses Hugging Face Transformers NLI as primary method and optional LLM
      verification via M02 LLM Gateway as secondary method.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from eclair.contracts.claim import Claim
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.verification.aggregator import EvidenceAggregator
from eclair.verification.llm_verifier import LLMVerifier
from eclair.verification.models import EvidenceVerification, VerificationDetail
from eclair.verification.nli import NLIEngine

__all__ = ["ClaimVerifier"]

logger = logging.getLogger(__name__)


class ClaimVerifier:
    """Primary claim verifier implementing the M01 ``Verifier`` Protocol."""

    def __init__(
        self,
        *,
        nli_engine: NLIEngine | None = None,
        llm_verifier: LLMVerifier | None = None,
        aggregator: EvidenceAggregator | None = None,
        use_llm_fallback: bool = False,
    ) -> None:
        """Initialize the ClaimVerifier.

        Args:
            nli_engine: Natural language inference engine (defaults to new instance).
            llm_verifier: Optional secondary LLM verifier.
            aggregator: Evidence aggregator (defaults to standard aggregator).
            use_llm_fallback: When True, queries LLM verifier if NLI is neutral/unknown.
        """
        self._nli_engine = nli_engine or NLIEngine()
        self._llm_verifier = llm_verifier
        self._aggregator = aggregator or EvidenceAggregator()
        self._use_llm_fallback = use_llm_fallback

    def verify(self, claim: Claim, evidence: list[Evidence]) -> VerificationResult:
        """Verify a single claim against a list of evidence passages.

        Conforms strictly to M01 ``Verifier`` Protocol:
            ``verify(claim: Claim, evidence: list[Evidence]) -> VerificationResult``

        Args:
            claim: The atomic factual claim to verify.
            evidence: List of retrieved evidence passages.

        Returns:
            Canonical VerificationResult with status (SUPPORTED/CONTRADICTED/UNKNOWN)
            and attached supporting evidence IDs.

        Raises:
            ContractValidationError: If inputs fail contract validation.
            ModuleError: If verification encounters an unrecoverable failure.
        """
        result, _ = self.verify_detailed(claim, evidence)
        return result

    def verify_detailed(
        self, claim: Claim, evidence: list[Evidence]
    ) -> tuple[VerificationResult, VerificationDetail]:
        """Verify a claim and return both the canonical result and rich internal details.

        Args:
            claim: Factual claim to verify.
            evidence: List of evidence items.

        Returns:
            Tuple of (VerificationResult, VerificationDetail).
        """
        claim_obj = self._validate_claim(claim)
        evidence_list = self._validate_evidence_list(evidence)

        # Non-negotiable: empty evidence list -> UNKNOWN with empty evidence_ids (Spec sec.4.9)
        if not evidence_list:
            return self._aggregator.aggregate(claim_obj, [])

        evaluations: list[EvidenceVerification] = []
        for ev in evidence_list:
            evaluation = self._verify_single_evidence(claim_obj, ev)
            evaluations.append(evaluation)

        return self._aggregator.aggregate(claim_obj, evaluations)

    def _verify_single_evidence(
        self, claim: Claim, evidence: Evidence
    ) -> EvidenceVerification:
        """Evaluate a single evidence item against the claim."""
        try:
            prediction = self._nli_engine.predict(
                premise=evidence.text, hypothesis=claim.text
            )
        except Exception as exc:
            logger.warning(
                "NLI evaluation failed for evidence %r: %s", evidence.evidence_id, exc
            )
            raise ModuleError(
                f"NLI evaluation failed for evidence {evidence.evidence_id!r}: {exc}",
                code="verification_nli_failed",
            ) from exc

        status = prediction.label.to_verification_status()
        support_score = prediction.entailment_score
        contradiction_score = prediction.contradiction_score

        # Optional secondary LLM verification if primary NLI returned UNKNOWN/NEUTRAL
        if (
            self._use_llm_fallback
            and status is VerificationStatus.UNKNOWN
            and self._llm_verifier is not None
        ):
            try:
                llm_res = self._llm_verifier.verify_claim_evidence(claim, evidence)
                if llm_res.status is not VerificationStatus.UNKNOWN:
                    status = llm_res.status
                    support_score = max(support_score, llm_res.support_score)
                    contradiction_score = max(
                        contradiction_score, llm_res.contradiction_score
                    )
            except Exception as exc:
                logger.debug("Secondary LLM verification skipped on error: %s", exc)

        return EvidenceVerification(
            evidence_id=evidence.evidence_id,
            status=status,
            support_score=support_score,
            contradiction_score=contradiction_score,
            nli_prediction=prediction,
        )

    def _validate_claim(self, claim: Any) -> Claim:
        """Validate or coerce input into a Claim contract."""
        if isinstance(claim, Claim):
            return claim
        try:
            return Claim.model_validate(claim)
        except (ValidationError, Exception) as exc:
            raise ContractValidationError(
                f"Invalid Claim input for verification: {exc}",
                code="verification_invalid_claim",
            ) from exc

    def _validate_evidence_list(self, evidence: Any) -> list[Evidence]:
        """Validate or coerce input into a list of Evidence contracts."""
        if not isinstance(evidence, list):
            raise ContractValidationError(
                f"Expected list of Evidence, got {type(evidence).__name__}",
                code="verification_invalid_evidence_list",
            )
        validated: list[Evidence] = []
        for i, item in enumerate(evidence):
            if isinstance(item, Evidence):
                validated.append(item)
            else:
                try:
                    validated.append(Evidence.model_validate(item))
                except (ValidationError, Exception) as exc:
                    raise ContractValidationError(
                        f"Invalid Evidence item at index {i}: {exc}",
                        code="verification_invalid_evidence_item",
                    ) from exc
        return validated

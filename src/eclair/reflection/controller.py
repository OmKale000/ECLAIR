"""Reflection controller orchestrator for M12 Self-Reflection & Self-Correction.

Executes bounded low-confidence correction loops:
    Generate -> Verify -> Low ECS? -> Critique -> Regenerate -> Verify again

Reliability Invariants:
    * Reuses M02 LLM Gateway, M03 Claim Extraction, M05 RAG, M07 Verification.
    * M12 does NOT define or calculate ECS (owned by M10/M11).
    * M12 does NOT define or apply risk policy (owned by M13).
    * Strict iteration limit is enforced; infinite loops are prevented under all paths.
    * Re-verifies all regenerated answers before returning them.
    * Absence of evidence remains UNKNOWN, never SUPPORTED.
"""

from __future__ import annotations

import logging

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.evidence import Evidence
from eclair.contracts.interfaces import (
    ClaimExtractor,
    ConfidenceEstimator,
    LLMProvider,
    Retriever,
    Verifier,
)
from eclair.contracts.query import Query
from eclair.contracts.verification import VerificationResult
from eclair.exceptions import ContractValidationError
from eclair.reflection.critic import ResponseCritic
from eclair.reflection.models import (
    IterationRecord,
    ReflectionConfig,
    ReflectionResult,
)
from eclair.reflection.rewriter import ResponseRewriter
from eclair.reflection.stopping import StoppingController

__all__ = ["ReflectionController"]

logger = logging.getLogger(__name__)


class ReflectionController:
    """Primary entry point for the M12 Self-Reflection & Self-Correction module."""

    def __init__(
        self,
        *,
        llm_provider: LLMProvider,
        claim_extractor: ClaimExtractor,
        verifier: Verifier,
        retriever: Retriever | None = None,
        confidence_estimator: ConfidenceEstimator | None = None,
        critic: ResponseCritic | None = None,
        rewriter: ResponseRewriter | None = None,
        stopping: StoppingController | None = None,
        config: ReflectionConfig | None = None,
    ) -> None:
        """Initialize the ReflectionController with required collaborators.

        Args:
            llm_provider: M02 LLM Gateway provider.
            claim_extractor: M03 atomic claim extractor.
            verifier: M07 claim verifier.
            retriever: Optional M05 retriever for grounding weak claims.
            confidence_estimator: Optional M10 confidence estimator.
            critic: Optional ResponseCritic instance.
            rewriter: Optional ResponseRewriter instance.
            stopping: Optional StoppingController instance.
            config: Reflection configuration.
        """
        self._llm_provider = llm_provider
        self._claim_extractor = claim_extractor
        self._verifier = verifier
        self._retriever = retriever
        self._confidence_estimator = confidence_estimator
        self._config = config or ReflectionConfig()

        self._critic = critic or ResponseCritic()
        self._rewriter = rewriter or ResponseRewriter(self._llm_provider, critic=self._critic)
        self._stopping = stopping or StoppingController()

    @property
    def config(self) -> ReflectionConfig:
        """Configured reflection parameters."""
        return self._config

    def reflect(
        self,
        query: Query | str,
        answer: str,
        claims: list[Claim],
        verifications: list[VerificationResult],
        confidence: ConfidenceResult | None = None,
        evidence: list[Evidence] | None = None,
    ) -> ReflectionResult:
        """Execute the bounded reflection loop on a low-confidence/failing response.

        Args:
            query: The original query object or query string.
            answer: The generated answer text requiring reflection.
            claims: Extracted atomic claims for the answer.
            verifications: Verification results for the claims.
            confidence: Optional confidence result from M10/M11.
            evidence: Supporting evidence passages.

        Returns:
            A ReflectionResult with the improved answer and updated verification lineage.

        Raises:
            ContractValidationError: If required inputs are invalid.
            ModuleError: If an unrecoverable module error occurs.
        """
        # Validate inputs
        query_text: str
        if isinstance(query, Query):
            query_text = query.question
        elif isinstance(query, str):
            query_text = query
        else:
            raise ContractValidationError(
                f"Query must be Query or str, got {type(query).__name__}",
                code="invalid_query_type",
            )

        if not query_text or not query_text.strip():
            raise ContractValidationError(
                "Query text cannot be empty",
                code="empty_query",
            )

        if not isinstance(answer, str) or not answer.strip():
            raise ContractValidationError(
                "Answer text cannot be empty",
                code="empty_answer",
            )

        if claims is None or not isinstance(claims, list):
            raise ContractValidationError(
                "Claims must be a list of Claim objects",
                code="invalid_claims",
            )

        if verifications is None or not isinstance(verifications, list):
            raise ContractValidationError(
                "Verifications must be a list of VerificationResult objects",
                code="invalid_verifications",
            )

        current_evidence: list[Evidence] = list(evidence) if evidence else []

        # Check trigger condition
        should_trigger, trigger_reason = self._stopping.should_trigger(
            claims=claims,
            verifications=verifications,
            confidence=confidence,
            config=self._config,
        )

        if not should_trigger:
            logger.info("Reflection not triggered: %s", trigger_reason)
            return ReflectionResult(
                original_answer=answer,
                improved_answer=answer,
                final_claims=claims,
                final_verifications=verifications,
                final_confidence=confidence,
                iterations_completed=0,
                max_iterations=self._config.max_iterations,
                triggered=False,
                improved=False,
                stop_reason=f"not_triggered_{trigger_reason}",
                history=[],
            )

        # Execute bounded correction loop
        current_answer = answer
        current_claims = list(claims)
        current_verifications = list(verifications)
        current_confidence = confidence

        history: list[IterationRecord] = []
        iterations_completed = 0
        final_stop_reason = "max_iterations_reached"
        was_improved = False

        for iteration in range(1, self._config.max_iterations + 1):
            iterations_completed = iteration

            # 1. Critique
            critique = self._critic.critique(
                claims=current_claims,
                verifications=current_verifications,
                evidence=current_evidence,
            )

            if not critique.has_weak_claims:
                final_stop_reason = "all_claims_verified"
                was_improved = True
                break

            # 2. Retrieve additional evidence for weak claims if retriever available
            if self._retriever is not None:
                existing_ev_ids = {e.evidence_id for e in current_evidence}
                for item in critique.items:
                    try:
                        additional_evidence = self._retriever.search(item.claim_text, top_k=2)
                        for ev in additional_evidence:
                            if ev.evidence_id not in existing_ev_ids:
                                current_evidence.append(ev)
                                existing_ev_ids.add(ev.evidence_id)
                    except Exception as ev_err:  # noqa: BLE001
                        logger.warning("Optional retrieval failed during reflection: %s", ev_err)

            # 3. Rewrite / Regenerate
            try:
                new_answer = self._rewriter.rewrite(
                    query=query_text,
                    current_answer=current_answer,
                    critique=critique,
                    evidence=current_evidence,
                    model=self._config.model,
                    temperature=self._config.temperature,
                )
            except Exception as rw_exc:  # noqa: BLE001
                logger.error("Reflection rewriter encountered error: %s", rw_exc)
                final_stop_reason = f"regeneration_failed_{rw_exc}"
                break

            # 4. Re-extract claims from regenerated answer
            try:
                new_claims = self._claim_extractor.extract(new_answer)
            except Exception as ce_exc:  # noqa: BLE001
                logger.error("Claim extraction failed on regenerated answer: %s", ce_exc)
                final_stop_reason = f"claim_extraction_failed_{ce_exc}"
                break

            # 5. Re-verify each new claim against available evidence
            new_verifications: list[VerificationResult] = []
            for clm in new_claims:
                try:
                    v_res = self._verifier.verify(clm, current_evidence)
                    new_verifications.append(v_res)
                except Exception as verif_exc:  # noqa: BLE001
                    logger.error("Verification failed during reflection: %s", verif_exc)
                    # When verifier fails, record UNKNOWN to avoid crashing loop
                    from eclair.contracts.enums import VerificationStatus

                    new_verifications.append(
                        VerificationResult(
                            claim_id=clm.claim_id,
                            status=VerificationStatus.UNKNOWN,
                            evidence_ids=[],
                        )
                    )

            # 6. Re-estimate confidence if estimator is available
            new_confidence: ConfidenceResult | None = None
            if self._confidence_estimator is not None:
                try:
                    new_confidence = self._confidence_estimator.calculate(
                        {
                            "claims": new_claims,
                            "verifications": new_verifications,
                            "evidence": current_evidence,
                        }
                    )
                except Exception as conf_exc:  # noqa: BLE001
                    logger.warning("Confidence re-estimation failed: %s", conf_exc)
                    new_confidence = None

            # 7. Check deterministic stopping condition
            should_stop, stop_reason, iteration_improved = self._stopping.check_stopping_condition(
                iteration=iteration,
                config=self._config,
                current_verifications=new_verifications,
                previous_verifications=current_verifications,
                current_confidence=new_confidence,
                previous_confidence=current_confidence,
                new_answer=new_answer,
                previous_answer=current_answer,
            )

            was_improved = was_improved or iteration_improved

            record = IterationRecord(
                iteration=iteration,
                answer=new_answer,
                claims=new_claims,
                verifications=new_verifications,
                confidence=new_confidence,
                critique=critique,
                improved=iteration_improved,
                stop_reason=stop_reason if should_stop else None,
            )
            history.append(record)

            # Update current state
            current_answer = new_answer
            current_claims = new_claims
            current_verifications = new_verifications
            current_confidence = new_confidence

            if should_stop:
                final_stop_reason = stop_reason
                break

        return ReflectionResult(
            original_answer=answer,
            improved_answer=current_answer,
            final_claims=current_claims,
            final_verifications=current_verifications,
            final_confidence=current_confidence,
            iterations_completed=iterations_completed,
            max_iterations=self._config.max_iterations,
            triggered=True,
            improved=was_improved,
            stop_reason=final_stop_reason,
            history=history,
        )

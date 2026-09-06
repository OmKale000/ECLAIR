"""ConfidenceEstimator service for M10 Confidence Estimation.

Implements the canonical ``ConfidenceEstimator`` protocol (Spec sec.4.3,
SHARED_CONTRACTS_REFERENCE sec.3):
    ConfidenceEstimator.calculate(signals) -> ConfidenceResult

Provides unified claim-level, batch-level, and response-level RAW confidence estimation.

Reliability invariant (Spec sec.4.4, SHARED_CONTRACTS_REFERENCE sec.6):
Produces RAW confidence only. Does NOT produce calibrated ECS (owned by M11).
"""

from __future__ import annotations

from typing import Any

from eclair.confidence.fusion import ConfidenceFuser
from eclair.confidence.models import (
    ClaimConfidenceResult,
    ConfidenceFusionConfig,
    ConfidenceSignals,
    ResponseConfidenceResult,
)
from eclair.confidence.signals import (
    extract_claim_signals,
    extract_response_signals,
)
from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import ConsensusLevel
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult
from eclair.evidence.models import EvidenceQualityReport, EvidenceQualitySignals
from eclair.exceptions import ModuleError
from eclair.hallucination.models import HallucinationResult, ResponseHallucinationResult

__all__ = [
    "ConfidenceEstimator",
]


class ConfidenceEstimator:
    """Estimates raw confidence from reliability signals using configurable weighted fusion.

    Conforms to the ``eclair.contracts.interfaces.ConfidenceEstimator`` Protocol.
    """

    def __init__(self, config: ConfidenceFusionConfig | None = None) -> None:
        self.config = config or ConfidenceFusionConfig()
        self.fuser = ConfidenceFuser(self.config)

    def estimate_claim_confidence(
        self,
        claim: Claim | None = None,
        verification: VerificationResult | None = None,
        evidence: list[Evidence] | None = None,
        quality_signals: list[EvidenceQualitySignals] | None = None,
        quality_report: EvidenceQualityReport | None = None,
        agreement_score: float | None = None,
        consensus_level: ConsensusLevel | None = None,
        hallucination: HallucinationResult | None = None,
        consistency_score: float | None = None,
        model_confidence: float | None = None,
        logprobs: list[float] | None = None,
        support_score: float | None = None,
        contradiction_score: float | None = None,
        signals: ConfidenceSignals | None = None,
    ) -> ClaimConfidenceResult:
        """Estimate RAW confidence for an individual claim."""
        claim_id = claim.claim_id if claim is not None else "claim_default"

        if signals is None:
            signals = extract_claim_signals(
                claim=claim,
                verification=verification,
                evidence=evidence,
                quality_signals=quality_signals,
                quality_report=quality_report,
                agreement_score=agreement_score,
                consensus_level=consensus_level,
                hallucination=hallucination,
                consistency_score=consistency_score,
                model_confidence=model_confidence,
                logprobs=logprobs,
                support_score=support_score,
                contradiction_score=contradiction_score,
            )

        raw_conf, breakdown = self.fuser.fuse(signals)

        return ClaimConfidenceResult(
            claim_id=claim_id,
            raw_confidence=raw_conf,
            signals=signals,
            breakdown=breakdown,
        )

    def estimate_batch_claims(
        self,
        claims: list[Claim],
        verifications: list[VerificationResult] | None = None,
        evidence: list[Evidence] | None = None,
        quality_report: EvidenceQualityReport | None = None,
        agreement_score: float | None = None,
        consensus_level: ConsensusLevel | None = None,
        hallucinations: list[HallucinationResult] | None = None,
        model_confidence: float | None = None,
    ) -> list[ClaimConfidenceResult]:
        """Estimate RAW confidence for multiple claims in a batch."""
        verif_map: dict[str, VerificationResult] = {}
        if verifications:
            verif_map = {v.claim_id: v for v in verifications}

        halluc_map: dict[str, HallucinationResult] = {}
        if hallucinations:
            halluc_map = {h.claim_id: h for h in hallucinations}

        results: list[ClaimConfidenceResult] = []
        for claim in claims:
            v_res = verif_map.get(claim.claim_id)
            h_res = halluc_map.get(claim.claim_id)
            claim_conf = self.estimate_claim_confidence(
                claim=claim,
                verification=v_res,
                evidence=evidence,
                quality_report=quality_report,
                agreement_score=agreement_score,
                consensus_level=consensus_level,
                hallucination=h_res,
                model_confidence=model_confidence,
            )
            results.append(claim_conf)

        return results

    def estimate_response_confidence(
        self,
        claims: list[Claim] | None = None,
        verifications: list[VerificationResult] | None = None,
        evidence: list[Evidence] | None = None,
        quality_report: EvidenceQualityReport | None = None,
        agreement_score: float | None = None,
        consensus_level: ConsensusLevel | None = None,
        response_hallucination: ResponseHallucinationResult | None = None,
        hallucinations: list[HallucinationResult] | None = None,
        model_confidence: float | None = None,
        consistency_score: float | None = None,
        aggregation_method: str | None = None,
        claim_confidences: list[ClaimConfidenceResult] | None = None,
        signals: ConfidenceSignals | None = None,
    ) -> ResponseConfidenceResult:
        """Estimate aggregate response-level RAW confidence."""
        agg_method = aggregation_method or self.config.response_aggregation

        # If claim confidences are already provided or claims exist to evaluate
        evaluated_claim_confs: list[ClaimConfidenceResult] = []
        if claim_confidences is not None:
            evaluated_claim_confs = claim_confidences
        elif claims:
            evaluated_claim_confs = self.estimate_batch_claims(
                claims=claims,
                verifications=verifications,
                evidence=evidence,
                quality_report=quality_report,
                agreement_score=agreement_score,
                consensus_level=consensus_level,
                hallucinations=hallucinations,
                model_confidence=model_confidence,
            )

        if evaluated_claim_confs and agg_method != "direct_fusion":
            raw_conf = self.fuser.aggregate_claim_confidences(
                evaluated_claim_confs, method=agg_method
            )
            return ResponseConfidenceResult(
                raw_confidence=raw_conf,
                claim_confidences=evaluated_claim_confs,
                overall_signals=None,
                overall_breakdown=None,
                aggregation_method=agg_method,
            )

        # Fall back to direct signal fusion for response level
        if signals is None:
            signals = extract_response_signals(
                verifications=verifications,
                evidence=evidence,
                quality_report=quality_report,
                agreement_score=agreement_score,
                consensus_level=consensus_level,
                response_hallucination=response_hallucination,
                consistency_score=consistency_score,
                model_confidence=model_confidence,
            )

        raw_conf, breakdown = self.fuser.fuse(signals)

        return ResponseConfidenceResult(
            raw_confidence=raw_conf,
            claim_confidences=evaluated_claim_confs,
            overall_signals=signals,
            overall_breakdown=breakdown,
            aggregation_method="direct_fusion",
        )

    def calculate(self, signals: Any) -> ConfidenceResult:
        """Entry point conforming to ``ConfidenceEstimator.calculate(signals) -> ConfidenceResult``.

        Accepts various signal representations and returns the shared M01 ``ConfidenceResult``.
        """
        if isinstance(signals, ConfidenceResult):
            return signals

        if isinstance(signals, ResponseConfidenceResult):
            return signals.to_confidence_result()

        if isinstance(signals, ClaimConfidenceResult):
            return ConfidenceResult(
                raw_confidence=signals.raw_confidence,
                calibrated_ecs=None,
            )

        if isinstance(signals, ConfidenceSignals):
            raw_conf, _ = self.fuser.fuse(signals)
            return ConfidenceResult(
                raw_confidence=raw_conf,
                calibrated_ecs=None,
            )

        if isinstance(signals, list) and all(
            isinstance(item, ClaimConfidenceResult) for item in signals
        ):
            raw_conf = self.fuser.aggregate_claim_confidences(signals)
            return ConfidenceResult(
                raw_confidence=raw_conf,
                calibrated_ecs=None,
            )

        if isinstance(signals, dict):
            # Check if dict directly specifies raw signal fields
            if any(
                k
                in {
                    "verification_score",
                    "evidence_score",
                    "agreement_score",
                    "consistency_score",
                    "model_confidence_score",
                }
                for k in signals
            ):
                sig_obj = ConfidenceSignals(
                    verification_score=signals.get("verification_score"),
                    evidence_score=signals.get("evidence_score"),
                    agreement_score=signals.get("agreement_score"),
                    consistency_score=signals.get("consistency_score"),
                    model_confidence_score=signals.get("model_confidence_score"),
                    details=signals.get("details", {}),
                )
                raw_conf, _ = self.fuser.fuse(sig_obj)
                return ConfidenceResult(raw_confidence=raw_conf, calibrated_ecs=None)

            # Otherwise, treat as kwargs to estimate_response_confidence
            try:
                resp_res = self.estimate_response_confidence(**signals)
                return resp_res.to_confidence_result()
            except TypeError as exc:
                raise ModuleError(
                    f"Invalid signal dictionary structure for ConfidenceEstimator: {exc}",
                    code="confidence_invalid_signals",
                ) from exc

        if isinstance(signals, (int, float)):
            val = float(signals)
            if not 0.0 <= val <= 1.0:
                raise ModuleError(
                    f"Numeric confidence value must be in [0.0, 1.0], got {val}",
                    code="confidence_out_of_bounds",
                )
            return ConfidenceResult(raw_confidence=val, calibrated_ecs=None)

        raise ModuleError(
            f"Unsupported signals type for ConfidenceEstimator: {type(signals).__name__}",
            code="confidence_unsupported_signals",
        )

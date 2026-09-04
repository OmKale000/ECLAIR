"""Hallucination detector orchestrator for M08 Hallucination Detection.

Provides the primary HallucinationDetector interface to evaluate single claims
or entire claim batches against evidence, verification results, and consensus signals.
"""

from __future__ import annotations

from eclair.contracts.claim import Claim
from eclair.contracts.enums import ConsensusLevel
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult
from eclair.evidence.models import EvidenceQualityReport, EvidenceQualitySignals
from eclair.hallucination.models import (
    HallucinationResult,
    ResponseHallucinationResult,
)
from eclair.hallucination.scoring import (
    HallucinationScorer,
    HallucinationScorerConfig,
)
from eclair.hallucination.signals import extract_hallucination_signals

__all__ = ["HallucinationDetector"]


class HallucinationDetector:
    """Primary detector for identifying fabricated, unsupported, or contradicted claims."""

    def __init__(
        self,
        scorer_config: HallucinationScorerConfig | None = None,
        scorer: HallucinationScorer | None = None,
    ) -> None:
        self.scorer = scorer or HallucinationScorer(config=scorer_config)

    def detect_claim(
        self,
        claim: Claim,
        verification: VerificationResult | None = None,
        evidence: list[Evidence] | None = None,
        quality_signals: list[EvidenceQualitySignals] | None = None,
        quality_report: EvidenceQualityReport | None = None,
        agreement_score: float | None = None,
        consensus_level: ConsensusLevel | None = None,
    ) -> HallucinationResult:
        """Evaluate an individual claim across the 5 hallucination reliability signals.

        Args:
            claim: The target atomic factual claim (M03).
            verification: Optional M07 verification result for this claim.
            evidence: Optional list of retrieved M05 evidence passages.
            quality_signals: Optional per-evidence quality signals from M06.
            quality_report: Optional comprehensive M06 evidence quality report.
            agreement_score: Optional consensus agreement score in [0.0, 1.0] from M09.
            consensus_level: Optional consensus level enum (FULL / PARTIAL) from M09.

        Returns:
            A structured HallucinationResult containing probability, flag, and reasons.
        """
        claim_evidence = evidence
        claim_quality_signals = quality_signals

        if verification is not None:
            if not verification.evidence_ids:
                claim_evidence = []
                claim_quality_signals = []
            elif evidence:
                matched_ev = [
                    ev for ev in evidence if ev.evidence_id in verification.evidence_ids
                ]
                if matched_ev:
                    claim_evidence = matched_ev
                if quality_signals:
                    matched_sig = [
                        s for s in quality_signals if s.evidence_id in verification.evidence_ids
                    ]
                    if matched_sig:
                        claim_quality_signals = matched_sig

        signals = extract_hallucination_signals(
            claim=claim,
            verification=verification,
            evidence=claim_evidence,
            quality_signals=claim_quality_signals,
            quality_report=quality_report,
            agreement_score=agreement_score,
            consensus_level=consensus_level,
        )

        prob, is_hallucination, reasons = self.scorer.score(signals)

        return HallucinationResult(
            claim_id=claim.claim_id,
            hallucination_probability=prob,
            is_hallucination=is_hallucination,
            reasons=reasons,
            signals=signals,
        )

    def detect_claims(
        self,
        claims: list[Claim],
        verifications: list[VerificationResult] | None = None,
        evidence: list[Evidence] | None = None,
        quality_report: EvidenceQualityReport | None = None,
        agreement_score: float | None = None,
        consensus_level: ConsensusLevel | None = None,
    ) -> ResponseHallucinationResult:
        """Evaluate a batch of claims from a generated response.

        Args:
            claims: List of atomic factual claims extracted from the answer (M03).
            verifications: List of M07 verification results matching claims.
            evidence: List of retrieved evidence passages (M05).
            quality_report: Quality analysis report for the evidence set (M06).
            agreement_score: Multi-model consensus score (M09).
            consensus_level: Multi-model consensus level (M09).

        Returns:
            ResponseHallucinationResult with per-claim results and overall assessment.
        """
        if not claims:
            return ResponseHallucinationResult(
                claim_results=[],
                overall_hallucination_probability=0.0,
                has_hallucination=False,
                hallucinated_claim_ids=[],
                summary_reasons=[],
            )

        verification_map: dict[str, VerificationResult] = {}
        if verifications:
            for v in verifications:
                verification_map[v.claim_id] = v

        claim_results: list[HallucinationResult] = []
        hallucinated_ids: list[str] = []
        all_reasons: list[str] = []

        for claim in claims:
            v_res = verification_map.get(claim.claim_id)
            res = self.detect_claim(
                claim=claim,
                verification=v_res,
                evidence=evidence,
                quality_report=quality_report,
                agreement_score=agreement_score,
                consensus_level=consensus_level,
            )
            claim_results.append(res)
            if res.is_hallucination:
                hallucinated_ids.append(claim.claim_id)
                all_reasons.extend(res.reasons)

        max_prob = max((r.hallucination_probability for r in claim_results), default=0.0)
        avg_prob = sum(r.hallucination_probability for r in claim_results) / len(claim_results)
        overall_prob = round(0.7 * max_prob + 0.3 * avg_prob, 4)

        # Deduplicate summary reasons preserving order
        unique_reasons: list[str] = []
        seen = set()
        for r in all_reasons:
            if r not in seen:
                seen.add(r)
                unique_reasons.append(r)

        return ResponseHallucinationResult(
            claim_results=claim_results,
            overall_hallucination_probability=max(0.0, min(1.0, overall_prob)),
            has_hallucination=len(hallucinated_ids) > 0,
            hallucinated_claim_ids=hallucinated_ids,
            summary_reasons=unique_reasons,
        )

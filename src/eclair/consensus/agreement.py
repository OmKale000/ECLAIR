"""Agreement score and consensus level calculation for M09 Consensus.

Computes pairwise semantic/lexical similarity across model outputs and fuses
vote shares into a quantified agreement score in [0.0, 1.0]. Categorizes the
result as FULL or PARTIAL consensus (Spec sec.M09, SHARED_CONTRACTS_REFERENCE sec.2).

Reliability Invariant:
    Model agreement is NOT proof of truth (Spec sec.4.6). Agreement is one
    reliability signal that is later fused by M10 and calibrated by M11.
"""

from __future__ import annotations

import difflib
import re
from typing import Sequence

from eclair.consensus.models import AgreementResult, ModelOutput, VotingResult
from eclair.contracts.enums import ConsensusLevel

__all__ = ["AgreementCalculator"]

_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


class AgreementCalculator:
    """Calculates cross-model agreement scores and assigns consensus levels.

    Combines pairwise token Jaccard similarity, word-level sequence alignment,
    and majority vote shares to compute a deterministic agreement score.
    """

    def __init__(
        self,
        *,
        full_consensus_threshold: float = 0.85,
        vote_weight: float = 0.5,
        pairwise_weight: float = 0.5,
    ) -> None:
        """Initialize calculator.

        Args:
            full_consensus_threshold: Score threshold above which consensus is
                marked as ConsensusLevel.FULL (default 0.85).
            vote_weight: Weight given to majority vote share in agreement fusion.
            pairwise_weight: Weight given to mean pairwise similarity in agreement fusion.
        """
        self._full_consensus_threshold = max(0.0, min(1.0, full_consensus_threshold))
        total_w = vote_weight + pairwise_weight
        if total_w <= 0:
            self._vote_weight = 0.5
            self._pairwise_weight = 0.5
        else:
            self._vote_weight = vote_weight / total_w
            self._pairwise_weight = pairwise_weight / total_w

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for consistent comparison."""
        cleaned = text.strip().lower()
        cleaned = _PUNCTUATION_PATTERN.sub(" ", cleaned)
        return _WHITESPACE_PATTERN.sub(" ", cleaned).strip()

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute deterministic lexical and token similarity between two strings."""
        norm_a = self._normalize(text_a)
        norm_b = self._normalize(text_b)

        if not norm_a and not norm_b:
            return 1.0
        if not norm_a or not norm_b:
            return 0.0
        if norm_a == norm_b:
            return 1.0

        words_a = norm_a.split()
        words_b = norm_b.split()
        tokens_a = set(words_a)
        tokens_b = set(words_b)

        # Word-level Jaccard similarity
        inter = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))
        jaccard = inter / union if union > 0 else 0.0

        if jaccard == 0.0:
            return 0.0

        # Word-level sequence matcher ratio
        seq_ratio = difflib.SequenceMatcher(None, words_a, words_b).ratio()

        # Weighted blend (70% token overlap, 30% sequence order)
        sim = (0.7 * jaccard) + (0.3 * seq_ratio)
        return max(0.0, min(1.0, sim))

    def calculate(
        self,
        outputs: Sequence[ModelOutput],
        voting_result: VotingResult | None = None,
    ) -> AgreementResult:
        """Calculate agreement score and classify consensus level.

        Args:
            outputs: Sequence of model outputs.
            voting_result: Optional pre-computed voting result.

        Returns:
            An :class:`AgreementResult` with agreement_score and ConsensusLevel.
        """
        valid_outputs = [out for out in outputs if out.success and out.text.strip()]
        num_valid = len(valid_outputs)

        if num_valid == 0:
            return AgreementResult(
                agreement_score=0.0,
                consensus_level=ConsensusLevel.PARTIAL,
                mean_pairwise_similarity=0.0,
                pairwise_similarities=[],
                unanimous=False,
                details={"reason": "No successful model outputs to evaluate agreement."},
            )

        if num_valid == 1:
            return AgreementResult(
                agreement_score=1.0,
                consensus_level=ConsensusLevel.FULL,
                mean_pairwise_similarity=1.0,
                pairwise_similarities=[1.0],
                unanimous=True,
                details={"reason": "Single model output is fully self-consistent."},
            )

        # Compute all unique pairwise similarities
        pairwise_sims: list[float] = []
        for i in range(num_valid):
            for j in range(i + 1, num_valid):
                sim = self.compute_similarity(
                    valid_outputs[i].text,
                    valid_outputs[j].text,
                )
                pairwise_sims.append(sim)

        mean_pairwise = sum(pairwise_sims) / len(pairwise_sims) if pairwise_sims else 0.0

        # Combine with majority ratio from voting if available
        if voting_result is not None and voting_result.total_votes > 0:
            maj_ratio = voting_result.majority_ratio
            unanimous = voting_result.unanimous
            has_majority = voting_result.has_majority
            score = (self._vote_weight * maj_ratio) + (self._pairwise_weight * mean_pairwise)
        else:
            unanimous = all(s >= 0.999 for s in pairwise_sims)
            has_majority = mean_pairwise > 0.5
            score = mean_pairwise

        score = max(0.0, min(1.0, score))

        # Assign consensus level (FULL vs PARTIAL per frozen enum)
        if (score >= self._full_consensus_threshold and has_majority) or unanimous:
            level = ConsensusLevel.FULL
        else:
            level = ConsensusLevel.PARTIAL

        return AgreementResult(
            agreement_score=score,
            consensus_level=level,
            mean_pairwise_similarity=mean_pairwise,
            pairwise_similarities=pairwise_sims,
            unanimous=unanimous,
            details={
                "pair_count": len(pairwise_sims),
                "full_consensus_threshold": self._full_consensus_threshold,
                "vote_weight": self._vote_weight,
                "pairwise_weight": self._pairwise_weight,
            },
        )

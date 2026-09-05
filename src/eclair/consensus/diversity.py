"""Model and output diversity metrics for M09 Consensus.

Measures output dispersion and architectural provider diversity across the
polled models during multi-model consensus execution.
"""

from __future__ import annotations

from typing import Sequence

from eclair.consensus.models import (
    AgreementResult,
    DiversityResult,
    ModelOutput,
    VotingResult,
)

__all__ = ["DiversityCalculator"]


class DiversityCalculator:
    """Calculates diversity metrics for multi-model consensus outputs.

    Provides quantitative measures of answer divergence, pairwise distance,
    and provider architecture diversity.
    """

    def calculate(
        self,
        outputs: Sequence[ModelOutput],
        agreement_result: AgreementResult | None = None,
        voting_result: VotingResult | None = None,
    ) -> DiversityResult:
        """Compute diversity metrics for model outputs.

        Args:
            outputs: Sequence of model outputs.
            agreement_result: Optional pre-computed agreement result.
            voting_result: Optional pre-computed voting result.

        Returns:
            A populated :class:`DiversityResult`.
        """
        valid_outputs = [out for out in outputs if out.success and out.text.strip()]
        num_valid = len(valid_outputs)

        if num_valid <= 1:
            providers = {out.provider for out in valid_outputs}
            return DiversityResult(
                diversity_score=0.0,
                unique_answer_count=num_valid,
                mean_pairwise_distance=0.0,
                provider_diversity_count=len(providers),
                details={"reason": "Insufficient outputs to compute multi-model diversity."},
            )

        # Count distinct providers
        providers = {out.provider for out in valid_outputs}

        # Determine unique answer count from voting or clusters
        if voting_result is not None:
            unique_count = len(voting_result.clusters)
        else:
            unique_count = len({out.text.strip().lower() for out in valid_outputs})

        # Pairwise distance = 1 - similarity
        if agreement_result is not None:
            mean_dist = max(0.0, min(1.0, 1.0 - agreement_result.mean_pairwise_similarity))
        else:
            mean_dist = 0.0

        # Normalized cluster diversity in [0.0, 1.0]
        cluster_diversity = (unique_count - 1) / (num_valid - 1) if num_valid > 1 else 0.0
        cluster_diversity = max(0.0, min(1.0, cluster_diversity))

        # Composite diversity score
        diversity_score = max(0.0, min(1.0, (0.5 * mean_dist) + (0.5 * cluster_diversity)))

        return DiversityResult(
            diversity_score=diversity_score,
            unique_answer_count=unique_count,
            mean_pairwise_distance=mean_dist,
            provider_diversity_count=len(providers),
            details={
                "total_valid_models": num_valid,
                "cluster_diversity": cluster_diversity,
                "providers": sorted(providers),
            },
        )

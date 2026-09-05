"""Majority voting and output clustering for M09 Consensus.

Implements deterministic majority voting over independent model outputs.
Groups identical or semantically close outputs into vote clusters, tallies
vote shares, and identifies majority or plurality consensus answers.
"""

from __future__ import annotations

import difflib
import re
from typing import Sequence

from eclair.consensus.models import ModelOutput, VoteCluster, VotingResult

__all__ = ["MajorityVoter"]

_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


class MajorityVoter:
    """Computes majority voting and output clustering across model responses.

    Groups model outputs by normalized text equivalence and token similarity,
    identifying the plurality/majority winning answer and full vote distribution.
    """

    def __init__(self, *, similarity_threshold: float = 0.75) -> None:
        """Initialize voter.

        Args:
            similarity_threshold: Minimum similarity in [0.0, 1.0]
                to cluster two non-identical texts together into the same vote.
        """
        self._similarity_threshold = max(0.0, min(1.0, similarity_threshold))

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for consistent string matching."""
        if not text:
            return ""
        cleaned = text.strip().lower()
        cleaned = _PUNCTUATION_PATTERN.sub(" ", cleaned)
        cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()
        return cleaned

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        """Compute similarity between two normalized strings."""
        if not text_a and not text_b:
            return 1.0
        if not text_a or not text_b:
            return 0.0
        if text_a == text_b:
            return 1.0

        words_a = text_a.split()
        words_b = text_b.split()
        tokens_a = set(words_a)
        tokens_b = set(words_b)

        inter = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))
        jaccard = inter / union if union > 0 else 0.0

        if jaccard == 0.0:
            return 0.0

        seq_ratio = difflib.SequenceMatcher(None, words_a, words_b).ratio()
        return (0.7 * jaccard) + (0.3 * seq_ratio)

    def vote(self, outputs: Sequence[ModelOutput]) -> VotingResult:
        """Tally votes across valid model outputs.

        Args:
            outputs: Sequence of :class:`ModelOutput` items from independent models.

        Returns:
            A populated :class:`VotingResult` containing clusters, winning answer,
            vote counts, and majority metrics.
        """
        valid_outputs = [out for out in outputs if out.success and out.text.strip()]
        total_votes = len(valid_outputs)

        if total_votes == 0:
            return VotingResult(
                majority_answer=None,
                winning_vote_count=0,
                total_votes=0,
                majority_ratio=0.0,
                has_majority=False,
                unanimous=False,
                clusters=[],
                vote_counts={},
                details={"reason": "No valid successful model outputs available to vote on."},
            )

        # Build clusters
        # Each cluster item: {"rep": str, "norm": str, "models": list[str], "count": int}
        clusters_data: list[dict[str, object]] = []

        for out in valid_outputs:
            raw_text = out.text.strip()
            norm = self.normalize_text(raw_text)
            matched_cluster: dict[str, object] | None = None

            for cl in clusters_data:
                cl_norm = cl["norm"]
                assert isinstance(cl_norm, str)

                # Exact normalized match
                if norm == cl_norm:
                    matched_cluster = cl
                    break

                # Similarity match
                sim = self._compute_similarity(norm, cl_norm)
                if sim >= self._similarity_threshold:
                    matched_cluster = cl
                    break

            if matched_cluster is not None:
                matched_cluster["count"] = int(matched_cluster["count"]) + 1  # type: ignore[arg-type]
                models_list = matched_cluster["models"]
                assert isinstance(models_list, list)
                models_list.append(out.model)
            else:
                clusters_data.append(
                    {
                        "rep": raw_text,
                        "norm": norm,
                        "models": [out.model],
                        "count": 1,
                    }
                )

        # Sort clusters by vote count descending, with deterministic tie-breaking
        clusters_data.sort(
            key=lambda c: (
                -int(c["count"]),  # type: ignore[arg-type]
                str(c["rep"]),
            )
        )

        vote_clusters: list[VoteCluster] = []
        vote_counts_summary: dict[str, int] = {}

        for cl in clusters_data:
            rep = str(cl["rep"])
            cnt = int(cl["count"])  # type: ignore[arg-type]
            models_list = list(cl["models"])  # type: ignore[arg-type]
            share = cnt / total_votes

            vote_clusters.append(
                VoteCluster(
                    representative_text=rep,
                    vote_count=cnt,
                    vote_share=share,
                    model_names=models_list,
                )
            )
            summary_key = rep if len(rep) <= 60 else f"{rep[:57]}..."
            vote_counts_summary[summary_key] = cnt

        winning_cluster = vote_clusters[0]
        winning_count = winning_cluster.vote_count
        majority_ratio = winning_count / total_votes
        has_majority = majority_ratio > 0.5
        unanimous = winning_count == total_votes and total_votes >= 1

        return VotingResult(
            majority_answer=winning_cluster.representative_text,
            winning_vote_count=winning_count,
            total_votes=total_votes,
            majority_ratio=majority_ratio,
            has_majority=has_majority,
            unanimous=unanimous,
            clusters=vote_clusters,
            vote_counts=vote_counts_summary,
            details={
                "unique_clusters": len(vote_clusters),
                "majority_threshold": 0.5,
                "similarity_threshold": self._similarity_threshold,
            },
        )

    def vote_strings(self, texts: Sequence[str]) -> VotingResult:
        """Convenience method to tally votes directly on a list of strings."""
        outputs = [
            ModelOutput(
                model=f"model_{i}",
                provider="generic",
                text=text,
                success=True,
            )
            for i, text in enumerate(texts)
        ]
        return self.vote(outputs)

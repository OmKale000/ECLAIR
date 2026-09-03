"""Source authority scoring for M06 Evidence Quality & Conflict Detection.

Evaluates the credibility, trustworthiness, and authority tier of evidence
sources, supporting controlled knowledge base policies, domain patterns,
custom authority mappings, and low-quality source detection.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

__all__ = [
    "SourceAuthorityScorer",
    "score_source_authority",
    "is_low_quality_source",
    "DEFAULT_MIN_AUTHORITY_THRESHOLD",
]

DEFAULT_MIN_AUTHORITY_THRESHOLD: float = 0.5

# Canonical controlled knowledge base documents (Spec §4.7)
CONTROLLED_KB_POLICIES: frozenset[str] = frozenset({
    "refund_policy",
    "customer_policy",
    "invoice_policy",
    "product_policy",
    "company_policy",
})

# Authority tiers and regex patterns
AUTHORITY_TIER_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    # Untrusted / Malicious / Blacklisted patterns -> 0.10
    (re.compile(r"(untrusted|spam|spoof|fake|unreliable|phishing|blacklisted)", re.IGNORECASE), 0.10),
    # Controlled KB paths -> 1.0
    (re.compile(r"(data[\\/]knowledge_base[\\/]|kb[\\/]|policies[\\/])", re.IGNORECASE), 1.0),
    # Official / Legal / Regulatory / Government / Edu -> 0.95
    (re.compile(r"(\.gov|\.edu|official|legal|regulatory|compliance|terms)", re.IGNORECASE), 0.95),
    # Internal docs / Standards / Handbooks / SOPs -> 0.85
    (re.compile(r"(internal|handbook|sop|standard|doc(s)?|manual)", re.IGNORECASE), 0.85),
    # General / Wiki / FAQ / Knowledge base -> 0.65
    (re.compile(r"(wiki|faq|help|guide|tutorial)", re.IGNORECASE), 0.65),
    # Unverified / Blogs / Forums / Social / User-generated -> 0.35
    (re.compile(r"(blog|forum|social|reddit|twitter|unverified|user_post|external)", re.IGNORECASE), 0.35),
]


def _normalize_source_string(source: str) -> str:
    """Normalize delimiters in source string for robust pattern matching."""
    return re.sub(r"[_\-\\/]+", " ", source.lower())


class SourceAuthorityScorer:
    """Scorer evaluating source authority and detecting low-quality origins."""

    def __init__(
        self,
        *,
        custom_mappings: Mapping[str, float] | None = None,
        min_authority_threshold: float = DEFAULT_MIN_AUTHORITY_THRESHOLD,
    ) -> None:
        self._custom_mappings = dict(custom_mappings) if custom_mappings else {}
        self._min_authority_threshold = min_authority_threshold

    @property
    def min_authority_threshold(self) -> float:
        """Threshold below which a source is deemed low quality."""
        return self._min_authority_threshold

    def score(
        self,
        source: str | None,
        metadata: Mapping[str, Any] | None = None,
    ) -> float:
        """Compute the source authority score in [0.0, 1.0].

        Args:
            source: Origin or file path of the evidence passage.
            metadata: Optional dictionary of document metadata.

        Returns:
            Authority score strictly bounded within [0.0, 1.0].
        """
        # Check explicit authority score override in metadata
        if metadata:
            explicit_score = metadata.get("authority_score")
            if explicit_score is not None:
                try:
                    return max(0.0, min(1.0, float(explicit_score)))
                except (ValueError, TypeError):
                    pass

            explicit_tier = metadata.get("tier") or metadata.get("source_tier")
            if isinstance(explicit_tier, str):
                tier_key = explicit_tier.strip().lower()
                tier_scores: dict[str, float] = {
                    "controlled_kb": 1.0,
                    "official": 0.95,
                    "verified": 0.85,
                    "internal": 0.85,
                    "general": 0.65,
                    "unverified": 0.35,
                    "untrusted": 0.10,
                }
                if tier_key in tier_scores:
                    return tier_scores[tier_key]

        # If source is missing, return baseline unverified score
        if not source or not source.strip():
            return 0.20

        clean_source = source.strip()

        # Check exact custom mappings
        if clean_source in self._custom_mappings:
            return max(0.0, min(1.0, float(self._custom_mappings[clean_source])))

        # Check partial custom mappings (prefix or substring)
        for custom_key, custom_val in self._custom_mappings.items():
            if custom_key.lower() in clean_source.lower():
                return max(0.0, min(1.0, float(custom_val)))

        source_raw = clean_source.lower().replace("\\", "/")
        source_normalized = _normalize_source_string(clean_source)

        # Check controlled KB policy names (Spec §4.7)
        for policy in CONTROLLED_KB_POLICIES:
            if policy in source_raw or _normalize_source_string(policy) in source_normalized:
                return 1.0

        # Match against authority tier regex patterns in order
        for pattern, score in AUTHORITY_TIER_PATTERNS:
            if pattern.search(source_raw) or pattern.search(source_normalized):
                return score

        # Default fallback for recognized file types (markdown, text, pdf)
        if any(source_raw.endswith(ext) for ext in [".md", ".txt", ".pdf", ".json"]):
            return 0.70

        # Unspecified source
        return 0.50

    def is_low_quality(
        self,
        source: str | None,
        metadata: Mapping[str, Any] | None = None,
        threshold: float | None = None,
    ) -> bool:
        """Determine whether the source is considered low quality.

        Args:
            source: Source identifier or path.
            metadata: Optional metadata.
            threshold: Optional threshold override.

        Returns:
            True if authority score is strictly below the threshold.
        """
        thresh = threshold if threshold is not None else self._min_authority_threshold
        return self.score(source, metadata=metadata) < thresh


def score_source_authority(
    source: str | None,
    metadata: Mapping[str, Any] | None = None,
    custom_mappings: Mapping[str, float] | None = None,
) -> float:
    """Convenience function to score source authority."""
    scorer = SourceAuthorityScorer(custom_mappings=custom_mappings)
    return scorer.score(source, metadata=metadata)


def is_low_quality_source(
    source: str | None,
    threshold: float = DEFAULT_MIN_AUTHORITY_THRESHOLD,
    metadata: Mapping[str, Any] | None = None,
) -> bool:
    """Convenience function to check if a source is low quality."""
    scorer = SourceAuthorityScorer(min_authority_threshold=threshold)
    return scorer.is_low_quality(source, metadata=metadata, threshold=threshold)

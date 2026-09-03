"""Duplicate and conflict detection for M06 Evidence Quality.

Identifies redundant/duplicate evidence passages and detects semantic,
numerical, and polarity contradictions between retrieved evidence items.
"""

from __future__ import annotations

import re
from typing import Sequence

from eclair.contracts.evidence import Evidence
from eclair.evidence.models import ConflictDetail

__all__ = [
    "ConflictDetector",
    "detect_duplicates",
    "detect_conflicts",
    "DEFAULT_DUPLICATE_THRESHOLD",
    "DEFAULT_CONFLICT_THRESHOLD",
]

DEFAULT_DUPLICATE_THRESHOLD: float = 0.80
DEFAULT_CONFLICT_THRESHOLD: float = 0.50

# Common English stopwords to ignore during topic overlap extraction
STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "then", "in", "on", "at", "to",
    "for", "with", "by", "from", "up", "about", "into", "over", "after", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "can", "could", "shall", "should", "will", "would", "may",
    "might", "must", "it", "its", "this", "that", "these", "those", "of", "as",
    "such", "all", "any", "both", "each", "few", "more", "most", "other", "some",
})

# Polarity affirmative and negative indicators
AFFIRMATIVE_TERMS: frozenset[str] = frozenset({
    "allowed", "permitted", "eligible", "accepted", "supported", "refundable",
    "valid", "included", "mandatory", "required", "compulsory", "guaranteed",
    "always", "entitled", "covered", "approved", "provided", "active",
})

NEGATIVE_TERMS: frozenset[str] = frozenset({
    "prohibited", "ineligible", "rejected", "unsupported", "non-refundable",
    "invalid", "excluded", "optional", "exempt", "never", "disallowed",
    "forbidden", "denied", "void", "inactive", "terminated", "unapproved",
})

# Direct antonym pairs
ANTONYM_PAIRS: list[tuple[frozenset[str], frozenset[str]]] = [
    (frozenset({"mandatory", "required", "compulsory"}), frozenset({"optional", "voluntary", "discretionary"})),
    (frozenset({"free", "complimentary"}), frozenset({"paid", "charged", "fee"})),
    (frozenset({"always", "guaranteed"}), frozenset({"never", "unsupported"})),
    (frozenset({"eligible", "entitled"}), frozenset({"ineligible", "disqualified"})),
    (frozenset({"refundable"}), frozenset({"non-refundable", "unrefundable"})),
]

# Numerical extraction pattern: e.g. "30 days", "$50", "100%", "5 business days"
NUMERICAL_REGEX = re.compile(
    r"(?P<amount>\$?\d+(?:\.\d+)?%?)\s*(?P<unit>calendar\s+days?|business\s+days?|days?|hours?|weeks?|months?|years?|percent|%|dollars?|usd)?",
    re.IGNORECASE,
)


def _stem(word: str) -> str:
    """Lightweight suffix stripping for token matching."""
    w = word.lower()
    for suffix in ("ing", "ed", "es", "s", "ly", "tion", "ment"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())


def _content_tokens(text: str) -> set[str]:
    """Extract content word stems excluding common stopwords."""
    tokens = _tokenize(text)
    return {_stem(t) for t in tokens if t not in STOPWORDS and len(t) > 1}


def _jaccard_similarity(tokens_a: set[str], tokens_b: set[str]) -> float:
    """Compute Jaccard similarity between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a.intersection(tokens_b))
    union = len(tokens_a.union(tokens_b))
    return float(intersection) / float(union) if union > 0 else 0.0


def _extract_quantities(text: str) -> list[tuple[str, str, str]]:
    """Extract (amount, unit, context) tuples from text."""
    results: list[tuple[str, str, str]] = []
    for match in NUMERICAL_REGEX.finditer(text):
        amount = match.group("amount") or ""
        unit = (match.group("unit") or "").strip().lower()
        start = max(0, match.start() - 30)
        end = min(len(text), match.end() + 30)
        context = text[start:end].lower()
        results.append((amount, unit, context))
    return results


class ConflictDetector:
    """Detects duplicate evidence and contradictions/conflicts across evidence items."""

    def __init__(
        self,
        *,
        duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
        conflict_threshold: float = DEFAULT_CONFLICT_THRESHOLD,
    ) -> None:
        self._duplicate_threshold = duplicate_threshold
        self._conflict_threshold = conflict_threshold

    @property
    def duplicate_threshold(self) -> float:
        """Threshold for duplicate detection."""
        return self._duplicate_threshold

    @property
    def conflict_threshold(self) -> float:
        """Threshold for conflict detection."""
        return self._conflict_threshold

    def detect_duplicates(
        self,
        evidence_list: Sequence[Evidence],
        threshold: float | None = None,
    ) -> tuple[set[str], list[list[str]]]:
        """Identify duplicate or near-identical evidence items.

        Args:
            evidence_list: Sequence of Evidence objects.
            threshold: Optional threshold override.

        Returns:
            Tuple of (set of duplicate evidence IDs, list of duplicate clusters).
        """
        thresh = threshold if threshold is not None else self._duplicate_threshold
        n = len(evidence_list)
        if n <= 1:
            return set(), []

        duplicate_ids: set[str] = set()
        clusters: list[list[str]] = []
        visited: set[int] = set()

        for i in range(n):
            if i in visited:
                continue
            item_a = evidence_list[i]
            tokens_a = set(_tokenize(item_a.text))
            stems_a = {_stem(t) for t in tokens_a}
            cluster = [item_a.evidence_id]

            for j in range(i + 1, n):
                if j in visited:
                    continue
                item_b = evidence_list[j]

                # Exact text match
                if item_a.text.strip().lower() == item_b.text.strip().lower():
                    duplicate_ids.add(item_b.evidence_id)
                    cluster.append(item_b.evidence_id)
                    visited.add(j)
                    continue

                # Fuzzy token and stem similarity
                tokens_b = set(_tokenize(item_b.text))
                stems_b = {_stem(t) for t in tokens_b}
                sim = max(_jaccard_similarity(tokens_a, tokens_b), _jaccard_similarity(stems_a, stems_b))
                if sim >= thresh:
                    duplicate_ids.add(item_b.evidence_id)
                    cluster.append(item_b.evidence_id)
                    visited.add(j)

            if len(cluster) > 1:
                clusters.append(cluster)

        return duplicate_ids, clusters

    def check_pairwise_conflict(
        self,
        item_a: Evidence,
        item_b: Evidence,
    ) -> ConflictDetail | None:
        """Analyze whether two evidence passages contradict each other."""
        text_a = item_a.text
        text_b = item_b.text

        content_a = _content_tokens(text_a)
        content_b = _content_tokens(text_b)

        # Compute topic similarity
        topic_similarity = _jaccard_similarity(content_a, content_b)

        # If completely unrelated topics, no conflict
        if topic_similarity < 0.20:
            return None

        # 1. Check Numerical Conflicts on shared context
        quantities_a = _extract_quantities(text_a)
        quantities_b = _extract_quantities(text_b)

        if quantities_a and quantities_b:
            for amount_a, unit_a, ctx_a in quantities_a:
                for amount_b, unit_b, ctx_b in quantities_b:
                    # If units match or are compatible
                    if unit_a == unit_b and amount_a != amount_b:
                        # Check if contexts share key topic words
                        ctx_overlap = _jaccard_similarity(_content_tokens(ctx_a), _content_tokens(ctx_b))
                        if ctx_overlap >= 0.25 or topic_similarity >= 0.35:
                            return ConflictDetail(
                                evidence_id_a=item_a.evidence_id,
                                evidence_id_b=item_b.evidence_id,
                                conflict_score=0.90,
                                conflict_type="numerical",
                                reason=(
                                    f"Numerical contradiction detected: '{amount_a} {unit_a}' vs '{amount_b} {unit_b}' "
                                    f"under similar context."
                                ),
                                passage_a_snippet=text_a[:120],
                                passage_b_snippet=text_b[:120],
                            )

        # 2. Check Specific Antonym Pairs FIRST (more specific than generic polarity)
        tokens_a_set = set(_tokenize(text_a))
        tokens_b_set = set(_tokenize(text_b))

        for group_1, group_2 in ANTONYM_PAIRS:
            in_a_1 = bool(tokens_a_set.intersection(group_1))
            in_a_2 = bool(tokens_a_set.intersection(group_2))
            in_b_1 = bool(tokens_b_set.intersection(group_1))
            in_b_2 = bool(tokens_b_set.intersection(group_2))

            if (in_a_1 and in_b_2) or (in_a_2 and in_b_1):
                if topic_similarity >= 0.25:
                    return ConflictDetail(
                        evidence_id_a=item_a.evidence_id,
                        evidence_id_b=item_b.evidence_id,
                        conflict_score=0.80,
                        conflict_type="policy",
                        reason="Direct antonym/incompatible policy terminology detected on shared topic.",
                        passage_a_snippet=text_a[:120],
                        passage_b_snippet=text_b[:120],
                    )

        # 3. Check Polarity / Explicit Negation Clashes
        has_not_a = any(neg in text_a.lower() for neg in ["not ", "never ", "no ", "cannot ", "neither "])
        has_not_b = any(neg in text_b.lower() for neg in ["not ", "never ", "no ", "cannot ", "neither "])

        aff_a = bool(tokens_a_set.intersection(AFFIRMATIVE_TERMS))
        neg_a = bool(tokens_a_set.intersection(NEGATIVE_TERMS)) or has_not_a

        aff_b = bool(tokens_b_set.intersection(AFFIRMATIVE_TERMS))
        neg_b = bool(tokens_b_set.intersection(NEGATIVE_TERMS)) or has_not_b

        if (aff_a and neg_b and not neg_a) or (neg_a and aff_b and not neg_b):
            if topic_similarity >= 0.25:
                return ConflictDetail(
                    evidence_id_a=item_a.evidence_id,
                    evidence_id_b=item_b.evidence_id,
                    conflict_score=0.85,
                    conflict_type="polarity",
                    reason="Contradictory polarity/permission statements on the same subject.",
                    passage_a_snippet=text_a[:120],
                    passage_b_snippet=text_b[:120],
                )

        return None

    def detect_conflicts(
        self,
        evidence_list: Sequence[Evidence],
    ) -> list[ConflictDetail]:
        """Detect all pairwise conflicts among a sequence of Evidence items."""
        conflicts: list[ConflictDetail] = []
        n = len(evidence_list)
        if n <= 1:
            return conflicts

        for i in range(n):
            for j in range(i + 1, n):
                conflict = self.check_pairwise_conflict(evidence_list[i], evidence_list[j])
                if conflict is not None:
                    conflicts.append(conflict)

        return conflicts

    def score_conflicts(
        self,
        evidence_list: Sequence[Evidence],
    ) -> tuple[dict[str, float], list[ConflictDetail]]:
        """Compute per-evidence conflict scores and return detailed conflicts.

        Args:
            evidence_list: Sequence of Evidence objects.

        Returns:
            Tuple of (mapping from evidence_id -> conflict_score, list of ConflictDetails).
        """
        conflicts = self.detect_conflicts(evidence_list)
        conflict_scores: dict[str, float] = {item.evidence_id: 0.0 for item in evidence_list}

        for conflict in conflicts:
            id_a = conflict.evidence_id_a
            id_b = conflict.evidence_id_b
            score = conflict.conflict_score

            if id_a in conflict_scores:
                conflict_scores[id_a] = max(conflict_scores[id_a], score)
            if id_b in conflict_scores:
                conflict_scores[id_b] = max(conflict_scores[id_b], score)

        return conflict_scores, conflicts


def detect_duplicates(
    evidence_list: Sequence[Evidence],
    threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
) -> tuple[set[str], list[list[str]]]:
    """Convenience function to detect duplicate evidence."""
    detector = ConflictDetector(duplicate_threshold=threshold)
    return detector.detect_duplicates(evidence_list, threshold=threshold)


def detect_conflicts(
    evidence_list: Sequence[Evidence],
    threshold: float = DEFAULT_CONFLICT_THRESHOLD,
) -> list[ConflictDetail]:
    """Convenience function to detect conflicts in evidence."""
    detector = ConflictDetector(conflict_threshold=threshold)
    return detector.detect_conflicts(evidence_list)

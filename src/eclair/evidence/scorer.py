"""Evidence quality scorer for M06 Evidence Quality & Conflict Detection.

Combines relevance, source authority, freshness, completeness, and conflict
signals into structured quality assessments and comprehensive batch reports.
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, Field

from eclair.contracts.evidence import Evidence
from eclair.exceptions import ContractValidationError
from eclair.evidence.authority import (
    DEFAULT_MIN_AUTHORITY_THRESHOLD,
    SourceAuthorityScorer,
)
from eclair.evidence.conflict import (
    DEFAULT_CONFLICT_THRESHOLD,
    DEFAULT_DUPLICATE_THRESHOLD,
    ConflictDetector,
)
from eclair.evidence.freshness import (
    DEFAULT_MIN_FRESHNESS_THRESHOLD,
    FreshnessScorer,
)
from eclair.evidence.models import (
    EvidenceQualityReport,
    EvidenceQualitySignals,
    ScoredEvidence,
)

__all__ = [
    "EvidenceScorerConfig",
    "EvidenceScorer",
    "score_completeness",
]


class EvidenceScorerConfig(BaseModel):
    """Configuration weights and detection thresholds for evidence quality scoring."""

    model_config = {"extra": "forbid"}

    weight_relevance: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Weight assigned to relevance score in overall quality fusion.",
    )
    weight_authority: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight assigned to source authority in overall quality fusion.",
    )
    weight_freshness: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight assigned to freshness/recency in overall quality fusion.",
    )
    weight_completeness: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight assigned to passage completeness in overall quality fusion.",
    )
    weight_conflict_penalty: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Penalty weight deducted for detected contradictions.",
    )
    min_quality_threshold: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Minimum overall quality score below which evidence is flagged as low quality.",
    )
    min_authority_threshold: float = Field(
        default=DEFAULT_MIN_AUTHORITY_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum source authority score threshold.",
    )
    min_freshness_threshold: float = Field(
        default=DEFAULT_MIN_FRESHNESS_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum freshness score threshold.",
    )
    conflict_threshold: float = Field(
        default=DEFAULT_CONFLICT_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Conflict score threshold above which evidence is flagged as conflicting.",
    )
    duplicate_threshold: float = Field(
        default=DEFAULT_DUPLICATE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for duplicate evidence detection.",
    )


def score_completeness(text: str) -> float:
    """Evaluate informativeness and passage completeness in [0.0, 1.0].

    Args:
        text: Passage textual content.

    Returns:
        Completeness score in [0.0, 1.0].
    """
    clean_text = text.strip()
    char_len = len(clean_text)
    if char_len == 0:
        return 0.0

    # Base length score
    if char_len < 20:
        base = 0.25
    elif char_len < 50:
        base = 0.50
    elif char_len < 70:
        base = 0.75
    elif char_len <= 800:
        base = 1.00
    else:
        base = 0.95

    # Check word count
    words = clean_text.split()
    if len(words) < 4:
        base = min(base, 0.40)

    # Penalize truncation ellipsis
    if clean_text.endswith("...") or clean_text.startswith("..."):
        base = max(0.2, base - 0.15)

    return max(0.0, min(1.0, base))


def _stem(word: str) -> str:
    """Simple stemmer for matching inflections."""
    w = word.lower()
    for suffix in ("ing", "ed", "es", "s", "ly", "tion", "ment"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


def _compute_lexical_relevance(claim: str, text: str) -> float:
    """Compute lexical/token overlap relevance between claim and evidence text."""
    claim_raw = re.findall(r"\b\w+\b", claim.lower())
    text_raw = re.findall(r"\b\w+\b", text.lower())
    if not claim_raw or not text_raw:
        return 0.5

    claim_stems = {_stem(w) for w in claim_raw}
    text_stems = {_stem(w) for w in text_raw}

    intersection = claim_stems.intersection(text_stems)
    jaccard = len(intersection) / float(len(claim_stems.union(text_stems)))
    recall = len(intersection) / float(len(claim_stems))
    score = 0.3 * jaccard + 0.7 * recall
    return max(0.0, min(1.0, score))


class EvidenceScorer:
    """Primary evidence quality scoring engine.

    Scores individual evidence items and batches against the five core quality
    signals: relevance, authority, freshness, completeness, and conflict.
    """

    def __init__(
        self,
        config: EvidenceScorerConfig | None = None,
        *,
        authority_scorer: SourceAuthorityScorer | None = None,
        freshness_scorer: FreshnessScorer | None = None,
        conflict_detector: ConflictDetector | None = None,
    ) -> None:
        self._config = config if config is not None else EvidenceScorerConfig()

        self._authority_scorer = (
            authority_scorer
            if authority_scorer is not None
            else SourceAuthorityScorer(
                min_authority_threshold=self._config.min_authority_threshold
            )
        )
        self._freshness_scorer = (
            freshness_scorer
            if freshness_scorer is not None
            else FreshnessScorer(
                min_freshness_threshold=self._config.min_freshness_threshold
            )
        )
        self._conflict_detector = (
            conflict_detector
            if conflict_detector is not None
            else ConflictDetector(
                duplicate_threshold=self._config.duplicate_threshold,
                conflict_threshold=self._config.conflict_threshold,
            )
        )

    @property
    def config(self) -> EvidenceScorerConfig:
        """The active scoring configuration."""
        return self._config

    def _validate_evidence(self, item: Any) -> Evidence:
        """Validate that an input object conforms to the M01 Evidence contract."""
        if isinstance(item, Evidence):
            return item
        if isinstance(item, dict):
            try:
                return Evidence(**item)
            except Exception as exc:
                raise ContractValidationError(
                    f"Failed to parse Evidence dictionary: {exc}",
                    code="contract_invalid_evidence",
                ) from exc
        raise ContractValidationError(
            f"Expected Evidence contract instance, got {type(item).__name__}",
            code="contract_invalid_evidence",
        )

    def score_item(
        self,
        evidence: Evidence,
        *,
        claim_text: str | None = None,
        conflict_score: float = 0.0,
        is_duplicate: bool = False,
        metadata: Mapping[str, Any] | None = None,
        reference_date: datetime | None = None,
    ) -> ScoredEvidence:
        """Score an individual Evidence item.

        Args:
            evidence: The M01 Evidence contract instance.
            claim_text: Optional claim/query text for computing relevance if missing.
            conflict_score: Pre-computed conflict score for this item (in [0.0, 1.0]).
            is_duplicate: Whether this item is flagged as duplicate.
            metadata: Optional document metadata dictionary.
            reference_date: Optional reference date for freshness scoring.

        Returns:
            A populated :class:`ScoredEvidence` instance.
        """
        ev = self._validate_evidence(evidence)

        # 1. Relevance Score
        if ev.relevance_score is not None:
            relevance = max(0.0, min(1.0, float(ev.relevance_score)))
        elif claim_text and claim_text.strip():
            relevance = _compute_lexical_relevance(claim_text, ev.text)
        else:
            relevance = 0.50

        # 2. Source Authority Score
        authority = self._authority_scorer.score(ev.source, metadata=metadata)

        # 3. Freshness Score
        freshness = self._freshness_scorer.score(
            source=ev.source,
            text=ev.text,
            metadata=metadata,
            reference_date=reference_date,
        )

        # 4. Completeness Score
        completeness = score_completeness(ev.text)

        # 5. Conflict Score
        conf_score = max(0.0, min(1.0, float(conflict_score)))

        # 6. Composite Overall Quality Score
        cfg = self._config
        overall = (
            cfg.weight_relevance * relevance
            + cfg.weight_authority * authority
            + cfg.weight_freshness * freshness
            + cfg.weight_completeness * completeness
            - cfg.weight_conflict_penalty * conf_score
        )
        overall_clamped = max(0.0, min(1.0, overall))

        # 7. Quality & Diagnostic Flags
        flags: list[str] = []
        is_outdated = freshness < cfg.min_freshness_threshold
        if is_outdated:
            flags.append("OUTDATED")

        if is_duplicate:
            flags.append("DUPLICATE")

        is_conflicting = conf_score >= cfg.conflict_threshold
        if is_conflicting:
            flags.append("CONFLICTING")

        is_low_authority = authority < cfg.min_authority_threshold
        if is_low_authority:
            flags.append("LOW_AUTHORITY")

        is_incomplete = completeness < 0.40
        if is_incomplete:
            flags.append("INCOMPLETE")

        is_low_quality = (
            overall_clamped < cfg.min_quality_threshold or is_low_authority
        )
        if is_low_quality:
            flags.append("LOW_QUALITY")

        signals = EvidenceQualitySignals(
            evidence_id=ev.evidence_id,
            relevance_score=relevance,
            authority_score=authority,
            freshness_score=freshness,
            completeness_score=completeness,
            conflict_score=conf_score,
            overall_score=overall_clamped,
            is_outdated=is_outdated,
            is_duplicate=is_duplicate,
            is_conflicting=is_conflicting,
            is_low_quality=is_low_quality,
            flags=flags,
            metadata=dict(metadata) if metadata else {},
        )

        return ScoredEvidence(evidence=ev, signals=signals)

    def score_evidence(
        self,
        evidence_list: Sequence[Evidence],
        *,
        claim_text: str | None = None,
        metadata_map: Mapping[str, Mapping[str, Any]] | None = None,
        reference_date: datetime | None = None,
    ) -> EvidenceQualityReport:
        """Evaluate and score a batch of retrieved Evidence objects.

        Args:
            evidence_list: Sequence of M01 Evidence contract items.
            claim_text: Optional query/claim text.
            metadata_map: Optional mapping from evidence_id -> metadata dict.
            reference_date: Optional reference date for freshness scoring.

        Returns:
            An :class:`EvidenceQualityReport` summarizing signals and detections.
        """
        # Handle empty evidence list -> Insufficient evidence signal (NO CRASH)
        if not evidence_list:
            return EvidenceQualityReport(
                items=[],
                average_quality=0.0,
                is_insufficient=True,
                has_conflicts=False,
                conflicts=[],
                duplicate_ids=[],
                outdated_ids=[],
                low_quality_ids=[],
                summary_flags=["NO_EVIDENCE", "INSUFFICIENT_EVIDENCE"],
            )

        # Validate all items
        validated_items = [self._validate_evidence(item) for item in evidence_list]

        # Detect duplicates across batch
        duplicate_ids, _ = self._conflict_detector.detect_duplicates(validated_items)

        # Detect pairwise conflicts across batch
        conflict_scores, conflicts = self._conflict_detector.score_conflicts(validated_items)

        scored_items: list[ScoredEvidence] = []
        outdated_ids: list[str] = []
        low_quality_ids: list[str] = []

        meta_lookup = dict(metadata_map) if metadata_map else {}

        for ev in validated_items:
            item_meta = meta_lookup.get(ev.evidence_id)
            conf_score = conflict_scores.get(ev.evidence_id, 0.0)
            is_dup = ev.evidence_id in duplicate_ids

            scored = self.score_item(
                ev,
                claim_text=claim_text,
                conflict_score=conf_score,
                is_duplicate=is_dup,
                metadata=item_meta,
                reference_date=reference_date,
            )
            scored_items.append(scored)

            if scored.signals.is_outdated:
                outdated_ids.append(ev.evidence_id)
            if scored.signals.is_low_quality:
                low_quality_ids.append(ev.evidence_id)

        # Compute aggregate metrics
        avg_quality = sum(item.signals.overall_score for item in scored_items) / float(len(scored_items))
        has_conflicts = len(conflicts) > 0

        # Summary flags
        summary_flags: list[str] = []
        if has_conflicts:
            summary_flags.append("HAS_CONFLICTS")
        if duplicate_ids:
            summary_flags.append("HAS_DUPLICATES")
        if outdated_ids:
            summary_flags.append("HAS_OUTDATED_EVIDENCE")

        # Insufficient evidence signal check: all items low quality or average quality < threshold
        is_insufficient = avg_quality < (self._config.min_quality_threshold * 0.85) or len(low_quality_ids) == len(scored_items)
        if is_insufficient:
            summary_flags.append("INSUFFICIENT_QUALITY")

        return EvidenceQualityReport(
            items=scored_items,
            average_quality=max(0.0, min(1.0, avg_quality)),
            is_insufficient=is_insufficient,
            has_conflicts=has_conflicts,
            conflicts=conflicts,
            duplicate_ids=list(duplicate_ids),
            outdated_ids=outdated_ids,
            low_quality_ids=low_quality_ids,
            summary_flags=summary_flags,
        )

    def evaluate(
        self,
        evidence_list: Sequence[Evidence],
        *,
        claim_text: str | None = None,
        metadata_map: Mapping[str, Mapping[str, Any]] | None = None,
        reference_date: datetime | None = None,
    ) -> EvidenceQualityReport:
        """Alias for :meth:`score_evidence`."""
        return self.score_evidence(
            evidence_list,
            claim_text=claim_text,
            metadata_map=metadata_map,
            reference_date=reference_date,
        )

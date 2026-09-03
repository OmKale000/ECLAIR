"""ECLAIR Evidence Quality & Conflict Detection (M06).

Provides evidence quality scoring and conflict detection over retrieved evidence:
- Evaluates relevance, source authority, freshness, completeness, and conflict.
- Detects outdated documents, duplicates, conflicting evidence, low-quality sources,
  and insufficient evidence.
- Exposes structured quality signals for downstream consumption by M07 Verification
  and M10 Confidence Estimation.
"""

from __future__ import annotations

from eclair.evidence.authority import (
    DEFAULT_MIN_AUTHORITY_THRESHOLD,
    SourceAuthorityScorer,
    is_low_quality_source,
    score_source_authority,
)
from eclair.evidence.conflict import (
    DEFAULT_CONFLICT_THRESHOLD,
    DEFAULT_DUPLICATE_THRESHOLD,
    ConflictDetector,
    detect_conflicts,
    detect_duplicates,
)
from eclair.evidence.freshness import (
    DEFAULT_MIN_FRESHNESS_THRESHOLD,
    FreshnessScorer,
    is_outdated_evidence,
    score_freshness,
)
from eclair.evidence.models import (
    ConflictDetail,
    EvidenceQualityReport,
    EvidenceQualitySignals,
    ScoredEvidence,
)
from eclair.evidence.scorer import (
    EvidenceScorer,
    EvidenceScorerConfig,
    score_completeness,
)

__all__ = [
    # Models
    "EvidenceQualitySignals",
    "ConflictDetail",
    "ScoredEvidence",
    "EvidenceQualityReport",
    # Authority
    "SourceAuthorityScorer",
    "score_source_authority",
    "is_low_quality_source",
    "DEFAULT_MIN_AUTHORITY_THRESHOLD",
    # Freshness
    "FreshnessScorer",
    "score_freshness",
    "is_outdated_evidence",
    "DEFAULT_MIN_FRESHNESS_THRESHOLD",
    # Conflict & Duplicates
    "ConflictDetector",
    "detect_duplicates",
    "detect_conflicts",
    "DEFAULT_DUPLICATE_THRESHOLD",
    "DEFAULT_CONFLICT_THRESHOLD",
    # Scorer Orchestration
    "EvidenceScorerConfig",
    "EvidenceScorer",
    "score_completeness",
]

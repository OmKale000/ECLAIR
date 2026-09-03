"""Freshness scoring and obsolescence detection for M06 Evidence Quality.

Calculates temporal validity and recency scores from document metadata,
ISO 8601 timestamps, textual date cues, and obsolescence keywords.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Mapping

__all__ = [
    "FreshnessScorer",
    "score_freshness",
    "is_outdated_evidence",
    "DEFAULT_MIN_FRESHNESS_THRESHOLD",
]

DEFAULT_MIN_FRESHNESS_THRESHOLD: float = 0.40

# Deprecation and obsolescence keywords
DEPRECATION_PATTERN = re.compile(
    r"(deprecated|obsolete|superseded|archived|outdated|legacy|expired|sunsetted|discontinued)",
    re.IGNORECASE,
)

# Regex to find 4-digit years (e.g. 1990 - 2099)
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")


def parse_iso_or_date(value: Any) -> datetime | None:
    """Safely parse a datetime or ISO 8601 string into a UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if not isinstance(value, str) or not value.strip():
        return None

    clean_str = value.strip()
    # Try standard fromisoformat (handles YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, with or without Z/+offset)
    try:
        normalized = clean_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        pass

    # Try standard date format matching
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(clean_str, fmt).replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    return None


class FreshnessScorer:
    """Scorer evaluating temporal validity and detecting outdated evidence."""

    def __init__(
        self,
        *,
        min_freshness_threshold: float = DEFAULT_MIN_FRESHNESS_THRESHOLD,
        reference_date: datetime | None = None,
        max_valid_age_days: float = 730.0,
    ) -> None:
        self._min_freshness_threshold = min_freshness_threshold
        self._reference_date = (
            reference_date.astimezone(timezone.utc)
            if reference_date and reference_date.tzinfo
            else reference_date.replace(tzinfo=timezone.utc)
            if reference_date
            else None
        )
        self._max_valid_age_days = max_valid_age_days

    @property
    def min_freshness_threshold(self) -> float:
        """Threshold below which evidence is classified as outdated."""
        return self._min_freshness_threshold

    def _get_reference_date(self, override: datetime | None = None) -> datetime:
        """Resolve the active reference date in UTC."""
        if override is not None:
            if override.tzinfo is None:
                return override.replace(tzinfo=timezone.utc)
            return override.astimezone(timezone.utc)
        if self._reference_date is not None:
            return self._reference_date
        return datetime.now(timezone.utc)

    def calculate_age_decay(self, doc_date: datetime, ref_date: datetime) -> float:
        """Compute exponential/piecewise temporal decay score in [0.0, 1.0]."""
        age_days = (ref_date - doc_date).total_seconds() / 86400.0

        # Current or future date -> full freshness
        if age_days <= 0:
            return 1.0
        if age_days <= 30:
            return 1.0
        if age_days <= 90:
            return 0.95
        if age_days <= 180:
            return 0.85
        if age_days <= 365:
            return 0.75
        if age_days <= 730:
            return 0.55

        # Beyond 2 years: decay towards 0.1
        excess_days = age_days - 730.0
        decay = 0.55 - (excess_days / 730.0) * 0.40
        return max(0.1, min(1.0, decay))

    def score(
        self,
        *,
        source: str | None = None,
        text: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        reference_date: datetime | None = None,
    ) -> float:
        """Compute freshness score in [0.0, 1.0].

        Args:
            source: Source identifier or path.
            text: Passage text.
            metadata: Document metadata containing dates or versions.
            reference_date: Optional reference date override.

        Returns:
            Freshness score in [0.0, 1.0].
        """
        ref_dt = self._get_reference_date(reference_date)

        # Check explicit freshness override in metadata
        if metadata:
            explicit_freshness = metadata.get("freshness_score")
            if explicit_freshness is not None:
                try:
                    return max(0.0, min(1.0, float(explicit_freshness)))
                except (ValueError, TypeError):
                    pass

        has_deprecation = False

        # Check for deprecation keywords in source or text
        combined_text = f"{source or ''} {text or ''}"
        normalized_combined = re.sub(r"[_\-\\/]+", " ", combined_text.lower())
        if DEPRECATION_PATTERN.search(combined_text) or DEPRECATION_PATTERN.search(normalized_combined):
            has_deprecation = True

        # Extract timestamp from metadata
        doc_dt: datetime | None = None
        if metadata:
            for date_key in ("modified_date", "created_date", "timestamp", "date", "updated_at"):
                val = metadata.get(date_key)
                if val:
                    parsed = parse_iso_or_date(val)
                    if parsed is not None:
                        doc_dt = parsed
                        break

        # If no metadata date, check if text has year references
        if doc_dt is None and text:
            years = [int(y) for y in YEAR_PATTERN.findall(text)]
            if years:
                latest_year = max(years)
                # If year is in valid past/present range
                if 1990 <= latest_year <= ref_dt.year + 2:
                    doc_dt = datetime(latest_year, 1, 1, tzinfo=timezone.utc)

        # Compute base score
        if doc_dt is not None:
            base_score = self.calculate_age_decay(doc_dt, ref_dt)
        else:
            # Controlled KB or standard documents without explicit date get strong default
            base_score = 0.85

        # Apply deprecation penalty
        if has_deprecation:
            base_score = min(base_score * 0.25, 0.20)

        return max(0.0, min(1.0, base_score))

    def is_outdated(
        self,
        *,
        source: str | None = None,
        text: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        threshold: float | None = None,
        reference_date: datetime | None = None,
    ) -> bool:
        """Check whether evidence is outdated or superseded."""
        thresh = threshold if threshold is not None else self._min_freshness_threshold
        freshness = self.score(
            source=source,
            text=text,
            metadata=metadata,
            reference_date=reference_date,
        )
        return freshness < thresh


def score_freshness(
    *,
    source: str | None = None,
    text: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    reference_date: datetime | None = None,
) -> float:
    """Convenience function to compute freshness score."""
    scorer = FreshnessScorer(reference_date=reference_date)
    return scorer.score(
        source=source,
        text=text,
        metadata=metadata,
        reference_date=reference_date,
    )


def is_outdated_evidence(
    *,
    source: str | None = None,
    text: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    threshold: float = DEFAULT_MIN_FRESHNESS_THRESHOLD,
    reference_date: datetime | None = None,
) -> bool:
    """Convenience function to check if evidence is outdated."""
    scorer = FreshnessScorer(
        min_freshness_threshold=threshold,
        reference_date=reference_date,
    )
    return scorer.is_outdated(
        source=source,
        text=text,
        metadata=metadata,
        threshold=threshold,
        reference_date=reference_date,
    )

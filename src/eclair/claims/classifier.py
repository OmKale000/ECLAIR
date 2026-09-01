"""Heuristic claim-type classification for M03 Claim Extraction.

Assigns each normalized claim exactly one frozen :class:`ClaimType` member
(FACTUAL, NUMERIC, TEMPORAL, ENTITY, OTHER — owned by M01). Classification is
deterministic and rule-based; anything unclassifiable maps to ``ClaimType.OTHER``.
This never introduces new type values — only the frozen M01 members are returned.
"""

from __future__ import annotations

import re

from eclair.contracts import ClaimType

__all__ = ["ClaimClassifier"]

# Detect an explicit number (digits, optionally with separators/decimals/percent).
_NUMERIC_RE = re.compile(r"\d")
_PERCENT_OR_CURRENCY_RE = re.compile(r"[%$€£]")

# Month names and common temporal words signal a TEMPORAL claim.
# NOTE: "may" is deliberately excluded here because it is overwhelmingly the
# modal verb ("you may return"); the capitalized month "May" is matched by
# ``_MONTH_MAY_RE`` below (case-sensitive) to avoid false positives.
_TEMPORAL_RE = re.compile(
    r"\b("
    r"year|years|month|months|day|days|week|weeks|hour|hours|minute|minutes|"
    r"today|yesterday|tomorrow|date|dates|century|decade|"
    r"january|february|march|april|june|july|august|september|october|"
    r"november|december|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r")\b",
    re.IGNORECASE,
)

# The month "May" only when capitalized (case-sensitive), to exclude the modal verb.
_MONTH_MAY_RE = re.compile(r"\bMay\b")

# A 4-digit year is a strong temporal signal.
_YEAR_RE = re.compile(r"\b(1\d{3}|20\d{2})\b")

# A capitalized multi-word or mid-sentence proper noun signals an ENTITY claim.
_PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


class ClaimClassifier:
    """Rule-based classifier mapping claim text to a frozen ``ClaimType``."""

    def classify(self, text: str) -> ClaimType:
        """Return the :class:`ClaimType` for ``text`` (OTHER if unclassifiable).

        Precedence: TEMPORAL (year/date words) -> NUMERIC (other numbers/percent/
        currency) -> ENTITY (proper-noun phrase) -> FACTUAL (has alphabetic
        content) -> OTHER.
        """
        stripped = text.strip()
        if not stripped:
            return ClaimType.OTHER

        if _YEAR_RE.search(stripped) or _TEMPORAL_RE.search(stripped) or _MONTH_MAY_RE.search(
            stripped
        ):
            return ClaimType.TEMPORAL

        if _NUMERIC_RE.search(stripped) or _PERCENT_OR_CURRENCY_RE.search(stripped):
            return ClaimType.NUMERIC

        if _PROPER_NOUN_RE.search(stripped):
            return ClaimType.ENTITY

        if any(ch.isalpha() for ch in stripped):
            return ClaimType.FACTUAL

        return ClaimType.OTHER

"""Deterministic claim-text normalization for M03 Claim Extraction.

Normalizes equivalent phrasing so that trivially-different wordings collapse to
the same claim. This step is deterministic and requires no LLM. It produces:

* a cleaned *display* text (collapsed whitespace, trimmed, trailing terminal
  punctuation removed), used as the ``Claim.text``; and
* a *comparison key* (lowercased, punctuation-stripped) used only for exact
  duplicate detection in the deduplicator.

No reliability logic lives here (COMMON_RULES sec.6); this is text hygiene only.
"""

from __future__ import annotations

import re

__all__ = ["ClaimNormalizer"]

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]")


class ClaimNormalizer:
    """Deterministic normalization of raw claim text."""

    def normalize(self, text: str) -> str:
        """Return cleaned display text for a raw claim.

        Collapses internal whitespace, trims surrounding whitespace, and removes
        a single trailing terminal punctuation mark (``. ! ?``). Returns an empty
        string when nothing meaningful remains.
        """
        collapsed = _WHITESPACE_RE.sub(" ", text).strip()
        if collapsed and collapsed[-1] in ".!?":
            collapsed = collapsed[:-1].rstrip()
        return collapsed

    def comparison_key(self, text: str) -> str:
        """Return a normalized key for exact-duplicate comparison.

        Lowercases, removes punctuation, and collapses whitespace so that
        equivalent phrasings differing only in case/punctuation/spacing map to
        the same key.
        """
        lowered = text.lower()
        without_punct = _PUNCT_RE.sub(" ", lowered)
        return _WHITESPACE_RE.sub(" ", without_punct).strip()

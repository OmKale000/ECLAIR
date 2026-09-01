"""ECLAIR Claim Extraction (M03).

Breaks one generated answer into atomic, normalized, deduplicated, classified
``Claim`` objects (M01 contract). Public entry point is
``ClaimExtractor.extract(text) -> list[Claim]`` (Spec sec.4.1, sec.4.3).

The extractor calls the LLM only through the M02 LLM Gateway and never contacts
providers directly. It performs no retrieval, verification, confidence, or
decision logic.
"""

from __future__ import annotations

from eclair.claims.classifier import ClaimClassifier
from eclair.claims.deduplicator import ClaimDeduplicator, Encoder
from eclair.claims.extractor import ClaimExtractor, LLMClient
from eclair.claims.models import ExtractionResult
from eclair.claims.normalizer import ClaimNormalizer

__all__ = [
    "ClaimExtractor",
    "LLMClient",
    "ClaimNormalizer",
    "ClaimDeduplicator",
    "Encoder",
    "ClaimClassifier",
    "ExtractionResult",
]

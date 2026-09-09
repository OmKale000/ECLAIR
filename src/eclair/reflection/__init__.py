"""ECLAIR Self-Reflection & Self-Correction (M12).

Executes bounded low-confidence correction loops:
    Generate -> Verify -> Low ECS? -> Critique -> Regenerate -> Verify again

Public entry point is :class:`ReflectionController`.
"""

from __future__ import annotations

from eclair.reflection.controller import ReflectionController
from eclair.reflection.critic import ResponseCritic
from eclair.reflection.models import (
    DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    DEFAULT_MAX_ITERATIONS,
    CritiqueItem,
    CritiqueReport,
    IterationRecord,
    ReflectionConfig,
    ReflectionResult,
)
from eclair.reflection.rewriter import ResponseRewriter
from eclair.reflection.stopping import StoppingController

__all__ = [
    "DEFAULT_LOW_CONFIDENCE_THRESHOLD",
    "DEFAULT_MAX_ITERATIONS",
    "CritiqueItem",
    "CritiqueReport",
    "IterationRecord",
    "ReflectionConfig",
    "ReflectionController",
    "ReflectionResult",
    "ResponseCritic",
    "ResponseRewriter",
    "StoppingController",
]

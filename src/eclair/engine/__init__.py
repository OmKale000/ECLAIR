"""ECLAIR engine scaffolding package (M01 Foundation).

Exposes the engine scaffolding shells. The integrated pipeline flow is owned by
the engine/orchestrator during the integration phase (Spec sec.4.2). M01 provides
scaffolding only.
"""

from __future__ import annotations

from eclair.engine.eclair_engine import EclairEngine
from eclair.engine.orchestrator import Orchestrator
from eclair.engine.pipeline import Pipeline

__all__ = ["EclairEngine", "Orchestrator", "Pipeline"]

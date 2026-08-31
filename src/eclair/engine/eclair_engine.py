"""ECLAIR engine facade scaffolding (M01 Foundation).

Top-level entry point that product layers (M15/M16/M17) consume (Spec sec.4.12).
M01 provides scaffolding only — NO reliability logic. The facade delegates to the
Orchestrator, which is wired during the integration phase (Spec sec.4.2).
"""

from __future__ import annotations

from eclair.contracts.query import Query
from eclair.contracts.result import EclairResult
from eclair.engine.orchestrator import Orchestrator

__all__ = ["EclairEngine"]


class EclairEngine:
    """Integrated engine facade. Scaffolding shell only."""

    def __init__(self, orchestrator: Orchestrator | None = None) -> None:
        self._orchestrator = orchestrator or Orchestrator()

    def ask(self, query: Query) -> EclairResult:
        """Run the reliability pipeline for a query and return the aggregate result.

        Not implemented in M01: delegates to the Orchestrator, wired during the
        integration phase.
        """
        return self._orchestrator.run(query)

"""Engine orchestrator scaffolding (M01 Foundation).

The engine/orchestrator owns how modules are wired into the integrated pipeline
(Spec sec.4.2). M01 provides scaffolding only — NO reliability logic. Wiring is
implemented during the integration phase, not by M01.
"""

from __future__ import annotations

from eclair.contracts.query import Query
from eclair.contracts.result import EclairResult

__all__ = ["Orchestrator"]


class Orchestrator:
    """Owns the integrated pipeline flow. Scaffolding shell only."""

    def run(self, query: Query) -> EclairResult:
        """Run the full reliability pipeline for a query.

        Not implemented in M01: pipeline wiring is owned by the integration phase.
        """
        raise NotImplementedError(
            "Orchestrator.run is wired during the integration phase, not by M01."
        )

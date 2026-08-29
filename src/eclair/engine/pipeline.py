"""Pipeline scaffolding (M01 Foundation).

Represents the ordered reliability pipeline stages (Spec sec.5). M01 provides
scaffolding only — NO reliability logic and no stage implementations. The
concrete stage wiring is owned by the integration phase (Spec sec.4.2).
"""

from __future__ import annotations

from eclair.contracts.query import Query
from eclair.contracts.result import EclairResult

__all__ = ["Pipeline"]


class Pipeline:
    """Ordered reliability pipeline. Scaffolding shell only."""

    def execute(self, query: Query) -> EclairResult:
        """Execute the pipeline stages for a query.

        Not implemented in M01: stage wiring is owned by the integration phase.
        """
        raise NotImplementedError(
            "Pipeline.execute is wired during the integration phase, not by M01."
        )

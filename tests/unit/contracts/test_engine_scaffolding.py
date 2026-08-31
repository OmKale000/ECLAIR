"""Unit tests for M01 engine scaffolding shells (no reliability logic)."""

from __future__ import annotations

import pytest

from eclair.contracts import Query
from eclair.engine import EclairEngine, Orchestrator, Pipeline


def test_orchestrator_run_not_implemented_in_m01() -> None:
    with pytest.raises(NotImplementedError):
        Orchestrator().run(Query(question="q"))


def test_pipeline_execute_not_implemented_in_m01() -> None:
    with pytest.raises(NotImplementedError):
        Pipeline().execute(Query(question="q"))


def test_engine_delegates_to_orchestrator() -> None:
    with pytest.raises(NotImplementedError):
        EclairEngine().ask(Query(question="q"))

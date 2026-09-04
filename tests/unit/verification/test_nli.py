"""Unit tests for M07 NLIEngine."""

from __future__ import annotations

import pytest

from eclair.exceptions import ContractValidationError, ModuleError
from eclair.verification import NLIEngine, NLILabel, NLIPrediction


def test_nli_engine_initialization_defaults() -> None:
    engine = NLIEngine()
    assert engine.model_name == "roberta-large-mnli"


def test_nli_engine_custom_pipeline_fn() -> None:
    engine = NLIEngine(
        pipeline_fn=lambda p, h: {"entailment": 0.8, "contradiction": 0.1, "neutral": 0.1}
    )
    pred = engine.predict("Premise text", "Hypothesis text")
    assert isinstance(pred, NLIPrediction)
    assert pred.label is NLILabel.ENTAILMENT
    assert pred.entailment_score == 0.8
    assert pred.contradiction_score == 0.1
    assert pred.neutral_score == 0.1


def test_nli_engine_predict_entailment_heuristic() -> None:
    engine = NLIEngine()
    pred = engine.predict(
        premise="The subscription cancellation fee is fifty dollars.",
        hypothesis="The subscription cancellation fee is fifty dollars.",
    )
    assert pred.label is NLILabel.ENTAILMENT
    assert pred.entailment_score > 0.8


def test_nli_engine_predict_contradiction_heuristic() -> None:
    engine = NLIEngine()
    pred = engine.predict(
        premise="Subscriptions can never be cancelled without penalty.",
        hypothesis="Subscriptions can be cancelled without penalty.",
    )
    assert pred.label is NLILabel.CONTRADICTION
    assert pred.contradiction_score > 0.7


def test_nli_engine_predict_neutral_heuristic() -> None:
    engine = NLIEngine()
    pred = engine.predict(
        premise="The weather in Seattle is rainy.",
        hypothesis="The company quarterly revenue grew by ten percent.",
    )
    assert pred.label is NLILabel.NEUTRAL
    assert pred.neutral_score > 0.6


def test_nli_engine_rejects_empty_or_non_string_inputs() -> None:
    engine = NLIEngine()

    with pytest.raises(ContractValidationError):
        engine.predict("", "Valid hypothesis")

    with pytest.raises(ContractValidationError):
        engine.predict("Valid premise", "")

    with pytest.raises(ContractValidationError):
        engine.predict(None, "Valid hypothesis")  # type: ignore[arg-type]

    with pytest.raises(ContractValidationError):
        engine.predict("Valid premise", 123)  # type: ignore[arg-type]


def test_nli_engine_handles_pipeline_callable_exception() -> None:
    def broken_callable(p: str, h: str) -> dict[str, float]:
        raise RuntimeError("Inference hardware error")

    engine = NLIEngine(pipeline_fn=broken_callable)
    with pytest.raises(ModuleError) as exc_info:
        engine.predict("Premise", "Hypothesis")

    assert exc_info.value.code == "nli_execution_failed"

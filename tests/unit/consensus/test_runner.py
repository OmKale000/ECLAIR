"""Unit tests for M09 ConsensusRunner orchestration."""

from __future__ import annotations

import pytest

from eclair.consensus.models import ModelCallConfig, ModelOutput
from eclair.consensus.runner import ConsensusRunner
from eclair.contracts.enums import ConsensusLevel
from eclair.contracts.query import Query
from eclair.exceptions import ModuleError
from eclair.llm.base import LLMRequest, LLMResponse


class FakeLLMClient:
    """Mock LLM Gateway client for testing."""

    def __init__(
        self, responses: dict[str, str] | None = None, failing_providers: set[str] | None = None
    ) -> None:
        self.responses = responses or {}
        self.failing_providers = failing_providers or set()
        self.call_count = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        model = request.model or "default-model"
        provider = "fake-provider"

        if model in self.failing_providers or provider in self.failing_providers:
            raise ModuleError(f"Provider failure for {model}", code="llm_request_failed")

        text = self.responses.get(model, f"Response from {model} for prompt: {request.prompt}")
        return LLMResponse(text=text, model=model, provider=provider)


def test_runner_unanimous_consensus() -> None:
    fake_client = FakeLLMClient(
        responses={
            "m1": "Refunds are available for 30 calendar days.",
            "m2": "Refunds are available for 30 calendar days.",
            "m3": "Refunds are available for 30 calendar days.",
        }
    )
    runner = ConsensusRunner(llm=fake_client)
    models = [
        ModelCallConfig(provider="ollama", model="m1"),
        ModelCallConfig(provider="ollama", model="m2"),
        ModelCallConfig(provider="ollama", model="m3"),
    ]

    res = runner.run("What is the refund window?", models=models)

    assert res.agreement_score == 1.0
    assert res.consensus_level == ConsensusLevel.FULL
    assert res.majority_answer == "Refunds are available for 30 calendar days."
    assert len(res.successful_models) == 3
    assert len(res.failed_models) == 0
    assert res.is_truth is False  # Non-negotiable invariant
    assert fake_client.call_count == 3


def test_runner_partial_consensus_divergence() -> None:
    fake_client = FakeLLMClient(
        responses={
            "m1": "Refunds are valid for 30 days.",
            "m2": "Refunds are strictly forbidden.",
            "m3": "Products are replaced after 90 days.",
        }
    )
    runner = ConsensusRunner(llm=fake_client)
    models = [
        ModelCallConfig(provider="ollama", model="m1"),
        ModelCallConfig(provider="gemini", model="m2"),
        ModelCallConfig(provider="groq", model="m3"),
    ]

    res = runner.run("Can I get a refund?", models=models)

    assert res.agreement_score < 0.60
    assert res.consensus_level == ConsensusLevel.PARTIAL
    assert len(res.successful_models) == 3
    assert len(res.failed_models) == 0
    assert res.is_truth is False


def test_runner_graceful_degradation_one_failed_model() -> None:
    fake_client = FakeLLMClient(
        responses={
            "m1": "Refunds take 5-7 business days to process.",
            "m2": "Refunds take 5-7 business days to process.",
        },
        failing_providers={"m3_broken"},
    )
    runner = ConsensusRunner(llm=fake_client)
    models = [
        ModelCallConfig(provider="ollama", model="m1"),
        ModelCallConfig(provider="ollama", model="m2"),
        ModelCallConfig(provider="ollama", model="m3_broken"),
    ]

    res = runner.run("How long do refunds take?", models=models)

    # Failed model did not crash consensus
    assert len(res.successful_models) == 2
    assert len(res.failed_models) == 1
    assert any("m3_broken" in f for f in res.failed_models)
    # Remaining 2 agree unanimously
    assert res.agreement_score == 1.0
    assert res.consensus_level == ConsensusLevel.FULL
    assert res.majority_answer == "Refunds take 5-7 business days to process."


def test_runner_all_models_failed_raises() -> None:
    fake_client = FakeLLMClient(failing_providers={"m1", "m2"})
    runner = ConsensusRunner(llm=fake_client)
    models = [
        ModelCallConfig(provider="ollama", model="m1"),
        ModelCallConfig(provider="ollama", model="m2"),
    ]

    with pytest.raises(ModuleError) as exc_info:
        runner.run("Query text", models=models)

    assert exc_info.value.code == "consensus_all_models_failed"


def test_runner_empty_query_raises() -> None:
    runner = ConsensusRunner(llm=FakeLLMClient())
    with pytest.raises(ModuleError) as exc_info:
        runner.run("   ")
    assert exc_info.value.code == "consensus_empty_query"


def test_runner_query_contract_input() -> None:
    fake_client = FakeLLMClient(responses={"default": "Answer text"})
    runner = ConsensusRunner(llm=fake_client)
    query_contract = Query(question="What is company policy?")

    res = runner.run(query_contract, models=[ModelCallConfig(provider="ollama", model="default")])
    assert res.query == "What is company policy?"
    assert res.agreement_score == 1.0


@pytest.mark.anyio
async def test_runner_async_run() -> None:
    fake_client = FakeLLMClient(
        responses={
            "m1": "Support available 24/7",
            "m2": "Support available 24/7",
        }
    )
    runner = ConsensusRunner(llm=fake_client)
    models = [
        ModelCallConfig(provider="ollama", model="m1"),
        ModelCallConfig(provider="ollama", model="m2"),
    ]

    res = await runner.async_run("What are support hours?", models=models)
    assert res.agreement_score == 1.0
    assert res.consensus_level == ConsensusLevel.FULL


def test_runner_evaluate_outputs_pure() -> None:
    runner = ConsensusRunner()
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Standard policy applies."),
        ModelOutput(model="m2", provider="gemini", text="Standard policy applies."),
    ]
    res = runner.evaluate_outputs("What policy applies?", outputs)
    assert res.agreement_score == 1.0
    assert res.consensus_level == ConsensusLevel.FULL
    assert res.majority_answer == "Standard policy applies."
    assert res.is_truth is False

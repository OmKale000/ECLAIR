"""Unit tests for M09 DiversityCalculator."""

from __future__ import annotations

from eclair.consensus.agreement import AgreementCalculator
from eclair.consensus.diversity import DiversityCalculator
from eclair.consensus.models import ModelOutput
from eclair.consensus.voting import MajorityVoter


def test_diversity_identical_outputs() -> None:
    calc = DiversityCalculator()
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Exact same text"),
        ModelOutput(model="m2", provider="ollama", text="Exact same text"),
        ModelOutput(model="m3", provider="ollama", text="Exact same text"),
    ]
    voting = MajorityVoter().vote(outputs)
    agreement = AgreementCalculator().calculate(outputs, voting)
    div = calc.calculate(outputs, agreement, voting)

    assert div.diversity_score == 0.0
    assert div.unique_answer_count == 1
    assert div.mean_pairwise_distance == 0.0
    assert div.provider_diversity_count == 1


def test_diversity_diverging_outputs_multi_provider() -> None:
    calc = DiversityCalculator()
    outputs = [
        ModelOutput(model="llama3", provider="ollama", text="Option A completely different"),
        ModelOutput(model="gemini-flash", provider="gemini", text="Option B totally separate"),
        ModelOutput(model="mixtral", provider="groq", text="Option C entirely distinct"),
    ]
    voting = MajorityVoter().vote(outputs)
    agreement = AgreementCalculator().calculate(outputs, voting)
    div = calc.calculate(outputs, agreement, voting)

    assert div.diversity_score > 0.5
    assert div.unique_answer_count == 3
    assert div.provider_diversity_count == 3


def test_diversity_single_output() -> None:
    calc = DiversityCalculator()
    outputs = [
        ModelOutput(model="llama3", provider="ollama", text="Only one output"),
    ]
    div = calc.calculate(outputs)
    assert div.diversity_score == 0.0
    assert div.unique_answer_count == 1

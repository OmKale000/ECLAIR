"""Unit tests for M09 AgreementCalculator."""

from __future__ import annotations

from eclair.consensus.agreement import AgreementCalculator
from eclair.consensus.models import ModelOutput
from eclair.consensus.voting import MajorityVoter
from eclair.contracts.enums import ConsensusLevel


def test_agreement_similarity_exact_matches() -> None:
    calc = AgreementCalculator()
    sim = calc.compute_similarity("Exact match text", "Exact match text")
    assert sim == 1.0


def test_agreement_similarity_disjoint_texts() -> None:
    calc = AgreementCalculator()
    sim = calc.compute_similarity("alpha beta gamma", "one two three")
    assert sim == 0.0


def test_agreement_similarity_partial_overlap() -> None:
    calc = AgreementCalculator()
    sim = calc.compute_similarity("Refund within 30 days", "Refund granted in 30 days")
    assert 0.5 < sim < 1.0


def test_agreement_unanimous_models() -> None:
    calc = AgreementCalculator(full_consensus_threshold=0.85)
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Refunds are 30 days"),
        ModelOutput(model="m2", provider="gemini", text="Refunds are 30 days"),
        ModelOutput(model="m3", provider="groq", text="Refunds are 30 days"),
    ]
    voting = MajorityVoter().vote(outputs)
    res = calc.calculate(outputs, voting)

    assert res.agreement_score == 1.0
    assert res.consensus_level == ConsensusLevel.FULL
    assert res.unanimous is True
    assert res.mean_pairwise_similarity == 1.0
    assert len(res.pairwise_similarities) == 3


def test_agreement_partial_consensus_divergent_models() -> None:
    calc = AgreementCalculator(full_consensus_threshold=0.85)
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Refunds are allowed for 30 days."),
        ModelOutput(
            model="m2", provider="gemini", text="Refunds are never allowed under any circumstances."
        ),
        ModelOutput(model="m3", provider="groq", text="Warranty covers 5 years with no returns."),
    ]
    voting = MajorityVoter().vote(outputs)
    res = calc.calculate(outputs, voting)

    assert res.agreement_score < 0.60
    assert res.consensus_level == ConsensusLevel.PARTIAL
    assert res.unanimous is False


def test_agreement_single_model_output() -> None:
    calc = AgreementCalculator()
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Single model response"),
    ]
    res = calc.calculate(outputs)
    assert res.agreement_score == 1.0
    assert res.consensus_level == ConsensusLevel.FULL
    assert res.unanimous is True


def test_agreement_zero_outputs() -> None:
    calc = AgreementCalculator()
    res = calc.calculate([])
    assert res.agreement_score == 0.0
    assert res.consensus_level == ConsensusLevel.PARTIAL
    assert res.unanimous is False


def test_agreement_deterministic_output() -> None:
    calc = AgreementCalculator()
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Answer A"),
        ModelOutput(model="m2", provider="gemini", text="Answer A"),
        ModelOutput(model="m3", provider="groq", text="Answer B"),
    ]
    res1 = calc.calculate(outputs)
    res2 = calc.calculate(outputs)
    assert res1.agreement_score == res2.agreement_score
    assert res1.consensus_level == res2.consensus_level
    assert res1.mean_pairwise_similarity == res2.mean_pairwise_similarity

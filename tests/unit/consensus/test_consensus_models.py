"""Unit tests for M09 Consensus data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair.consensus.models import (
    AgreementResult,
    ConsensusResult,
    DiversityResult,
    ModelCallConfig,
    ModelOutput,
    VoteCluster,
    VotingResult,
)
from eclair.contracts.enums import ConsensusLevel


def test_model_call_config_defaults() -> None:
    config = ModelCallConfig()
    assert config.provider == "ollama"
    assert config.model is None
    assert config.temperature is None
    assert config.max_tokens is None
    assert config.json_mode is False


def test_model_call_config_custom() -> None:
    config = ModelCallConfig(
        provider="groq",
        model="llama3-70b-8192",
        temperature=0.5,
        max_tokens=256,
        json_mode=True,
    )
    assert config.provider == "groq"
    assert config.model == "llama3-70b-8192"
    assert config.temperature == 0.5
    assert config.max_tokens == 256
    assert config.json_mode is True


def test_model_call_config_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        ModelCallConfig.model_validate({"provider": "ollama", "extra_param": "forbidden"})


def test_model_output_creation() -> None:
    output = ModelOutput(
        model="llama3",
        provider="ollama",
        text="Refunds are available for 30 days.",
        success=True,
        latency_seconds=0.25,
    )
    assert output.model == "llama3"
    assert output.provider == "ollama"
    assert output.success is True
    assert output.error is None
    assert output.latency_seconds == 0.25


def test_model_output_failure() -> None:
    output = ModelOutput(
        model="gemini-1.5-flash",
        provider="gemini",
        text="",
        success=False,
        error="Network timeout connecting to provider",
    )
    assert output.success is False
    assert output.error == "Network timeout connecting to provider"


def test_vote_cluster() -> None:
    cluster = VoteCluster(
        representative_text="30-day refund window",
        vote_count=3,
        vote_share=0.75,
        model_names=["m1", "m2", "m3"],
    )
    assert cluster.vote_count == 3
    assert cluster.vote_share == 0.75
    assert len(cluster.model_names) == 3


def test_voting_result_properties() -> None:
    res = VotingResult(
        majority_answer="Yes, within 30 days.",
        winning_vote_count=2,
        total_votes=3,
        majority_ratio=2 / 3,
        has_majority=True,
        unanimous=False,
    )
    assert res.has_majority is True
    assert res.unanimous is False
    assert res.winning_vote_count == 2
    assert res.total_votes == 3


def test_agreement_result_range_validation() -> None:
    # Valid agreement score in [0.0, 1.0]
    res = AgreementResult(
        agreement_score=0.92,
        consensus_level=ConsensusLevel.FULL,
        mean_pairwise_similarity=0.92,
        unanimous=False,
    )
    assert res.agreement_score == 0.92
    assert res.consensus_level == ConsensusLevel.FULL

    with pytest.raises(ValidationError):
        AgreementResult(
            agreement_score=1.5,
            consensus_level=ConsensusLevel.FULL,
        )

    with pytest.raises(ValidationError):
        AgreementResult(
            agreement_score=-0.1,
            consensus_level=ConsensusLevel.PARTIAL,
        )


def test_diversity_result() -> None:
    div = DiversityResult(
        diversity_score=0.35,
        unique_answer_count=2,
        mean_pairwise_distance=0.4,
        provider_diversity_count=2,
    )
    assert div.diversity_score == 0.35
    assert div.unique_answer_count == 2
    assert div.provider_diversity_count == 2


def test_consensus_result_invariant() -> None:
    consensus = ConsensusResult(
        query="What is the refund window?",
        agreement_score=0.95,
        consensus_level=ConsensusLevel.FULL,
        majority_answer="30 days",
    )
    assert consensus.query == "What is the refund window?"
    assert consensus.agreement_score == 0.95
    assert consensus.consensus_level == ConsensusLevel.FULL
    # Model agreement is NEVER proof of truth (Spec sec.4.6)
    assert consensus.is_truth is False

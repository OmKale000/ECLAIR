"""Unit tests for M09 MajorityVoter."""

from __future__ import annotations

from eclair.consensus.models import ModelOutput
from eclair.consensus.voting import MajorityVoter


def test_voter_text_normalization() -> None:
    voter = MajorityVoter()
    assert voter.normalize_text("  Hello, World!  ") == "hello world"
    assert voter.normalize_text("Refund: 30 days.") == "refund 30 days"
    assert voter.normalize_text("") == ""


def test_voter_unanimous_votes() -> None:
    voter = MajorityVoter()
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Refunds are granted within 30 days."),
        ModelOutput(model="m2", provider="gemini", text="Refunds are granted within 30 days."),
        ModelOutput(model="m3", provider="groq", text="Refunds are granted within 30 days."),
    ]
    res = voter.vote(outputs)
    assert res.total_votes == 3
    assert res.winning_vote_count == 3
    assert res.majority_ratio == 1.0
    assert res.has_majority is True
    assert res.unanimous is True
    assert len(res.clusters) == 1
    assert res.majority_answer == "Refunds are granted within 30 days."


def test_voter_majority_with_clustering() -> None:
    voter = MajorityVoter(similarity_threshold=0.75)
    outputs = [
        ModelOutput(
            model="m1", provider="ollama", text="Refunds are available for 30 calendar days."
        ),
        ModelOutput(
            model="m2", provider="gemini", text="Refunds are available within 30 calendar days."
        ),
        ModelOutput(model="m3", provider="groq", text="No refunds are allowed after 100 days."),
    ]
    res = voter.vote(outputs)
    assert res.total_votes == 3
    assert res.winning_vote_count == 2
    assert res.has_majority is True
    assert res.unanimous is False
    assert len(res.clusters) == 2


def test_voter_tie_or_split_votes() -> None:
    voter = MajorityVoter()
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Option Alpha"),
        ModelOutput(model="m2", provider="gemini", text="Option Beta"),
        ModelOutput(model="m3", provider="groq", text="Option Gamma"),
    ]
    res = voter.vote(outputs)
    assert res.total_votes == 3
    assert res.winning_vote_count == 1
    assert res.majority_ratio == 1 / 3
    assert res.has_majority is False
    assert res.unanimous is False
    assert len(res.clusters) == 3


def test_voter_single_valid_vote() -> None:
    voter = MajorityVoter()
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="Only one answer available."),
    ]
    res = voter.vote(outputs)
    assert res.total_votes == 1
    assert res.winning_vote_count == 1
    assert res.majority_ratio == 1.0
    assert res.has_majority is True
    assert res.unanimous is True
    assert res.majority_answer == "Only one answer available."


def test_voter_no_valid_votes() -> None:
    voter = MajorityVoter()
    outputs = [
        ModelOutput(model="m1", provider="ollama", text="", success=False, error="Failed"),
        ModelOutput(model="m2", provider="gemini", text="   ", success=True),
    ]
    res = voter.vote(outputs)
    assert res.total_votes == 0
    assert res.majority_answer is None
    assert res.has_majority is False
    assert res.unanimous is False
    assert len(res.clusters) == 0


def test_voter_vote_strings_convenience() -> None:
    voter = MajorityVoter()
    res = voter.vote_strings(["answer A", "answer A", "answer B"])
    assert res.total_votes == 3
    assert res.winning_vote_count == 2
    assert res.has_majority is True
    assert res.majority_answer == "answer A"

"""Unit tests for M12 ResponseCritic."""

from __future__ import annotations

from eclair.contracts.claim import Claim
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult
from eclair.reflection.critic import ResponseCritic


def test_critic_identifies_contradicted_claims() -> None:
    critic = ResponseCritic()
    c1 = Claim(claim_id="c1", text="Refunds are never issued.")
    c2 = Claim(claim_id="c2", text="Items can be returned within 30 days.")

    v1 = VerificationResult(
        claim_id="c1",
        status=VerificationStatus.CONTRADICTED,
        evidence_ids=["e1"],
    )
    v2 = VerificationResult(
        claim_id="c2",
        status=VerificationStatus.SUPPORTED,
        evidence_ids=["e2"],
    )

    ev = [Evidence(evidence_id="e1", text="Full refunds are issued within 14 days.")]

    report = critic.critique(claims=[c1, c2], verifications=[v1, v2], evidence=ev)

    assert report.has_weak_claims is True
    assert report.weak_claim_count == 1
    assert len(report.items) == 1
    assert report.items[0].claim_id == "c1"
    assert report.items[0].verification_status == VerificationStatus.CONTRADICTED
    assert "contradicted" in report.items[0].issue.lower()


def test_critic_identifies_unknown_claims() -> None:
    critic = ResponseCritic()
    c1 = Claim(claim_id="c1", text="Shipping is free worldwide.")
    v1 = VerificationResult(
        claim_id="c1",
        status=VerificationStatus.UNKNOWN,
        evidence_ids=[],
    )

    report = critic.critique(claims=[c1], verifications=[v1])

    assert report.has_weak_claims is True
    assert report.weak_claim_count == 1
    assert report.items[0].claim_id == "c1"
    assert report.items[0].verification_status == VerificationStatus.UNKNOWN
    assert "lacks supporting evidence" in report.items[0].issue.lower()


def test_critic_handles_all_supported_claims() -> None:
    critic = ResponseCritic()
    c1 = Claim(claim_id="c1", text="Customer support is open 24/7.")
    v1 = VerificationResult(
        claim_id="c1",
        status=VerificationStatus.SUPPORTED,
        evidence_ids=["e1"],
    )

    report = critic.critique(claims=[c1], verifications=[v1])

    assert report.has_weak_claims is False
    assert report.weak_claim_count == 0
    assert len(report.items) == 0
    assert "all claims are supported" in report.summary.lower()


def test_critic_handles_unverified_claim_as_unknown() -> None:
    critic = ResponseCritic()
    c1 = Claim(claim_id="c1", text="Unverified statement.")

    # No verification provided for c1
    report = critic.critique(claims=[c1], verifications=[])

    assert report.has_weak_claims is True
    assert report.weak_claim_count == 1
    assert report.items[0].verification_status == VerificationStatus.UNKNOWN


def test_format_critique_for_prompt() -> None:
    critic = ResponseCritic()
    c1 = Claim(claim_id="c1", text="Wrong claim.")
    v1 = VerificationResult(
        claim_id="c1",
        status=VerificationStatus.CONTRADICTED,
        evidence_ids=["e1"],
    )
    ev = [Evidence(evidence_id="e1", text="Fact from policy.", source="refund_policy.md")]

    report = critic.critique(claims=[c1], verifications=[v1], evidence=ev)
    prompt_text = critic.format_critique_for_prompt(report, evidence=ev)

    assert "CRITIQUE OF CURRENT ANSWER:" in prompt_text
    assert "Wrong claim." in prompt_text
    assert "CONTRADICTED" in prompt_text
    assert "Fact from policy." in prompt_text
    assert "Source: refund_policy.md" in prompt_text

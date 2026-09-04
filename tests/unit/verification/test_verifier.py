"""Unit tests for M07 Claim Verification (ClaimVerifier and end-to-end M07 behavior)."""

from __future__ import annotations

import pytest

from eclair.contracts import Claim, Evidence, VerificationResult, VerificationStatus, Verifier
from eclair.exceptions import ContractValidationError
from eclair.verification import (
    ClaimVerifier,
    NLIEngine,
    NLILabel,
)


def test_claim_verifier_conforms_to_verifier_protocol() -> None:
    verifier = ClaimVerifier()
    assert isinstance(verifier, Verifier)


# --- Test 1: Supported claim ------------------------------------------------


def test_supported_claim_produces_supported_status() -> None:
    engine = NLIEngine(
        pipeline_fn=lambda p, h: {"entailment": 0.95, "contradiction": 0.02, "neutral": 0.03}
    )
    verifier = ClaimVerifier(nli_engine=engine)
    claim = Claim(text="The return window is 30 days.")
    evidence = [Evidence(text="Items may be returned within 30 calendar days of purchase.")]

    result = verifier.verify(claim, evidence)

    assert isinstance(result, VerificationResult)
    assert result.claim_id == claim.claim_id
    assert result.status is VerificationStatus.SUPPORTED
    assert evidence[0].evidence_id in result.evidence_ids


# --- Test 2: Contradicted claim ---------------------------------------------


def test_contradicted_claim_produces_contradicted_status() -> None:
    engine = NLIEngine(
        pipeline_fn=lambda p, h: {"entailment": 0.02, "contradiction": 0.92, "neutral": 0.06}
    )
    verifier = ClaimVerifier(nli_engine=engine)
    claim = Claim(text="Refunds are never granted.")
    evidence = [Evidence(text="All customers are entitled to a full refund within 14 days.")]

    result = verifier.verify(claim, evidence)

    assert result.claim_id == claim.claim_id
    assert result.status is VerificationStatus.CONTRADICTED
    assert evidence[0].evidence_id in result.evidence_ids


# --- Test 3: Neutral / Insufficient evidence --------------------------------


def test_neutral_evidence_produces_unknown_status() -> None:
    engine = NLIEngine(
        pipeline_fn=lambda p, h: {"entailment": 0.20, "contradiction": 0.15, "neutral": 0.65}
    )
    verifier = ClaimVerifier(nli_engine=engine)
    claim = Claim(text="The store accepts Bitcoin.")
    evidence = [Evidence(text="Our customer support team is available from 9 AM to 5 PM.")]

    result = verifier.verify(claim, evidence)

    assert result.status is VerificationStatus.UNKNOWN


# --- Test 4: No evidence (Mandatory Invariant) ------------------------------


def test_no_evidence_maps_to_unknown_with_empty_evidence_ids() -> None:
    verifier = ClaimVerifier()
    claim = Claim(text="The warranty covers accidental water damage.")

    result = verifier.verify(claim, [])

    assert result.claim_id == claim.claim_id
    assert result.status is VerificationStatus.UNKNOWN
    assert result.evidence_ids == []


# --- Test 5: Multiple evidence items aggregation ----------------------------


def test_multiple_evidence_items_aggregation() -> None:
    def fake_pipeline(p: str, h: str) -> dict[str, float]:
        if "30 days" in p:
            return {"entailment": 0.90, "contradiction": 0.05, "neutral": 0.05}
        return {"entailment": 0.10, "contradiction": 0.10, "neutral": 0.80}

    engine = NLIEngine(pipeline_fn=fake_pipeline)
    verifier = ClaimVerifier(nli_engine=engine)

    claim = Claim(text="Refunds are available for 30 days.")
    ev1 = Evidence(text="Unrelated company policy regarding parking.")
    ev2 = Evidence(text="Customers can request a refund within 30 days of receipt.")

    result, detail = verifier.verify_detailed(claim, [ev1, ev2])

    assert result.status is VerificationStatus.SUPPORTED
    assert ev2.evidence_id in result.evidence_ids
    assert ev2.evidence_id in detail.supporting_evidence_ids
    assert detail.support_score >= 0.80
    assert len(detail.evidence_verifications) == 2


# --- Test 6: Supporting evidence attachment ---------------------------------


def test_supporting_evidence_attached_to_result() -> None:
    engine = NLIEngine(
        pipeline_fn=lambda p, h: {"entailment": 0.90, "contradiction": 0.05, "neutral": 0.05}
    )
    verifier = ClaimVerifier(nli_engine=engine)

    claim = Claim(text="Shipping is free on orders over $50.")
    ev1 = Evidence(text="Free standard shipping applies to all orders exceeding $50.")

    result = verifier.verify(claim, [ev1])

    assert result.status is VerificationStatus.SUPPORTED
    assert result.evidence_ids == [ev1.evidence_id]


# --- Test 7: Contradicting evidence dominates -------------------------------


def test_contradicting_evidence_dominates_when_conflict_arises() -> None:
    def fake_pipeline(p: str, h: str) -> dict[str, float]:
        if "no refunds" in p.lower():
            return {"entailment": 0.01, "contradiction": 0.98, "neutral": 0.01}
        return {"entailment": 0.60, "contradiction": 0.20, "neutral": 0.20}

    engine = NLIEngine(pipeline_fn=fake_pipeline)
    verifier = ClaimVerifier(nli_engine=engine)

    claim = Claim(text="All digital products are eligible for refunds.")
    ev_weak_support = Evidence(text="Some products may qualify for returns.")
    ev_strong_contra = Evidence(text="Strictly NO REFUNDS are granted on digital products.")

    result, detail = verifier.verify_detailed(claim, [ev_weak_support, ev_strong_contra])

    assert result.status is VerificationStatus.CONTRADICTED
    assert ev_strong_contra.evidence_id in result.evidence_ids
    assert detail.contradiction_score > detail.support_score


# --- Test 8: Score bounds ---------------------------------------------------


def test_verification_scores_remain_bounded_in_zero_to_one() -> None:
    engine = NLIEngine()
    verifier = ClaimVerifier(nli_engine=engine)

    claim = Claim(text="Company founded in 2020.")
    evidence = [Evidence(text="Founded in 2020 by two engineers.")]

    _, detail = verifier.verify_detailed(claim, evidence)

    assert 0.0 <= detail.support_score <= 1.0
    assert 0.0 <= detail.contradiction_score <= 1.0
    for ev_eval in detail.evidence_verifications:
        assert 0.0 <= ev_eval.support_score <= 1.0
        assert 0.0 <= ev_eval.contradiction_score <= 1.0


# --- Test 9: Invalid input handling -----------------------------------------


def test_invalid_claim_input_raises_contract_validation_error() -> None:
    verifier = ClaimVerifier()
    with pytest.raises(ContractValidationError):
        verifier.verify("not a claim object", [])  # type: ignore[arg-type]


def test_invalid_evidence_input_raises_contract_validation_error() -> None:
    verifier = ClaimVerifier()
    claim = Claim(text="Valid claim.")
    with pytest.raises(ContractValidationError):
        verifier.verify(claim, "not a list")  # type: ignore[arg-type]

    with pytest.raises(ContractValidationError):
        verifier.verify(claim, ["not an evidence object"])  # type: ignore[list-item]


# --- Test 10: NLI output mapping --------------------------------------------


def test_nli_label_mapping_to_verification_status() -> None:
    assert NLILabel.ENTAILMENT.to_verification_status() is VerificationStatus.SUPPORTED
    assert NLILabel.CONTRADICTION.to_verification_status() is VerificationStatus.CONTRADICTED
    assert NLILabel.NEUTRAL.to_verification_status() is VerificationStatus.UNKNOWN

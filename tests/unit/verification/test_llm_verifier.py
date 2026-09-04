"""Unit tests for M07 LLMVerifier."""

from __future__ import annotations

import pytest

from eclair.contracts import Claim, Evidence, VerificationStatus
from eclair.exceptions import ContractValidationError, ModuleError
from eclair.llm.base import LLMRequest, LLMResponse
from eclair.verification import LLMVerificationResult, LLMVerifier


class DummyLLMProvider:
    """Mock LLMProvider implementing LLMProvider protocol."""

    def __init__(self, response_text: str, structured: dict[str, object] | None = None) -> None:
        self.response_text = response_text
        self.structured = structured
        self.last_request: LLMRequest | None = None

    def generate(self, request: object) -> LLMResponse:
        if isinstance(request, LLMRequest):
            self.last_request = request
        return LLMResponse(
            text=self.response_text,
            model="mock-llm",
            provider="mock-provider",
            structured=self.structured,
        )


def test_llm_verifier_supported_structured_response() -> None:
    provider = DummyLLMProvider(
        response_text='{"status": "SUPPORTED", "support_score": 0.95, "contradiction_score": 0.0, "reasoning": "Direct match."}',
        structured={
            "status": "SUPPORTED",
            "support_score": 0.95,
            "contradiction_score": 0.0,
            "reasoning": "Direct match.",
        },
    )
    verifier = LLMVerifier(provider=provider)
    claim = Claim(text="Return window is 30 days.")
    evidence = Evidence(text="Policy grants 30 days for returns.")

    res = verifier.verify_claim_evidence(claim, evidence)

    assert isinstance(res, LLMVerificationResult)
    assert res.status is VerificationStatus.SUPPORTED
    assert res.support_score == 0.95
    assert res.contradiction_score == 0.0
    assert res.reasoning == "Direct match."


def test_llm_verifier_contradicted_response() -> None:
    provider = DummyLLMProvider(
        response_text='{"status": "CONTRADICTED", "support_score": 0.0, "contradiction_score": 0.90, "reasoning": "Policy says no returns."}',
        structured={
            "status": "CONTRADICTED",
            "support_score": 0.0,
            "contradiction_score": 0.90,
            "reasoning": "Policy says no returns.",
        },
    )
    verifier = LLMVerifier(provider=provider)
    claim = Claim(text="Return window is 30 days.")
    evidence = Evidence(text="Policy states all sales are final.")

    res = verifier.verify_claim_evidence(claim, evidence)

    assert res.status is VerificationStatus.CONTRADICTED
    assert res.contradiction_score == 0.90


def test_llm_verifier_requires_configured_provider() -> None:
    verifier = LLMVerifier(provider=None)
    claim = Claim(text="Test claim")
    evidence = Evidence(text="Test evidence")

    with pytest.raises(ModuleError) as exc_info:
        verifier.verify_claim_evidence(claim, evidence)

    assert exc_info.value.code == "llm_verifier_unconfigured"


def test_llm_verifier_input_type_validation() -> None:
    provider = DummyLLMProvider(response_text="{}")
    verifier = LLMVerifier(provider=provider)

    with pytest.raises(ContractValidationError):
        verifier.verify_claim_evidence("not a claim", Evidence(text="ev"))  # type: ignore[arg-type]

    with pytest.raises(ContractValidationError):
        verifier.verify_claim_evidence(Claim(text="cl"), "not evidence")  # type: ignore[arg-type]

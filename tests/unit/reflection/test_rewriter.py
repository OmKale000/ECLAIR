"""Unit tests for M12 ResponseRewriter."""

from __future__ import annotations

import pytest

from eclair.contracts.enums import VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.exceptions import ModuleError
from eclair.llm.base import LLMRequest, LLMResponse
from eclair.reflection.models import CritiqueItem, CritiqueReport
from eclair.reflection.rewriter import ResponseRewriter


class DummyLLMProvider:
    """Mock LLM provider conforming to M01 LLMProvider protocol."""

    def __init__(self, response_text: str = "Corrected answer.") -> None:
        self.response_text = response_text
        self.last_request: LLMRequest | None = None
        self.should_fail: bool = False

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        if self.should_fail:
            raise RuntimeError("Underlying LLM service unavailable")
        return LLMResponse(
            text=self.response_text,
            model="test-model",
            provider="mock-llm",
        )


def test_rewriter_generates_correction() -> None:
    provider = DummyLLMProvider(response_text="The revised factual response.")
    rewriter = ResponseRewriter(provider)

    critique = CritiqueReport(
        has_weak_claims=True,
        weak_claim_count=1,
        items=[
            CritiqueItem(
                claim_id="c1",
                claim_text="Returns are impossible.",
                verification_status=VerificationStatus.CONTRADICTED,
                issue="Contradicted by policy",
                recommendation="State that returns are allowed in 14 days",
            )
        ],
        summary="One contradicted claim",
    )

    evidence = [Evidence(text="Customers can return items within 14 days.", source="policy.txt")]

    result = rewriter.rewrite(
        query="What is the refund policy?",
        current_answer="Returns are impossible.",
        critique=critique,
        evidence=evidence,
        model="custom-model",
        temperature=0.2,
    )

    assert result == "The revised factual response."
    assert provider.last_request is not None
    assert "What is the refund policy?" in provider.last_request.prompt
    assert "Returns are impossible." in provider.last_request.prompt
    assert "Customers can return items within 14 days." in provider.last_request.prompt
    assert provider.last_request.model == "custom-model"
    assert provider.last_request.temperature == 0.2


def test_rewriter_raises_on_empty_response() -> None:
    provider = DummyLLMProvider(response_text="")
    rewriter = ResponseRewriter(provider)

    critique = CritiqueReport(has_weak_claims=False, weak_claim_count=0, items=[])

    with pytest.raises(ModuleError, match="empty response|blank text"):
        rewriter.rewrite(
            query="Test query",
            current_answer="Test draft",
            critique=critique,
        )


def test_rewriter_raises_on_provider_exception() -> None:
    provider = DummyLLMProvider()
    provider.should_fail = True
    rewriter = ResponseRewriter(provider)

    critique = CritiqueReport(has_weak_claims=False, weak_claim_count=0, items=[])

    with pytest.raises(ModuleError, match="Reflection rewriter failed"):
        rewriter.rewrite(
            query="Test query",
            current_answer="Test draft",
            critique=critique,
        )

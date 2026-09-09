"""Unit tests for M12 ReflectionController (end-to-end reflection loop)."""

from __future__ import annotations

import pytest

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.query import Query
from eclair.contracts.verification import VerificationResult
from eclair.exceptions import ContractValidationError
from eclair.llm.base import LLMRequest, LLMResponse
from eclair.reflection.controller import ReflectionController
from eclair.reflection.models import ReflectionConfig, ReflectionResult


class MockLLMProvider:
    """Mock LLM provider for tests."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = list(responses) if responses else ["Default rewritten text."]
        self.call_count = 0

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        resp = self.responses.pop(0) if self.responses else "Fallback rewritten text."
        return LLMResponse(text=resp, model="mock-model", provider="mock")


class MockClaimExtractor:
    """Mock claim extractor conforming to M03 ClaimExtractor protocol."""

    def __init__(self, claims_by_text: dict[str, list[Claim]] | None = None) -> None:
        self.claims_by_text = claims_by_text or {}
        self.call_count = 0

    def extract(self, text: str) -> list[Claim]:
        self.call_count += 1
        if text in self.claims_by_text:
            return self.claims_by_text[text]
        return [Claim(text=text)]


class MockVerifier:
    """Mock verifier conforming to M07 Verifier protocol."""

    def __init__(self, status_map: dict[str, VerificationStatus] | None = None) -> None:
        self.status_map = status_map or {}
        self.call_count = 0
        self.fail_for_claim: str | None = None

    def verify(self, claim: Claim, evidence: list[Evidence]) -> VerificationResult:
        self.call_count += 1
        if self.fail_for_claim == claim.text:
            raise RuntimeError(f"Simulated verifier failure for {claim.text}")
        status = self.status_map.get(claim.text, VerificationStatus.SUPPORTED)
        ev_ids = [e.evidence_id for e in evidence]
        return VerificationResult(claim_id=claim.claim_id, status=status, evidence_ids=ev_ids)


class MockRetriever:
    """Mock retriever conforming to M05 Retriever protocol."""

    def __init__(self, evidence_to_return: list[Evidence] | None = None) -> None:
        self.evidence_to_return = evidence_to_return or []
        self.call_count = 0

    def search(self, query: str, top_k: int = 5) -> list[Evidence]:
        self.call_count += 1
        return self.evidence_to_return


class MockConfidenceEstimator:
    """Mock confidence estimator conforming to M10 protocol."""

    def __init__(self, return_scores: list[float] | None = None) -> None:
        self.scores = list(return_scores) if return_scores else [0.90]
        self.call_count = 0

    def calculate(self, signals: dict) -> ConfidenceResult:
        self.call_count += 1
        score = self.scores.pop(0) if self.scores else 0.90
        return ConfidenceResult(raw_confidence=score, calibrated_ecs=score)


# --- Tests -------------------------------------------------------------------


def test_reflection_does_not_trigger_when_confident_and_supported() -> None:
    llm = MockLLMProvider()
    extractor = MockClaimExtractor()
    verifier = MockVerifier()

    controller = ReflectionController(
        llm_provider=llm,
        claim_extractor=extractor,
        verifier=verifier,
        config=ReflectionConfig(low_confidence_threshold=0.60),
    )

    c1 = Claim(text="Company policy allows returns within 30 days.")
    v1 = VerificationResult(claim_id=c1.claim_id, status=VerificationStatus.SUPPORTED)
    conf = ConfidenceResult(raw_confidence=0.85, calibrated_ecs=0.82)

    res = controller.reflect(
        query=Query(question="What is the refund policy?"),
        answer="Company policy allows returns within 30 days.",
        claims=[c1],
        verifications=[v1],
        confidence=conf,
    )

    assert isinstance(res, ReflectionResult)
    assert res.triggered is False
    assert res.iterations_completed == 0
    assert res.improved_answer == "Company policy allows returns within 30 days."
    assert "not_triggered" in res.stop_reason
    assert llm.call_count == 0


def test_reflection_triggers_and_succeeds_in_single_iteration() -> None:
    # Original answer has a contradicted claim
    initial_answer = "Items can never be returned."
    c_bad = Claim(text="Items can never be returned.")
    v_bad = VerificationResult(claim_id=c_bad.claim_id, status=VerificationStatus.CONTRADICTED)

    # Rewritten answer
    revised_answer = "Items can be returned within 14 days with receipt."
    c_good = Claim(text="Items can be returned within 14 days with receipt.")

    llm = MockLLMProvider(responses=[revised_answer])
    extractor = MockClaimExtractor(claims_by_text={revised_answer: [c_good]})
    verifier = MockVerifier(status_map={c_good.text: VerificationStatus.SUPPORTED})

    evidence = [Evidence(text="Items may be returned within 14 days of purchase.")]

    controller = ReflectionController(
        llm_provider=llm,
        claim_extractor=extractor,
        verifier=verifier,
        config=ReflectionConfig(max_iterations=3),
    )

    res = controller.reflect(
        query="What is the return window?",
        answer=initial_answer,
        claims=[c_bad],
        verifications=[v_bad],
        evidence=evidence,
    )

    assert res.triggered is True
    assert res.improved is True
    assert res.iterations_completed == 1
    assert res.improved_answer == revised_answer
    assert len(res.final_claims) == 1
    assert res.final_claims[0].text == c_good.text
    assert res.final_verifications[0].status == VerificationStatus.SUPPORTED
    assert res.stop_reason == "all_claims_supported"
    assert len(res.history) == 1


def test_reflection_stops_at_hard_iteration_cap() -> None:
    # Model repeatedly generates answers with ungrounded claims
    c_bad = Claim(text="Perpetually ungrounded claim.")
    v_bad = VerificationResult(claim_id=c_bad.claim_id, status=VerificationStatus.UNKNOWN)

    llm = MockLLMProvider(
        responses=[
            "Attempt 1 with ungrounded claim.",
            "Attempt 2 with ungrounded claim.",
        ]
    )
    extractor = MockClaimExtractor(
        claims_by_text={
            "Attempt 1 with ungrounded claim.": [Claim(text="Attempt 1 claim")],
            "Attempt 2 with ungrounded claim.": [Claim(text="Attempt 2 claim")],
        }
    )
    # Verifier continuously returns UNKNOWN
    verifier = MockVerifier(
        status_map={
            "Attempt 1 claim": VerificationStatus.UNKNOWN,
            "Attempt 2 claim": VerificationStatus.UNKNOWN,
        }
    )

    controller = ReflectionController(
        llm_provider=llm,
        claim_extractor=extractor,
        verifier=verifier,
        config=ReflectionConfig(max_iterations=2),
    )

    res = controller.reflect(
        query="Test query",
        answer="Initial ungrounded answer.",
        claims=[c_bad],
        verifications=[v_bad],
    )

    assert res.triggered is True
    assert res.iterations_completed == 2
    assert res.stop_reason == "max_iterations_reached"
    assert len(res.history) == 2


def test_reflection_stops_on_identical_answer_to_prevent_loop() -> None:
    # Model generates identical answer to previous draft
    same_answer = "Same draft text."
    c1 = Claim(text="Same claim.")
    v1 = VerificationResult(claim_id=c1.claim_id, status=VerificationStatus.UNKNOWN)

    llm = MockLLMProvider(responses=[same_answer])
    extractor = MockClaimExtractor(claims_by_text={same_answer: [c1]})
    verifier = MockVerifier(status_map={c1.text: VerificationStatus.UNKNOWN})

    controller = ReflectionController(
        llm_provider=llm,
        claim_extractor=extractor,
        verifier=verifier,
        config=ReflectionConfig(max_iterations=5),
    )

    res = controller.reflect(
        query="Test query",
        answer=same_answer,
        claims=[c1],
        verifications=[v1],
    )

    # Stops on iteration 1 because answer didn't change
    assert res.triggered is True
    assert res.iterations_completed == 1
    assert res.stop_reason == "regeneration_unchanged"
    assert res.improved is False


def test_reflection_with_optional_retriever_and_confidence() -> None:
    c_bad = Claim(text="Unsupported detail.")
    v_bad = VerificationResult(claim_id=c_bad.claim_id, status=VerificationStatus.UNKNOWN)

    c_good = Claim(text="Evidence backed detail.")

    llm = MockLLMProvider(responses=["Evidence backed answer."])
    extractor = MockClaimExtractor(claims_by_text={"Evidence backed answer.": [c_good]})
    verifier = MockVerifier(status_map={c_good.text: VerificationStatus.SUPPORTED})

    new_ev = Evidence(text="Policy evidence text.", source="policy.txt")
    retriever = MockRetriever(evidence_to_return=[new_ev])
    conf_estimator = MockConfidenceEstimator(return_scores=[0.92])

    controller = ReflectionController(
        llm_provider=llm,
        claim_extractor=extractor,
        verifier=verifier,
        retriever=retriever,
        confidence_estimator=conf_estimator,
        config=ReflectionConfig(max_iterations=3),
    )

    res = controller.reflect(
        query="Query needing retrieval",
        answer="Initial weak answer.",
        claims=[c_bad],
        verifications=[v_bad],
    )

    assert res.triggered is True
    assert retriever.call_count >= 1
    assert conf_estimator.call_count == 1
    assert res.final_confidence is not None
    assert res.final_confidence.raw_confidence == 0.92
    assert res.stop_reason == "all_claims_supported"


def test_reflection_handles_verifier_error_gracefully() -> None:
    c_bad = Claim(text="Bad claim.")
    v_bad = VerificationResult(claim_id=c_bad.claim_id, status=VerificationStatus.CONTRADICTED)

    c_failing = Claim(text="Claim that triggers verifier error")

    llm = MockLLMProvider(responses=["Answer triggering error."])
    extractor = MockClaimExtractor(claims_by_text={"Answer triggering error.": [c_failing]})
    verifier = MockVerifier()
    verifier.fail_for_claim = c_failing.text

    controller = ReflectionController(
        llm_provider=llm,
        claim_extractor=extractor,
        verifier=verifier,
        config=ReflectionConfig(max_iterations=1),
    )

    res = controller.reflect(
        query="Test query",
        answer="Initial answer.",
        claims=[c_bad],
        verifications=[v_bad],
    )

    # Does not crash; records UNKNOWN verification for failing claim
    assert res.triggered is True
    assert len(res.final_verifications) == 1
    assert res.final_verifications[0].status == VerificationStatus.UNKNOWN


def test_reflection_input_validation() -> None:
    controller = ReflectionController(
        llm_provider=MockLLMProvider(),
        claim_extractor=MockClaimExtractor(),
        verifier=MockVerifier(),
    )

    # Empty query string
    with pytest.raises(ContractValidationError):
        controller.reflect(query="", answer="Answer", claims=[], verifications=[])

    # Empty answer
    with pytest.raises(ContractValidationError):
        controller.reflect(query="Query", answer="", claims=[], verifications=[])

    # Invalid query type
    with pytest.raises(ContractValidationError):
        controller.reflect(query=123, answer="Answer", claims=[], verifications=[])  # type: ignore[arg-type]

    # Invalid claims type
    with pytest.raises(ContractValidationError):
        controller.reflect(query="Query", answer="Answer", claims="not_a_list", verifications=[])  # type: ignore[arg-type]

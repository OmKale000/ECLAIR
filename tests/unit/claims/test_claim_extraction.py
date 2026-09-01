"""Unit tests for M03 Claim Extraction (offline; fakes only, no downloads/network).

Confirms the module contract:
* ``ClaimExtractor.extract(text) -> list[Claim]`` (M01 output contract).
* Multiple atomic claims with IDs and valid ``ClaimType`` from one answer.
* Equivalent phrasing is normalized and collapsed.
* Semantically similar claims are deduplicated (via a fake encoder).
* Empty/whitespace input returns ``[]``.
* Bad LLM structured output raises the shared ``ModuleError``.
"""

from __future__ import annotations

import pytest

from eclair.claims import (
    ClaimClassifier,
    ClaimDeduplicator,
    ClaimExtractor,
    ClaimNormalizer,
)
from eclair.contracts import Claim, ClaimType
from eclair.exceptions import ModuleError
from eclair.llm import LLMResponse


class FakeLLM:
    """Fake LLM Gateway returning a canned structured claim list."""

    def __init__(self, claims: list[str] | None, *, structured_override: object = ...) -> None:
        self._claims = claims
        self._structured_override = structured_override

    def generate(self, request: object) -> LLMResponse:  # noqa: ARG002 - request unused
        structured: object
        if self._structured_override is not ...:
            structured = self._structured_override
        else:
            structured = {"claims": list(self._claims or [])}
        return LLMResponse(
            text="",
            model="fake-model",
            provider="fake",
            structured=structured,
        )


class FakeEncoder:
    """Deterministic fake encoder.

    Maps each distinct comparison key (lowercased, punctuation-stripped) to a
    distinct one-hot vector, so only *identical* normalized keys are treated as
    semantically similar unless an explicit alias map says otherwise.
    """

    def __init__(self, alias: dict[str, str] | None = None) -> None:
        self._alias = alias or {}
        self._vocab: dict[str, int] = {}

    def _key(self, sentence: str) -> str:
        norm = sentence.lower().strip()
        return self._alias.get(norm, norm)

    def encode(self, sentences: list[str]) -> list[list[float]]:
        keys = [self._key(s) for s in sentences]
        for key in keys:
            if key not in self._vocab:
                self._vocab[key] = len(self._vocab)
        size = len(self._vocab)
        vectors: list[list[float]] = []
        for key in keys:
            vec = [0.0] * size
            vec[self._vocab[key]] = 1.0
            vectors.append(vec)
        return vectors


def _make_extractor(claims: list[str], *, alias: dict[str, str] | None = None) -> ClaimExtractor:
    normalizer = ClaimNormalizer()
    dedup = ClaimDeduplicator(encoder=FakeEncoder(alias=alias), normalizer=normalizer)
    return ClaimExtractor(
        FakeLLM(claims),
        normalizer=normalizer,
        deduplicator=dedup,
        classifier=ClaimClassifier(),
    )


def test_extract_yields_multiple_atomic_claims() -> None:
    extractor = _make_extractor(
        [
            "The Eiffel Tower is located in Paris.",
            "The tower was completed in 1889.",
            "It is 330 meters tall.",
        ]
    )
    claims = extractor.extract("some answer")

    assert isinstance(claims, list)
    assert len(claims) == 3
    for claim in claims:
        assert isinstance(claim, Claim)
        assert claim.claim_id  # non-empty id
        assert isinstance(claim.claim_type, ClaimType)


def test_output_is_list_of_claim() -> None:
    extractor = _make_extractor(["Water boils at 100 degrees."])
    claims = extractor.extract("answer")
    assert all(isinstance(c, Claim) for c in claims)


def test_claim_types_assigned() -> None:
    extractor = _make_extractor(
        [
            "The event happened in 1889.",  # TEMPORAL (year)
            "The bridge is 330 meters long.",  # NUMERIC
            "Barack Obama was president.",  # ENTITY (proper-noun phrase)
            "water is wet",  # FACTUAL
        ]
    )
    by_text = {c.text: c.claim_type for c in extractor.extract("answer")}

    assert by_text["The event happened in 1889"] == ClaimType.TEMPORAL
    assert by_text["The bridge is 330 meters long"] == ClaimType.NUMERIC
    assert by_text["Barack Obama was president"] == ClaimType.ENTITY
    assert by_text["water is wet"] == ClaimType.FACTUAL


def test_equivalent_phrasing_is_normalized_and_collapsed() -> None:
    # Same claim differing only by case/punctuation/whitespace -> one claim.
    extractor = _make_extractor(
        [
            "The sky is blue.",
            "the sky is blue",
            "THE  SKY   IS BLUE!!",
        ]
    )
    claims = extractor.extract("answer")
    assert len(claims) == 1
    assert claims[0].text == "The sky is blue"


def test_semantic_duplicates_removed() -> None:
    # Two different surface forms mapped to the same semantic key via alias.
    extractor = _make_extractor(
        [
            "A car is a vehicle.",
            "An automobile is a vehicle.",
        ],
        alias={"an automobile is a vehicle": "a car is a vehicle"},
    )
    claims = extractor.extract("answer")
    assert len(claims) == 1
    assert claims[0].text == "A car is a vehicle"


@pytest.mark.parametrize("bad", ["", "   ", "\n\t "])
def test_empty_input_returns_empty_list(bad: str) -> None:
    extractor = _make_extractor(["unused"])
    assert extractor.extract(bad) == []


def test_no_structured_output_raises_module_error() -> None:
    extractor = ClaimExtractor(FakeLLM(None, structured_override=None))
    with pytest.raises(ModuleError):
        extractor.extract("answer")


def test_bad_structured_shape_raises_module_error() -> None:
    extractor = ClaimExtractor(FakeLLM(None, structured_override={"wrong": 123}))
    with pytest.raises(ModuleError):
        extractor.extract("answer")


def test_blank_claims_are_dropped() -> None:
    extractor = _make_extractor(["Valid claim here.", "   ", "."])
    claims = extractor.extract("answer")
    assert len(claims) == 1
    assert claims[0].text == "Valid claim here"


def test_deduplicator_keeps_first_occurrence_order() -> None:
    dedup = ClaimDeduplicator(encoder=FakeEncoder())
    result = dedup.deduplicate(["alpha", "beta", "alpha", "gamma"])
    assert result == ["alpha", "beta", "gamma"]


def test_lowercase_may_modal_is_not_temporal() -> None:
    # "may" as a modal verb must not be misclassified as the month.
    classifier = ClaimClassifier()
    assert classifier.classify("You may return items within 30 days") == ClaimType.TEMPORAL
    # (contains "days" -> temporal). Without other temporal words it is not temporal:
    assert classifier.classify("Customers may request a refund") == ClaimType.FACTUAL


def test_capitalized_may_month_is_temporal() -> None:
    classifier = ClaimClassifier()
    assert classifier.classify("The sale starts in May") == ClaimType.TEMPORAL

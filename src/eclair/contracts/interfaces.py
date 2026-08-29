"""Stable module interfaces / Protocols (M01 Foundation, Spec sec.4.3).

These are the interface signatures the whole system builds against. Concrete
implementations live in their owning modules (M02, M03, M05, M07, M10, M13) and
MUST conform to these Protocols. M01 defines the shapes only and implements no
behaviour.

Notes on typing:
    * ``LLMRequest`` / ``LLMResponse`` are owned by M02 and are not yet defined
      as shared contracts. To avoid inventing another module's contracts here,
      the ``LLMProvider`` signature uses ``Any`` for those positions while
      preserving the frozen method name and arity (Spec sec.4.3). M02 will refine
      its own request/response types within its module boundary.
    * ``ConfidenceEstimator.calculate`` takes ``signals``; the Spec does not fix a
      shared contract for the fused signals, so it is typed ``Any`` here.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult

__all__ = [
    "LLMProvider",
    "ClaimExtractor",
    "Retriever",
    "Verifier",
    "ConfidenceEstimator",
    "DecisionEngine",
]


@runtime_checkable
class LLMProvider(Protocol):
    """Provider abstraction implemented by M02 (Ollama/Gemini/Groq/OpenRouter)."""

    def generate(self, request: Any) -> Any:
        """Generate a response for the given request (M02-owned request/response)."""
        ...


@runtime_checkable
class ClaimExtractor(Protocol):
    """Answer-to-claims extractor implemented by M03."""

    def extract(self, text: str) -> list[Claim]:
        """Extract atomic factual claims from answer text."""
        ...


@runtime_checkable
class Retriever(Protocol):
    """Evidence retriever implemented by M05."""

    def search(self, query: str, top_k: int = 5) -> list[Evidence]:
        """Retrieve up to ``top_k`` evidence items for the query."""
        ...


@runtime_checkable
class Verifier(Protocol):
    """Claim verifier implemented by M07."""

    def verify(self, claim: Claim, evidence: list[Evidence]) -> VerificationResult:
        """Verify a claim against evidence (no evidence -> UNKNOWN)."""
        ...


@runtime_checkable
class ConfidenceEstimator(Protocol):
    """Raw confidence estimator implemented by M10."""

    def calculate(self, signals: Any) -> ConfidenceResult:
        """Fuse reliability signals into a raw ConfidenceResult."""
        ...


@runtime_checkable
class DecisionEngine(Protocol):
    """Risk/decision engine implemented by M13."""

    def decide(self, signals: Any) -> DecisionResult:
        """Select a decision action from reliability signals."""
        ...

"""ECLAIR Claim Verification (M07).

Determines whether evidence actually supports a given claim using Natural
Language Inference (NLI) and optional secondary LLM verification.

Conforms to the frozen M01 ``Verifier`` Protocol:
    ``Verifier.verify(claim: Claim, evidence: list[Evidence]) -> VerificationResult``

Reliability Invariants (Spec sec.M07, sec.4.5, sec.4.9):
    * Explicit verification: RAG retrieval alone is not verification.
    * Absence of evidence (evidence = []) MUST return ``VerificationStatus.UNKNOWN``
      with ``evidence_ids=[]``, never ``SUPPORTED``.
    * NLI mapping: ENTAILMENT -> SUPPORTED, CONTRADICTION -> CONTRADICTED,
      NEUTRAL -> UNKNOWN.
"""

from __future__ import annotations

from eclair.verification.aggregator import EvidenceAggregator
from eclair.verification.llm_verifier import LLMVerifier
from eclair.verification.models import (
    EvidenceVerification,
    LLMVerificationResult,
    NLILabel,
    NLIPrediction,
    VerificationDetail,
)
from eclair.verification.nli import DEFAULT_NLI_MODEL, NLIEngine
from eclair.verification.verifier import ClaimVerifier

__all__ = [
    "ClaimVerifier",
    "NLIEngine",
    "DEFAULT_NLI_MODEL",
    "LLMVerifier",
    "EvidenceAggregator",
    "NLILabel",
    "NLIPrediction",
    "EvidenceVerification",
    "VerificationDetail",
    "LLMVerificationResult",
]

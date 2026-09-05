"""ECLAIR Multi-Agent / Multi-Model Consensus Module (M09).

Measures agreement across independent model outputs. Provides majority voting,
pairwise similarity agreement scoring, output and provider diversity analysis,
and concurrent multi-model orchestration via the M02 LLM Gateway.

Reliability Semantics (Spec sec.4.6):
    Model agreement is NOT proof of truth. Consensus provides one reliability
    signal that downstream modules combine with evidence quality (M06),
    claim verification (M07), confidence estimation (M10), and calibration (M11).
"""

from __future__ import annotations

from eclair.consensus.agreement import AgreementCalculator
from eclair.consensus.diversity import DiversityCalculator
from eclair.consensus.models import (
    AgreementResult,
    ConsensusResult,
    DiversityResult,
    ModelCallConfig,
    ModelOutput,
    VoteCluster,
    VotingResult,
)
from eclair.consensus.runner import ConsensusRunner, LLMClient
from eclair.consensus.voting import MajorityVoter

__all__ = [
    "ConsensusRunner",
    "LLMClient",
    "MajorityVoter",
    "AgreementCalculator",
    "DiversityCalculator",
    "ModelCallConfig",
    "ModelOutput",
    "VoteCluster",
    "VotingResult",
    "AgreementResult",
    "DiversityResult",
    "ConsensusResult",
]

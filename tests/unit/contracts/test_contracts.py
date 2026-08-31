"""Unit tests for M01 Foundation shared contracts, enums, interfaces, config."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eclair import (
    ConfigurationError,
    ContractValidationError,
    EclairConfig,
    EclairError,
    ModuleError,
    load_config,
)
from eclair.config import LLMProviderConfig
from eclair import __version__ as pkg_version
from eclair.contracts import (
    Claim,
    ClaimExtractor,
    ConfidenceEstimator,
    ConfidenceResult,
    ConsensusLevel,
    DecisionAction,
    DecisionEngine,
    DecisionResult,
    EclairResult,
    Evidence,
    LLMProvider,
    Query,
    Retriever,
    RiskResult,
    Verifier,
    VerificationResult,
    VerificationStatus,
)
from eclair.version import VERSION


# --- Version ---------------------------------------------------------------


def test_version_constants_match() -> None:
    assert VERSION == pkg_version == "0.1.0"


# --- Frozen enums ----------------------------------------------------------


def test_verification_status_members_frozen() -> None:
    assert {s.value for s in VerificationStatus} == {
        "SUPPORTED",
        "CONTRADICTED",
        "UNKNOWN",
    }


def test_decision_action_members_frozen() -> None:
    assert {a.value for a in DecisionAction} == {
        "RETURN",
        "VERIFY_MORE",
        "REGENERATE",
        "ABSTAIN",
        "HUMAN_REVIEW",
        "BLOCK_ACTION",
    }


def test_consensus_level_members_frozen() -> None:
    assert {c.value for c in ConsensusLevel} == {"FULL", "PARTIAL"}


# --- Query -----------------------------------------------------------------


def test_query_valid_and_autogenerates_id() -> None:
    q = Query(question="What is the refund window?")
    assert q.question == "What is the refund window?"
    assert q.query_id


def test_query_rejects_empty_question() -> None:
    with pytest.raises(ValidationError):
        Query(question="")


def test_query_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Query(question="x", unexpected="y")


# --- Claim / Evidence ------------------------------------------------------


def test_claim_valid() -> None:
    c = Claim(text="Refunds are issued within 30 days.")
    assert c.text
    assert c.claim_id


def test_evidence_optional_annotations() -> None:
    e = Evidence(text="Our policy allows refunds within 30 days.")
    assert e.source is None
    assert e.relevance_score is None


def test_evidence_relevance_score_bounds() -> None:
    with pytest.raises(ValidationError):
        Evidence(text="x", relevance_score=1.5)


# --- VerificationResult (no-evidence -> UNKNOWN semantic) ------------------


def test_verification_no_evidence_maps_to_unknown() -> None:
    vr = VerificationResult(
        claim_id="c1",
        status=VerificationStatus.UNKNOWN,
        evidence_ids=[],
    )
    assert vr.status is VerificationStatus.UNKNOWN
    assert vr.evidence_ids == []


def test_verification_supported_requires_valid_enum() -> None:
    vr = VerificationResult(claim_id="c1", status=VerificationStatus.SUPPORTED)
    assert vr.status is VerificationStatus.SUPPORTED


# --- ConfidenceResult (raw vs calibrated ECS separation) -------------------


def test_confidence_raw_only_by_default() -> None:
    cr = ConfidenceResult(raw_confidence=0.42)
    assert cr.raw_confidence == 0.42
    assert cr.calibrated_ecs is None


def test_confidence_calibrated_ecs_separate_field() -> None:
    cr = ConfidenceResult(raw_confidence=0.42, calibrated_ecs=0.51)
    assert cr.raw_confidence != cr.calibrated_ecs


def test_confidence_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        ConfidenceResult(raw_confidence=1.2)


# --- Risk / Decision -------------------------------------------------------


def test_risk_result_valid() -> None:
    r = RiskResult(risk_level="low", risk_score=0.1)
    assert r.risk_level == "low"


def test_decision_result_uses_enum() -> None:
    d = DecisionResult(action=DecisionAction.RETURN, reason="high ECS")
    assert d.action is DecisionAction.RETURN


# --- EclairResult aggregate ------------------------------------------------


def test_eclair_result_minimal_and_serializes() -> None:
    result = EclairResult(query_id="q1")
    dumped = result.model_dump()
    assert dumped["query_id"] == "q1"
    assert dumped["claims"] == []
    assert dumped["confidence"] is None


def test_eclair_result_aggregates_stage_outputs() -> None:
    result = EclairResult(
        query_id="q1",
        answer="Refunds within 30 days.",
        claims=[Claim(claim_id="c1", text="Refunds within 30 days.")],
        evidence=[Evidence(evidence_id="e1", text="Policy: 30 day refunds.")],
        verifications=[
            VerificationResult(
                claim_id="c1",
                status=VerificationStatus.SUPPORTED,
                evidence_ids=["e1"],
            )
        ],
        confidence=ConfidenceResult(raw_confidence=0.8, calibrated_ecs=0.75),
        risk=RiskResult(risk_level="low"),
        decision=DecisionResult(action=DecisionAction.RETURN),
    )
    assert result.decision is not None
    assert result.decision.action is DecisionAction.RETURN
    assert result.verifications[0].status is VerificationStatus.SUPPORTED
    # round-trip
    reloaded = EclairResult.model_validate(result.model_dump())
    assert reloaded == result


# --- Config ----------------------------------------------------------------


def test_load_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ECLAIR_ENVIRONMENT", raising=False)
    monkeypatch.delenv("ECLAIR_DEBUG", raising=False)
    cfg = load_config()
    assert cfg.environment == "development"
    assert cfg.debug is False


def test_load_config_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ECLAIR_ENVIRONMENT", "production")
    monkeypatch.setenv("ECLAIR_DEBUG", "true")
    cfg = load_config()
    assert cfg.environment == "production"
    assert cfg.debug is True


def test_config_is_frozen_and_forbids_extra() -> None:
    cfg = EclairConfig()
    with pytest.raises(ValidationError):
        cfg.environment = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        EclairConfig(unexpected="x")


# --- LLM provider config (generic sub-model) -------------------------------


def test_default_config_exposes_llm_submodel_with_safe_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for var in (
        "ECLAIR_LLM_ACTIVE_PROVIDER",
        "ECLAIR_LLM_TIMEOUT_SECONDS",
        "ECLAIR_LLM_RETRIES",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = load_config()
    assert isinstance(cfg.llm, LLMProviderConfig)
    # Zero-config EclairConfig() also carries the default sub-model.
    assert isinstance(EclairConfig().llm, LLMProviderConfig)
    assert cfg.llm.active_provider == "ollama"
    assert cfg.llm.ollama_base_url == "http://localhost:11434"
    assert cfg.llm.ollama_model == "llama3"
    assert cfg.llm.timeout_seconds == 30.0
    assert cfg.llm.retries == 2
    # Optional providers unconfigured by default.
    assert cfg.llm.gemini_api_key is None
    assert cfg.llm.groq_api_key is None
    assert cfg.llm.openrouter_api_key is None


def test_load_config_reads_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ECLAIR_LLM_ACTIVE_PROVIDER", "gemini")
    monkeypatch.setenv("ECLAIR_LLM_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("ECLAIR_LLM_RETRIES", "5")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.local:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    monkeypatch.setenv("GEMINI_API_KEY", "placeholder-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    cfg = load_config()
    assert cfg.llm.active_provider == "gemini"
    assert cfg.llm.timeout_seconds == 12.5
    assert cfg.llm.retries == 5
    assert cfg.llm.ollama_base_url == "http://ollama.local:11434"
    assert cfg.llm.ollama_model == "mistral"
    assert cfg.llm.gemini_api_key == "placeholder-key"
    assert cfg.llm.gemini_model == "gemini-1.5-flash"


def test_load_config_invalid_timeout_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ECLAIR_LLM_TIMEOUT_SECONDS", "not-a-number")
    with pytest.raises(ConfigurationError):
        load_config()


def test_load_config_nonpositive_timeout_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ECLAIR_LLM_TIMEOUT_SECONDS", "0")
    with pytest.raises(ConfigurationError):
        load_config()


def test_load_config_invalid_retries_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ECLAIR_LLM_RETRIES", "-1")
    with pytest.raises(ConfigurationError):
        load_config()


def test_llm_config_is_frozen_and_forbids_extra() -> None:
    llm = LLMProviderConfig()
    with pytest.raises(ValidationError):
        llm.active_provider = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        LLMProviderConfig(unexpected="x")


# --- Exceptions ------------------------------------------------------------


def test_exception_hierarchy() -> None:
    assert issubclass(ConfigurationError, EclairError)
    assert issubclass(ContractValidationError, EclairError)
    assert issubclass(ModuleError, EclairError)


def test_exception_code_formatting() -> None:
    err = EclairError("bad", code="x1")
    assert str(err) == "[x1] bad"
    assert str(EclairError("bad")) == "bad"


# --- Interfaces (Protocol conformance via duck typing) ---------------------


def test_protocols_are_runtime_checkable() -> None:
    class _Extractor:
        def extract(self, text: str) -> list[Claim]:
            return [Claim(text=text)]

    class _Retriever:
        def search(self, query: str, top_k: int = 5) -> list[Evidence]:
            return [Evidence(text=query)]

    class _Verifier:
        def verify(self, claim: Claim, evidence: list[Evidence]) -> VerificationResult:
            return VerificationResult(claim_id=claim.claim_id, status=VerificationStatus.UNKNOWN)

    class _Provider:
        def generate(self, request: object) -> object:
            return request

    class _Confidence:
        def calculate(self, signals: object) -> ConfidenceResult:
            return ConfidenceResult(raw_confidence=0.5)

    class _Decision:
        def decide(self, signals: object) -> DecisionResult:
            return DecisionResult(action=DecisionAction.ABSTAIN)

    assert isinstance(_Extractor(), ClaimExtractor)
    assert isinstance(_Retriever(), Retriever)
    assert isinstance(_Verifier(), Verifier)
    assert isinstance(_Provider(), LLMProvider)
    assert isinstance(_Confidence(), ConfidenceEstimator)
    assert isinstance(_Decision(), DecisionEngine)

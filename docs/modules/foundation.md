# M01 — Foundation & Shared Contracts

> Module documentation (Spec §4.8 deliverable). Derived only from the Spec (§M01, §4.1–§4.3) and the
> repository. Authoritative rules: `rules/M01_foundation.md`, `rules/COMMON_RULES.md`,
> `rules/SHARED_CONTRACTS_REFERENCE.md`. Do not invent contracts, fields, or behavior.

## Identity
- **ID:** M01
- **Name:** Foundation & Shared Contracts
- **Folder:** `src/eclair/` (+ `contracts/`, `engine/`, `config.py`, `exceptions.py`, `version.py`)
- **Tests:** `tests/unit/contracts/`

## Purpose (Spec §M01)
Provide the common foundation that every other module depends on.

## Responsibility
- Define typed, validated shared data contracts used across all modules.
- Provide shared application configuration (`config.py`) and shared exception types (`exceptions.py`).
- Provide project version metadata (`version.py`).
- Provide the engine scaffolding that owns the integrated pipeline flow (Spec §4.2):
  `engine/eclair_engine.py`, `engine/pipeline.py`, `engine/orchestrator.py`.

## Non-responsibility
- Does NOT implement any reliability logic (LLM calls, extraction, retrieval, verification,
  confidence, calibration, risk, provenance, API, SDK, dashboard).
- Does NOT contain provider-specific or model-specific code.

## Files (Spec §M01)
```
src/eclair/config.py
src/eclair/exceptions.py
src/eclair/version.py
src/eclair/contracts/  query.py claim.py evidence.py verification.py
                       confidence.py risk.py decision.py result.py
src/eclair/engine/     eclair_engine.py pipeline.py orchestrator.py
tests/unit/contracts/
```

## Required functionality (Spec §M01)
- Every major module has a stable input/output contract.
- Shared structures include at minimum: `Claim`, `Evidence`, `VerificationResult`,
  `ConfidenceResult`, `DecisionResult`, `EclairResult` (plus `Query`, `RiskResult`).

## Shared contracts owned here (Spec §4.1, SHARED_CONTRACTS_REFERENCE §1)
| Contract | File | Produced by |
|----------|------|-------------|
| `Query` | `contracts/query.py` | API / engine entry |
| `Claim` | `contracts/claim.py` | M03 |
| `Evidence` | `contracts/evidence.py` | M05 (annotated by M06) |
| `VerificationResult` | `contracts/verification.py` | M07 |
| `ConfidenceResult` | `contracts/confidence.py` | M10 (raw) / M11 (calibrated ECS) |
| `RiskResult` | `contracts/risk.py` | M13 |
| `DecisionResult` | `contracts/decision.py` | M13 |
| `EclairResult` | `contracts/result.py` | engine |

## Frozen enums defined here (SHARED_CONTRACTS_REFERENCE §2)
- Verification status: `SUPPORTED`, `CONTRADICTED`, `UNKNOWN`.
- Decision actions: `RETURN`, `VERIFY_MORE`, `REGENERATE`, `ABSTAIN`, `HUMAN_REVIEW`, `BLOCK_ACTION`.
- Consensus level: full or partial consensus + numeric agreement score.

## Interfaces (Spec §4.3)
Define the stable Protocols the whole system builds against:
```
LLMProvider.generate(request) -> LLMResponse
ClaimExtractor.extract(text) -> list[Claim]
Retriever.search(query, top_k=5) -> list[Evidence]
Verifier.verify(claim, evidence) -> VerificationResult
ConfidenceEstimator.calculate(signals) -> ConfidenceResult
DecisionEngine -> DecisionResult
```

## Technology (Spec §M01)
Python 3.12, Pydantic v2, uv, pytest, Ruff.

## Configuration surface (`config.py`)
The single shared configuration mechanism (COMMON_RULES §10). `load_config()` builds a validated,
frozen `EclairConfig` from environment variables using the standard library `os.getenv` only — no
extra configuration library. `EclairConfig()` and `load_config()` work with zero env vars set;
missing variables fall back to safe defaults.

`EclairConfig` fields:
- `environment: str` — deployment environment name (default `development`).
- `debug: bool` — debug flag (default `False`).
- `llm: LLMProviderConfig` — generic LLM-provider configuration (default sub-model).

`LLMProviderConfig` is a nested, validated, frozen (`extra="forbid"`) sub-model carrying only the
**generic** values needed to *construct* a provider. It contains **no** routing/fallback/HTTP or
reliability logic (that is M02) and **no** provider-specific behaviour. `active_provider` is a
free-form string, not an enum, so M02 may recognise additional providers without changing M01. The
Ollama defaults reflect the permanent zero-cost local fallback (Spec §4.11) as default *values*.

`LLMProviderConfig` fields:
- `active_provider: str` — provider to build by default (default `ollama`).
- `timeout_seconds: float` — generic request timeout, must be `> 0` (default `30.0`).
- `retries: int` — generic retry count, must be `>= 0` (default `2`).
- `ollama_base_url: str` (default `http://localhost:11434`), `ollama_model: str` (default `llama3`).
- `gemini_api_key / gemini_base_url / gemini_model` — optional (`None` when unconfigured).
- `groq_api_key / groq_base_url / groq_model` — optional (`None` when unconfigured).
- `openrouter_api_key / openrouter_base_url / openrouter_model` — optional (`None` when unconfigured).

Invalid values (non-numeric or out-of-bounds timeout/retries) raise the shared `ConfigurationError`.

Recognised environment variables (see `.env.example`; names match `load_config()` exactly):
```
ECLAIR_ENVIRONMENT          -> environment
ECLAIR_DEBUG                -> debug (truthy: 1, true, yes)
ECLAIR_LLM_ACTIVE_PROVIDER  -> llm.active_provider
ECLAIR_LLM_TIMEOUT_SECONDS  -> llm.timeout_seconds (float > 0)
ECLAIR_LLM_RETRIES          -> llm.retries (int >= 0)
OLLAMA_BASE_URL             -> llm.ollama_base_url
OLLAMA_MODEL                -> llm.ollama_model
GEMINI_API_KEY              -> llm.gemini_api_key
GEMINI_BASE_URL             -> llm.gemini_base_url
GEMINI_MODEL                -> llm.gemini_model
GROQ_API_KEY                -> llm.groq_api_key
GROQ_BASE_URL               -> llm.groq_base_url
GROQ_MODEL                  -> llm.groq_model
OPENROUTER_API_KEY          -> llm.openrouter_api_key
OPENROUTER_BASE_URL         -> llm.openrouter_base_url
OPENROUTER_MODEL            -> llm.openrouter_model
```

This config is consumed by M02 (LLM Gateway): `load_config() -> EclairConfig.llm -> M02 factory ->
providers`. M02 must not read env vars directly or invent its own config mechanism (COMMON_RULES §10).

## Inputs / Outputs
- **Inputs:** N/A — foundation module, consumed by all others.
- **Outputs:** importable Pydantic contract classes, config object, exception types, version
  constant, engine scaffolding. Consumed by **all** modules M02–M18.

## Error handling
M01 DEFINES the shared exception types in `src/eclair/exceptions.py`. All later modules must reuse
these; no module may introduce a new error format.

## Do not change
Once defined, contract names, fields, and enum values are frozen for every other module. Only M01 may
edit `contracts/`, `config.py`, `exceptions.py`, `version.py`.

## Expected outcome (Spec §M01)
All team members build against the same structures, and module integration does not require ad-hoc
data conversions.

## Verification before complete (Spec §4.8)
- Contracts import cleanly and validate sample data.
- Enum values for verification/risk/decision match the Spec semantics.
- `tests/unit/contracts/` pass; config and exceptions are importable; no invented behavior.

## Sample input / output

Constructing and serializing the aggregate contract (illustrates the frozen shapes):

```python
from eclair.contracts import (
    Claim, ConfidenceResult, DecisionAction, DecisionResult,
    EclairResult, Evidence, RiskResult, VerificationResult, VerificationStatus,
)

# Sample input: pipeline stage outputs assembled by the engine.
result = EclairResult(
    query_id="q1",
    answer="Refunds are issued within 30 days.",
    claims=[Claim(claim_id="c1", text="Refunds are issued within 30 days.")],
    evidence=[Evidence(evidence_id="e1", text="Policy: refunds within 30 days.")],
    verifications=[
        VerificationResult(
            claim_id="c1", status=VerificationStatus.SUPPORTED, evidence_ids=["e1"]
        )
    ],
    confidence=ConfidenceResult(raw_confidence=0.80, calibrated_ecs=0.75),
    risk=RiskResult(risk_level="low"),
    decision=DecisionResult(action=DecisionAction.RETURN),
)

# Sample output: validated, serializable dict keyed by query_id.
print(result.model_dump())
```

```python
{
    "query_id": "q1",
    "answer": "Refunds are issued within 30 days.",
    "claims": [{"claim_id": "c1", "text": "Refunds are issued within 30 days."}],
    "evidence": [{"evidence_id": "e1", "text": "Policy: refunds within 30 days.",
                  "source": None, "relevance_score": None}],
    "verifications": [{"claim_id": "c1", "status": "SUPPORTED", "evidence_ids": ["e1"]}],
    "confidence": {"raw_confidence": 0.8, "calibrated_ecs": 0.75},
    "risk": {"risk_level": "low", "risk_score": None},
    "decision": {"action": "RETURN", "reason": None},
}
```

## Implementation status
Implemented on branch `M01-Foundation`. Contracts, enums, interfaces, `config.py`,
`exceptions.py`, `version.py`, and engine scaffolding shells are in place. The engine
scaffolding (`Orchestrator`, `Pipeline`, `EclairEngine`) intentionally raises
`NotImplementedError` — pipeline wiring is owned by the integration phase (Spec §4.2), not M01.
Unit tests in `tests/unit/contracts/` pass (28 tests) and Ruff lint is clean.

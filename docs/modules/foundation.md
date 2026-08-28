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

# M01 — Foundation & Shared Contracts — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply. This file adds the
> module-specific contract. Values are taken only from the repository and the authoritative Spec.

```text
MODULE: M01 — Foundation & Shared Contracts
IDENTIFIER: M01

PURPOSE:
  Provide the common foundation that every other module depends on.

RESPONSIBILITY:
  - Define typed, validated shared data contracts used across all modules.
  - Provide shared application configuration and shared exception types.
  - Provide project version metadata.
  - Provide the engine scaffolding that owns the integrated pipeline flow
    (engine/orchestrator ownership per Spec §4.2).

NON-RESPONSIBILITY:
  - Does NOT implement any reliability logic (LLM calls, extraction, retrieval,
    verification, confidence, calibration, risk, provenance, API, SDK, dashboard).
  - Does NOT contain provider-specific or model-specific code.

LOCATION:
  src/eclair/
EXISTING FOLDERS USED:
  src/eclair/                (config.py, exceptions.py, version.py, __init__.py)
  src/eclair/contracts/      (query, claim, evidence, verification, confidence, risk, decision, result)
  src/eclair/engine/         (eclair_engine.py, pipeline.py, orchestrator.py)
  tests/unit/contracts/
NEW FILES REQUIRED:
  None beyond the placeholders already present in the folders above.

DEPENDENCIES:
  Internal: none (M01 is the base; nothing upstream).
  External: Python 3.12, Pydantic v2, uv, pytest, Ruff.
  Configuration: owns src/eclair/config.py (the shared config mechanism).

INPUTS:
  Source: N/A (foundation module; consumed by all others).
  Format: N/A.
  Validation: define validation rules inside the Pydantic contracts.

PROCESSING:
  Existing logic reused: none.
  New logic required: typed contracts, validation, enums, immutable/validated models where
    appropriate. Shared structures MUST include at least:
    Claim, Evidence, VerificationResult, ConfidenceResult, DecisionResult, EclairResult.

OUTPUTS:
  Format: importable Pydantic contract classes, config object, exception types, version constant.
  Destination: imported by every other module.

CONSUMERS:
  Module/service: ALL modules M02–M18.
  Expected contract: stable class names, fields, and enum values that downstream modules import.

INTEGRATION POINTS:
  APIs used: none.
  APIs exposed: none (library-level contracts only).
  Database: none (DB models are M14; contracts here are transport/domain models).
  Events/Queues: none.
  Configuration: defines it.

ERROR HANDLING:
  Existing pattern: none yet — M01 DEFINES the shared exception types in src/eclair/exceptions.py.
  All later modules must reuse these.

VALIDATION RULES:
  Contracts must validate their own fields (Pydantic v2). Enum values used across modules
  (e.g. verification states SUPPORTED / CONTRADICTED / UNKNOWN) must be defined here once.

INTEGRATION REQUIREMENTS:
  Contract names and fields must remain stable; downstream modules depend on them.

DO NOT CHANGE:
  Existing APIs: n/a.
  Existing models: n/a (this module creates them; once created they are frozen for others).
  Existing modules: do not touch any other module folder.
  Existing architecture: follow the Spec folder layout exactly.

REUSE RULES:
  Reuse Pydantic v2 primitives; do not add new validation libraries.

NO UNREQUESTED FUNCTIONALITY:
  Only the contracts, config, exceptions, version, and engine scaffolding listed above.

NO NEW DEPENDENCIES:
  Do not add libraries beyond the approved stack (COMMON_RULES §9).

NO UNRELATED REFACTORING:
  None.

MODULE BOUNDARY:
  This module handles: shared contracts, config, exceptions, version, engine scaffolding.
  This module does NOT handle: any concrete reliability step or product interface.

VERIFICATION BEFORE COMPLETE:
  - Contracts import cleanly and validate sample data.
  - Enum values for verification/risk/decision match the semantics in the Spec.
  - Unit tests in tests/unit/contracts/ pass.
  - Config and exceptions are importable and used by no invented behavior.
```

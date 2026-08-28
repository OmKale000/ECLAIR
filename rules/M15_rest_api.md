# M15 — ECLAIR REST API — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M15 — ECLAIR REST API
IDENTIFIER: M15

PURPOSE:
  Expose the integrated ECLAIR engine to external applications.

RESPONSIBILITY:
  - Provide a RESTful API layer over the integrated ECLAIR engine.
  - Endpoints: POST /v1/ask, POST /v1/verify, GET /v1/explain/{query_id},
    POST /v1/feedback, GET /v1/health, GET /v1/metrics.

NON-RESPONSIBILITY:
  - MUST NOT independently implement claim verification, confidence fusion, hallucination
    detection, or risk/decision logic (Spec §4.12). It calls the engine.

LOCATION:
  src/eclair/api/
EXISTING FOLDERS USED:
  src/eclair/api/  (main.py, dependencies.py, middleware.py, routes/, schemas/)
  tests/api/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: engine (src/eclair/engine/), M01 contracts, M14 (explain via engine).
  External: FastAPI, Pydantic, Uvicorn.
  Configuration: via M01 config.

INPUTS:
  Source: external HTTP clients.
  Format: request schemas in api/schemas/requests.py (Pydantic).
  Validation: FastAPI/Pydantic validation at the boundary.

PROCESSING:
  New logic: thin request handling that delegates to the engine and maps results to responses.

OUTPUTS:
  Format: response schemas in api/schemas/responses.py; OpenAPI/Swagger auto-provided by FastAPI.
  Destination: HTTP clients; also the SDK (M16) and Dashboard (M17).

CONSUMERS:
  Module/service: M16 SDK, M17 Dashboard, external apps.
  Expected contract: versioned endpoints above with stable request/response schemas.

INTEGRATION POINTS:
  APIs exposed: the six /v1 endpoints. APIs used: internal engine.
  Database: only via engine/M14. Events/Queues: none. Configuration: M01.
  Auth: only if defined by configuration/engine — do not invent an auth scheme.

ERROR HANDLING: use M01 exceptions mapped to consistent HTTP error responses; do not invent formats.
VALIDATION RULES: validate all requests via Pydantic schemas.
INTEGRATION REQUIREMENTS: stays thin; all reliability logic lives in the engine/modules.

DO NOT CHANGE: engine contracts; M01 contracts; any other module folder.
REUSE RULES: reuse engine + M01 contracts; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only the six endpoints listed.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: HTTP exposure of the integrated engine.
  Does NOT handle: any reliability computation.

VERIFICATION BEFORE COMPLETE:
  - All six versioned endpoints respond and delegate to the engine.
  - Swagger/OpenAPI available.
  - tests/api/ pass; sample request/response; docs/api/endpoints.md + examples.md written.
```

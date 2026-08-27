# M16 — Python SDK — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M16 — Python SDK
IDENTIFIER: M16

PURPOSE:
  Provide the easiest developer integration path — a thin client over the REST API.

RESPONSIBILITY:
  - Provide EclairClient with: client.ask(...), client.verify(...), client.explain(...),
    client.feedback(...).

NON-RESPONSIBILITY:
  - MUST NOT duplicate reliability logic (verification, confidence, hallucination, risk) — it
    wraps the REST API only (Spec §4.12).

LOCATION:
  sdk/python/
EXISTING FOLDERS USED:
  sdk/python/  (pyproject.toml, eclair/__init__.py, client.py, models.py, exceptions.py, utils.py)
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: mirrors M15 request/response schemas (by contract, not by importing server code).
  External: Python, HTTPX, Pydantic.
  Configuration: base_url and client settings passed by the developer.

INPUTS:
  Source: SDK method arguments from the developer.
  Format: SDK models in sdk/python/eclair/models.py.
  Validation: validate client-side with Pydantic before HTTP calls.

PROCESSING:
  New logic: construct/execute HTTP requests to the M15 endpoints and parse responses.

OUTPUTS:
  Format: typed SDK result objects (e.g. exposing ecs) mapping M15 responses.
  Destination: the developer's application.

CONSUMERS:
  Module/service: external developer applications.
  Expected contract: EclairClient methods returning typed results.

INTEGRATION POINTS:
  APIs used: M15 REST endpoints (/v1/ask, /v1/verify, /v1/explain/{query_id}, /v1/feedback).
  APIs exposed: Python client methods. Database: none. Events/Queues: none.
  Configuration: base_url. Auth: only if M15 defines it.

ERROR HANDLING: use sdk/python/eclair/exceptions.py; map HTTP errors consistently; no invented formats.
VALIDATION RULES: validate arguments before sending.
INTEGRATION REQUIREMENTS: must stay in sync with M15's request/response contracts; no logic duplication.

DO NOT CHANGE: M15 API contract; server modules; any other folder.
REUSE RULES: reuse HTTPX + M15 contract shapes; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only ask/verify/explain/feedback client methods.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: thin HTTP client over the REST API.
  Does NOT handle: any reliability computation.

VERIFICATION BEFORE COMPLETE:
  - EclairClient.ask/verify/explain/feedback call M15 and return typed results without local logic.
  - Sample usage provided; docs updated as applicable.
```

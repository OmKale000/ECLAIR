# M02 — LLM Gateway — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M02 — LLM Gateway
IDENTIFIER: M02

PURPOSE:
  Make ECLAIR independent of any single LLM provider.

RESPONSIBILITY:
  - Provider abstraction, routing, retries, fallbacks, and model selection.
  - Text generation and structured JSON generation through one stable interface.

NON-RESPONSIBILITY:
  - Does NOT extract claims, retrieve evidence, verify, score confidence, or make decisions.
  - Does NOT persist data.

LOCATION:
  src/eclair/llm/
EXISTING FOLDERS USED:
  src/eclair/llm/  (base.py, router.py, factory.py, ollama.py, gemini.py, groq.py, openrouter.py)
  tests/unit/llm/
NEW FILES REQUIRED:
  None beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 shared contracts/config/exceptions.
  External: Python, HTTPX, Ollama, provider SDKs/APIs, Pydantic.
  Configuration: reads provider settings from src/eclair/config.py (M01).

INPUTS:
  Source: internal callers (engine, consensus, verification, reflection, claim extraction).
  Format: an LLMRequest (prompt / structured-output request) per the shared/module contract.
  Validation: validate request via Pydantic before dispatch.

PROCESSING:
  New logic required: adapter pattern / provider abstraction with a stable LLMProvider interface
    (Protocol). Gemini, Groq, Ollama, OpenRouter all implement the same contract (Spec §4.3).
    Handle timeouts, retries, provider-failure fallback, model selection.

OUTPUTS:
  Format: LLMResponse (text or structured JSON) per the module contract.
  Destination: returned to the calling module.

CONSUMERS:
  Module/service: M03 Claim Extraction, M07 Verification (llm_verifier), M09 Consensus,
    M12 Reflection, and the engine.
  Expected contract: callers use llm.generate(...) and never call providers directly.

INTEGRATION POINTS:
  APIs used: external provider HTTP APIs (Ollama local; Gemini/Groq/OpenRouter optional free-tier).
  APIs exposed: internal Python interface only (LLMProvider / generate).
  Database: none. Events/Queues: none.
  Configuration: provider keys/endpoints/model names via M01 config.
  Auth: provider API keys via configuration only (never hardcoded).

ERROR HANDLING:
  Use M01 shared exceptions. On provider failure, apply retry then fallback (Ollama is the
  permanent zero-cost fallback, Spec §4.11). Do not silently swallow errors.

VALIDATION RULES:
  Validate request/response with Pydantic. Enforce timeouts.

INTEGRATION REQUIREMENTS:
  All providers conform to the same interface so callers are provider-agnostic.

DO NOT CHANGE:
  Existing APIs: none. Existing models: M01 contracts.
  Existing modules: none. Existing architecture: keep provider abstraction stable.

REUSE RULES: reuse HTTPX + M01 contracts; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only generation/routing/retry/fallback/model-selection.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: provider-agnostic generation.
  Does NOT handle: any reliability analysis or persistence.

VERIFICATION BEFORE COMPLETE:
  - All providers implement the same interface.
  - Fallback to Ollama works when a provider fails.
  - Timeouts/retries behave per contract.
  - tests/unit/llm/ pass; sample input/output provided; docs/modules/llm_gateway.md written.
```

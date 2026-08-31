# M02 — LLM Gateway

> Module documentation (Spec §4.8). Derived only from the Spec (§M02, §4.3, §4.11) and the repo.
> Authoritative rules: `rules/M02_llm_gateway.md`, `rules/COMMON_RULES.md`. Do not invent providers,
> parameters, or behavior.

## Identity
- **ID:** M02
- **Name:** LLM Gateway
- **Folder:** `src/eclair/llm/`
- **Tests:** `tests/unit/llm/`

## Purpose (Spec §M02)
Make ECLAIR independent of any single LLM provider.

## Responsibility
- Provider abstraction, routing, retries, fallbacks and model selection.
- Expose a stable `LLMProvider` interface that all providers implement (Spec §4.3).

## Non-responsibility
- Does NOT extract claims, retrieve evidence, verify, score confidence, calibrate, or decide.
- Does NOT embed reliability logic; it only generates text / structured output.

## Files (Spec §M02)
```
src/eclair/llm/  base.py  router.py  factory.py
                 ollama.py  gemini.py  groq.py  openrouter.py
```

## Technology (Spec §M02)
Python, HTTPX, Ollama, provider SDKs/APIs, Pydantic.

## Method (Spec §M02, §4.3)
Adapter pattern / provider abstraction with a stable `LLMProvider` interface. Gemini, Groq, Ollama
and OpenRouter all implement the same contract:
```
class LLMProvider(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
```

## Required functionality (Spec §M02)
- Text generation
- Structured JSON generation
- Provider switching
- Timeout handling
- Retry handling
- Provider failure fallback
- Model selection

## Inputs / Outputs
- **Inputs:** `LLMRequest` (prompt/model/params) from the engine or any module needing generation.
- **Outputs:** `LLMResponse` (generated text or structured JSON). Consumed by M03 (claim extraction),
  M07 (optional LLM verification), M08, M09 (consensus runs multiple model calls), M12 (regeneration),
  and the engine.

## Free-tier / fallback rule (Spec §4.11)
Ollama remains the **permanent zero-cost fallback**. Gemini, Groq and OpenRouter are optional
providers through their free quotas only; ECLAIR must not depend on temporary trials. On provider
failure, the gateway falls back so callers can rely on `llm.generate(...)` regardless of active
provider.

## Error handling
Use M01 shared exceptions. Handle timeouts and provider failures with retries and fallback; do not
silently swallow errors or invent a new error format.

## Do not change
M01 contracts; the `LLMProvider` interface signature that downstream modules depend on; any other
module folder.

## Expected outcome (Spec §M02)
Other modules call `llm.generate(...)` without caring which provider is active.

## Module surface (M02-owned)
`LLMRequest` and `LLMResponse` are owned by M02 (M01's `LLMProvider` Protocol leaves those types as
`Any` for M02 to refine within its boundary). They are Pydantic v2 models defined in
`src/eclair/llm/base.py`:

- **`LLMRequest`** — `prompt` (required), `model` (optional override → model selection),
  `temperature` (0.0–2.0, optional), `max_tokens` (>0, optional), `json_mode` (bool, structured JSON).
- **`LLMResponse`** — `text`, `model`, `provider`, `structured` (parsed JSON when `json_mode` produced
  valid JSON, else `None`).

Public exports (`eclair.llm`): `LLMRequest`, `LLMResponse`, `BaseHTTPProvider`, `OllamaProvider`,
`GeminiProvider`, `GroqProvider`, `OpenRouterProvider`, `build_provider`, `SUPPORTED_PROVIDERS`,
`LLMRouter`, `FALLBACK_PROVIDER`.

## Usage
Callers build a router from the shared M01 config and call `generate(...)`; they never touch
providers directly:

```python
from eclair.config import load_config
from eclair.llm import LLMRequest, LLMRouter

router = LLMRouter(load_config().llm)
response = router.generate(LLMRequest(prompt="Summarize the refund policy."))
print(response.text)
```

The router routes to `config.active_provider`, retries up to `config.retries` extra attempts, and
falls back to Ollama (the permanent zero-cost fallback, Spec §4.11) if the active provider fails —
unless Ollama is already the active provider. If both fail it raises `ModuleError`
(`code="llm_all_providers_failed"`).

## Sample input / output
**Sample input** — an `LLMRequest`:

```json
{
  "prompt": "Return the max refund window in days as JSON.",
  "model": null,
  "temperature": 0.0,
  "max_tokens": 64,
  "json_mode": true
}
```

**Sample output** — an `LLMResponse` (Ollama active, provider returned `{"refund_window_days": 30}`):

```json
{
  "text": "{\"refund_window_days\": 30}",
  "model": "llama3",
  "provider": "ollama",
  "structured": {"refund_window_days": 30}
}
```

## Error codes (shared `ModuleError`)
`llm_invalid_request`, `llm_timeout`, `llm_http_error`, `llm_request_failed`, `llm_bad_response`,
`llm_unknown_provider`, `llm_provider_unconfigured`, `llm_all_providers_failed`. No new error format
is introduced; all use M01's `eclair.exceptions.ModuleError`.

## Verification before complete (Spec §4.8)
- All providers implement the same `LLMProvider` interface.
- Fallback and retry behavior works; Ollama is the guaranteed fallback.
- `tests/unit/llm/` pass; sample input/output provided.

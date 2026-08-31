"""Unit tests for the M02 LLM Gateway.

All provider HTTP calls are mocked (via monkeypatching ``httpx.post``); no live
Ollama/Gemini/Groq/OpenRouter server is required. Tests cover interface
conformance, request building, JSON-mode parsing, timeout/HTTP error mapping,
retry behavior, and provider-failure fallback to Ollama.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from eclair.config import LLMProviderConfig
from eclair.contracts.interfaces import LLMProvider
from eclair.exceptions import ModuleError
from eclair.llm import (
    BaseHTTPProvider,
    GeminiProvider,
    GroqProvider,
    LLMRequest,
    LLMResponse,
    LLMRouter,
    OllamaProvider,
    OpenRouterProvider,
    build_provider,
)


class _FakeResponse:
    """Minimal stand-in for httpx.Response used by mocked httpx.post."""

    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", "http://test"),
                response=httpx.Response(self.status_code),
            )


def _capture_post(store: dict[str, Any], payload: dict[str, Any]):
    """Return a fake httpx.post that records call args and returns ``payload``."""

    def _post(url: str, *, json: dict[str, Any], headers: dict[str, str], timeout: float):
        store["url"] = url
        store["json"] = json
        store["headers"] = headers
        store["timeout"] = timeout
        return _FakeResponse(payload)

    return _post


# --------------------------------------------------------------------------- #
# Provider construction helpers                                               #
# --------------------------------------------------------------------------- #

def _ollama() -> OllamaProvider:
    return OllamaProvider(
        base_url="http://localhost:11434", model="llama3", timeout_seconds=30.0
    )


def _groq() -> GroqProvider:
    return GroqProvider(
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.1-8b",
        timeout_seconds=30.0,
        api_key="k",
    )


def _openrouter() -> OpenRouterProvider:
    return OpenRouterProvider(
        base_url="https://openrouter.ai/api/v1",
        model="meta-llama/llama-3.1-8b",
        timeout_seconds=30.0,
        api_key="k",
    )


def _gemini() -> GeminiProvider:
    return GeminiProvider(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        model="gemini-1.5-flash",
        timeout_seconds=30.0,
        api_key="k",
    )


ALL_PROVIDERS = [_ollama, _groq, _openrouter, _gemini]


# --------------------------------------------------------------------------- #
# Interface conformance                                                       #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("factory", ALL_PROVIDERS)
def test_provider_conforms_to_llmprovider_protocol(factory) -> None:
    provider = factory()
    assert isinstance(provider, LLMProvider)
    assert isinstance(provider, BaseHTTPProvider)
    assert callable(provider.generate)


def test_llmrequest_requires_nonempty_prompt() -> None:
    with pytest.raises(Exception):  # pydantic ValidationError
        LLMRequest(prompt="")


# --------------------------------------------------------------------------- #
# Per-provider request building + response parsing                            #
# --------------------------------------------------------------------------- #

def test_ollama_builds_generate_request_and_parses(monkeypatch) -> None:
    store: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "post", _capture_post(store, {"response": "hi"}))
    resp = _ollama().generate(LLMRequest(prompt="hello", temperature=0.2, max_tokens=10))
    assert isinstance(resp, LLMResponse)
    assert resp.text == "hi"
    assert resp.provider == "ollama"
    assert resp.model == "llama3"
    assert store["url"].endswith("/api/generate")
    assert store["json"]["prompt"] == "hello"
    assert store["json"]["stream"] is False
    assert store["json"]["options"] == {"temperature": 0.2, "num_predict": 10}


def test_groq_builds_chat_request_with_bearer_and_parses(monkeypatch) -> None:
    store: dict[str, Any] = {}
    payload = {"choices": [{"message": {"content": "answer"}}]}
    monkeypatch.setattr(httpx, "post", _capture_post(store, payload))
    resp = _groq().generate(LLMRequest(prompt="q"))
    assert resp.text == "answer"
    assert resp.provider == "groq"
    assert store["url"].endswith("/chat/completions")
    assert store["headers"]["Authorization"] == "Bearer k"
    assert store["json"]["messages"] == [{"role": "user", "content": "q"}]


def test_openrouter_builds_chat_request_and_parses(monkeypatch) -> None:
    store: dict[str, Any] = {}
    payload = {"choices": [{"message": {"content": "ro"}}]}
    monkeypatch.setattr(httpx, "post", _capture_post(store, payload))
    resp = _openrouter().generate(LLMRequest(prompt="q"))
    assert resp.text == "ro"
    assert resp.provider == "openrouter"
    assert store["headers"]["Authorization"] == "Bearer k"


def test_gemini_builds_generatecontent_request_and_parses(monkeypatch) -> None:
    store: dict[str, Any] = {}
    payload = {"candidates": [{"content": {"parts": [{"text": "g"}]}}]}
    monkeypatch.setattr(httpx, "post", _capture_post(store, payload))
    resp = _gemini().generate(LLMRequest(prompt="q"))
    assert resp.text == "g"
    assert resp.provider == "gemini"
    assert ":generateContent" in store["url"]
    assert "key=k" in store["url"]


# --------------------------------------------------------------------------- #
# Model selection + JSON mode                                                 #
# --------------------------------------------------------------------------- #

def test_model_override_is_honored(monkeypatch) -> None:
    store: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "post", _capture_post(store, {"response": "x"}))
    resp = _ollama().generate(LLMRequest(prompt="p", model="mistral"))
    assert store["json"]["model"] == "mistral"
    assert resp.model == "mistral"


def test_json_mode_parses_structured(monkeypatch) -> None:
    store: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "post", _capture_post(store, {"response": '{"a": 1}'}))
    resp = _ollama().generate(LLMRequest(prompt="p", json_mode=True))
    assert store["json"]["format"] == "json"
    assert resp.structured == {"a": 1}


def test_json_mode_invalid_json_yields_none_structured(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "post", _capture_post({}, {"response": "not json"}))
    resp = _ollama().generate(LLMRequest(prompt="p", json_mode=True))
    assert resp.structured is None


# --------------------------------------------------------------------------- #
# Error mapping                                                               #
# --------------------------------------------------------------------------- #

def test_timeout_maps_to_module_error(monkeypatch) -> None:
    def _timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(httpx, "post", _timeout)
    with pytest.raises(ModuleError) as exc:
        _ollama().generate(LLMRequest(prompt="p"))
    assert exc.value.code == "llm_timeout"


def test_http_status_maps_to_module_error(monkeypatch) -> None:
    def _post(*args, **kwargs):
        return _FakeResponse({}, status_code=500)

    monkeypatch.setattr(httpx, "post", _post)
    with pytest.raises(ModuleError) as exc:
        _ollama().generate(LLMRequest(prompt="p"))
    assert exc.value.code == "llm_http_error"


@pytest.mark.parametrize(
    ("factory", "bad_payload"),
    [
        (_ollama, {"error": "model not found"}),
        (_groq, {"choices": []}),
        (_openrouter, {"unexpected": True}),
        (_gemini, {"candidates": [{}]}),
    ],
)
def test_unexpected_response_shape_maps_to_module_error(
    monkeypatch, factory, bad_payload
) -> None:
    """A 200 response missing expected keys must surface as ModuleError, not a raw
    KeyError/IndexError/TypeError leak (M02 must use M01 shared exceptions)."""
    monkeypatch.setattr(httpx, "post", _capture_post({}, bad_payload))
    with pytest.raises(ModuleError) as exc:
        factory().generate(LLMRequest(prompt="p"))
    assert exc.value.code == "llm_bad_response"


# --------------------------------------------------------------------------- #
# Factory                                                                     #
# --------------------------------------------------------------------------- #

def test_factory_builds_ollama_by_default() -> None:
    provider = build_provider("ollama", LLMProviderConfig())
    assert isinstance(provider, OllamaProvider)


def test_factory_unknown_provider_raises() -> None:
    with pytest.raises(ModuleError) as exc:
        build_provider("nope", LLMProviderConfig())
    assert exc.value.code == "llm_unknown_provider"


def test_factory_unconfigured_optional_provider_raises() -> None:
    with pytest.raises(ModuleError) as exc:
        build_provider("groq", LLMProviderConfig())
    assert exc.value.code == "llm_provider_unconfigured"


def test_factory_builds_configured_optional_provider() -> None:
    config = LLMProviderConfig(
        groq_api_key="k",
        groq_base_url="https://api.groq.com/openai/v1",
        groq_model="llama-3.1-8b",
    )
    assert isinstance(build_provider("groq", config), GroqProvider)


# --------------------------------------------------------------------------- #
# Router: retries + fallback                                                  #
# --------------------------------------------------------------------------- #

class _StubProvider(BaseHTTPProvider):
    """Provider stub that fails a fixed number of times then succeeds."""

    def __init__(self, name: str, *, fail_times: int, always_fail: bool = False) -> None:
        super().__init__(base_url="http://x", model="m", timeout_seconds=1.0)
        self.name = name
        self._fail_times = fail_times
        self._always_fail = always_fail
        self.calls = 0

    def generate(self, request: LLMRequest) -> LLMResponse:  # type: ignore[override]
        self.calls += 1
        if self._always_fail or self.calls <= self._fail_times:
            raise ModuleError("boom", code="llm_request_failed")
        return LLMResponse(text="ok", model="m", provider=self.name)

    def _build_request(self, request, model):  # pragma: no cover - unused
        raise NotImplementedError

    def _parse_response(self, data):  # pragma: no cover - unused
        raise NotImplementedError


def test_router_retries_active_provider_then_succeeds() -> None:
    config = LLMProviderConfig(active_provider="ollama", retries=2)
    stub = _StubProvider("ollama", fail_times=1)
    router = LLMRouter(config, provider=stub)
    resp = router.generate(LLMRequest(prompt="p"))
    assert resp.text == "ok"
    assert stub.calls == 2  # 1 failure + 1 success


def test_router_falls_back_to_ollama(monkeypatch) -> None:
    config = LLMProviderConfig(
        active_provider="groq",
        retries=0,
        groq_api_key="k",
        groq_base_url="https://api.groq.com/openai/v1",
        groq_model="llama-3.1-8b",
    )
    failing_groq = _StubProvider("groq", fail_times=0, always_fail=True)

    # Fallback path builds a real OllamaProvider; mock its HTTP call to succeed.
    monkeypatch.setattr(httpx, "post", _capture_post({}, {"response": "fallback"}))
    router = LLMRouter(config, provider=failing_groq)
    resp = router.generate(LLMRequest(prompt="p"))
    assert resp.provider == "ollama"
    assert resp.text == "fallback"


def test_router_no_fallback_when_active_is_ollama() -> None:
    config = LLMProviderConfig(active_provider="ollama", retries=0)
    failing = _StubProvider("ollama", fail_times=0, always_fail=True)
    router = LLMRouter(config, provider=failing)
    with pytest.raises(ModuleError) as exc:
        router.generate(LLMRequest(prompt="p"))
    assert exc.value.code == "llm_request_failed"


def test_router_both_fail_raises_all_providers_failed(monkeypatch) -> None:
    config = LLMProviderConfig(
        active_provider="groq",
        retries=0,
        groq_api_key="k",
        groq_base_url="https://api.groq.com/openai/v1",
        groq_model="llama-3.1-8b",
    )
    failing_groq = _StubProvider("groq", fail_times=0, always_fail=True)

    def _fail(*args, **kwargs):
        raise httpx.TimeoutException("down")

    monkeypatch.setattr(httpx, "post", _fail)
    router = LLMRouter(config, provider=failing_groq)
    with pytest.raises(ModuleError) as exc:
        router.generate(LLMRequest(prompt="p"))
    assert exc.value.code == "llm_all_providers_failed"

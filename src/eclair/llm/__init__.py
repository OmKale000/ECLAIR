"""ECLAIR LLM Gateway (M02).

Provider-agnostic text / structured-JSON generation. Callers use the router's
``generate(request)`` and never call providers directly. Providers
(Ollama/Gemini/Groq/OpenRouter) all conform to the frozen M01 ``LLMProvider``
Protocol via ``BaseHTTPProvider``. Ollama is the permanent zero-cost fallback
(Spec sec.4.11).
"""

from __future__ import annotations

from eclair.llm.base import BaseHTTPProvider, LLMRequest, LLMResponse
from eclair.llm.factory import SUPPORTED_PROVIDERS, build_provider
from eclair.llm.gemini import GeminiProvider
from eclair.llm.groq import GroqProvider
from eclair.llm.ollama import OllamaProvider
from eclair.llm.openrouter import OpenRouterProvider
from eclair.llm.router import FALLBACK_PROVIDER, LLMRouter

__all__ = [
    "LLMRequest",
    "LLMResponse",
    "BaseHTTPProvider",
    "OllamaProvider",
    "GeminiProvider",
    "GroqProvider",
    "OpenRouterProvider",
    "build_provider",
    "SUPPORTED_PROVIDERS",
    "LLMRouter",
    "FALLBACK_PROVIDER",
]

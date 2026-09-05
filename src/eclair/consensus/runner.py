"""Consensus runner orchestration for M09 Multi-Agent / Multi-Model Consensus.

Executes multiple independent model calls concurrently via the M02 LLM Gateway,
collects successful outputs with graceful error degradation, tallies majority
votes, calculates cross-model agreement scores, measures diversity, and returns
the aggregate :class:`ConsensusResult`.

Reliability Invariant:
    Model agreement is NOT proof of truth (Spec sec.4.6).
    M09 produces a consensus agreement signal only; it does NOT perform claim
    verification (M07), confidence calibration (M11), or risk decisions (M13).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol, Sequence, runtime_checkable

from eclair.config import EclairConfig, LLMProviderConfig, load_config
from eclair.consensus.agreement import AgreementCalculator
from eclair.consensus.diversity import DiversityCalculator
from eclair.consensus.models import (
    AgreementResult,
    ConsensusResult,
    DiversityResult,
    ModelCallConfig,
    ModelOutput,
    VotingResult,
)
from eclair.consensus.voting import MajorityVoter
from eclair.contracts.query import Query
from eclair.exceptions import ModuleError
from eclair.llm.base import BaseHTTPProvider, LLMRequest, LLMResponse
from eclair.llm.factory import build_provider

__all__ = ["ConsensusRunner", "LLMClient"]


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM provider abstraction (conforms to M02)."""

    def generate(self, request: Any) -> Any:
        """Generate response for the given request."""
        ...


class ConsensusRunner:
    """Orchestrates multi-model consensus evaluation across independent providers.

    Dispatches model requests in parallel using asyncio, isolates provider failures,
    runs majority voting and agreement calculations, and produces a structured
    :class:`ConsensusResult`.
    """

    def __init__(
        self,
        *,
        config: EclairConfig | LLMProviderConfig | None = None,
        llm: LLMClient | None = None,
        default_models: Sequence[ModelCallConfig | str] | None = None,
        voter: MajorityVoter | None = None,
        agreement_calculator: AgreementCalculator | None = None,
        diversity_calculator: DiversityCalculator | None = None,
    ) -> None:
        """Initialize ConsensusRunner.

        Args:
            config: Shared configuration. Defaults to loading from environment.
            llm: Optional injected LLM client / router (e.g. for testing).
            default_models: Default set of models/providers to query.
            voter: Custom majority voter instance.
            agreement_calculator: Custom agreement calculator instance.
            diversity_calculator: Custom diversity calculator instance.
        """
        if config is None:
            try:
                self._config = load_config().llm
            except Exception:
                self._config = LLMProviderConfig()
        elif isinstance(config, EclairConfig):
            self._config = config.llm
        else:
            self._config = config

        self._llm = llm
        self._default_models = list(default_models) if default_models is not None else None
        self._voter = voter or MajorityVoter()
        self._agreement_calc = agreement_calculator or AgreementCalculator()
        self._diversity_calc = diversity_calculator or DiversityCalculator()

    def _resolve_model_configs(
        self,
        models: Sequence[ModelCallConfig | str] | None,
    ) -> list[ModelCallConfig]:
        """Resolve model specifications into validated :class:`ModelCallConfig` objects."""
        raw_models = models if models is not None else self._default_models

        if not raw_models:
            # Default to polling active provider with standard variations
            active = self._config.active_provider
            return [
                ModelCallConfig(provider=active, temperature=0.0),
                ModelCallConfig(provider=active, temperature=0.7),
                ModelCallConfig(provider=active, temperature=1.0),
            ]

        resolved: list[ModelCallConfig] = []
        for m in raw_models:
            if isinstance(m, ModelCallConfig):
                resolved.append(m)
            elif isinstance(m, str):
                # Parse provider or provider/model syntax
                if "/" in m:
                    prov, mod = m.split("/", 1)
                    resolved.append(ModelCallConfig(provider=prov.strip(), model=mod.strip()))
                else:
                    resolved.append(ModelCallConfig(provider=m.strip()))
            else:
                raise ModuleError(
                    f"Invalid model specification: {m!r}",
                    code="consensus_invalid_model_config",
                )
        return resolved

    def _call_single_model(
        self,
        query: str,
        spec: ModelCallConfig,
    ) -> ModelOutput:
        """Synchronously execute a single model call with error trapping and timing."""
        start_time = time.perf_counter()
        provider_name = spec.provider
        model_name = spec.model or "default"

        request = LLMRequest(
            prompt=query,
            model=spec.model,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            json_mode=spec.json_mode,
        )

        try:
            if self._llm is not None:
                response = self._llm.generate(request)
            else:
                # Build provider dynamically via M02 factory
                provider: BaseHTTPProvider = build_provider(provider_name, self._config)
                response = provider.generate(request)

            latency = time.perf_counter() - start_time
            text = response.text if isinstance(response, LLMResponse) else str(response)
            actual_model = getattr(response, "model", model_name)
            actual_provider = getattr(response, "provider", provider_name)

            return ModelOutput(
                model=actual_model,
                provider=actual_provider,
                text=text,
                success=True,
                error=None,
                latency_seconds=latency,
            )
        except Exception as exc:
            latency = time.perf_counter() - start_time
            return ModelOutput(
                model=model_name,
                provider=provider_name,
                text="",
                success=False,
                error=str(exc),
                latency_seconds=latency,
            )

    async def async_run(
        self,
        query: str | Query,
        models: Sequence[ModelCallConfig | str] | None = None,
    ) -> ConsensusResult:
        """Asynchronously execute multi-model consensus over independent model calls.

        Args:
            query: The user query or prompt string (or :class:`Query` object).
            models: Optional list of model configurations/providers to query.

        Returns:
            A populated :class:`ConsensusResult`.

        Raises:
            ModuleError: if the query is empty or all model calls fail.
        """
        query_text = query.question if isinstance(query, Query) else str(query)
        query_text = query_text.strip()

        if not query_text:
            raise ModuleError(
                "Query text cannot be empty for consensus evaluation",
                code="consensus_empty_query",
            )

        model_specs = self._resolve_model_configs(models)

        # Dispatch all model calls concurrently in background worker threads
        tasks = [
            asyncio.to_thread(self._call_single_model, query_text, spec) for spec in model_specs
        ]
        outputs: list[ModelOutput] = await asyncio.gather(*tasks)

        return self.evaluate_outputs(query_text, outputs)

    def run(
        self,
        query: str | Query,
        models: Sequence[ModelCallConfig | str] | None = None,
    ) -> ConsensusResult:
        """Synchronous wrapper for :meth:`async_run`."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # In an existing event loop, run directly in background thread to avoid loop collision
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.async_run(query, models))
                return future.result()
        return asyncio.run(self.async_run(query, models))

    def evaluate_outputs(
        self,
        query: str,
        outputs: Sequence[ModelOutput],
    ) -> ConsensusResult:
        """Evaluate pre-collected model outputs without dispatching network calls.

        Args:
            query: The evaluated query or prompt.
            outputs: List of :class:`ModelOutput` results from models.

        Returns:
            A populated :class:`ConsensusResult`.

        Raises:
            ModuleError: if all model outputs are marked as failed or empty.
        """
        outputs_list = list(outputs)
        successful = [out for out in outputs_list if out.success and out.text.strip()]
        failed = [out for out in outputs_list if not out.success or not out.text.strip()]

        successful_names = [f"{out.provider}:{out.model}" for out in successful]
        failed_names = [f"{out.provider}:{out.model}" for out in failed]

        if not successful:
            raise ModuleError(
                "All model calls failed during multi-model consensus execution",
                code="consensus_all_models_failed",
            )

        # Run voting
        voting_res: VotingResult = self._voter.vote(successful)

        # Run agreement
        agreement_res: AgreementResult = self._agreement_calc.calculate(successful, voting_res)

        # Run diversity
        diversity_res: DiversityResult = self._diversity_calc.calculate(
            successful, agreement_res, voting_res
        )

        return ConsensusResult(
            query=query,
            agreement_score=agreement_res.agreement_score,
            consensus_level=agreement_res.consensus_level,
            majority_answer=voting_res.majority_answer,
            model_outputs=outputs_list,
            successful_models=successful_names,
            failed_models=failed_names,
            voting=voting_res,
            agreement=agreement_res,
            diversity=diversity_res,
            is_truth=False,  # Explicit reliability invariant: model agreement is NOT truth
            details={
                "total_models_polled": len(outputs_list),
                "successful_count": len(successful),
                "failed_count": len(failed),
                "unanimous": agreement_res.unanimous,
            },
        )

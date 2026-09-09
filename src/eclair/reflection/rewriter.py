"""Response rewriter implementation for M12 Self-Reflection & Self-Correction.

Revises answers using the M02 LLM Gateway guided by claim-targeted critiques
and verified evidence.

Reliability Invariant:
    * Must use M02 LLM Gateway abstraction (conforms to LLMProvider Protocol).
    * Claim-targeted: addresses specific weak claims while preserving supported facts.
    * Uses shared M01 exception types (ModuleError).
"""

from __future__ import annotations

from eclair.contracts.evidence import Evidence
from eclair.contracts.interfaces import LLMProvider
from eclair.exceptions import ModuleError
from eclair.llm.base import LLMRequest
from eclair.reflection.critic import ResponseCritic
from eclair.reflection.models import CritiqueReport

__all__ = ["ResponseRewriter"]


class ResponseRewriter:
    """Regenerates answers using the M02 LLM Gateway guided by critique and evidence."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        critic: ResponseCritic | None = None,
    ) -> None:
        """Initialize the rewriter.

        Args:
            llm_provider: Provider implementing M01 LLMProvider protocol (Spec sec.4.3).
            critic: Optional ResponseCritic instance for formatting critique prompts.
        """
        self._llm_provider = llm_provider
        self._critic = critic or ResponseCritic()

    def rewrite(
        self,
        query: str,
        current_answer: str,
        critique: CritiqueReport,
        evidence: list[Evidence] | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a corrected answer addressing the critique and grounded in evidence.

        Args:
            query: The original user question or query text.
            current_answer: The draft response requiring reflection/correction.
            critique: The critique report detailing weak/contradicted claims.
            evidence: Supporting evidence passages.
            model: Optional model override.
            temperature: Optional sampling temperature.

        Returns:
            The regenerated and corrected answer text.

        Raises:
            ModuleError: If generation fails or returns empty output.
        """
        critique_text = self._critic.format_critique_for_prompt(critique, evidence)

        prompt = (
            "You are a factual revision assistant for the ECLAIR reliability engine.\n"
            "Your task is to revise the draft answer to correct all identified weaknesses, "
            "remove unsupported or contradicted claims, and adhere strictly to verified evidence.\n\n"
            f"USER QUERY:\n{query}\n\n"
            f"CURRENT DRAFT ANSWER:\n{current_answer}\n\n"
            f"{critique_text}\n\n"
            "REVISION RULES:\n"
            "1. Remove or correct any statement flagged as CONTRADICTED.\n"
            "2. Do not assert details flagged as UNKNOWN/unsupported unless explicitly backed by the evidence above.\n"
            "3. Keep all factual, verified statements intact.\n"
            "4. Provide a clear, cohesive, factual revised answer directly answering the query.\n\n"
            "REVISED FACTUAL ANSWER:"
        )

        request = LLMRequest(
            prompt=prompt,
            model=model,
            temperature=temperature if temperature is not None else 0.3,
        )

        try:
            response = self._llm_provider.generate(request)
        except Exception as exc:
            raise ModuleError(
                f"Reflection rewriter failed during LLM generation: {exc}",
                code="reflection_llm_error",
            ) from exc

        if not hasattr(response, "text") or not response.text:
            raise ModuleError(
                "LLM provider returned empty response during reflection rewriting",
                code="reflection_empty_response",
            )

        revised_text = str(response.text).strip()
        if not revised_text:
            raise ModuleError(
                "LLM provider returned blank text during reflection rewriting",
                code="reflection_blank_response",
            )

        return revised_text

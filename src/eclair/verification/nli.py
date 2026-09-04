"""Natural Language Inference (NLI) engine for M07 Claim Verification.

Maps (premise, hypothesis) pairs — representing (evidence, claim) — to NLI
classifications: ENTAILMENT, CONTRADICTION, or NEUTRAL.

Follows Spec sec.M07 and sec.4.9:
    * ENTAILMENT    -> SUPPORTED
    * CONTRADICTION -> CONTRADICTED
    * NEUTRAL       -> UNKNOWN

Reuses Hugging Face Transformers NLI models (via pipeline or custom callable)
with lazy initialization, deterministic fallback, and strict score bounds [0.0, 1.0].
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from eclair.exceptions import ContractValidationError, ModuleError
from eclair.verification.models import NLILabel, NLIPrediction

__all__ = ["NLIEngine", "DEFAULT_NLI_MODEL"]

logger = logging.getLogger(__name__)

DEFAULT_NLI_MODEL = "roberta-large-mnli"


class NLIEngine:
    """Natural Language Inference engine for claim-evidence verification.

    Evaluates whether an evidence premise entails, contradicts, or is neutral
    with respect to a claim hypothesis.
    """

    def __init__(
        self,
        *,
        model_name: str | None = None,
        pipeline_fn: Callable[[str, str], dict[str, float]] | None = None,
        pipeline: Any = None,
        device: str | None = None,
        auto_load: bool = False,
    ) -> None:
        """Initialize the NLI engine.

        Args:
            model_name: HuggingFace model identifier (e.g. "roberta-large-mnli").
            pipeline_fn: Optional custom callable taking (premise, hypothesis) and
                returning a dict of label probabilities for testing or custom inference.
            pipeline: Optional pre-loaded HuggingFace pipeline instance.
            device: Optional torch device string (e.g. "cpu", "cuda:0").
            auto_load: When True, lazily downloads/loads the HuggingFace transformer model.
                Defaults to False for fast, deterministic offline inference and test stability.
        """
        self._model_name = model_name or DEFAULT_NLI_MODEL
        self._pipeline_fn = pipeline_fn
        self._pipeline = pipeline
        self._device = device
        self._auto_load = auto_load

    @property
    def model_name(self) -> str:
        """The configured NLI model name."""
        return self._model_name

    def _get_pipeline(self) -> Any:
        """Lazy-load the HuggingFace transformers classification pipeline if auto_load is enabled."""
        if self._pipeline is not None or not self._auto_load:
            return self._pipeline

        try:
            from transformers import pipeline

            kwargs: dict[str, Any] = {"model": self._model_name}
            if self._device is not None:
                kwargs["device"] = self._device

            self._pipeline = pipeline("text-classification", **kwargs)
            return self._pipeline
        except Exception as exc:
            logger.warning(
                "Could not load HuggingFace pipeline for %r (%s). Using fallback evaluator.",
                self._model_name,
                exc,
            )
            return None

    def predict(self, premise: str, hypothesis: str) -> NLIPrediction:
        """Predict NLI relationship between premise (evidence) and hypothesis (claim).

        Args:
            premise: The evidence text passage.
            hypothesis: The claim text.

        Returns:
            NLIPrediction with label, entailment_score, contradiction_score, neutral_score.

        Raises:
            ContractValidationError: If premise or hypothesis is not a string or is empty.
            ModuleError: If NLI prediction encounters an unrecoverable failure.
        """
        if not isinstance(premise, str) or not premise.strip():
            raise ContractValidationError(
                "NLI premise must be a non-empty string",
                code="nli_invalid_premise",
            )
        if not isinstance(hypothesis, str) or not hypothesis.strip():
            raise ContractValidationError(
                "NLI hypothesis must be a non-empty string",
                code="nli_invalid_hypothesis",
            )

        premise_clean = premise.strip()
        hypothesis_clean = hypothesis.strip()

        # 1. Custom callable provided
        if self._pipeline_fn is not None:
            try:
                scores = self._pipeline_fn(premise_clean, hypothesis_clean)
                return self._parse_scores_dict(scores)
            except Exception as exc:
                raise ModuleError(
                    f"Custom NLI pipeline callable failed: {exc}",
                    code="nli_execution_failed",
                ) from exc

        # 2. Transformers pipeline (if provided or auto_load enabled)
        pipe = self._get_pipeline()
        if pipe is not None:
            try:
                res = pipe(
                    {"text": premise_clean, "text_pair": hypothesis_clean},
                    top_k=None,
                )
                return self._parse_transformers_output(res)
            except Exception as exc:
                logger.warning("Transformers pipeline execution failed: %s; using fallback", exc)

        # 3. Deterministic lexical/semantic rule evaluator
        return self._heuristic_predict(premise_clean, hypothesis_clean)

    def _parse_scores_dict(self, scores: dict[str, float]) -> NLIPrediction:
        """Parse and normalize scores from a mapping."""
        normalized: dict[str, float] = {}
        for k, v in scores.items():
            key = k.strip().lower()
            if "entail" in key or "support" in key:
                normalized["entailment"] = max(0.0, min(1.0, float(v)))
            elif "contra" in key:
                normalized["contradiction"] = max(0.0, min(1.0, float(v)))
            elif "neutral" in key or "unknown" in key:
                normalized["neutral"] = max(0.0, min(1.0, float(v)))

        ent = normalized.get("entailment", 0.0)
        con = normalized.get("contradiction", 0.0)
        neu = normalized.get("neutral", 0.0)

        total = ent + con + neu
        if total > 0.0:
            ent, con, neu = ent / total, con / total, neu / total
        else:
            neu = 1.0

        if ent >= con and ent >= neu:
            top_label = NLILabel.ENTAILMENT
        elif con >= ent and con >= neu:
            top_label = NLILabel.CONTRADICTION
        else:
            top_label = NLILabel.NEUTRAL

        return NLIPrediction(
            label=top_label,
            entailment_score=round(ent, 4),
            contradiction_score=round(con, 4),
            neutral_score=round(neu, 4),
        )

    def _parse_transformers_output(self, raw_output: Any) -> NLIPrediction:
        """Extract probabilities from transformers pipeline output."""
        scores: dict[str, float] = {}
        if isinstance(raw_output, list):
            for item in raw_output:
                if isinstance(item, dict) and "label" in item and "score" in item:
                    scores[str(item["label"])] = float(item["score"])
                elif isinstance(item, list):
                    for sub in item:
                        if isinstance(sub, dict) and "label" in sub and "score" in sub:
                            scores[str(sub["label"])] = float(sub["score"])
        return self._parse_scores_dict(scores)

    def _heuristic_predict(self, premise: str, hypothesis: str) -> NLIPrediction:
        """Deterministic lexical/semantic evaluator when transformers model is not loaded."""
        p_lower = premise.lower()
        h_lower = hypothesis.lower()

        # Check exact or strong substring containment
        if h_lower in p_lower:
            return NLIPrediction(
                label=NLILabel.ENTAILMENT,
                entailment_score=0.95,
                contradiction_score=0.02,
                neutral_score=0.03,
            )

        # Check negative tokens / polarities
        negations = {"not", "never", "no", "cannot", "neither", "prohibited", "forbidden", "disallowed"}
        h_words = set(h_lower.split())
        p_words = set(p_lower.split())

        has_h_neg = bool(h_words & negations)
        has_p_neg = bool(p_words & negations)

        overlap = len(h_words & p_words)
        total_h = max(1, len(h_words))
        overlap_ratio = overlap / total_h

        if overlap_ratio >= 0.5 and (has_h_neg != has_p_neg):
            # Same context with inverted polarity -> Contradiction
            return NLIPrediction(
                label=NLILabel.CONTRADICTION,
                entailment_score=0.05,
                contradiction_score=0.85,
                neutral_score=0.10,
            )
        elif overlap_ratio >= 0.5:
            # High overlap without polarity clash -> Entailment
            return NLIPrediction(
                label=NLILabel.ENTAILMENT,
                entailment_score=0.85,
                contradiction_score=0.05,
                neutral_score=0.10,
            )

        # Insufficient or neutral overlap
        return NLIPrediction(
            label=NLILabel.NEUTRAL,
            entailment_score=0.15,
            contradiction_score=0.10,
            neutral_score=0.75,
        )

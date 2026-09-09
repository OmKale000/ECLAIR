"""Stopping and trigger controller for M12 Self-Reflection & Self-Correction.

Enforces deterministic trigger evaluation and hard stopping conditions to
guarantee loop termination and prevent infinite loops under all paths.

Reliability Invariant:
    * Hard iteration cap is non-negotiable and strictly enforced.
    * No infinite loop under any failure or degradation path.
    * Improvement requires measurable confidence improvement or full claim support.
"""

from __future__ import annotations

from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.verification import VerificationResult
from eclair.reflection.models import ReflectionConfig

__all__ = ["StoppingController"]


class StoppingController:
    """Controls the trigger gate and stopping conditions for the reflection loop."""

    def should_trigger(
        self,
        claims: list[Claim],
        verifications: list[VerificationResult],
        confidence: ConfidenceResult | None = None,
        config: ReflectionConfig | None = None,
    ) -> tuple[bool, str]:
        """Determine whether the response requires reflection/correction.

        Args:
            claims: The extracted claims for the response.
            verifications: M07 verification results for the claims.
            confidence: Optional M10/M11 confidence result.
            config: Reflection configuration.

        Returns:
            Tuple of (should_trigger: bool, reason: str).
        """
        cfg = config or ReflectionConfig()

        # Check 1: Explicit low confidence score (calibrated ECS takes priority, else raw)
        if confidence is not None:
            effective_conf = (
                confidence.calibrated_ecs
                if confidence.calibrated_ecs is not None
                else confidence.raw_confidence
            )
            if effective_conf < cfg.low_confidence_threshold:
                return True, f"confidence_{effective_conf:.3f}_below_threshold_{cfg.low_confidence_threshold:.3f}"

        # Check 2: Any contradicted claim triggers reflection
        contradicted_count = sum(
            1 for v in verifications if v.status == VerificationStatus.CONTRADICTED
        )
        if contradicted_count > 0:
            return True, f"{contradicted_count}_contradicted_claims_detected"

        # Check 3: Any unsupported/unknown claim triggers reflection
        unknown_count = sum(
            1 for v in verifications if v.status == VerificationStatus.UNKNOWN
        )
        if unknown_count > 0:
            return True, f"{unknown_count}_unsupported_claims_detected"

        # Check 4: If no claims extracted or no verifications, do not trigger reflection
        if not claims or not verifications:
            return False, "no_claims_or_verifications_to_reflect"

        # If all claims are supported and confidence is satisfactory
        return False, "all_claims_supported_and_confident"

    def check_stopping_condition(
        self,
        iteration: int,
        config: ReflectionConfig,
        current_verifications: list[VerificationResult],
        previous_verifications: list[VerificationResult] | None,
        current_confidence: ConfidenceResult | None,
        previous_confidence: ConfidenceResult | None,
        new_answer: str,
        previous_answer: str,
    ) -> tuple[bool, str, bool]:
        """Evaluate deterministic stopping conditions for the current iteration.

        Args:
            iteration: Current iteration index (1-based).
            config: Reflection configuration with max_iterations.
            current_verifications: Verification results for the new answer.
            previous_verifications: Verification results before this iteration.
            current_confidence: Confidence of the new answer if computed.
            previous_confidence: Confidence before this iteration if computed.
            new_answer: Generated answer text in this iteration.
            previous_answer: Answer text prior to this iteration.

        Returns:
            Tuple of (should_stop: bool, reason: str, improved: bool).
        """
        # 1. Check for identical output (no progress / infinite loop guard)
        if new_answer.strip() == previous_answer.strip():
            # If no change was made, stop immediately to prevent cycling
            return True, "regeneration_unchanged", False

        # 2. Check if all claims are now supported
        all_supported = (
            len(current_verifications) > 0
            and all(v.status == VerificationStatus.SUPPORTED for v in current_verifications)
        )
        if all_supported:
            return True, "all_claims_supported", True

        # 3. Check for confidence improvement if confidence is tracked
        improved = False
        if current_confidence is not None and previous_confidence is not None:
            curr_score = (
                current_confidence.calibrated_ecs
                if current_confidence.calibrated_ecs is not None
                else current_confidence.raw_confidence
            )
            prev_score = (
                previous_confidence.calibrated_ecs
                if previous_confidence.calibrated_ecs is not None
                else previous_confidence.raw_confidence
            )
            delta = curr_score - prev_score
            if delta >= config.min_improvement_margin:
                improved = True
                # If confidence reached the acceptable threshold, stop on improvement
                if curr_score >= config.low_confidence_threshold:
                    return True, f"confidence_improved_to_{curr_score:.3f}", True

        # 4. Check support ratio improvement when confidence is not available
        elif previous_verifications is not None:
            prev_supported = sum(
                1 for v in previous_verifications if v.status == VerificationStatus.SUPPORTED
            )
            curr_supported = sum(
                1 for v in current_verifications if v.status == VerificationStatus.SUPPORTED
            )
            curr_contradicted = sum(
                1 for v in current_verifications if v.status == VerificationStatus.CONTRADICTED
            )
            prev_contradicted = sum(
                1 for v in previous_verifications if v.status == VerificationStatus.CONTRADICTED
            )

            # Improved if more supported or fewer contradicted
            if (curr_supported > prev_supported and curr_contradicted <= prev_contradicted) or (
                curr_contradicted < prev_contradicted
            ):
                improved = True

        # 5. Check hard iteration cap
        if iteration >= config.max_iterations:
            return True, "max_iterations_reached", improved

        # Continue loop
        return False, "continue_iteration", improved

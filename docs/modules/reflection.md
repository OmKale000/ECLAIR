# M12 — Self-Reflection & Self-Correction

> Module documentation (Spec §4.8, §M12). Derived only from the authoritative Specification and repository contracts. Authoritative rules: `rules/M12_reflection.md`, `rules/COMMON_RULES.md`, `rules/SHARED_CONTRACTS_REFERENCE.md`.

## 1. Module Purpose (Spec §M12)
Correct responses that fail reliability checks by orchestrating a bounded self-reflection loop before final risk decision-making:
`Generate -> Verify -> Low ECS? -> Critique -> Regenerate -> Verify again`

## 2. Responsibility
- Enforce the low-confidence / weak-claim trigger gate.
- Perform claim-targeted critique on contradicted (`CONTRADICTED`) and ungrounded (`UNKNOWN`) claims.
- Regenerate corrected draft answers via the M02 LLM Gateway (`LLMProvider`).
- Re-extract atomic claims via M03 Claim Extraction (`ClaimExtractor`).
- Re-verify every regenerated claim via M07 Claim Verification (`Verifier`).
- Optionally ground weak claims via M05 RAG (`Retriever`).
- Enforce a deterministic hard iteration cap (`max_iterations`) to strictly prevent infinite loops.
- Stop when reliability improves or when the iteration cap is reached.
- Return the final result containing improved text, fresh claims, updated verification records, and complete iteration history to the engine.

## 3. Module Boundary & Non-Responsibilities
- **Does NOT define, compute, or calibrate confidence or ECS**: Confidence estimation is owned by M10 (`src/eclair/confidence/`) and calibration is owned by M11 (`src/eclair/calibration/`).
- **Does NOT define or apply risk policies**: Risk classification and decision selection (`RETURN`, `ABSTAIN`, `HUMAN_REVIEW`) are owned by M13 (`src/eclair/risk/`).
- **Does NOT own the top-level pipeline**: Pipeline execution and integration orchestration are owned by the engine (`src/eclair/engine/`).
- **Does NOT own persistence, API, SDK, or UI**: Provenance tracking is owned by M14, REST API by M15, SDK by M16, and Dashboard by M17.
- **Does NOT bypass verification**: Absence of evidence remains `UNKNOWN`, never `SUPPORTED`.

## 4. Inputs
The primary entry point `ReflectionController.reflect(...)` accepts:
- `query: Query | str` — The user/application query.
- `answer: str` — The draft answer text requiring reflection.
- `claims: list[Claim]` — The M03 extracted claims for the answer.
- `verifications: list[VerificationResult]` — The M07 verification results for the claims.
- `confidence: ConfidenceResult | None` — Optional M10 raw confidence and/or M11 calibrated ECS.
- `evidence: list[Evidence] | None` — Retrieved supporting evidence passages.

## 5. Outputs
Returns a structured `ReflectionResult` (`src/eclair/reflection/models.py`) containing:
- `original_answer: str` — The initial uncorrected answer.
- `improved_answer: str` — The corrected answer after reflection.
- `final_claims: list[Claim]` — Re-extracted claims from the final answer.
- `final_verifications: list[VerificationResult]` — Verification outcomes for the final claims.
- `final_confidence: ConfidenceResult | None` — Updated confidence if re-estimated.
- `iterations_completed: int` — Total reflection iterations executed (1-based).
- `max_iterations: int` — The configured hard iteration cap.
- `triggered: bool` — Whether reflection was triggered.
- `improved: bool` — Whether reliability/confidence measurably improved.
- `stop_reason: str` — Deterministic reason for termination (`all_claims_supported`, `confidence_improved`, `regeneration_unchanged`, `max_iterations_reached`).
- `history: list[IterationRecord]` — Detailed audit log of every intermediate iteration.

## 6. Control Flow
```
                   Input (Query, Answer, Claims, Verifications, Confidence)
                                          │
                                          ▼
                         [StoppingController.should_trigger]
                                    /           \
                           No (Confident)     Yes (Low ECS / Weak Claims)
                                  │                       │
                                  ▼                       ▼
                        Return unreflected         Iteration 1 .. max_iterations
                                                    │
                                                    ▼
                                          [ResponseCritic.critique]
                                          (Isolates CONTRADICTED/UNKNOWN)
                                                    │
                                                    ▼
                                          [Optional M05 Retrieval]
                                          (Grounded context expansion)
                                                    │
                                                    ▼
                                          [ResponseRewriter.rewrite]
                                          (Via M02 LLM Gateway)
                                                    │
                                                    ▼
                                          [M03 Claim Extraction]
                                          (Fresh atomic claims)
                                                    │
                                                    ▼
                                          [M07 Claim Verification]
                                          (Re-verify each new claim)
                                                    │
                                                    ▼
                                          [StoppingController.check]
                                           /                      \
                                      Should Stop?             Continue?
                                      (Improved / Cap / Same)      │
                                          │                        ▼
                                          ▼                   Next Iteration
                                 Return ReflectionResult
                                 to Engine for Final Decision
```

## 7. Critique Behavior (`ResponseCritic`)
Analyzes `VerificationResult` outcomes per claim:
- `CONTRADICTED`: Flagged as an explicit conflict with verified evidence. Directive: remove statement or invert to align strictly with factual evidence.
- `UNKNOWN`: Flagged as an ungrounded claim lacking evidence. Directive: ground with knowledge-base facts or omit unsupported claims.
- `SUPPORTED`: Preserved as verified factual content.

## 8. Regeneration Behavior (`ResponseRewriter`)
- Formulates a structured prompt detailing the user query, draft answer, claim-targeted critique directives, and verified evidence excerpts.
- Dispatches prompt to the M02 `LLMProvider` using `LLMRequest(prompt=..., model=..., temperature=...)`.
- Enforces strict factual revision rules: contradicted statements are corrected/removed; ungrounded statements are pruned; verified statements are maintained.
- Maps LLM failures to `ModuleError`.

## 9. Re-Verification Behavior
- The regenerated text is immediately submitted to `ClaimExtractor.extract(...)` to obtain fresh atomic claims.
- Each fresh claim is submitted to `Verifier.verify(claim, evidence)`.
- Re-verification guarantees that newly introduced assertions are independently checked. Lack of evidence maps to `UNKNOWN`, never `SUPPORTED`.

## 10. Iteration Limit & Infinite Loop Prevention
- Configured via `ReflectionConfig.max_iterations` (default: 3, minimum: 1).
- Hard iteration cap strictly halts the loop when `iteration >= max_iterations`.
- Infinite loops are guarded against all failure modes:
  - If the rewriter generates identical text (`new_answer == previous_answer`), the loop terminates immediately with `regeneration_unchanged`.
  - If claim extraction or regeneration raises an error, the loop halts and records the failure reason.
  - If verifier encounters an exception, failing claims are safely recorded as `UNKNOWN` rather than causing an unhandled loop crash.

## 11. Stopping Conditions (`StoppingController`)
The reflection loop halts upon the first satisfied condition:
1. `all_claims_supported`: All re-extracted claims achieve `VerificationStatus.SUPPORTED`.
2. `confidence_improved`: Recomputed confidence/ECS improves by at least `min_improvement_margin` and reaches the acceptable threshold.
3. `regeneration_unchanged`: No textual change between iterations.
4. `max_iterations_reached`: Hard iteration cap consumed.

## 12. Error Handling & Validation
- Validates query text, answer text, claims list, and verifications list using `ContractValidationError` from `eclair.exceptions`.
- Reuses `ModuleError` for generation and subsystem errors.
- Never fabricates evidence or confidence scores.

## 13. Subsystem Integration
- **Upstream Modules Reused**:
  - `LLMProvider` (M02) for generation.
  - `ClaimExtractor` (M03) for claim extraction.
  - `Retriever` (M05, optional) for evidence expansion.
  - `Verifier` (M07) for claim verification.
  - `ConfidenceEstimator` (M10, optional) for confidence re-estimation.
- **Downstream Consumer**:
  - `Engine` / `Orchestrator` (`src/eclair/engine/`) consumes `ReflectionResult` to execute final confidence evaluation and invoke M13 `DecisionEngine`.

## 14. Example Input (M01 Contracts)
```python
from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.query import Query
from eclair.contracts.verification import VerificationResult

query = Query(question="What is the refund window for defective electronics?")
answer = "Customers cannot return defective electronics under any circumstances."

c1 = Claim(claim_id="c1", text="Defective electronics cannot be returned.")
v1 = VerificationResult(
    claim_id="c1",
    status=VerificationStatus.CONTRADICTED,
    evidence_ids=["ev_1"],
)
conf = ConfidenceResult(raw_confidence=0.35, calibrated_ecs=0.28)
evidence = [
    Evidence(
        evidence_id="ev_1",
        text="Defective electronic items may be returned within 30 days for a full refund.",
        source="refund_policy.md",
        relevance_score=0.95,
    )
]
```

## 15. Example Output (`ReflectionResult`)
```python
# Result returned by ReflectionController.reflect(...)
ReflectionResult(
    original_answer="Customers cannot return defective electronics under any circumstances.",
    improved_answer="Defective electronic items may be returned within 30 days for a full refund.",
    final_claims=[
        Claim(claim_id="c2", text="Defective electronic items may be returned within 30 days for a full refund.")
    ],
    final_verifications=[
        VerificationResult(
            claim_id="c2",
            status=VerificationStatus.SUPPORTED,
            evidence_ids=["ev_1"],
        )
    ],
    final_confidence=ConfidenceResult(raw_confidence=0.92, calibrated_ecs=0.90),
    iterations_completed=1,
    max_iterations=3,
    triggered=True,
    improved=True,
    stop_reason="all_claims_supported",
    history=[
        IterationRecord(
            iteration=1,
            answer="Defective electronic items may be returned within 30 days for a full refund.",
            claims=[...],
            verifications=[...],
            confidence=...,
            improved=True,
            stop_reason="all_claims_supported",
        )
    ],
)
```

## 16. Verification Suite
Unit tests located in `tests/unit/reflection/`:
- `test_models.py`: Validates model schemas, configuration defaults, field constraints, and immutability.
- `test_critic.py`: Validates detection of `CONTRADICTED` and `UNKNOWN` claims, prompt formatting, and preservation of `SUPPORTED` claims.
- `test_rewriter.py`: Validates LLM prompt formation, parameter forwarding, error mapping, and blank response handling.
- `test_stopping.py`: Validates trigger rules (low confidence, contradicted claims, ungrounded claims) and stopping conditions (`all_claims_supported`, `regeneration_unchanged`, `max_iterations_reached`).
- `test_controller.py`: Validates end-to-end multi-turn loop, optional retriever grounding, verifier error recovery, input validation, and loop termination guarantees.

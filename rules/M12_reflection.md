# M12 — Self-Reflection & Self-Correction — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M12 — Self-Reflection & Self-Correction
IDENTIFIER: M12

PURPOSE:
  Correct responses that fail reliability checks.

RESPONSIBILITY:
  - Loop: Generate -> Verify -> Low ECS? -> Critique -> Regenerate -> Verify again.
  - Enforce iteration limit, low-confidence trigger, claim-targeted correction,
    stop when confidence improves, and prevent infinite loops.

NON-RESPONSIBILITY:
  - Does NOT define confidence/ECS (M10/M11) or the risk policy (M13).
  - Does NOT own the overall pipeline (engine owns it, Spec §4.2).

LOCATION:
  src/eclair/reflection/
EXISTING FOLDERS USED:
  src/eclair/reflection/  (controller.py, critic.py, rewriter.py, stopping.py, models.py)
  tests/unit/reflection/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts; M02 LLM Gateway; M03 Claim Extraction; M05 RAG; M07 Verification;
    (triggered by low ECS from M11 / decision from M13).
  External: none beyond the modules above.
  Configuration: iteration limit + trigger thresholds via M01 config.

INPUTS:
  Source: a low-confidence answer + its claims/verification/ECS.
  Format: M01 contracts.
  Validation: validate inputs; respect iteration limit.

PROCESSING:
  New logic: critique weak claims, retrieve, regenerate, re-verify within the iteration limit.

OUTPUTS:
  Format: improved + re-verified response (M01 contracts).
  Destination: back to engine for final decision.

CONSUMERS:
  Module/service: engine (final decision path).
  Expected contract: improved response with updated verification.

INTEGRATION POINTS:
  APIs used: M02. APIs exposed: reflection controller interface.
  Database: none. Events/Queues: none. Configuration: M01. Auth: via M02.

ERROR HANDLING: use M01 exceptions; MUST prevent infinite loops (hard iteration cap).
VALIDATION RULES: stop when confidence improves or cap reached.
INTEGRATION REQUIREMENTS: triggered only on low confidence; re-verifies before final decision.

DO NOT CHANGE: M01 contracts; M02/M03/M05/M07/M11/M13 folders; any other module.
REUSE RULES: reuse M02/M03/M05/M07; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only critique/rewrite/regenerate/stopping.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: low-confidence correction loop.
  Does NOT handle: confidence/ECS definition, risk policy, pipeline ownership.

VERIFICATION BEFORE COMPLETE:
  - Low-confidence responses are improved and re-verified within the iteration limit.
  - No infinite loops.
  - tests/unit/reflection/ pass; sample input/output; docs/modules/reflection.md written.
```

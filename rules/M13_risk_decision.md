# M13 — Risk & Decision Engine — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M13 — Risk & Decision Engine
IDENTIFIER: M13

PURPOSE:
  Determine the action ECLAIR should take after reliability analysis.

RESPONSIBILITY:
  - Risk-based policy using configurable thresholds.
  - Select one of: Return, Verify more, Regenerate, Abstain, Human review, Block action.

NON-RESPONSIBILITY:
  - Does NOT compute confidence/ECS (M10/M11) or run reflection loops (M12 executes correction).
  - Does NOT persist decisions (M14).

LOCATION:
  src/eclair/risk/
EXISTING FOLDERS USED:
  src/eclair/risk/  (classifier.py, policy.py, thresholds.py, decision.py, models.py)
  tests/unit/risk/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts (DecisionResult, risk contract); M11 calibrated ECS; M10 confidence;
    M08 hallucination; M07 verification.
  External: Python (rule engine initially).
  Configuration: thresholds via M01 config.

INPUTS:
  Source: calibrated ECS (M11) + reliability signals.
  Format: M01 contracts.
  Validation: validate inputs.

PROCESSING:
  New logic: risk-based policy using configurable thresholds mapping ECS/signals to a decision.

OUTPUTS:
  Format: DecisionResult (M01) with one of RETURN / VERIFY_MORE / REGENERATE / ABSTAIN /
    HUMAN_REVIEW / BLOCK_ACTION.
  Destination: consumed by M12 Reflection (on low ECS), engine, M14 Provenance.

CONSUMERS:
  Module/service: M12, engine, M14.
  Expected contract: DecisionResult with a defined action.

INTEGRATION POINTS:
  APIs used: none. APIs exposed: DecisionEngine interface.
  Database: none directly. Events/Queues: none. Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; no invented decision states beyond the six defined.
VALIDATION RULES: decision restricted to the six actions; thresholds from config.
INTEGRATION REQUIREMENTS: turns reliability signals + ECS into an actionable decision, not a score.

DO NOT CHANGE: M01 DecisionResult contract; M10/M11 folders; any other module.
REUSE RULES: reuse config thresholds; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only risk classification + decision selection.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: risk assessment + decision selection.
  Does NOT handle: confidence/calibration, correction execution, persistence.

VERIFICATION BEFORE COMPLETE:
  - Returns actionable decisions (RETURN, ABSTAIN, HUMAN_REVIEW, etc.) from ECS/signals.
  - tests/unit/risk/ pass; sample input/output; docs/modules/risk.md written.
```

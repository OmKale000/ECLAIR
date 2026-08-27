# M08 — Hallucination Detection — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M08 — Hallucination Detection
IDENTIFIER: M08

PURPOSE:
  Detect claims that appear fabricated, unsupported or contradicted.

RESPONSIBILITY:
  - Combine signals: no evidence, contradictory evidence, low semantic support,
    model disagreement, numerical inconsistency.
  - Return hallucination probability, hallucination flag, and reasons for the flag.

NON-RESPONSIBILITY:
  - Does NOT verify claims (M07), compute confidence (M10), or make decisions (M13).

LOCATION:
  src/eclair/hallucination/
EXISTING FOLDERS USED:
  src/eclair/hallucination/  (detector.py, signals.py, scoring.py, models.py)
  tests/unit/hallucination/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts; M07 VerificationResult; M06 evidence signals; M09 consensus signals.
  External: NLI, embeddings, LLM, Python.
  Configuration: via M01 config.

INPUTS:
  Source: verification results (M07), evidence/quality (M06), consensus (M09).
  Format: M01 contracts + module-local signal models.
  Validation: validate inputs.

PROCESSING:
  New logic: combine the listed signals into a structured hallucination result.

OUTPUTS:
  Format: structured hallucination result (probability, flag, reasons) for claims or responses.
  Destination: consumed by M10 Confidence and engine.

CONSUMERS:
  Module/service: M10, engine.
  Expected contract: hallucination probability + flag + reasons.

INTEGRATION POINTS:
  APIs used: M02 (optional LLM signal). APIs exposed: detector interface.
  Database: none. Events/Queues: none. Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; missing signals reduce evidence, never fabricate a result.
VALIDATION RULES: probability in [0,1]; reasons non-empty when flagged.
INTEGRATION REQUIREMENTS: is a signal source for confidence, not a decision maker.

DO NOT CHANGE: M01 contracts; M06/M07/M09 folders; any other module.
REUSE RULES: reuse M07/M06/M09 outputs; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only signal combination + scoring.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: hallucination signal fusion + flagging.
  Does NOT handle: verification, confidence, calibration, decisions.

VERIFICATION BEFORE COMPLETE:
  - Structured hallucination result produced for claims/responses.
  - tests/unit/hallucination/ pass; sample input/output; docs/modules/hallucination.md written.
```

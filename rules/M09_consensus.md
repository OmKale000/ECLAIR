# M09 — Multi-Agent / Multi-Model Consensus — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M09 — Multi-Agent / Multi-Model Consensus
IDENTIFIER: M09

PURPOSE:
  Determine whether independent model outputs agree.

RESPONSIBILITY:
  - Run multiple independent model calls, compare claims or answers,
    calculate an agreement score, and report full or partial consensus.

NON-RESPONSIBILITY:
  - Does NOT treat agreement as proof of truth (Spec §4.6).
  - Does NOT verify claims (M07) or make decisions (M13).

LOCATION:
  src/eclair/consensus/
EXISTING FOLDERS USED:
  src/eclair/consensus/  (runner.py, voting.py, agreement.py, diversity.py, models.py)
  tests/unit/consensus/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts; M02 LLM Gateway.
  External: asyncio, Pydantic.
  Configuration: via M01 config (models to poll).

INPUTS:
  Source: a query/answer/claims to evaluate across models (from engine).
  Format: text/claims + model set.
  Validation: validate inputs.

PROCESSING:
  New logic: start with majority voting and agreement score; later support weighted voting based
    on historical model performance.

OUTPUTS:
  Format: agreement score + full/partial consensus indicator.
  Destination: consumed by M08 Hallucination and M10 Confidence.

CONSUMERS:
  Module/service: M08, M10, engine.
  Expected contract: agreement score as one reliability signal.

INTEGRATION POINTS:
  APIs used: M02 (multiple provider calls). APIs exposed: consensus runner interface.
  Database: none. Events/Queues: none. Configuration: M01. Auth: via M02.

ERROR HANDLING: use M01 exceptions; a failed model call must degrade gracefully, not crash consensus.
VALIDATION RULES: agreement score in valid range.
INTEGRATION REQUIREMENTS: consensus is one signal only, never truth.

DO NOT CHANGE: M01 contracts; M02 interface; any other module.
REUSE RULES: reuse M02; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only multi-model runs + agreement scoring.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: cross-model agreement measurement.
  Does NOT handle: verification, confidence fusion, decisions.

VERIFICATION BEFORE COMPLETE:
  - Multiple model calls run; agreement score + consensus level reported.
  - tests/unit/consensus/ pass; sample input/output; docs/modules/consensus.md written.
```

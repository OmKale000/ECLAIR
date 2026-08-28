# M10 — Confidence Estimation — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M10 — Confidence Estimation
IDENTIFIER: M10

PURPOSE:
  Estimate RAW confidence from available reliability signals.

RESPONSIBILITY:
  - Configurable weighted fusion of verification, evidence, agreement, consistency and
    model-confidence signals.
  - Generate claim confidence and response confidence; return a confidence breakdown;
    keep fusion weights configurable.

NON-RESPONSIBILITY:
  - Does NOT produce calibrated ECS — that is M11 (Spec §4.4).
  - Does NOT make decisions (M13).

LOCATION:
  src/eclair/confidence/
EXISTING FOLDERS USED:
  src/eclair/confidence/  (estimator.py, signals.py, fusion.py, models.py)
  tests/unit/confidence/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts (ConfidenceResult); M07 verification; M06 evidence; M09 consensus;
    M08 hallucination.
  External: Python, NumPy.
  Configuration: fusion weights via M01 config.

INPUTS:
  Source: verification/evidence/agreement/consistency/model-confidence signals.
  Format: M01 contracts + module-local signal models.
  Validation: validate signals.

PROCESSING:
  New logic: configurable weighted fusion of the listed signals.

OUTPUTS:
  Format: ConfidenceResult (M01) — RAW confidence only, with breakdown.
  Destination: consumed by M11 Calibration, M12 Reflection, M13 Risk, engine.

CONSUMERS:
  Module/service: M11, M12, M13, engine.
  Expected contract: RAW confidence (explicitly NOT calibrated ECS).

INTEGRATION POINTS:
  APIs used: none. APIs exposed: ConfidenceEstimator.calculate(signals)->ConfidenceResult.
  Database: none. Events/Queues: none. Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; missing signals handled per configurable weights, not invented.
VALIDATION RULES: confidence in [0,1]; output labeled as raw.
INTEGRATION REQUIREMENTS: output must remain raw until M11 calibrates it.

DO NOT CHANGE: M01 ConfidenceResult contract; M11 folder; any other module.
REUSE RULES: reuse upstream signals; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only signal fusion into raw confidence.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: raw confidence estimation.
  Does NOT handle: calibration, decisions.

VERIFICATION BEFORE COMPLETE:
  - Produces raw claim + response confidence with breakdown; weights configurable.
  - Output is NOT claimed to be calibrated ECS.
  - tests/unit/confidence/ pass; sample input/output; docs/modules/confidence.md written.
```

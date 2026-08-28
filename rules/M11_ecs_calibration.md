# M11 — ECS Calibration — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M11 — ECS Calibration
IDENTIFIER: M11

PURPOSE:
  Convert raw confidence into a statistically meaningful Epistemic Confidence Score (ECS).

RESPONSIBILITY:
  - Input raw confidence and observed correctness.
  - Produce calibrated ECS.
  - Calculate ECE and Brier Score.
  - Generate calibration curves / reliability diagrams.

NON-RESPONSIBILITY:
  - Does NOT estimate raw confidence (M10) or make decisions (M13).

LOCATION:
  src/eclair/calibration/
EXISTING FOLDERS USED:
  src/eclair/calibration/  (calibrator.py, isotonic.py, temperature.py, metrics.py,
                            reliability.py, models.py)
  tests/unit/calibration/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts; M10 raw ConfidenceResult; observed correctness from M18/M14.
  External: scikit-learn, NumPy, Pandas, Matplotlib.
  Configuration: via M01 config.

INPUTS:
  Source: raw confidence (M10) + observed correctness labels.
  Format: M01 contracts + arrays of (confidence, correctness).
  Validation: validate inputs.

PROCESSING:
  New logic: start with Platt/sigmoid scaling and isotonic regression; use reliability diagrams
    to inspect calibration quality.

OUTPUTS:
  Format: calibrated ECS + ECE + Brier Score + calibration/reliability diagrams.
  Destination: consumed by M13 Risk, engine, M17 Dashboard (via engine), M18 Evaluation.

CONSUMERS:
  Module/service: M13, engine, M18.
  Expected contract: calibrated ECS (distinct from raw confidence).

INTEGRATION POINTS:
  APIs used: none. APIs exposed: calibrator interface.
  Database: none directly. Events/Queues: none. Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; do not claim calibration without observed correctness (Spec §4.4).
VALIDATION RULES: ECS in [0,1]; metrics computed on valid label sets.
INTEGRATION REQUIREMENTS: only after calibration+benchmark validation may ECLAIR make a stronger
  statement about how ECS relates to observed correctness.

DO NOT CHANGE: M01 contracts; M10 folder; any other module.
REUSE RULES: reuse scikit-learn; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only calibration + calibration metrics/diagrams.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: raw confidence -> calibrated ECS + calibration metrics.
  Does NOT handle: raw estimation, decisions.

VERIFICATION BEFORE COMPLETE:
  - Raw confidence (e.g. 0.90) maps to a calibrated ECS after evaluation.
  - ECE, Brier, and reliability diagrams produced.
  - tests/unit/calibration/ pass; sample input/output; docs/modules/calibration.md written.
```

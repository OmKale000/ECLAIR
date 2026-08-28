# M10 — Confidence Estimation

> Module documentation (Spec §4.8). Derived only from the Spec (§M10, §4.4) and the repo.
> Authoritative rules: `rules/M10_confidence_estimation.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M10
- **Name:** Confidence Estimation
- **Folder:** `src/eclair/confidence/`
- **Tests:** `tests/unit/confidence/`

## Purpose (Spec §M10)
Estimate raw confidence from available reliability signals.

## Responsibility
Fuse reliability signals into raw claim confidence and raw response confidence, and return a
confidence breakdown, with configurable fusion weights.

## Non-responsibility
- Does NOT calibrate — **raw confidence is not calibrated ECS (Spec §4.4)**. Calibration is M11.
- Does NOT make the risk decision (M13).

## Files (Spec §M10)
```
src/eclair/confidence/  estimator.py  signals.py  fusion.py  models.py
```

## Technology (Spec §M10)
Python, NumPy.

## Method (Spec §M10)
Configurable weighted fusion of verification, evidence, agreement, consistency and model-confidence
signals.

## Required functionality (Spec §M10)
- Generate claim confidence.
- Generate response confidence.
- Return confidence breakdown.
- Keep fusion weights configurable.

## Inputs / Outputs
- **Input:** reliability signals — verification (M07), evidence quality (M06), agreement (M09),
  consistency, and model confidence.
- **Output:** `ConfidenceResult` (M01), **raw** confidence only. Interface:
  `ConfidenceEstimator.calculate(signals) -> ConfidenceResult` (Spec §4.1, §4.3).
- **Consumers:** M11 Calibration, M13 Risk/Decision, M12 Reflection, engine.

## Reliability semantic (Spec §4.4)
```
Raw confidence -> Calibration + benchmark correctness -> Calibrated ECS
```
M10 produces raw confidence only. It is **not** called a calibrated ECS at this stage. Only after
calibration (M11) and benchmark validation may ECLAIR make a stronger statement about how its ECS
relates to observed correctness.

## Dependencies
- Internal: M01 contracts (`ConfidenceResult`); signals from M06, M07, M09.
- External: NumPy.

## Configuration
Fusion weights are configurable via the M01 config mechanism; do not hardcode weights.

## Do not change
M01 `ConfidenceResult` contract; any other module folder.

## Expected outcome (Spec §M10)
Produces raw confidence only. It is not called calibrated ECS at this stage.

## Verification before complete (Spec §4.8)
- Claim + response confidence and a breakdown are produced; fusion weights are configurable.
- Output is clearly raw (not labeled calibrated ECS).
- `tests/unit/confidence/` pass; sample input/output provided.

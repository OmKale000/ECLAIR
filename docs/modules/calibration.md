# M11 — ECS Calibration

> Module documentation (Spec §4.8). Derived only from the Spec (§M11, §4.4) and the repo.
> Authoritative rules: `rules/M11_ecs_calibration.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M11
- **Name:** ECS Calibration
- **Folder:** `src/eclair/calibration/`
- **Tests:** `tests/unit/calibration/`

## Purpose (Spec §M11)
Convert raw confidence into a statistically meaningful Epistemic Confidence Score (ECS).

## Responsibility
Calibrate raw confidence against observed correctness, produce a calibrated ECS, and compute
calibration quality metrics and reliability diagrams.

## Non-responsibility
- Does NOT fuse raw signals (M10) or make the risk decision (M13).

## Files (Spec §M11)
```
src/eclair/calibration/  calibrator.py  isotonic.py  temperature.py  metrics.py  reliability.py  models.py
```

## Technology (Spec §M11)
scikit-learn, NumPy, Pandas, Matplotlib.

## Method (Spec §M11)
Start with Platt/sigmoid scaling and isotonic regression; use reliability diagrams to inspect
calibration quality.

## Required functionality (Spec §M11)
- Input raw confidence and observed correctness.
- Produce calibrated ECS.
- Calculate ECE (Expected Calibration Error).
- Calculate Brier Score.
- Generate calibration curves / reliability diagrams.

## Inputs / Outputs
- **Input:** raw confidence (M10 `ConfidenceResult`) + observed correctness.
- **Output:** calibrated ECS (the calibrated form of `ConfidenceResult`) + calibration metrics
  (ECE, Brier) + reliability diagrams.
- **Consumers:** M13 Risk/Decision (branches on ECS), engine, M18 Evaluation.

## Reliability semantic (Spec §4.4)
Only M11 produces a calibrated ECS, and only after calibration against observed correctness. Example
from the Spec: a raw confidence of 0.90 can become a calibrated ECS of 0.73 after evaluation and
calibration.

## Dependencies
- Internal: M01 contracts; M10 raw confidence.
- External: scikit-learn (Platt/isotonic), NumPy, Pandas, Matplotlib.

## Do not change
M01 `ConfidenceResult` contract; M10 folder; any other module folder.

## Expected outcome (Spec §M11)
Raw confidence such as 0.90 can become a calibrated ECS such as 0.73 after evaluation and calibration.

## Verification before complete (Spec §4.8)
- Calibrated ECS is produced from raw confidence + observed correctness; ECE and Brier computed;
  reliability diagrams generated.
- `tests/unit/calibration/` pass; sample input/output provided.

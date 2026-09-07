# M11 — ECS Calibration

> Module documentation (Spec §4.8, §M11, §4.4).
> Authoritative rules: `rules/M11_ecs_calibration.md`, `rules/COMMON_RULES.md`, `rules/SHARED_CONTRACTS_REFERENCE.md`.

## 1. Identity
- **Module ID:** M11
- **Module Name:** ECS Calibration
- **Package Location:** `src/eclair/calibration/`
- **Unit Tests:** `tests/unit/calibration/`

## 2. Purpose (Spec §M11)
Convert raw fused confidence produced by M10 into a statistically meaningful **Epistemic Confidence Score (ECS)** calibrated against empirical correctness, calculate calibration error metrics (ECE, Brier Score, MCE), and generate structured reliability diagrams.

## 3. Responsibilities
- Accept raw confidence scores (floats, `ConfidenceResult`, `ClaimConfidenceResult`, `ResponseConfidenceResult`).
- Accept observed empirical binary correctness labels ($0$ or $1$, `False` or `True`).
- Validate all calibration inputs strictly at the boundary.
- Support Platt / Sigmoid parametric scaling (`PlattCalibrator`).
- Support Isotonic non-parametric monotonic regression (`IsotonicCalibrator`).
- Support Temperature scaling (`TemperatureCalibrator`).
- Produce calibrated ECS values bounded strictly in $[0.0, 1.0]$.
- Calculate Expected Calibration Error (ECE) across confidence bins.
- Calculate Brier Score (mean squared error).
- Calculate Maximum Calibration Error (MCE).
- Generate structured reliability diagram and calibration curve data (`ReliabilityDiagramData`).
- Populate the canonical `ConfidenceResult.calibrated_ecs` contract.

## 4. Non-Responsibilities
- Does **NOT** estimate raw confidence or fuse signals (owned by M10).
- Does **NOT** perform claim verification or NLI (owned by M07).
- Does **NOT** detect hallucinations (owned by M08).
- Does **NOT** make risk policies or final operational decisions (owned by M13).
- Does **NOT** implement REST endpoints or Streamlit UI components (owned by M15/M17).
- Does **NOT** persist provenance to database (owned by M14).

## 5. Core Reliability Invariant (Spec §4.4)
> **Raw confidence is NOT calibrated ECS.**
> Calibrated ECS is produced **only by M11**, and **only after fitting against empirical observed correctness**.
> Attempting to claim calibrated ECS without training data raises a `ModuleError`.
> 
> Example: A raw confidence of $0.90$ from M10 can become a calibrated ECS of $0.73$ after evaluation and calibration against observed ground truth.

## 6. Conceptual Distinctions

| Metric / Term | Definition | Role |
| :--- | :--- | :--- |
| **Raw Confidence** | Fused reliability signals $\in [0.0, 1.0]$ produced by M10. | Uncalibrated score representing heuristic signal fusion. |
| **Calibrated ECS** | Statistically adjusted confidence $\in [0.0, 1.0]$ produced by M11. | Reflects true empirical probability of correctness. |
| **ECE (Expected Calibration Error)** | Weighted average difference $\sum \frac{\|B_m\|}{N} \|\text{acc}(B_m) - \text{conf}(B_m)\|$. | Measures global calibration misalignment (lower is better). |
| **Brier Score** | Mean squared error $\frac{1}{N} \sum (p_i - y_i)^2$. | Combined measure of calibration and sharpness (lower is better). |
| **MCE (Maximum Calibration Error)** | Maximum bin error $\max_m \|\text{acc}(B_m) - \text{conf}(B_m)\|$. | Worst-case calibration error across bins. |

## 7. Architecture & Files
```
src/eclair/calibration/
├── __init__.py           # Public module interface and exports
├── calibrator.py         # High-level ECSCalibrator facade
├── isotonic.py           # Non-parametric isotonic regression calibrator
├── temperature.py        # Platt / Sigmoid and Temperature scaling calibrators
├── metrics.py            # ECE, Brier score, and MCE calculation functions
├── reliability.py        # Reliability diagram data structures and plotting
└── models.py             # Pydantic data models and schemas
```

## 8. Calibration Algorithms

### A. Platt / Sigmoid Scaling (`PlattCalibrator`)
Fits a parametric logistic sigmoid model mapping logits of raw confidence to empirical correctness:
$$P(y=1 \mid p) = \sigma(a \cdot \text{logit}(p) + b)$$

### B. Isotonic Regression (`IsotonicCalibrator`)
Fits a non-parametric piecewise constant monotonic function minimizing squared error:
$$\min \sum (y_i - \hat{p}_i)^2 \quad \text{subject to } \hat{p}_i \le \hat{p}_j \text{ for } p_i \le p_j$$

### C. Temperature Scaling (`TemperatureCalibrator`)
Learns a single temperature parameter $T > 0$ optimizing negative log-likelihood:
$$P_{\text{cal}}(p) = \sigma\left(\frac{\text{logit}(p)}{T}\right)$$

## 9. Input Validation & Error Handling
- Inputs must be non-empty paired sequences of confidences and labels.
- Lengths must match exactly; otherwise `ContractValidationError` is raised.
- Confidences must be numeric floats in $[0.0, 1.0]$.
- Labels must be binary ($0$ or $1$, `False` or `True`).
- Calling `calibrate()` before `fit()` raises `ModuleError(code="calibrator_not_fitted")`.

## 10. Sample Usage

```python
from eclair.calibration import ECSCalibrator
from eclair.contracts.confidence import ConfidenceResult

# 1. Training data (raw confidence scores and observed correctness labels)
train_confidences = [0.20, 0.40, 0.60, 0.80, 0.90, 0.95]
train_labels = [0, 0, 1, 1, 1, 1]

# 2. Initialize and fit ECS Calibrator
calibrator = ECSCalibrator(method="platt")
calibrator.fit(train_confidences, train_labels)

# 3. Calibrate M10 raw confidence
raw_result = ConfidenceResult(raw_confidence=0.90)
calibrated_result = calibrator.calibrate_result(raw_result)

print(f"Raw Confidence: {calibrated_result.raw_confidence}")
print(f"Calibrated ECS: {calibrated_result.calibrated_ecs}")

# 4. Evaluate calibration metrics on test data
test_confidences = [0.25, 0.55, 0.85]
test_labels = [0, 1, 1]
metrics = calibrator.evaluate(test_confidences, test_labels, n_bins=5)

print(f"ECE: {metrics.ece:.4f}")
print(f"Brier Score: {metrics.brier_score:.4f}")
```

## 11. Testing
Run M11 unit tests:
```bash
pytest tests/unit/calibration
```
Or run the full test suite:
```bash
pytest
```
Linting:
```bash
ruff check src/eclair/calibration tests/unit/calibration
```

## 12. Integration Flow
```
M10 Confidence Result (raw_confidence) + Observed Correctness (M18/Evaluation/Lineage)
                        │
                        ▼
                M11 ECS Calibration
      (Platt / Isotonic / Temperature / Metrics)
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
  Calibrated ECS       ECE &       Reliability
(ConfidenceResult)  Brier Score   Diagram Data
        │               │               │
        ▼               ▼               ▼
   M13 Decision   M18 Benchmark   M17 Dashboard
```

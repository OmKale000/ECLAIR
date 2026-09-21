# M13 — Risk & Decision Engine

> Module documentation (Spec §4.8). Derived only from the Spec (§M13, §5) and the repo. Authoritative
> rules: `rules/M13_risk_decision.md`, `rules/COMMON_RULES.md`, `rules/SHARED_CONTRACTS_REFERENCE.md`.

## 1. Identity
- **ID:** M13
- **Name:** Risk & Decision Engine
- **Folder:** `src/eclair/risk/`
- **Tests:** `tests/unit/risk/`

## 2. Purpose (Spec §M13)
Determine the action ECLAIR should take after reliability analysis.
M13 converts calibrated Epistemic Confidence Scores (ECS) and upstream reliability signals into exactly one actionable decision.

## 3. Responsibilities
- Evaluate pre-computed calibrated ECS (M11) and reliability signals from upstream modules (M06, M07, M08, M09).
- Compute composite risk score ($[0.0, 1.0]$) and categorize qualitative risk levels (`low`, `medium`, `high`, `critical`).
- Apply configurable threshold-based policy cascade mapping signals to an operational decision.
- Select exactly one of the six frozen `DecisionAction` enum members.
- Return validated M01 `RiskResult` and `DecisionResult` contracts.
- Conform to the frozen `DecisionEngine` Protocol (`contracts/interfaces.py`).

## 4. Non-Responsibilities
- Does **NOT** compute raw confidence (responsibility of M10 Confidence Estimation).
- Does **NOT** calibrate confidence or compute Epistemic Confidence Scores (responsibility of M11 ECS Calibration).
- Does **NOT** execute reflection loops, rewrite answers, or call critics (responsibility of M12 Self-Reflection).
- Does **NOT** persist decisions or provenance audit logs (responsibility of M14 Provenance & Database).
- Does **NOT** orchestrate the overall reliability pipeline (responsibility of the Engine/Orchestrator).
- Does **NOT** expose REST API endpoints (M15) or SDK wrappers (M16).

---

## 5. Architecture & Files

```text
src/eclair/risk/
  ├── models.py       # RiskLevel, RiskSignals, RiskAssessmentResult
  ├── thresholds.py   # RiskThresholds, load_risk_thresholds, default constants
  ├── classifier.py   # RiskClassifier (evaluates signals -> RiskResult)
  ├── policy.py       # DecisionPolicy (evaluates signals + risk -> DecisionResult)
  ├── decision.py     # RiskDecisionEngine / DecisionEngine facade (Protocol implementation)
  └── __init__.py     # Module exports
```

### Component Breakdown

1. **`models.py`**:
   - `RiskLevel`: String enum with members `LOW = "low"`, `MEDIUM = "medium"`, `HIGH = "high"`, `CRITICAL = "critical"`.
   - `RiskSignals`: Validated Pydantic container for all reliability inputs (calibrated ECS, verifications, hallucination probability, agreement score, evidence conflict, unsafe action flag, escalation flag, iteration count). Automatically synchronizes nested contract attributes from `ConfidenceResult` and `HallucinationResult`.
   - `RiskAssessmentResult`: Composite result containing M01 `RiskResult`, M01 `DecisionResult`, evaluated signals, explanatory reasons, and policy rule identifier.

2. **`thresholds.py`**:
   - `RiskThresholds`: Validated Pydantic model enforcing boundary constraints ($[0.0, 1.0]$) and logical ordering (`low_ecs <= high_ecs`, `medium_risk <= high_risk <= critical_risk`).
   - `load_risk_thresholds()`: Reads environment variables (`ECLAIR_RISK_*`) with safe fallbacks and validates them via M01 `ConfigurationError`.

3. **`classifier.py`**:
   - `RiskClassifier`: Assesses risk from calibrated ECS uncertainty ($1.0 - \text{ECS}$), verification contradictions, unverified claims ratio, hallucination probabilities, consensus disagreement, and safety flags.
   - Produces M01 `RiskResult(risk_level=..., risk_score=...)`.

4. **`policy.py`**:
   - `DecisionPolicy`: Executes the deterministic decision cascade mapping signals and risk to one of the six frozen decision actions.

5. **`decision.py`**:
   - `RiskDecisionEngine` (aliased as `DecisionEngine`): Main entry point implementing `eclair.contracts.interfaces.DecisionEngine`:
     ```python
     def decide(self, signals: Any = None, **kwargs: Any) -> DecisionResult
     ```
   - Normalizes input from `RiskSignals`, `ConfidenceResult`, dictionaries, floats, or keyword arguments.

---

## 6. Six Frozen Decision Actions (Spec §M13, SHARED_CONTRACTS_REFERENCE §2)

| Decision Action | Conceptual Meaning | Decision Trigger Condition |
| :--- | :--- | :--- |
| `RETURN` | Return the final answer as trusted. | Calibrated ECS $\ge \text{high\_ecs\_threshold}$, risk level is `low`, no contradicted claims, and no hallucination. |
| `VERIFY_MORE` | Request additional evidence retrieval. | Verified claims have `UNKNOWN` status (no supporting evidence found), iteration count is 0, and no severe contradiction. |
| `REGENERATE` | Route to reflection loop for correction. | Calibrated ECS is low, or claims have contradictions/hallucinations, and reflection iteration count $< \text{max\_reflection\_iterations}$. |
| `ABSTAIN` | Withhold answer; do not provide untrusted text. | Calibrated ECS remains low or unsupported after reflection iteration limit is reached ($\ge \text{max\_reflection\_iterations}$). |
| `HUMAN_REVIEW` | Escalate for manual human oversight. | High risk classification or explicit `escalate_to_human` flag set. |
| `BLOCK_ACTION` | Prevent unsafe or malicious execution. | Explicit `unsafe_action` flag set or critical risk classification ($\text{risk\_score} \ge \text{critical\_risk\_threshold}$). |

---

## 7. Decision Policy Evaluation Cascade (Spec §5)

The policy evaluates incoming signals using the following deterministic cascade:

1. **Safety Check:** If `unsafe_action` is `True` or `risk_level == "critical"`:
   $$\longrightarrow \mathbf{BLOCK\_ACTION}$$
2. **Explicit Escalation:** If `escalate_to_human` is `True`:
   $$\longrightarrow \mathbf{HUMAN\_REVIEW}$$
3. **Reflection Exhaustion:** If `iteration_count >= max_reflection_iterations` and confidence is low or claims are ungrounded:
   $$\longrightarrow \mathbf{ABSTAIN}$$
4. **High Risk Oversight:** If `risk_level == "high"` (prior to iteration exhaustion):
   $$\longrightarrow \mathbf{HUMAN\_REVIEW}$$
5. **High Confidence Acceptance:** If $\text{ECS} \ge \text{high\_ecs\_threshold}$ and `risk_level == "low"` without contradictions or hallucinations:
   $$\longrightarrow \mathbf{RETURN}$$
6. **Verification Deficit:** If verified claims have `UNKNOWN` status and `iteration_count == 0`:
   $$\longrightarrow \mathbf{VERIFY\_MORE}$$
7. **Correction Trigger:** If $\text{ECS} < \text{high\_ecs\_threshold}$, contradiction, or hallucination exists:
   $$\longrightarrow \mathbf{REGENERATE}$$
8. **Fallback:** Otherwise:
   $$\longrightarrow \mathbf{ABSTAIN}$$

---

## 8. Configuration & Environment Variables

Thresholds are configurable without code modifications:

| Setting | Default | Environment Variable | Description |
| :--- | :--- | :--- | :--- |
| `high_ecs_threshold` | `0.70` | `ECLAIR_RISK_HIGH_ECS_THRESHOLD` | Calibrated ECS threshold for high-confidence `RETURN`. |
| `low_ecs_threshold` | `0.40` | `ECLAIR_RISK_LOW_ECS_THRESHOLD` | Threshold below which confidence triggers reflection or abstention. |
| `hallucination_threshold` | `0.50` | `ECLAIR_RISK_HALLUCINATION_THRESHOLD` | Probability threshold for hallucination flag. |
| `critical_risk_threshold` | `0.80` | `ECLAIR_RISK_CRITICAL_RISK_THRESHOLD` | Score at or above which risk level is `critical`. |
| `high_risk_threshold` | `0.60` | `ECLAIR_RISK_HIGH_RISK_THRESHOLD` | Score at or above which risk level is `high`. |
| `medium_risk_threshold` | `0.30` | `ECLAIR_RISK_MEDIUM_RISK_THRESHOLD` | Score at or above which risk level is `medium`. |
| `min_agreement_threshold` | `0.50` | `ECLAIR_RISK_MIN_AGREEMENT_THRESHOLD` | Model consensus agreement baseline. |
| `max_unknown_ratio` | `0.50` | `ECLAIR_RISK_MAX_UNKNOWN_RATIO` | Max fraction of `UNKNOWN` claims before `VERIFY_MORE`. |
| `max_contradicted_claims` | `0` | `ECLAIR_RISK_MAX_CONTRADICTED_CLAIMS` | Max tolerated contradictions for `RETURN`. |
| `max_reflection_iterations` | `3` | `ECLAIR_RISK_MAX_REFLECTION_ITERATIONS` | Iteration limit for M12 correction loops. |

---

## 9. Error Handling & Input Validation

- Input dictionaries and models are validated via Pydantic v2.
- Out-of-bounds or malformed contracts raise `ContractValidationError` (M01).
- Unsupported input types raise `ModuleError` (M01).
- Invalid environment variables raise `ConfigurationError` (M01).
- Decision output is strictly constrained to the six frozen `DecisionAction` enum members.

---

## 10. Integration Contract

```text
  M10 Confidence (raw)
        │
  M11 Calibration (calibrated ECS)
        │
  M07 Verification (VerificationResult)
  M08 Hallucination (HallucinationResult)
  M09 Consensus (ConsensusLevel, agreement)
  M06 Evidence Quality (conflict score)
        │
        ▼
  M13 Risk & Decision Engine
  [DecisionEngine.decide(signals) -> DecisionResult]
        │
        ├── RiskResult (M01 contracts/risk.py)
        └── DecisionResult (M01 contracts/decision.py)
              │
              ├── High ECS ──────────────► Engine (return answer to user)
              ├── Low ECS / Correction ──► M12 Reflection (critique / rewrite)
              ├── Escalation ────────────► Engine (route to human review)
              └── Audit / Provenance ────► M14 Database (persist lineage)
```

---

## 11. Sample Input & Output

### Sample Input

```python
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.enums import VerificationStatus
from eclair.contracts.verification import VerificationResult
from eclair.risk.models import RiskSignals

# Input assembled by engine from upstream reliability modules
signals = RiskSignals(
    confidence_result=ConfidenceResult(
        raw_confidence=0.88,
        calibrated_ecs=0.82,
    ),
    verifications=[
        VerificationResult(
            claim_id="claim_001",
            status=VerificationStatus.SUPPORTED,
            evidence_ids=["ev_101", "ev_102"],
        ),
    ],
    hallucination_probability=0.08,
    is_hallucination=False,
    agreement_score=0.92,
)
```

### Sample Output

```python
from eclair.risk.decision import DecisionEngine

engine = DecisionEngine()
assessment = engine.evaluate(signals)

# M01 RiskResult
print(assessment.risk)
# RiskResult(risk_level='low', risk_score=0.108)

# M01 DecisionResult
print(assessment.decision)
# DecisionResult(
#     action=<DecisionAction.RETURN: 'RETURN'>,
#     reason='Calibrated ECS (0.82) satisfies high threshold (0.70) with low risk.'
# )
```

---

## 12. Unit Test Coverage

Comprehensive unit tests live in `tests/unit/risk/`:
- `test_risk_models.py`: Model creation, bounds validation, nested sync, extra fields forbidden, verification metrics.
- `test_risk_thresholds.py`: Default threshold values, invariant ordering, env var overrides, error handling on invalid configs.
- `test_risk_classifier.py`: Signal weighting, risk scores, risk levels (`low`, `medium`, `high`, `critical`), unsafe action overrides.
- `test_risk_policy.py`: All six decision actions (`RETURN`, `VERIFY_MORE`, `REGENERATE`, `ABSTAIN`, `HUMAN_REVIEW`, `BLOCK_ACTION`), threshold boundaries.
- `test_decision_engine.py`: `DecisionEngine` protocol compliance, input normalization (contracts, dicts, kwargs), non-modification of ECS, error handling.

# M10 — Confidence Estimation

> Module documentation (Spec §4.8). Derived only from the Spec (§M10, §4.4) and the repository rules.
> Authoritative rules: `rules/M10_confidence_estimation.md`, `rules/COMMON_RULES.md`, `rules/SHARED_CONTRACTS_REFERENCE.md`.

---

## 1. Identity & Purpose
- **Module ID:** `M10`
- **Module Name:** `Confidence Estimation`
- **Module Folder:** `src/eclair/confidence/`
- **Test Folder:** `tests/unit/confidence/`
- **Purpose:** Estimate **RAW confidence** in $[0.0, 1.0]$ from available reliability signals.

---

## 2. Responsibilities & Non-Responsibilities

### Responsibilities
1. **Configurable Weighted Fusion:** Fuse 5 core reliability signals (verification, evidence quality, agreement, consistency, model confidence).
2. **Claim-Level Confidence:** Calculate raw confidence per atomic claim (`ClaimConfidenceResult`).
3. **Response-Level Confidence:** Aggregate claim confidences or compute response-level raw confidence (`ResponseConfidenceResult`).
4. **Transparent Breakdown:** Provide a detailed `ConfidenceBreakdown` detailing signal contributions, effective weights, and missing signals.
5. **Configurable Weights:** Support configurable nominal weights via `ConfidenceFusionConfig`.
6. **M01 Contract Conformance:** Output `ConfidenceResult(raw_confidence=..., calibrated_ecs=None)`.

### Non-Responsibilities
- **Does NOT perform calibration:** Raw confidence is explicitly **NOT** a calibrated Epistemic Confidence Score (ECS). Calibration (Platt scaling, isotonic regression, ECE, Brier score) is strictly owned by **M11 ECS Calibration** (Spec §4.4).
- **Does NOT make risk decisions:** Return/Abstain/Human Review/Block decisions belong strictly to **M13 Risk & Decision Engine**.
- **Does NOT perform claim verification or retrieval:** RAG is M05, Evidence Quality is M06, Verification is M07.

---

## 3. The 5 Core Reliability Signals

| Signal | Source | Representation in M10 | Description |
| :--- | :--- | :--- | :--- |
| **Verification** | M07 Claim Verification | `verification_score` $\in [0, 1]$ | Derived from NLI verification status (`SUPPORTED` $\approx 0.95$, `CONTRADICTED` $\approx 0.05$, `UNKNOWN` $\approx 0.30$). |
| **Evidence** | M06 Evidence Quality | `evidence_score` $\in [0, 1]$ | Composite score accounting for relevance, source authority, freshness, completeness, and penalizing evidence conflicts. |
| **Agreement** | M09 Consensus | `agreement_score` $\in [0, 1]$ | Cross-model agreement score. Agreement is a reliability signal, not proof of truth (Spec §4.6). |
| **Consistency** | M08 / Evidence | `consistency_score` $\in [0, 1]$ | Logical and numerical consistency (derived from $1.0 - \text{hallucination\_probability}$ or conflict scores). |
| **Model Confidence** | LLM Gateway / Output | `model_confidence_score` $\in [0, 1]$ | Direct self-reported or exponentiated average token log-probability confidence. |

---

## 4. Weighted Fusion & Missing Signal Handling

### Nominal Default Weights
- `weight_verification`: $0.35$
- `weight_evidence`: $0.25$
- `weight_agreement`: $0.15$
- `weight_consistency`: $0.15$
- `weight_model_confidence`: $0.10$

### Weight Renormalization Formula
When a subset $\mathcal{A} \subseteq \text{Signals}$ of signals is available and $\mathcal{M} = \text{Signals} \setminus \mathcal{A}$ are missing:
1. Missing signals are **never fabricated** or silently treated as observed truths.
2. Effective weights are normalized over available signals:
   $$\text{effective\_weight}_i = \frac{w_i}{\sum_{j \in \mathcal{A}} w_j} \quad \forall i \in \mathcal{A}$$
3. Raw confidence is computed via weighted linear combination:
   $$\text{raw\_confidence} = \sum_{i \in \mathcal{A}} \text{effective\_weight}_i \cdot s_i$$
4. Output is strictly bounded in $[0.0, 1.0]$:
   $$\text{raw\_confidence} = \max(0.0, \min(1.0, \text{raw\_confidence}))$$

---

## 5. Module Architecture & Files

```
src/eclair/confidence/
├── __init__.py       # Public module exports and constants
├── models.py         # ConfidenceSignals, SignalContribution, ConfidenceBreakdown, ClaimConfidenceResult, ResponseConfidenceResult, ConfidenceFusionConfig
├── signals.py        # Upstream signal extraction and normalization helpers
├── fusion.py         # ConfidenceFuser: mathematical fusion and NumPy aggregation
└── estimator.py      # ConfidenceEstimator: implements ConfidenceEstimator Protocol
```

---

## 6. Sample Input & Output

### Sample Input
```python
from eclair.contracts.claim import Claim, ClaimType
from eclair.contracts.verification import VerificationResult, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.confidence import ConfidenceEstimator, ConfidenceFusionConfig

estimator = ConfidenceEstimator()

# Claim from generated response
claim = Claim(
    text="Standard refunds are processed within 14 calendar days.",
    claim_type=ClaimType.NUMERIC,
)

# Verified by M07
verification = VerificationResult(
    claim_id=claim.claim_id,
    status=VerificationStatus.SUPPORTED,
    evidence_ids=["ev_101"],
)

# Evidence from M05/M06
evidence = [
    Evidence(
        evidence_id="ev_101",
        text="Eligible refunds will be credited back within 14 days of receipt.",
        source="refund_policy.md",
        relevance_score=0.95,
    )
]

# Estimate claim confidence with consensus agreement
claim_conf = estimator.estimate_claim_confidence(
    claim=claim,
    verification=verification,
    evidence=evidence,
    agreement_score=0.90,
    consistency_score=0.95,
    model_confidence=0.85,
)
```

### Sample Output
```json
{
  "claim_id": "c7a8b9e0f1...",
  "raw_confidence": 0.925,
  "breakdown": {
    "total_raw_confidence": 0.925,
    "available_signals": [
      "verification",
      "evidence",
      "agreement",
      "consistency",
      "model_confidence"
    ],
    "missing_signals": [],
    "effective_weights": {
      "verification": 0.35,
      "evidence": 0.25,
      "agreement": 0.15,
      "consistency": 0.15,
      "model_confidence": 0.10
    },
    "contributions": {
      "verification": {
        "signal_name": "verification",
        "raw_value": 0.95,
        "configured_weight": 0.35,
        "effective_weight": 0.35,
        "weighted_contribution": 0.3325,
        "is_available": true
      },
      "evidence": {
        "signal_name": "evidence",
        "raw_value": 0.95,
        "configured_weight": 0.25,
        "effective_weight": 0.25,
        "weighted_contribution": 0.2375,
        "is_available": true
      },
      "agreement": {
        "signal_name": "agreement",
        "raw_value": 0.90,
        "configured_weight": 0.15,
        "effective_weight": 0.15,
        "weighted_contribution": 0.135,
        "is_available": true
      },
      "consistency": {
        "signal_name": "consistency",
        "raw_value": 0.95,
        "configured_weight": 0.15,
        "effective_weight": 0.15,
        "weighted_contribution": 0.1425,
        "is_available": true
      },
      "model_confidence": {
        "signal_name": "model_confidence",
        "raw_value": 0.85,
        "configured_weight": 0.10,
        "effective_weight": 0.10,
        "weighted_contribution": 0.085,
        "is_available": true
      }
    }
  }
}
```

### Shared Contract Output (`ConfidenceResult`)
```python
contract_result = estimator.calculate(claim_conf)
# Returns:
# ConfidenceResult(
#     raw_confidence=0.925,
#     calibrated_ecs=None  # Explicitly uncalibrated!
# )
```

---

## 7. Verification & Testing

All unit tests are located in `tests/unit/confidence/`:
- `test_confidence_models.py`: Validates signal containers, config validation, breakdown serialization, and contract conversion.
- `test_confidence_signals.py`: Validates signal extraction across all 5 dimensions including reliability invariants (absence of evidence $\to$ UNKNOWN).
- `test_confidence_fusion.py`: Validates weighted fusion mathematics, missing signal renormalization, zero/one bounds, and aggregation strategies.
- `test_confidence_estimator.py`: Validates Protocol conformance (`calculate`), batch estimation, and error handling.

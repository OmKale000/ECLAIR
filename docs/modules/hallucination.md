# M08 — Hallucination Detection

> Module documentation (Spec §4.8). Derived only from the Spec (§M08) and the repository.
> Authoritative rules: `rules/M08_hallucination_detection.md`, `rules/COMMON_RULES.md`.

---

## 1. Identity & Purpose
- **ID:** M08
- **Name:** Hallucination Detection
- **Folder:** `src/eclair/hallucination/`
- **Tests:** `tests/unit/hallucination/`
- **Purpose (Spec §M08):** Detect claims that appear fabricated, unsupported, or contradicted by fusing reliability signals into a structured hallucination result.

---

## 2. Module Responsibilities
- **Extract & Combine 5 Core Reliability Signals:**
  1. **No Evidence:** Evaluates absence of supporting evidence or insufficient quality signals (Spec §4.9).
  2. **Contradictory Evidence:** Captures direct NLI contradiction (`VerificationStatus.CONTRADICTED`) and severe evidence conflicts.
  3. **Low Semantic Support:** Computes semantic divergence based on retrieved passage relevance scores or lexical similarity.
  4. **Model Disagreement:** Measures cross-model divergence from multi-model consensus ($1.0 - \text{agreement\_score}$).
  5. **Numerical Inconsistency:** Identifies disparities in numbers, quantities, and dates between claims and evidence passages.
- **Compute Hallucination Probability:** Deterministically combine the 5 signals into a bounded score in $[0.0, 1.0]$.
- **Determine Hallucination Flag:** Apply threshold evaluation (`probability >= hallucination_threshold`, default 0.50).
- **Generate Explanatory Reasons:** Provide non-empty, human-readable explanations detailing all active contributing signals when flagged.
- **Provide Response-Level Assessment:** Aggregate claim-level detections across a full response batch.

---

## 3. Non-Responsibilities
- Does **NOT** perform claim verification itself (responsibility of M07 Claim Verification).
- Does **NOT** retrieve evidence or perform RAG (responsibility of M05 RAG).
- Does **NOT** score raw source authority, freshness, or duplicates (responsibility of M06 Evidence Quality).
- Does **NOT** compute raw confidence for M10 or calibrated ECS for M11.
- Does **NOT** make risk decisions or select decision actions like `RETURN`, `ABSTAIN`, or `BLOCK_ACTION` (responsibility of M13 Risk & Decision).
- Does **NOT** execute self-reflection or text rewriting (responsibility of M12 Reflection).
- Does **NOT** manage persistence, REST APIs, or dashboard UI.

---

## 4. Architecture & Components

```text
src/eclair/hallucination/
  ├── models.py       # HallucinationReason, HallucinationSignals, HallucinationResult, ResponseHallucinationResult
  ├── signals.py      # Extractors for the 5 core reliability signals
  ├── scoring.py      # HallucinationScorer, HallucinationScorerConfig, probability fusion & reason generation
  ├── detector.py     # HallucinationDetector orchestrating single claim and response batch evaluations
  └── __init__.py     # Clean module exports
```

### Component Breakdown
1. **`models.py`**:
   - `HallucinationSignals`: Encapsulates scores for `no_evidence_score`, `contradiction_score`, `low_semantic_support_score`, `model_disagreement_score`, and `numerical_inconsistency_score`.
   - `HallucinationResult`: Per-claim assessment carrying `claim_id`, `hallucination_probability` ($[0.0, 1.0]$), `is_hallucination` (bool), `reasons` (list[str]), and `signals`.
   - `ResponseHallucinationResult`: Batch container with `claim_results`, `overall_hallucination_probability`, `has_hallucination`, `hallucinated_claim_ids`, and `summary_reasons`.
   - `HallucinationReason`: Standardized enum reasons for diagnostics.

2. **`signals.py`**:
   - `extract_no_evidence_signal`: Maps missing evidence or `VerificationStatus.UNKNOWN` to high risk without fabricating support.
   - `extract_contradiction_signal`: Identifies `VerificationStatus.CONTRADICTED` or M06 pairwise conflict severity.
   - `extract_semantic_support_signal`: Evaluates relevance scores from M05/M06 or lexical Jaccard overlap.
   - `extract_model_disagreement_signal`: Inverts consensus agreement ($1.0 - \text{agreement}$); treats omitted consensus neutrally.
   - `extract_numerical_inconsistency_signal`: Detects quantity, currency, and date mismatches via regex extraction and conflict analysis.

3. **`scoring.py` (`HallucinationScorer`)**:
   - Weighted linear combination:
     $$P = \frac{w_{\text{no\_ev}} s_{\text{no\_ev}} + w_{\text{contra}} s_{\text{contra}} + w_{\text{sem}} s_{\text{sem}} + w_{\text{disagree}} s_{\text{disagree}} + w_{\text{num}} s_{\text{num}}}{\sum w_i}$$
   - High-severity overrides for direct contradictions ($s_{\text{contra}} \ge 0.85 \implies P \ge 0.85$) and severe numerical disparities ($s_{\text{num}} \ge 0.80 \implies P \ge 0.70$).
   - Reason generation guaranteeing non-empty explanations when `is_hallucination` is `True`.

4. **`detector.py` (`HallucinationDetector`)**:
   - `detect_claim(...)`: Evaluates an atomic claim against evidence, M07 verification, and M09 consensus.
   - `detect_claims(...)`: Evaluates a batch of claims and produces response-level metrics.

---

## 5. Input / Output & Integration Flow

```text
M07 Claim Verification (VerificationResult)
                    │
M06 Evidence Quality (EvidenceQualityReport / EvidenceQualitySignals)
                    │
M09 Consensus (agreement_score / ConsensusLevel)
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│              M08 Hallucination Detection                │
│                 (HallucinationDetector)                 │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  HallucinationResult                    │
│  - claim_id: str                                        │
│  - hallucination_probability: float [0.0, 1.0]          │
│  - is_hallucination: bool                               │
│  - reasons: list[str] (non-empty when flagged)          │
│  - signals: HallucinationSignals                        │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
      M10 Confidence Estimation / M12 Reflection / Engine
```

---

## 6. Missing or Partial Signals Behavior
- **Missing Signals Reduce Evidence:** If an optional signal (e.g. M09 consensus) is not provided, it defaults to a neutral 0.0 without fabricating agreement or disagreement.
- **Absence of Evidence is a Signal:** If evidence is omitted or empty, `no_evidence_score = 1.0`, contributing to hallucination risk (Spec §4.9).
- **Zero Hallucination Fabrication:** If evidence and verification confirm `SUPPORTED` with high relevance, hallucination probability remains close to 0.0.

---

## 7. Sample Input and Output

### Input: Claim, Verification, Evidence, and Consensus
```python
from eclair.contracts.claim import Claim, ClaimType
from eclair.contracts.evidence import Evidence
from eclair.contracts.verification import VerificationResult, VerificationStatus
from eclair.hallucination import HallucinationDetector

claim = Claim(
    text="Customers may return opened software within 90 days.",
    claim_type=ClaimType.NUMERIC,
)
evidence = [
    Evidence(
        evidence_id="ev-01",
        text="Opened software is strictly non-refundable.",
        relevance_score=0.92,
        source="refund_policy.md",
    )
]
verification = VerificationResult(
    claim_id=claim.claim_id,
    status=VerificationStatus.CONTRADICTED,
    evidence_ids=["ev-01"],
)
```

### Execution: Detection
```python
detector = HallucinationDetector()
result = detector.detect_claim(
    claim=claim,
    verification=verification,
    evidence=evidence,
    agreement_score=0.20,
)
```

### Output: Structured HallucinationResult
```python
# result.hallucination_probability -> 0.85
# result.is_hallucination          -> True
# result.reasons -> [
#     "Evidence directly contradicts the claim (Claim is verified as CONTRADICTED by evidence (M07).)",
#     "Numerical or quantitative inconsistency detected (Numerical disparity: claim states ['90'] while evidence contains []).",
#     "High model disagreement across independent model outputs (Consensus agreement score is 0.20 (disagreement=0.80).)"
# ]
# result.signals -> HallucinationSignals(
#     no_evidence_score=0.0,
#     contradiction_score=1.0,
#     low_semantic_support_score=0.08,
#     model_disagreement_score=0.80,
#     numerical_inconsistency_score=0.70,
# )
```

---

## 8. Verification & Test Suite
The module test suite is located in `tests/unit/hallucination/`:
- `test_hallucination_models.py`: Contract validation, forbidden extra fields, range enforcement.
- `test_hallucination_signals.py`: Verification of all 5 individual signal extractors across edge and normal cases.
- `test_hallucination_scoring.py`: Fusion calculations, high-severity overrides, custom weights, reason generation guarantees.
- `test_hallucination_detector.py`: End-to-end detector tests covering clean, contradicted, unevidenced, numerical disparity, consensus divergence, and batch evaluations.

> **Result:** 39 unit tests passing with zero errors and Ruff clean.

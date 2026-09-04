# M07 — Claim Verification

> Module documentation (Spec §4.8). Derived only from the Spec (§M07, §4.5, §4.9) and repository state.
> Authoritative rules: `rules/M07_claim_verification.md`, `rules/COMMON_RULES.md`, `rules/SHARED_CONTRACTS_REFERENCE.md`.

---

## 1. Identity & Purpose

- **Module ID:** M07
- **Module Name:** Claim Verification
- **Primary Location:** `src/eclair/verification/`
- **Unit Tests:** `tests/unit/verification/`
- **Purpose (Spec §M07):** Determine whether evidence actually supports the claim.

The module receives extracted atomic claims and retrieved evidence, runs Natural Language Inference (NLI) and optional secondary LLM verification, aggregates the evidence-level assessments, and produces a structured `VerificationResult`.

---

## 2. Non-Negotiable Reliability Semantics

1. **RAG retrieval is NOT verification (Spec §4.5):**
   Retrieving a document ("I found this passage in the knowledge base") does not constitute proof. Verification is the explicit determination of whether the evidence entails, contradicts, or is neutral towards the claim.
2. **Absence of evidence MUST map to UNKNOWN, never SUPPORTED (Spec §4.9):**
   When `evidence = []`, the verifier returns `status = VerificationStatus.UNKNOWN` with `evidence_ids = []`.
3. **Frozen verification states (Spec §M07, §4.9):**
   The verification status is strictly restricted to:
   - `SUPPORTED`
   - `CONTRADICTED`
   - `UNKNOWN`

---

## 3. Inputs & Outputs

### Input
- `claim: Claim` (from M03 Claim Extraction)
- `evidence: list[Evidence]` (from M05 RAG / M06 Evidence Quality)

### Output
- `VerificationResult` (frozen M01 shared contract):
  - `claim_id: str`
  - `status: VerificationStatus` (`SUPPORTED` | `CONTRADICTED` | `UNKNOWN`)
  - `evidence_ids: list[str]` (supporting evidence IDs attached to the result)

---

## 4. Verification Flow & NLI Mapping

```
Claim + Evidence[]
       │
       ▼
Input Validation (Pydantic / Contracts)
       │
       ├─── evidence == [] ───► VerificationStatus.UNKNOWN (evidence_ids=[])
       │
       ▼
Per-Evidence Evaluation (NLIEngine)
Premise (Evidence) + Hypothesis (Claim)
       │
       ├─── ENTAILMENT    ────► SUPPORTED
       ├─── CONTRADICTION ────► CONTRADICTED
       └─── NEUTRAL       ────► UNKNOWN
       │
       ▼ (optional if UNKNOWN)
Secondary LLM Verification (M02 LLM Gateway via LLMVerifier)
       │
       ▼
Evidence Aggregation (EvidenceAggregator)
       │
       ▼
VerificationResult (claim_id, status, evidence_ids)
```

---

## 5. Evidence Aggregation

When multiple evidence passages are evaluated for a single claim:
1. Each evidence passage is evaluated independently.
2. Scores for support and contradiction are tracked across items.
3. If contradicting evidence dominates, status resolves to `CONTRADICTED`.
4. If supporting evidence dominates, status resolves to `SUPPORTED` and supporting evidence IDs are attached to `evidence_ids`.
5. If evidence is neutral, ambiguous, or empty, status resolves to `UNKNOWN`.

---

## 6. Public Interface

Conforms strictly to the frozen M01 `Verifier` Protocol:

```python
from eclair.contracts import Claim, Evidence, VerificationResult

class Verifier(Protocol):
    def verify(self, claim: Claim, evidence: list[Evidence]) -> VerificationResult: ...
```

Concrete implementation:

```python
from eclair.verification import ClaimVerifier

verifier = ClaimVerifier()
result = verifier.verify(claim, evidence)
```

---

## 7. Sample Input & Output

### Sample Input
```python
from eclair.contracts import Claim, Evidence

claim = Claim(
    claim_id="claim-refund-window",
    text="Customers may return items within 30 days.",
)

evidence = [
    Evidence(
        evidence_id="ev-refund-doc-1",
        text="All physical products can be returned within 30 calendar days of delivery for a full refund.",
        source="refund_policy.md",
    )
]
```

### Sample Output
```python
VerificationResult(
    claim_id="claim-refund-window",
    status=VerificationStatus.SUPPORTED,
    evidence_ids=["ev-refund-doc-1"],
)
```

### No-Evidence Case
```python
verifier.verify(claim, [])
# Output:
# VerificationResult(
#     claim_id="claim-refund-window",
#     status=VerificationStatus.UNKNOWN,
#     evidence_ids=[],
# )
```

---

## 8. Module Boundaries & Non-Responsibilities

M07 handles **only** claim-vs-evidence verification:
- Does **NOT** perform vector search or retrieval (M05 responsibility).
- Does **NOT** calculate source authority, freshness, or quality scores (M06 responsibility).
- Does **NOT** calculate hallucination probability (M08 responsibility).
- Does **NOT** fuse confidence or calibrate ECS (M10/M11 responsibility).
- Does **NOT** make risk decisions or decide to abstain (M13 responsibility).

---

## 9. Error Handling

- Reuses the shared M01 exception hierarchy (`ContractValidationError`, `ModuleError`, `ConfigurationError`).
- Malformed claim or evidence inputs raise `ContractValidationError`.
- Runtime failures raise `ModuleError` with machine-readable error codes.

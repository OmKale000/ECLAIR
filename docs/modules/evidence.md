# M06 — Evidence Quality & Conflict Detection

> Module documentation (Spec §4.8). Derived only from the Spec (§M06) and the repository.
> Authoritative rules: `rules/M06_evidence_quality.md`, `rules/COMMON_RULES.md`.

---

## 1. Identity & Purpose
- **ID:** M06
- **Name:** Evidence Quality & Conflict Detection
- **Folder:** `src/eclair/evidence/`
- **Tests:** `tests/unit/evidence/`
- **Purpose (Spec §M06):** Determine whether retrieved evidence is reliable enough to support verification before claim verification (M07) and confidence estimation (M10).

---

## 2. Module Responsibilities
- **Score Quality Signals:** Evaluate relevance, source authority, freshness, completeness, and conflict for each evidence item.
- **Detect Anomaly Signals:**
  - **Outdated Documents:** Identify temporal decay, expired policies, and deprecated materials.
  - **Duplicate Documents:** Detect exact and near-identical redundant passages across retrieved items.
  - **Conflicting Evidence:** Detect numerical contradictions, polarity clashes, and policy incompatibilities.
  - **Low-Quality Sources:** Identify unverified blogs, forums, missing origins, or untrusted sources.
  - **Insufficient Evidence:** Represent missing or insufficient evidence as a clear structured signal without crashing.
- **Provide Structured Output:** Emit `ScoredEvidence` and `EvidenceQualityReport` exposing standardized signals bounded in `[0.0, 1.0]`.

---

## 3. Non-Responsibilities
- Does **NOT** retrieve evidence from knowledge bases (responsibility of M05 RAG).
- Does **NOT** verify claims or decide `SUPPORTED` / `CONTRADICTED` / `UNKNOWN` (responsibility of M07 Claim Verification).
- Does **NOT** compute raw confidence (responsibility of M10) or calibrated ECS (responsibility of M11).
- Does **NOT** make risk decisions or select decision actions (responsibility of M13).

---

## 4. Architecture & Components

```text
src/eclair/evidence/
  ├── models.py       # EvidenceQualitySignals, ConflictDetail, ScoredEvidence, EvidenceQualityReport
  ├── authority.py    # SourceAuthorityScorer, controlled KB tiers, low-quality source detection
  ├── freshness.py    # FreshnessScorer, ISO 8601 temporal decay, deprecation detection
  ├── conflict.py     # ConflictDetector, duplicate clustering, contradiction analysis
  ├── scorer.py       # EvidenceScorer combining quality signals into composite assessments
  └── __init__.py     # Module public exports
```

### Component Breakdown
1. **`models.py`**:
   - `EvidenceQualitySignals`: Per-item quality metrics (`relevance_score`, `authority_score`, `freshness_score`, `completeness_score`, `conflict_score`, `overall_score`, `is_outdated`, `is_duplicate`, `is_conflicting`, `is_low_quality`, `flags`).
   - `ConflictDetail`: Detailed pairwise conflict records with `conflict_type`, `conflict_score`, and explanation `reason`.
   - `ScoredEvidence`: Container linking an M01 `Evidence` contract with its `EvidenceQualitySignals`.
   - `EvidenceQualityReport`: Aggregate batch report with `items`, `average_quality`, `is_insufficient`, `has_conflicts`, `duplicate_ids`, `outdated_ids`, and `summary_flags`.

2. **`authority.py` (`SourceAuthorityScorer`)**:
   - Scores source authority based on controlled knowledge base policies (`refund_policy`, `company_policy`, etc. = 1.0), official/regulatory sources (0.95), internal docs (0.85), general wikis (0.65), and unverified blogs/forums (0.35).
   - Identifies low-quality sources below `min_authority_threshold` (0.50).

3. **`freshness.py` (`FreshnessScorer`)**:
   - Computes temporal validity using exponential/piecewise age decay from ISO 8601 dates or text-extracted years.
   - Detects deprecation keywords (`deprecated`, `obsolete`, `superseded`, `archived`) to penalize outdated materials.

4. **`conflict.py` (`ConflictDetector`)**:
   - Detects duplicates using token-level Jaccard similarity and exact matching.
   - Detects contradictions: numerical disparities on shared topics (e.g. "30 days" vs "14 days"), polarity/negation clashes, and antonym conflicts.

5. **`scorer.py` (`EvidenceScorer`)**:
   - Orchestrates multi-signal fusion:
     $$\text{overall} = w_{\text{rel}} \cdot \text{rel} + w_{\text{auth}} \cdot \text{auth} + w_{\text{fresh}} \cdot \text{fresh} + w_{\text{comp}} \cdot \text{comp} - w_{\text{conf}} \cdot \text{conf}$$
   - Evaluates passage completeness and diagnostic flags.
   - Gracefully handles empty evidence sets as `is_insufficient = True` without raising exceptions.

---

## 5. Input / Output & Integration Flow

```text
M05 RAG / Evidence Retrieval (list[Evidence])
                    ↓
M06 Evidence Quality & Conflict Detection (EvidenceScorer)
                    ↓
┌─────────────────────────────────────────────────────────┐
│              EvidenceQualityReport                      │
│  - items: list[ScoredEvidence]                          │
│  - average_quality: float [0.0, 1.0]                    │
│  - is_insufficient: bool (Signal, not crash)           │
│  - has_conflicts: bool                                  │
│  - conflicts: list[ConflictDetail]                      │
│  - duplicate_ids, outdated_ids, low_quality_ids         │
└─────────────────────────────────────────────────────────┘
                    ↓
M07 Claim Verification / M10 Confidence Estimation / Engine
```

---

## 6. Sample Input and Output

### Input: M05 Retrieved Evidence List
```python
from eclair.contracts.evidence import Evidence

evidence_list = [
    Evidence(
        evidence_id="ev-refund-01",
        text="Customers may request a full refund within 30 calendar days of initial purchase.",
        source="data/knowledge_base/refund_policy/refund_policy.md",
        relevance_score=0.92,
    ),
    Evidence(
        evidence_id="ev-refund-02",
        text="Customers may request a full refund within 14 calendar days of initial purchase.",
        source="unverified_blog.com/post_123",
        relevance_score=0.88,
    ),
]
```

### Execution: Quality Scoring & Conflict Detection
```python
from eclair.evidence import EvidenceScorer

scorer = EvidenceScorer()
report = scorer.score_evidence(evidence_list, claim_text="Refunds within 30 days")
```

### Output: Structured EvidenceQualityReport
```python
# report.average_quality -> 0.72
# report.has_conflicts   -> True
# report.is_insufficient -> False

# Pairwise Conflict Detected:
# report.conflicts[0] -> ConflictDetail(
#     evidence_id_a="ev-refund-01",
#     evidence_id_b="ev-refund-02",
#     conflict_score=0.90,
#     conflict_type="numerical",
#     reason="Numerical contradiction detected: '30 calendar days' vs '14 calendar days' under similar context.",
# )

# Individual Quality Signals:
# report.items[0].signals -> EvidenceQualitySignals(
#     evidence_id="ev-refund-01",
#     relevance_score=0.92,
#     authority_score=1.0,    # Controlled KB
#     freshness_score=0.85,
#     completeness_score=1.0,
#     conflict_score=0.90,
#     overall_score=0.82,
#     is_conflicting=True,
#     flags=["CONFLICTING"],
# )
```

---

## 7. Reliability Semantics
- **Evidence Quality ≠ Claim Verification:** High evidence quality does not imply claim entailment (M07 is an explicit verification step).
- **Insufficient Evidence is a Signal:** Absence of evidence produces `is_insufficient = True` and an empty list, allowing M07 to return `VerificationStatus.UNKNOWN` without application crashes.
- **Signals are Bounded:** All scores are strictly constrained to $[0.0, 1.0]$.

# M14 — Provenance (part of Provenance & Database)

> Module documentation (Spec §4.8). Derived only from the Spec (§M14) and the repository. M14 owns TWO
> folders: `src/eclair/provenance/` (this document) and `src/eclair/database/` (see `database.md`).
> Authoritative rules: `rules/M14_provenance_database.md`, `rules/COMMON_RULES.md`.

## 1. Identity & Purpose
- **Module ID:** M14
- **Name:** Provenance & Database — Provenance Component
- **Folder:** `src/eclair/provenance/`
- **Tests:** `tests/unit/provenance/`
- **Purpose:** Store everything needed to reproduce, explain, and audit reliability decisions keyed by `query_id`, and reconstruct the decision path for authorized consumers without recomputing reliability signals.

## 2. Responsibilities & Non-Responsibilities

### Responsibilities
- Record query-to-decision lineage for all pipeline stages: Query, Claims, Evidence, Verification, Confidence, Consensus, Risk, Decision, Final Answer, Feedback, and Timestamp.
- Validate required lineage contracts before persistence at the service boundary.
- Atomically commit complete pipeline outputs via single-transaction writes.
- Reconstruct the exact decision path from stored records without recalculating confidence, verification, or risk.
- Support consumers: Engine, M15 API (`GET /v1/explain/{query_id}`), and M17 Dashboard (audit views).

### Non-Responsibilities
- Does NOT calculate confidence or calibrated ECS (M10, M11).
- Does NOT execute verification or hallucination detection (M07, M08).
- Does NOT evaluate multi-model consensus (M09).
- Does NOT select risk-based actions or alter decisions (M13).
- Does NOT expose HTTP REST endpoints directly (M15).

## 3. Architecture & Data Flow

```text
Engine Stage Outputs ──► EclairResult
                              │
                              ▼
                 ProvenanceService.record_result()
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
           ProvenanceTracker    AuditRepository
                    │                   │
                    ▼                   ▼
           ORM Models (10 tables, FK to queries.query_id)
                    │
                    ▼
           Database Persistence (Single Atomic Transaction)

Audit Retrieval Flow:
query_id ──► ProvenanceService.get_audit_trail(query_id)
                  │
                  ▼
          AuditReconstructor.reconstruct(query_id)
                  │
                  ▼
          DecisionPath (Lineage + Explainable Narrative)
```

## 4. Key Components

### 4.1 ProvenanceTracker (`tracker.py`)
Provides stage-by-stage recording methods with strict contract validation:
- `record_query(query: Query, final_answer: str | None = None)`
- `record_claims(query_id: str, claims: Sequence[Claim])`
- `record_evidence(query_id: str, evidence: Sequence[Evidence])`
- `record_verifications(query_id: str, verifications: Sequence[VerificationResult])`
- `record_confidence(query_id: str, confidence: ConfidenceResult)`
- `record_risk(query_id: str, risk: RiskResult)`
- `record_decision(query_id: str, decision: DecisionResult)`
- `record_consensus(query_id: str, agreement_score: float, consensus_level: str, ...)`
- `record_final_answer(query_id: str, final_answer: str)`
- `record_feedback(query_id: str, rating: float | None = None, ...)`

### 4.2 AuditReconstructor (`audit.py`)
Reconstructs the decision path without re-evaluating reliability. Produces a `DecisionPath` dataclass containing:
- Complete lineage objects (claims, evidence, verifications, confidence, consensus, risk, decision, feedback).
- `is_complete: bool`: whether all pipeline stages are recorded.
- `explanation: str`: human-readable narrative explaining how the recorded outputs led to the decision.

### 4.3 ProvenanceService (`service.py`)
Facade for the application and API layers:
- `record_result(result: EclairResult, question: str | None = None, consensus: Any | None = None) -> str`
- `record_feedback(query_id: str, rating: float | None = None, feedback_text: str | None = None, user_id: str | None = None) -> str`
- `get_audit_trail(query_id: str) -> DecisionPath`
- `get_lineage(query_id: str) -> dict[str, Any]`

## 5. Sample Input & Output

### Sample Input: Persisting Pipeline Output
```python
from eclair.contracts.claim import Claim
from eclair.contracts.confidence import ConfidenceResult
from eclair.contracts.decision import DecisionResult
from eclair.contracts.enums import ClaimType, DecisionAction, VerificationStatus
from eclair.contracts.evidence import Evidence
from eclair.contracts.result import EclairResult
from eclair.contracts.risk import RiskResult
from eclair.contracts.verification import VerificationResult
from eclair.provenance import ProvenanceService

service = ProvenanceService()

result = EclairResult(
    query_id="query-abc-123",
    answer="Items may be returned within 30 days of purchase.",
    claims=[
        Claim(claim_id="c-1", text="Items may be returned within 30 days.", claim_type=ClaimType.FACTUAL),
    ],
    evidence=[
        Evidence(evidence_id="e-1", text="Return window is 30 days from delivery.", source="refund_policy.md", relevance_score=0.95),
    ],
    verifications=[
        VerificationResult(claim_id="c-1", status=VerificationStatus.SUPPORTED, evidence_ids=["e-1"]),
    ],
    confidence=ConfidenceResult(raw_confidence=0.88, calibrated_ecs=0.91),
    risk=RiskResult(risk_level="LOW", risk_score=0.10),
    decision=DecisionResult(action=DecisionAction.RETURN, reason="Claims supported with high confidence."),
)

saved_query_id = service.record_result(
    result=result,
    question="What is the return window?",
)
```

### Sample Output: Reconstructed Decision Path
```python
audit_trail = service.get_audit_trail("query-abc-123")

print(audit_trail.to_dict())
# {
#   "query_id": "query-abc-123",
#   "question": "What is the return window?",
#   "final_answer": "Items may be returned within 30 days of purchase.",
#   "created_at": "2026-10-19T18:30:00+00:00",
#   "claims": [{"claim_id": "c-1", "text": "Items may be returned within 30 days.", "claim_type": "FACTUAL", "position": 0}],
#   "evidence": [{"evidence_id": "e-1", "text": "Return window is 30 days from delivery.", "source": "refund_policy.md", "relevance_score": 0.95}],
#   "verifications": [{"claim_id": "c-1", "status": "SUPPORTED", "evidence_ids": ["e-1"]}],
#   "confidence": {"raw_confidence": 0.88, "calibrated_ecs": 0.91},
#   "consensus": null,
#   "risk": {"risk_level": "LOW", "risk_score": 0.1},
#   "decision": {"action": "RETURN", "reason": "Claims supported with high confidence."},
#   "feedback": [],
#   "audit_summary": {"claims_count": 1, "evidence_count": 1, "verifications_count": 1, "raw_confidence": 0.88, "calibrated_ecs": 0.91, "risk_level": "LOW", "decision_action": "RETURN"},
#   "explanation": "Query: 'What is the return window?' Extracted 1 claim(s). Verification outcomes: 1 SUPPORTED, 0 CONTRADICTED, 0 UNKNOWN. Confidence: raw=0.8800, calibrated_ecs=0.9100. Risk: level=LOW, score=0.1. Decision action: RETURN (reason: 'Claims supported with high confidence.'). Final answer: 'Items may be returned within 30 days of purchase....'",
#   "is_complete": true
# }
```

## 6. Error Handling

- Invalid contracts raise M01 `ContractValidationError`.
- Nonexistent query IDs on lineage attachment or retrieval raise M01 `ModuleError` with code `query_not_found`.
- Persistence failures trigger transaction rollbacks and raise `ModuleError` with code `database_transaction_error`.
- Provenance records are never silently dropped.

## 7. Verification

Tested in `tests/unit/provenance/`:
- `test_tracker.py`: Stage-by-stage recording, validation, ordering, non-existent query handling.
- `test_audit.py`: DecisionPath reconstruction, completeness checks, narrative generation, partial lineage handling.
- `test_service.py`: End-to-end `record_result`, atomic transaction rollback, feedback recording.

All 11 provenance unit tests pass.

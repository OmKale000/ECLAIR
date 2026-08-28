# ECLAIR — Shared Contracts & Frozen Values Reference

**Status:** FROZEN for Prototype v1. Sourced only from the authoritative Spec.
**Ownership:** M01 (Foundation) is the ONLY module allowed to define these in code.
**Rule:** No module may invent, rename, extend, or locally redefine anything on this page. If a
value you need is not here, it does not exist yet — raise it as a gap for M01, do not invent it.

> These are contract *names and values* fixed by the Spec. Exact Pydantic field lists are defined
> by M01 in `src/eclair/contracts/`. Where the Spec does not fix a field, M01 decides it once and it
> then becomes frozen for everyone else.

---

## 1. Required shared contracts (Spec §M01)

Defined in `src/eclair/contracts/` and owned by M01:

| Contract | File | Produced by |
|----------|------|-------------|
| `Query` | `contracts/query.py` | API / engine entry |
| `Claim` | `contracts/claim.py` | M03 Claim Extraction |
| `Evidence` | `contracts/evidence.py` | M05 RAG (quality-annotated by M06) |
| `VerificationResult` | `contracts/verification.py` | M07 Claim Verification |
| `ConfidenceResult` | `contracts/confidence.py` | M10 Confidence (raw) / M11 (calibrated ECS) |
| `RiskResult` (risk contract) | `contracts/risk.py` | M13 Risk |
| `DecisionResult` | `contracts/decision.py` | M13 Decision |
| `EclairResult` | `contracts/result.py` | Engine (final aggregate) |

The Spec explicitly names at minimum: `Claim`, `Evidence`, `VerificationResult`,
`ConfidenceResult`, `DecisionResult`, `EclairResult` (Spec §M01).

## 2. Frozen enum values (do NOT add/rename members)

**Verification status** (Spec §M07, §4.9):
```
SUPPORTED
CONTRADICTED
UNKNOWN
```
Mapping from NLI: `ENTAILMENT -> SUPPORTED`, `CONTRADICTION -> CONTRADICTED`,
`NEUTRAL -> UNKNOWN`. **No evidence MUST map to UNKNOWN, never SUPPORTED.**

**Decision actions** (Spec §M13):
```
RETURN
VERIFY_MORE
REGENERATE
ABSTAIN
HUMAN_REVIEW
BLOCK_ACTION
```

**Consensus level** (Spec §M09): full or partial consensus + a numeric agreement score.
(Exact enum spelling for full/partial is defined once by M01/M09 and then frozen.)

## 3. Frozen module interfaces (Spec §4.1, §4.3)

```
LLMProvider.generate(request: LLMRequest) -> LLMResponse     # M02; Ollama/Gemini/Groq/OpenRouter implement it
ClaimExtractor.extract(text: str) -> list[Claim]             # M03
Retriever.search(query: str, top_k: int = 5) -> list[Evidence]  # M05
Verifier.verify(claim: Claim, evidence: list[Evidence]) -> VerificationResult  # M07
ConfidenceEstimator.calculate(signals) -> ConfidenceResult   # M10 (raw)
DecisionEngine -> DecisionResult                             # M13
```
The engine/orchestrator (`src/eclair/engine/`) owns how these are wired together (Spec §4.2).

## 4. Frozen REST endpoints (Spec §M15) — owned by M15 only

```
POST /v1/ask
POST /v1/verify
GET  /v1/explain/{query_id}
POST /v1/feedback
GET  /v1/health
GET  /v1/metrics
```
Request/response schemas live in `src/eclair/api/schemas/`. Endpoints are versioned (`/v1`).

## 5. Frozen SDK surface (Spec §M16) — owned by M16 only

```
EclairClient.ask(...)
EclairClient.verify(...)
EclairClient.explain(...)
EclairClient.feedback(...)
```
The SDK wraps the REST API; it must not duplicate reliability logic.

## 6. Reliability semantics that are non-negotiable

- Raw confidence (M10) is NOT calibrated ECS. Calibrated ECS is produced only by M11 after
  calibration against observed correctness (Spec §4.4).
- RAG retrieval is not verification (Spec §4.5).
- Model agreement is not truth (Spec §4.6).

## 7. Provenance lineage fields (Spec §M14) — persisted, keyed by `query_id`

```
Query, Claims, Evidence, Verification, Confidence, Consensus, Risk, Decision,
Final Answer, Feedback, Timestamp
```

## 8. Evaluation metrics (Spec §M18) — exact set

```
Accuracy, Hallucination Rate, Unsupported Claim Rate, ECE, Brier Score,
High-Confidence Error Rate, Correct Abstention Rate, Conflict Detection Rate,
False Action Rate, Latency
```
Baselines compared: `LLM Only`, `LLM + RAG`, `LLM + Multi-Agent`, `ECLAIR`.

## 9. Approved dependency stack (Spec §4.10) — do not exceed

Python 3.12 · FastAPI · Uvicorn · FAISS · sentence-transformers · HuggingFace Transformers ·
PostgreSQL · SQLAlchemy 2 · Alembic · Streamlit · Plotly/Matplotlib · scikit-learn · Pandas ·
NumPy · HTTPX · Pydantic v2 · Ollama · Docker · Docker Compose · uv · pytest · Ruff · GitHub Actions.

**Forbidden in v1:** Kubernetes, Kafka, microservices, Neo4j, Elasticsearch, fine-tuned models,
heavy agent frameworks, paid observability.

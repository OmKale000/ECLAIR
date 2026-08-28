# ECLAIR REST API — Endpoints (M15)

> Derived only from the Spec (§M15, §4.12) and `rules/SHARED_CONTRACTS_REFERENCE.md` §4. The Spec
> **freezes the endpoint set, methods, paths, and versioning**. It does NOT fix the exact
> request/response field schemas — those live in `src/eclair/api/schemas/` and are owned by M15.
> This document does not invent field names. Where a schema field is not fixed by the Spec, it is
> marked as **defined by M15**. Read `rules/M15_rest_api.md` first.

## Ownership & rules
- **Owner:** M15 (`src/eclair/api/`). Endpoints are the only thing M15 exposes.
- **Thin layer (Spec §4.12):** the API must NOT independently implement claim verification,
  confidence fusion, hallucination detection, or risk/decision logic. It delegates to the integrated
  engine and maps results to responses.
- **Versioning:** all endpoints are under `/v1`.
- **Docs:** FastAPI auto-provides OpenAPI / Swagger (Spec §M15).
- **Validation:** all requests validated via Pydantic schemas at the boundary
  (`api/schemas/requests.py`); responses in `api/schemas/responses.py`.
- **Errors:** M01 shared exceptions mapped to consistent HTTP error responses; no invented formats.

## Frozen endpoint set (Spec §M15, SHARED_CONTRACTS_REFERENCE §4)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/ask` | Run a question through the full ECLAIR reliability pipeline and return the traceable result. |
| POST | `/v1/verify` | Verify a supplied answer/claims against evidence via the engine. |
| GET | `/v1/explain/{query_id}` | Return the persisted provenance / decision path for a query (M14). |
| POST | `/v1/feedback` | Submit feedback for a previous query (persisted by M14). |
| GET | `/v1/health` | Liveness/health check. |
| GET | `/v1/metrics` | Expose evaluation/reliability metrics. |

> No endpoint may be added, renamed, or un-versioned. If a new endpoint seems necessary, STOP and
> raise it as a gap — do not invent it (`rules/COMMON_RULES.md` §A/§C).

## Endpoint semantics

### POST `/v1/ask`
- **Does:** Question → LLM answer → claims → evidence → verification → hallucination → consensus →
  raw confidence → calibrated ECS → risk decision → final answer/abstain/human-review, persisted by
  M14 (Spec §5, §7). Delegates entirely to the engine.
- **Request:** question (+ optional parameters) — schema defined by M15 in `api/schemas/requests.py`.
- **Response:** the aggregated `EclairResult` mapped to a response schema — including the final
  decision (one of `RETURN`/`VERIFY_MORE`/`REGENERATE`/`ABSTAIN`/`HUMAN_REVIEW`/`BLOCK_ACTION`),
  the calibrated ECS, and a `query_id` for later `explain`. Response schema defined by M15.

### POST `/v1/verify`
- **Does:** Verify supplied content against evidence through the engine's verification path (M07),
  honoring the invariant that no-evidence → `UNKNOWN` (Spec §4.9). No reliability logic in the API.
- **Request / Response:** schemas defined by M15; verification status is restricted to
  `SUPPORTED`/`CONTRADICTED`/`UNKNOWN`.

### GET `/v1/explain/{query_id}`
- **Does:** Return the persisted lineage for `query_id` (Query, Claims, Evidence, Verification,
  Confidence, Consensus, Risk, Decision, Final Answer, Feedback, Timestamp — Spec §M14). Read-only.
- **Path param:** `query_id`.
- **Response:** reconstructed decision path (audit trail) — schema defined by M15/M14.

### POST `/v1/feedback`
- **Does:** Persist feedback against a `query_id` (Spec §M14 stores Feedback). Feedback can later
  inform calibration (M11) against observed correctness.
- **Request / Response:** schemas defined by M15.

### GET `/v1/health`
- **Does:** Report service health/liveness. Response schema defined by M15.

### GET `/v1/metrics`
- **Does:** Expose reliability/evaluation metrics (the M18 metric set: Accuracy, Hallucination Rate,
  Unsupported Claim Rate, ECE, Brier Score, High-Confidence Error Rate, Correct Abstention Rate,
  Conflict Detection Rate, False Action Rate, Latency — SHARED_CONTRACTS_REFERENCE §8). Response
  schema defined by M15.

## Consumers
The Python SDK (M16) and the Dashboard (M17) consume these endpoints, as do external applications
(Spec §M15). Both consumers stay thin (Spec §4.12).

See `docs/api/examples.md` for request/response usage examples.

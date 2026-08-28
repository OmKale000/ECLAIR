# ECLAIR REST API — Examples (M15 / M16)

> Derived only from the Spec (§M15, §M16, §7) and `rules/SHARED_CONTRACTS_REFERENCE.md`. The Spec
> freezes endpoint paths/methods and the SDK method names; it does NOT fix exact request/response
> field names (those are defined by M15 in `src/eclair/api/schemas/`). Examples below therefore show
> the **frozen** parts (paths, methods, SDK calls, enum values) and mark schema-specific fields as
> **defined by M15** — no invented field names.

## 1. Frozen surfaces used in examples
- Endpoints (Spec §M15): `POST /v1/ask`, `POST /v1/verify`, `GET /v1/explain/{query_id}`,
  `POST /v1/feedback`, `GET /v1/health`, `GET /v1/metrics`.
- SDK methods (Spec §M16): `client.ask(...)`, `client.verify(...)`, `client.explain(...)`,
  `client.feedback(...)`.
- Verification status enum: `SUPPORTED` / `CONTRADICTED` / `UNKNOWN`.
- Decision actions enum: `RETURN` / `VERIFY_MORE` / `REGENERATE` / `ABSTAIN` / `HUMAN_REVIEW` /
  `BLOCK_ACTION`.

## 2. Health check

```bash
curl -s http://localhost:8000/v1/health
```

Returns a health/liveness response (schema defined by M15).

## 3. Ask a question — `POST /v1/ask`

```bash
curl -s -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -d '{ "...request fields defined by M15 (e.g. the question)..." }'
```

The engine runs the full pipeline (Spec §5, §7) and returns an aggregated result that includes the
final `decision` (one of the frozen decision actions), the calibrated ECS, and a `query_id` used by
`explain`. Exact response fields are defined by M15's response schema.

## 4. Verify content — `POST /v1/verify`

```bash
curl -s -X POST http://localhost:8000/v1/verify \
  -H "Content-Type: application/json" \
  -d '{ "...request fields defined by M15 (answer/claims to verify)..." }'
```

Each verified claim carries a status restricted to `SUPPORTED` / `CONTRADICTED` / `UNKNOWN`.
No-evidence maps to `UNKNOWN`, never `SUPPORTED` (Spec §4.9).

## 5. Explain a decision — `GET /v1/explain/{query_id}`

```bash
curl -s http://localhost:8000/v1/explain/<query_id>
```

Returns the persisted lineage for that `query_id` (Query, Claims, Evidence, Verification, Confidence,
Consensus, Risk, Decision, Final Answer, Feedback, Timestamp — Spec §M14).

## 6. Submit feedback — `POST /v1/feedback`

```bash
curl -s -X POST http://localhost:8000/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{ "...request fields defined by M15 (query_id + feedback)..." }'
```

Feedback is persisted by M14 and can later inform calibration (M11).

## 7. Metrics — `GET /v1/metrics`

```bash
curl -s http://localhost:8000/v1/metrics
```

Exposes the M18 metric set (Accuracy, Hallucination Rate, Unsupported Claim Rate, ECE, Brier Score,
High-Confidence Error Rate, Correct Abstention Rate, Conflict Detection Rate, False Action Rate,
Latency).

## 8. Python SDK (M16) — frozen method names

```python
from eclair import EclairClient  # sdk/python/eclair/client.py (M16)

client = EclairClient(...)        # constructor args defined by M16

result   = client.ask(...)        # wraps POST /v1/ask
verified = client.verify(...)     # wraps POST /v1/verify
trace    = client.explain(...)    # wraps GET  /v1/explain/{query_id}
ack      = client.feedback(...)   # wraps POST /v1/feedback
```

The SDK is a thin client over the REST API (Spec §M16) and must not duplicate reliability logic
(Spec §4.12). Argument and return types are defined by M16 in `sdk/python/eclair/`.

## 9. Same result, three surfaces (Spec §7)
The same pipeline result must be accessible through the REST API, the Python SDK, and the ECLAIR
Dashboard. None of the three surfaces implements reliability logic itself (Spec §4.12).

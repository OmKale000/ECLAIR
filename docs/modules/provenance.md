# M14 — Provenance (part of Provenance & Database)

> Module documentation (Spec §4.8). Derived only from the Spec (§M14) and the repo. M14 owns TWO
> folders: `src/eclair/provenance/` (this doc) and `src/eclair/database/` (see `database.md`).
> Authoritative rules: `rules/M14_provenance_database.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M14
- **Name:** Provenance & Database — Provenance component
- **Folder:** `src/eclair/provenance/`
- **Tests:** `tests/unit/provenance/`

## Purpose (Spec §M14)
Store everything needed to reproduce, explain and audit reliability decisions.

## Responsibility
Track query-to-decision lineage keyed by `query_id`, and reconstruct why a decision was made
(complete audit history).

## Non-responsibility
- Does NOT compute any reliability signal.
- Does NOT expose HTTP endpoints (M15) — it provides the data the `explain` endpoint returns.

## Files (Spec §M14)
```
src/eclair/provenance/  tracker.py  audit.py  service.py
```

## Method (Spec §M14)
Persistence plus provenance tracking keyed by `query_id`.

## Required functionality (Spec §M14)
- Store, keyed by `query_id`: **Query, Claims, Evidence, Verification, Confidence, Consensus, Risk,
  Decision, Final Answer, Feedback, Timestamp** (SHARED_CONTRACTS_REFERENCE §7).
- Reconstruct why a decision was made.
- Support the audit trail used by `GET /v1/explain/{query_id}`.

## Inputs / Outputs
- **Input:** all stage outputs from the pipeline (via the engine), keyed by `query_id`.
- **Output:** persisted lineage + reconstructable audit trail.
- **Consumers:** engine, M15 (`/v1/explain`), M17 Dashboard audit view, M18 Evaluation.

## Dependencies
- Internal: M01 contracts; the database component (`src/eclair/database/`, see `database.md`).
- External: PostgreSQL / SQLAlchemy 2 / Alembic (via the database component).

## Error handling
Use M01 exceptions. Persistence failures must be surfaced, not silently dropped.

## Do not change
M01 contracts; other module folders. Provenance stores contract data; it does not redefine it.

## Expected outcome (Spec §M14)
Given a `query_id`, the system can reproduce the decision path and provide a complete audit trail.

## Verification before complete (Spec §4.8)
- A completed request persists all listed lineage fields under its `query_id` and the decision path
  can be reconstructed.
- `tests/unit/provenance/` pass; sample input/output provided.

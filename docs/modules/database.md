# M14 — Database (part of Provenance & Database)

> Module documentation (Spec §4.8). Derived only from the Spec (§M14, §1 folder structure) and the
> repo. M14 owns TWO folders: `src/eclair/database/` (this doc) and `src/eclair/provenance/` (see
> `provenance.md`). Authoritative rules: `rules/M14_provenance_database.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M14
- **Name:** Provenance & Database — Database component
- **Folder:** `src/eclair/database/` (+ Alembic migrations under `deployment/migrations/alembic/`)
- **Tests:** `tests/unit/database/`

## Purpose (Spec §M14)
Provide the persistence layer that stores everything needed to reproduce, explain and audit
reliability decisions.

## Responsibility
Provide database engine/session management, ORM models, and repositories; support database
repositories and migrations.

## Non-responsibility
- Does NOT compute reliability signals or make decisions.
- Does NOT expose HTTP endpoints (M15).

## Files (Spec §M14, §1)
```
src/eclair/database/  database.py  session.py
src/eclair/database/models/        query.py claim.py evidence.py verification.py
                                   confidence.py consensus.py risk.py decision.py
                                   feedback.py audit.py
src/eclair/database/repositories/  query_repository.py claim_repository.py
                                   evidence_repository.py verification_repository.py
                                   confidence_repository.py decision_repository.py
                                   audit_repository.py
deployment/migrations/alembic/     env.py  script.py.mako  versions/
```

## Technology (Spec §M14)
PostgreSQL, SQLAlchemy 2, Alembic.

## Method (Spec §M14)
Persistence plus provenance tracking keyed by `query_id`.

## Required functionality (Spec §M14)
- Persist the lineage fields (Query, Claims, Evidence, Verification, Confidence, Consensus, Risk,
  Decision, Final Answer, Feedback, Timestamp) via ORM models and repositories.
- Support database repositories and migrations (Alembic).

## Inputs / Outputs
- **Input:** contract data from the pipeline (via the provenance component / engine).
- **Output:** persisted rows and repository query results, keyed by `query_id`.
- **Consumers:** provenance component (`service.py`, `tracker.py`, `audit.py`), engine, M15
  `/v1/explain`, M18 Evaluation.

## Dependencies
- Internal: M01 contracts (for mapping domain data to ORM models); provenance component.
- External: SQLAlchemy 2 (ORM/session), PostgreSQL (store), Alembic (migrations).

## Configuration
Database connection is configured via the M01 config mechanism / environment (see
`docs/deployment/environment.md`); do not hardcode connection strings.

## Error handling
Use M01 exceptions. Wrap persistence errors; do not silently drop writes.

## Do not change
M01 contracts; other module folders. ORM models mirror the persisted lineage; they do not redefine
the shared transport contracts.

## Expected outcome (Spec §M14)
The persistence layer lets the system reproduce the decision path and provide a complete audit trail
given a `query_id`.

## Verification before complete (Spec §4.8)
- ORM models + repositories persist and retrieve lineage keyed by `query_id`; Alembic migrations run.
- `tests/unit/database/` pass; sample input/output provided.

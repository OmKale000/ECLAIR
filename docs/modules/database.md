# M14 — Database (part of Provenance & Database)

> Module documentation (Spec §4.8). Derived only from the Spec (§M14, §1 folder structure) and the
> repository. M14 owns TWO folders: `src/eclair/database/` (this document) and `src/eclair/provenance/`
> (see `provenance.md`). Authoritative rules: `rules/M14_provenance_database.md`, `rules/COMMON_RULES.md`.

## 1. Identity & Purpose
- **Module ID:** M14
- **Name:** Provenance & Database — Database Component
- **Folder:** `src/eclair/database/` (+ Alembic migrations under `deployment/migrations/alembic/`)
- **Tests:** `tests/unit/database/`
- **Purpose:** Provide the database engine, transaction/session management, ORM models, and repositories needed to persist and retrieve everything required to reproduce, explain, and audit ECLAIR reliability decisions.

## 2. Responsibilities & Non-Responsibilities

### Responsibilities
- Manage SQLAlchemy 2 database engines, connection resolution, and credential sanitization.
- Provide scoped session lifecycle and atomic transaction management with automatic rollback on errors.
- Define ORM models for all query-to-decision lineage entities anchored by `query_id`.
- Provide typed repository interfaces for queries, claims, evidence, verifications, confidence, decisions/risks, and audit logs.
- Provide versioned Alembic database migrations matching the ORM schema.

### Non-Responsibilities
- Does NOT compute confidence, calibrated ECS, hallucination, or consensus signals (M07–M11).
- Does NOT make risk-based actions or decisions (M13).
- Does NOT expose HTTP REST endpoints (M15).
- Does NOT implement user interface views (M17).

## 3. Implemented Architecture & Data Flow

```text
Pipeline outputs (EclairResult)
         │
         ▼
M14 ProvenanceService (`src/eclair/provenance/service.py`)
         │
         ▼
M14 Database Repositories (`src/eclair/database/repositories/`)
         │
         ▼
SQLAlchemy 2 ORM Models (`src/eclair/database/models/`)
         │
         ▼
Engine / Session Manager (`src/eclair/database/session.py`)
         │
         ▼
PostgreSQL / SQLite (`queries`, `claims`, `evidence`, etc.)
```

## 4. ORM Models & Database Schema

All tables use `query_id` as the foreign key with `ondelete="CASCADE"`, anchoring the entire lineage to the query:

| Model | Table | Key Fields | Description |
|---|---|---|---|
| `QueryModel` | `queries` | `query_id` (PK), `question`, `final_answer`, `created_at` | Lineage root query entry |
| `ClaimModel` | `claims` | `claim_id` (PK), `query_id` (FK), `text`, `claim_type`, `position`, `created_at` | Extracted atomic claims (ordered) |
| `EvidenceModel` | `evidence` | `evidence_id` (PK), `query_id` (FK), `text`, `source`, `relevance_score`, `created_at` | Retrieved evidence passages |
| `VerificationModel` | `verifications` | `id` (PK), `query_id` (FK), `claim_id`, `status`, `evidence_ids` (JSON), `created_at` | Per-claim verification outcomes |
| `ConfidenceModel` | `confidences` | `id` (PK), `query_id` (FK unique), `raw_confidence`, `calibrated_ecs`, `created_at` | Raw & calibrated ECS confidence |
| `ConsensusModel` | `consensus_records` | `id` (PK), `query_id` (FK unique), `agreement_score`, `consensus_level`, `majority_answer`, `details`, `created_at` | Multi-model consensus evaluation |
| `RiskModel` | `risks` | `id` (PK), `query_id` (FK unique), `risk_level`, `risk_score`, `created_at` | Risk classification |
| `DecisionModel` | `decisions` | `id` (PK), `query_id` (FK unique), `action`, `reason`, `created_at` | Selected action (RETURN, ABSTAIN, etc.) |
| `FeedbackModel` | `feedbacks` | `feedback_id` (PK), `query_id` (FK), `rating`, `feedback_text`, `user_id`, `created_at` | User quality feedback |
| `AuditModel` | `audit_logs` | `audit_id` (PK), `query_id` (FK unique), `timestamp`, `final_answer`, `decision_action`, `summary` (JSON), `created_at` | Reconstructed decision summary |

## 5. Repositories

- `QueryRepository`: CRUD operations, listing, and final answer updates for `QueryModel`.
- `ClaimRepository`: Batch creation and ordered position-based retrieval of `ClaimModel`.
- `EvidenceRepository`: Batch persistence and retrieval of `EvidenceModel`.
- `VerificationRepository`: Persistence and lookup of `VerificationModel` per claim.
- `ConfidenceRepository`: Upsert and retrieval of raw and calibrated confidence scores.
- `DecisionRepository`: Upsert and retrieval of `DecisionModel` and `RiskModel`.
- `AuditRepository`: Persistence of `AuditModel`, consensus, feedback, and eager multi-join retrieval via `get_full_lineage(query_id)`.

## 6. Configuration & Secrets Handling

Database URL resolution precedence in `resolve_database_url()`:
1. Explicit `url` argument.
2. `config.database_url` on provided `EclairConfig`.
3. `ECLAIR_DATABASE_URL` environment variable.
4. `DATABASE_URL` environment variable.
5. Safe fallback: `sqlite:///:memory:` for tests and local execution.

Credentials are sanitized using `sanitize_database_url()` to ensure passwords are never leaked into logs, tracebacks, or representations.

## 7. Alembic Migrations

Migrations live in `deployment/migrations/alembic/`:
- Configuration: `deployment/migrations/alembic/alembic.ini`
- Environment: `deployment/migrations/alembic/env.py`
- Revisions: `deployment/migrations/alembic/versions/001_initial_m14_schema.py`

### Running Migrations
```bash
# Upgrade to latest revision
alembic -c deployment/migrations/alembic/alembic.ini upgrade head

# Rollback migration
alembic -c deployment/migrations/alembic/alembic.ini downgrade -1
```

## 8. Error Handling & Transaction Guarantees

- All writes within `DatabaseSessionManager.session()` execute in a single atomic transaction.
- If any operation fails or an error is raised, the transaction rolls back immediately.
- Low-level database errors are wrapped into M01 `ModuleError` with code `database_transaction_error`.
- Partial writes never silently corrupt the audit trail.

## 9. Verification & Test Results

Tested in `tests/unit/database/`:
- `test_database.py`: URL resolution, credential sanitization, engine creation, table init/drop.
- `test_database_models.py`: All 10 models, JSON data types, foreign keys, cascade deletes.
- `test_repositories.py`: Query, claim, evidence, verification, confidence, decision, audit repositories.
- `test_session.py`: Commit, rollback on exception, transaction error wrapping.
- `test_migrations.py`: Safe in-memory/temp database migration upgrade and downgrade validation.

All 17 database tests pass.

## 10. Known Limitations

- Unit tests validate schema and constraints using SQLite (with SQLAlchemy JSON compatibility).
- In production, PostgreSQL provides native JSONB indexing; PostgreSQL-specific performance optimizations should be verified against a live PostgreSQL staging database.

# M14 — Provenance & Database — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M14 — Provenance & Database
IDENTIFIER: M14

PURPOSE:
  Store everything needed to reproduce, explain and audit reliability decisions.

RESPONSIBILITY:
  - Persist Query, Claims, Evidence, Verification, Confidence, Consensus, Risk, Decision,
    Final Answer, Feedback and Timestamp.
  - Reconstruct why a decision was made (keyed by query_id).
  - Provide database repositories and migrations.

NON-RESPONSIBILITY:
  - Does NOT compute any reliability signal or decision (only persists them).
  - Does NOT expose HTTP endpoints (that is M15).

LOCATION:
  src/eclair/provenance/  and  src/eclair/database/
EXISTING FOLDERS USED:
  src/eclair/provenance/  (tracker.py, audit.py, service.py)
  src/eclair/database/    (database.py, session.py, models/, repositories/)
  deployment/migrations/alembic/
  tests/unit/provenance/  and  tests/unit/database/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts (domain data to persist).
  External: PostgreSQL, SQLAlchemy 2, Alembic.
  Configuration: DB connection via M01 config.

INPUTS:
  Source: pipeline outputs from the engine (all stages).
  Format: M01 contracts -> ORM models in src/eclair/database/models/.
  Validation: validate before persistence.

PROCESSING:
  New logic: persistence + provenance tracking keyed by query_id; migrations via Alembic.

OUTPUTS:
  Format: persisted rows + a reconstructable decision path per query_id.
  Destination: consumed by M15 API (explain), M17 Dashboard (audit) via the engine/API.

CONSUMERS:
  Module/service: engine, M15 (explain endpoint), M17 (audit view).
  Expected contract: given a query_id, return the full lineage/audit trail.

INTEGRATION POINTS:
  APIs used: none. APIs exposed: repository/service interfaces.
  Database: PostgreSQL (owns schema in database/models/ + migrations).
  Events/Queues: none. Configuration: M01 (DB URL). Auth: DB credentials via config only.

ERROR HANDLING: use M01 exceptions; do not silently drop provenance records.
VALIDATION RULES: required lineage fields persisted; query_id is the reconstruction key.
INTEGRATION REQUIREMENTS: audit must reconstruct the decision path.

DO NOT CHANGE: M01 contracts; any other module folder; do not migrate DB without requirement.
REUSE RULES: reuse SQLAlchemy/Alembic; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only persistence + provenance + migrations/repositories.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: persistence + provenance/audit.
  Does NOT handle: reliability computation, HTTP exposure.

VERIFICATION BEFORE COMPLETE:
  - Given a query_id, the decision path is reproducible with a complete audit trail.
  - Repositories and migrations exist and run.
  - tests/unit/provenance/ and tests/unit/database/ pass; docs/modules/provenance.md and
    docs/modules/database.md written.
```

# ECLAIR — Contribution Guide

> Derived only from the Spec and the repository's `rules/` files. This guide tells a developer or AI
> agent how to contribute a module to ECLAIR without breaking the multi-developer contract.

## 1. Golden rule: never assume, never invent
Use only information confirmed by: explicit task requirements → this repository → repository
conventions → shared contracts → the Spec (`rules/COMMON_RULES.md` §1, §18). Do not invent a folder,
file, API, model, database field, dependency, configuration value, workflow, behavior, or
integration point. If something is undefined, STOP and surface the gap.

## 2. Read first (in order)
1. `rules/COMMON_RULES.md` (all rules + the CONDITIONS gates)
2. `rules/SHARED_CONTRACTS_REFERENCE.md` (frozen names/enums/interfaces/endpoints)
3. `rules/M<NN>_*.md` (your module contract)
4. `docs/architecture/system_architecture.md`, `docs/architecture/pipeline.md`
5. `docs/modules/<module>.md` (your module doc)

## 3. Scope boundaries (must remain true at all times — `COMMON_RULES.md` §B)
- Modify files **only inside your module's folder(s)**, its `tests/unit/<module>/`, and its
  `docs/modules/<module>.md`.
- Do NOT edit `src/eclair/contracts/`, `src/eclair/config.py`, or `src/eclair/exceptions.py` unless
  your module IS M01.
- Do NOT edit root `pyproject.toml` / `uv.lock` unless your module IS M01; propose dependency
  additions through M01/integration, only from the approved stack.
- Add NO functionality beyond your module's required list (Spec §4.8, per-module doc).
- Introduce NO enum member, field, endpoint, method, or interface not already frozen in
  `SHARED_CONTRACTS_REFERENCE.md`.

## 4. Reuse priority
Always: **reuse → extend → modify → create** (`COMMON_RULES.md` §14). Do not duplicate existing
functionality, do not refactor unrelated code, do not "future-proof".

## 5. Shared contracts are mandatory (Spec §4.1)
All inter-module data flows through the M01 contracts in `src/eclair/contracts/`. Do not redefine,
duplicate, or locally reinvent a shared contract. If a contract you need does not exist, raise it as
a gap for M01 — do not invent it in your module.

## 6. Reliability invariants you must not violate
- RAG is not verification (Spec §4.5).
- Model agreement is not truth (Spec §4.6).
- Raw confidence (M10) is not calibrated ECS; only M11 produces calibrated ECS (Spec §4.4).
- No evidence → `UNKNOWN`, never `SUPPORTED` (Spec §4.9).
- API/SDK/Dashboard stay thin — no reliability logic in them (Spec §4.12).

## 7. Dependencies (Spec §4.10, §4.11)
Use only the approved stack (`SHARED_CONTRACTS_REFERENCE.md` §9). Do not add Kubernetes, Kafka,
microservices, Neo4j, Elasticsearch, fine-tuned models, heavy agent frameworks, or paid
observability. Ollama is the permanent zero-cost fallback; optional providers use free quotas only.

## 8. Definition of Done (Spec §4.8)
Implementation + unit tests (passing) + sample input + sample output + `docs/modules/<module>.md` +
no breaking contract changes + existing functionality still works + Ruff passes + clean diff.

## 9. Required report after implementation (`COMMON_RULES.md` §17)
Provide only: **Changes Made**, **Why**, **Integration** (`Input → Module → Output → Consumer`),
**Verification**. No unrelated explanations.

## 10. Forbidden (automatic fail — `COMMON_RULES.md` §E)
Inventing a folder/file/API/model/field/dependency/config/flow/behavior; redefining or duplicating a
shared contract or another module's logic; putting reliability logic into API/SDK/Dashboard; mapping
no-evidence to SUPPORTED; calling raw confidence a calibrated ECS; refactoring/renaming/optimizing
code outside your module.

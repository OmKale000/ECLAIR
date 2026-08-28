# ECLAIR — Common AI Development Rules (READ FIRST)

**Applies to:** every module (M01–M18) and every developer / AI agent working on this repository.
**Authority:** These rules are derived only from the ECLAIR repository state and the authoritative
specification *"ECLAIR Prototype v1 — Updated Modular Development Specification"* (the "Spec").
**Status of this branch:** `Rules` is the team's common base branch. It contains the agreed folder
structure and module contracts only. It contains **no module implementation**.

---

## 0. How to use this repository

1. Create your feature branch **from `Rules`** (e.g. `feature/llm-gateway`).
2. Read, in order: this `COMMON_RULES.md`, then `rules/SHARED_CONTRACTS_REFERENCE.md`, then your
   module's `rules/M<NN>_*.md`.
3. Use `rules/MODULE_PROMPT_TEMPLATE.md` as the prompt you give to your AI agent for the module.
4. Satisfy the PRE-FLIGHT conditions (see CONDITIONS §A below) before writing any code.
5. Implement **only** your assigned module, inside **only** your module's folder.
6. Ship implementation + unit tests + sample input/output + module doc (see Spec §4.8) and pass the
   COMPLETION gate (CONDITIONS §D).

---

## 1. Never assume, never invent

- Use only information confirmed by: explicit task requirements → this repository → repository
  conventions → shared contracts → the Spec.
- Do **not** invent a folder, file, API, model, database field, dependency, configuration value,
  workflow, behavior, or integration point.
- If something is not defined, **stop and surface the gap** — do not fill it with an assumption.
- Do not create something merely because it "seems architecturally reasonable".

## 2. Shared contracts are mandatory and owned by M01 (Spec §4.1)

- All inter-module data flows through the shared Pydantic contracts in `src/eclair/contracts/`.
- Only **M01 (Foundation & Shared Contracts)** may define or change files in `src/eclair/contracts/`.
- No other module may redefine, duplicate, or locally reinvent a shared contract.
- If a contract you need does not exist, do not invent it in your module — raise it as a gap for M01.

Canonical contract-producing interfaces (Spec §4.1, §4.3):
```
ClaimExtractor      -> list[Claim]
Retriever           -> list[Evidence]
Verifier            -> VerificationResult
ConfidenceEstimator -> ConfidenceResult
DecisionEngine      -> DecisionResult
Engine              -> EclairResult
```

## 3. Module boundaries are strict

- Each module has exactly one folder (see its rules file). Work only inside it.
- Do **not** modify another module's files, rename its files/classes/functions, or move
  functionality between modules.
- Do **not** change folder ownership.
- Do **not** refactor, "clean up", or optimize code outside your module.

## 4. Pipeline ownership is separate from module ownership (Spec §4.2)

- You may own a module (e.g. RAG), but the overall pipeline and integration flow is owned by the
  **engine/orchestrator** (`src/eclair/engine/`) during the integration phase.
- Do not wire modules together yourself outside your module boundary unless your module *is* the
  engine/orchestrator (M01/integration scope).

## 5. Interfaces everywhere (Spec §4.3)

- Provider and module implementations must conform to stable interfaces/Protocols.
- Do not change an interface signature that other modules depend on.

## 6. Reliability semantics that must not be violated

- **RAG is not verification (Spec §4.5):** retrieving a document is not proof. Verification is a
  separate explicit step (M07).
- **Model agreement is not truth (Spec §4.6):** consensus (M09) is one signal only.
- **Raw confidence is not calibrated ECS (Spec §4.4):** M10 produces *raw* confidence only.
  A calibrated ECS is produced *only* by M11 after calibration against observed correctness.
- **No evidence -> UNKNOWN, never SUPPORTED (Spec §4.9):** verification must map absence of
  evidence to `UNKNOWN`.

## 7. Product layers must stay thin (Spec §4.12)

- API (M15), SDK (M16) and Dashboard (M17) consume the integrated engine.
- They must **not** independently implement claim verification, confidence fusion, hallucination
  detection, or risk/decision logic.

## 8. Do not add unrequested functionality

- Implement only what your module's contract requires.
- No extra endpoints, fields, validation, logging systems, services, abstractions, UI, or config.
- No "future-proofing".

## 9. Dependency rules

- The approved Prototype v1 stack (Spec §4.10) is: Python 3.12, FastAPI, FAISS,
  sentence-transformers, HuggingFace Transformers, PostgreSQL/SQLAlchemy 2/Alembic, Streamlit,
  scikit-learn, Pandas, NumPy, Matplotlib/Plotly, HTTPX, Pydantic v2, Ollama, Docker, uv, pytest,
  Ruff, GitHub Actions.
- **Do not** add Kubernetes, Kafka, microservices, Neo4j, Elasticsearch, fine-tuned models,
  heavy agent frameworks, or paid observability (Spec §4.10).
- Do not add a new library if the approved stack or existing code already satisfies the need.
- Do not upgrade unrelated dependencies or churn the lockfile unnecessarily.
- Only M01 owns root `pyproject.toml`/`uv.lock`; propose dependency additions through M01/integration.

## 10. Configuration rules

- Reuse the shared configuration mechanism in `src/eclair/config.py` (owned by M01).
- Do not hardcode values that belong in configuration. Do not add env vars unless required by your
  module's contract.

## 11. Error handling & validation

- Use the shared exception types in `src/eclair/exceptions.py` (owned by M01).
- Do not introduce a new error format. Do not silently swallow errors. Do not invent fallback
  behavior beyond what the contract specifies.
- Validate inputs at the module boundary using the shared contracts.

## 12. Free-tier / zero-cost rule (Spec §4.11)

- Ollama is the permanent zero-cost fallback. Gemini/Groq/OpenRouter are optional providers via free
  quotas only. ECLAIR must not depend on paid or temporary trials.

## 13. Controlled knowledge base (Spec §4.7)

- Prototype v1 uses the deterministic controlled knowledge base under `data/knowledge_base/`
  (refund_policy, customer_policy, invoice_policy, product_policy, company_policy).
- Do not add live web-search dependence in Prototype v1.

## 14. Reuse priority

Always follow: **reuse → extend → modify → create**, in that order.

## 15. Definition of Done for any module (Spec §4.8)

A module branch is complete only when it ships:
- Implementation (inside the module folder only)
- Unit tests (in the module's `tests/unit/<module>/` folder)
- Sample input and sample output
- Module documentation (`docs/modules/<module>.md`)
- No breaking changes to shared contracts
- Existing functionality still works

## 16. Cross-module consistency (never independently redefine)

Never independently redefine any of these — check the repo/contract first and reuse it:
API contracts · data models · naming conventions · folder conventions · shared utilities ·
error formats · auth behavior · configuration mechanism · service interfaces · event/message formats.

## 17. Required report after implementing a module

Report only:
- **Changes Made** — `<file/path> — what changed`
- **Why** — one line per change tied to the module requirement
- **Integration** — `Input → Module → Output → Consumer`
- **Verification** — exactly what was tested/verified

## 18. Non-negotiables

Do not assume · Do not invent · Do not redesign · Do not refactor unrelated code ·
Do not add functionality outside the requirement · Do not change existing contracts unnecessarily ·
Do not duplicate existing functionality · Do not create unnecessary files/dependencies ·
Do not modify unrelated modules · Do not break existing integration · Do not silently change behavior ·
Always inspect the repository before implementation.

---

## Module map (identity → folder → rules file)

| ID  | Module | Primary folder | Rules file |
|-----|--------|----------------|------------|
| M01 | Foundation & Shared Contracts | `src/eclair/` (+ `contracts/`, `engine/`, `config.py`, `exceptions.py`, `version.py`) | `rules/M01_foundation.md` |
| M02 | LLM Gateway | `src/eclair/llm/` | `rules/M02_llm_gateway.md` |
| M03 | Claim Extraction | `src/eclair/claims/` | `rules/M03_claim_extraction.md` |
| M04 | Document Ingestion | `src/eclair/ingestion/` | `rules/M04_document_ingestion.md` |
| M05 | RAG / Evidence Retrieval | `src/eclair/rag/` | `rules/M05_rag_evidence_retrieval.md` |
| M06 | Evidence Quality & Conflict Detection | `src/eclair/evidence/` | `rules/M06_evidence_quality.md` |
| M07 | Claim Verification | `src/eclair/verification/` | `rules/M07_claim_verification.md` |
| M08 | Hallucination Detection | `src/eclair/hallucination/` | `rules/M08_hallucination_detection.md` |
| M09 | Multi-Agent / Multi-Model Consensus | `src/eclair/consensus/` | `rules/M09_consensus.md` |
| M10 | Confidence Estimation | `src/eclair/confidence/` | `rules/M10_confidence_estimation.md` |
| M11 | ECS Calibration | `src/eclair/calibration/` | `rules/M11_ecs_calibration.md` |
| M12 | Self-Reflection & Self-Correction | `src/eclair/reflection/` | `rules/M12_reflection.md` |
| M13 | Risk & Decision Engine | `src/eclair/risk/` | `rules/M13_risk_decision.md` |
| M14 | Provenance & Database | `src/eclair/provenance/`, `src/eclair/database/` | `rules/M14_provenance_database.md` |
| M15 | ECLAIR REST API | `src/eclair/api/` | `rules/M15_rest_api.md` |
| M16 | Python SDK | `sdk/python/` | `rules/M16_python_sdk.md` |
| M17 | Dashboard | `dashboard/` | `rules/M17_dashboard.md` |
| M18 | Evaluation, Benchmarking & Deployment | `evaluation/`, `deployment/` | `rules/M18_evaluation_deployment.md` |

## Recommended implementation order (Spec §6)

- Wave 1 — Foundation: M01, M02, M03
- Wave 2 — Knowledge & Verification: M04, M05, M06, M07
- Wave 3 — Reliability: M08, M09, M10, M11
- Wave 4 — Decision & Audit: M12, M13, M14
- Wave 5 — Product Interfaces: M15, M16, M17
- Wave 6 — Proof & Release: M18

---

## CONDITIONS (hard gates — an AI/developer MUST obey these)

These are pass/fail conditions. If any PRE-FLIGHT condition is not satisfiable, **STOP and report
the gap** — do not proceed with an assumption.

### A. PRE-FLIGHT conditions (must all be TRUE before writing any code)

1. You are on a feature branch created **from `Rules`** (e.g. `feature/<module>`), not on `Rules`
   or `main` directly.
2. You have read `rules/COMMON_RULES.md`, `rules/SHARED_CONTRACTS_REFERENCE.md`, and your module's
   `rules/M<NN>_*.md` in full.
3. Your assigned module ID and its folder are confirmed from the module map above.
4. Every shared name/enum/interface/endpoint you will use already exists in
   `SHARED_CONTRACTS_REFERENCE.md`. If one is missing, STOP (do not invent it).
5. Upstream module contracts you depend on already exist in the repo, OR are stubbed by M01/known
   contracts. If an upstream contract is undefined, STOP and report.

### B. SCOPE conditions (must remain TRUE at all times)

6. You modify files **only inside your module's folder(s)** (and its `tests/unit/<module>/`,
   `docs/modules/<module>.md`). Touching any other module's files is FORBIDDEN.
7. You do **not** edit `src/eclair/contracts/`, `src/eclair/config.py`, or
   `src/eclair/exceptions.py` unless your module IS M01.
8. You do **not** edit root `pyproject.toml` / `uv.lock` unless your module IS M01; new dependencies
   are proposed through M01/integration, and only from the approved stack.
9. You add **no** functionality beyond your module's REQUIRED functionality list.
10. You introduce **no** enum member, field, endpoint, method, or interface not already frozen in
    `SHARED_CONTRACTS_REFERENCE.md`.

### C. STOP conditions (halt and report instead of guessing)

- A required input source, contract, field, or enum is undefined anywhere in the repo/Spec.
- Two specs/files appear to conflict.
- Implementing your module correctly would require changing another module or a shared contract.
- A required dependency is outside the approved stack.

### D. COMPLETION gate (module is NOT done unless ALL are TRUE — Spec §4.8)

11. Implementation exists **only** inside the module folder(s).
12. Unit tests exist in `tests/unit/<module>/` and pass.
13. A sample input and sample output are provided.
14. Module documentation `docs/modules/<module>.md` is written.
15. The module's INPUT contract and OUTPUT contract match `SHARED_CONTRACTS_REFERENCE.md` exactly.
16. No shared contract, other module, API contract, or folder ownership was changed.
17. Ruff lint passes and no unrelated files appear in the diff.
18. The post-implementation report (COMMON_RULES §17) is provided.

### E. FORBIDDEN outputs (automatic fail)

- Inventing a folder/file/API/model/field/dependency/config/flow/behavior.
- Redefining or duplicating a shared contract or another module's logic.
- Putting reliability logic into API/SDK/Dashboard (they stay thin, Spec §4.12).
- Mapping "no evidence" to SUPPORTED (must be UNKNOWN, Spec §4.9).
- Calling raw confidence a calibrated ECS before M11 calibration (Spec §4.4).
- Refactoring/renaming/optimizing code outside the module scope.

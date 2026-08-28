# ECLAIR — Prototype v1

> Derived only from *"ECLAIR Prototype v1 — Updated Modular Development Specification"* (the "Spec")
> and the repository state. This README orients any developer or AI agent to the **`Rules` branch
> baseline**. It contains no invented architecture.

ECLAIR Prototype v1 is a single modular reliability product — **REST API + Python SDK + Web
Dashboard** — built on one shared reliability pipeline. One request travels through the full pipeline
and produces a **traceable decision**, accessible identically through the API, the SDK, and the
Dashboard (Spec §7).

## What this branch is

`Rules` is the team's common base branch. It contains the agreed **folder structure**, **module
contracts**, and **documentation** only — **no module implementation**. Each developer/AI creates a
feature branch from `Rules`, reads the rules for their assigned module, and implements only that
module.

## Start here (read in order)

1. `rules/COMMON_RULES.md` — non-negotiable rules + hard CONDITIONS gates.
2. `rules/SHARED_CONTRACTS_REFERENCE.md` — frozen contract names, enums, interfaces, endpoints.
3. `rules/M<NN>_*.md` — your assigned module's contract.
4. `rules/MODULE_PROMPT_TEMPLATE.md` — the prompt to give your AI agent.
5. `docs/architecture/` — system architecture, pipeline, components, sequence diagrams.
6. `docs/modules/<module>.md` — your module's documentation.
7. `docs/development/` — workflow, contribution guide, module contracts, testing.
8. `docs/api/` and `docs/deployment/` — API endpoints/examples and deployment/CI.

## Modules (Spec §2)

M01 Foundation & Shared Contracts · M02 LLM Gateway · M03 Claim Extraction · M04 Document Ingestion ·
M05 RAG / Evidence Retrieval · M06 Evidence Quality & Conflict Detection · M07 Claim Verification ·
M08 Hallucination Detection · M09 Multi-Agent / Multi-Model Consensus · M10 Confidence Estimation ·
M11 ECS Calibration · M12 Self-Reflection & Self-Correction · M13 Risk & Decision Engine ·
M14 Provenance & Database · M15 REST API · M16 Python SDK · M17 Dashboard ·
M18 Evaluation, Benchmarking & Deployment.

See `docs/architecture/system_architecture.md` for the full module map and folder ownership.

## Pipeline (Spec §5, §7)

```
Question -> LLM Answer -> Claims -> Evidence -> Verification -> Hallucination Analysis
-> Model Agreement -> Raw Confidence -> Calibrated ECS -> Risk Decision
-> Final Answer / Abstain / Human Review
```

Full flow: `docs/architecture/pipeline.md`.

## Non-negotiable reliability semantics

- RAG is not verification (Spec §4.5).
- Model agreement is not truth (Spec §4.6).
- Raw confidence (M10) is not calibrated ECS — only M11 produces calibrated ECS (Spec §4.4).
- No evidence → `UNKNOWN`, never `SUPPORTED` (Spec §4.9).
- API / SDK / Dashboard stay thin — no reliability logic in them (Spec §4.12).

## Technology (Spec §4.10, §4.11)

Python 3.12 · FastAPI · Uvicorn · FAISS · sentence-transformers · HuggingFace Transformers ·
PostgreSQL · SQLAlchemy 2 · Alembic · Streamlit · Plotly/Matplotlib · scikit-learn · Pandas · NumPy ·
HTTPX · Pydantic v2 · Ollama · Docker · Docker Compose · uv · pytest · Ruff · GitHub Actions.

**Forbidden in v1:** Kubernetes, Kafka, microservices, Neo4j, Elasticsearch, fine-tuned models,
heavy agent frameworks, paid observability. **Ollama is the permanent zero-cost fallback.**

## Definition of Done for a module (Spec §4.8)

Implementation + passing unit tests + sample input + sample output + `docs/modules/<module>.md`,
with no breaking contract changes, Ruff passing, and a clean module-scoped diff. See
`docs/development/development_workflow.md`.

## Implementation order (Spec §6)

Wave 1: M01, M02, M03 · Wave 2: M04–M07 · Wave 3: M08–M11 · Wave 4: M12–M14 ·
Wave 5: M15–M17 · Wave 6: M18.

## License

See `LICENSE`.

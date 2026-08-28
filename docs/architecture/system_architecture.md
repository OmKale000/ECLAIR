# ECLAIR — System Architecture

> **Authority.** This document is derived only from *"ECLAIR Prototype v1 — Updated Modular
> Development Specification"* (the "Spec") and the repository state. It contains no invented
> architecture. If a detail is not here, it is not defined yet — raise it as a gap for M01, do not
> assume it. Read `rules/COMMON_RULES.md` and `rules/SHARED_CONTRACTS_REFERENCE.md` before any work.

## 1. What ECLAIR is

ECLAIR Prototype v1 is a **single modular product architecture** — REST API + Python SDK + Web
Dashboard — built on one shared reliability pipeline. It is not three disconnected demonstrations
(Spec §7). One request must travel through the full reliability pipeline and produce a **traceable
decision** (Spec §7).

The system is developed **module by module by multiple developers / AI agents**. Modules are
separately owned for development, but they must consume and produce **common contracts** (Spec §4.1).

## 2. Module inventory (Spec §2)

| ID  | Module | Main responsibility |
|-----|--------|---------------------|
| M01 | Foundation & Shared Contracts | Common architecture, typed contracts, validation and shared data models. |
| M02 | LLM Gateway | Provider abstraction, routing, retries, fallbacks and model selection. |
| M03 | Claim Extraction | Convert generated answers into normalized atomic factual claims. |
| M04 | Document Ingestion | Load PDF, TXT and Markdown knowledge sources into standardized documents. |
| M05 | RAG / Evidence Retrieval | Chunk, embed, index, retrieve and optionally rerank relevant evidence. |
| M06 | Evidence Quality & Conflict Detection | Score relevance, authority, freshness, completeness and conflict. |
| M07 | Claim Verification | Verify each claim against evidence using NLI and optional LLM verification. |
| M08 | Hallucination Detection | Detect unsupported, contradicted or suspicious claims. |
| M09 | Multi-Agent / Multi-Model Consensus | Measure agreement across independent model outputs. |
| M10 | Confidence Estimation | Fuse reliability signals into raw claim and response confidence. |
| M11 | ECS Calibration | Convert raw confidence into a calibrated Epistemic Confidence Score. |
| M12 | Self-Reflection & Self-Correction | Critique, rewrite, regenerate and re-verify low-confidence answers. |
| M13 | Risk & Decision Engine | Select return, verify-more, regenerate, abstain, human-review or block. |
| M14 | Provenance & Database | Persist query-to-decision lineage and complete audit history. |
| M15 | ECLAIR REST API | Expose the integrated ECLAIR engine to external applications. |
| M16 | Python SDK | Provide a thin, developer-friendly interface over the REST API. |
| M17 | Dashboard | Provide visual monitoring, verification, calibration and audit views. |
| M18 | Evaluation, Benchmarking & Deployment | Benchmark reliability, generate reports and make the system reproducible. |

## 3. Layered view

```
+-----------------------------------------------------------------------+
|  PRODUCT LAYER  (thin — Spec §4.12)                                   |
|   M15 REST API   |   M16 Python SDK   |   M17 Dashboard               |
|   (consume the integrated engine; NO reliability logic here)          |
+-----------------------------------------------------------------------+
|  ORCHESTRATION LAYER                                                  |
|   src/eclair/engine/  (eclair_engine, pipeline, orchestrator)         |
|   Owns the final integrated flow (Spec §4.2)                          |
+-----------------------------------------------------------------------+
|  RELIABILITY LAYER  (module-owned reliability steps)                  |
|   M03 Claims  M04 Ingestion  M05 RAG  M06 Evidence  M07 Verification  |
|   M08 Hallucination  M09 Consensus  M10 Confidence  M11 Calibration   |
|   M12 Reflection  M13 Risk/Decision                                   |
+-----------------------------------------------------------------------+
|  PROVIDER / PERSISTENCE LAYER                                         |
|   M02 LLM Gateway (Ollama/Gemini/Groq/OpenRouter)                     |
|   M14 Provenance & Database (PostgreSQL / SQLAlchemy 2 / Alembic)     |
+-----------------------------------------------------------------------+
|  FOUNDATION LAYER                                                     |
|   M01 contracts/ · config.py · exceptions.py · version.py · engine    |
+-----------------------------------------------------------------------+
|  KNOWLEDGE BASE (controlled — Spec §4.7)                              |
|   data/knowledge_base/ refund/customer/invoice/product/company policy |
+-----------------------------------------------------------------------+
```

## 4. Ownership rules

- **Module ownership vs pipeline ownership are separate (Spec §4.2).** A developer may own a module
  (e.g. RAG), but the overall ECLAIR pipeline and integration flow is owned by the
  engine/orchestrator during the integration phase. Do not wire modules together outside your module
  boundary unless your module *is* the engine/orchestrator.
- **Shared contracts are mandatory and owned by M01 (Spec §4.1).** All inter-module data flows
  through the shared contracts in `src/eclair/contracts/`. Only M01 may define or change them.
- **Interfaces everywhere (Spec §4.3).** Provider and module implementations conform to stable
  interfaces / Protocols (e.g. `LLMProvider.generate`, `Retriever`, `Verifier`, `ClaimExtractor`,
  `Calibrator`). Do not change a signature other modules depend on.

## 5. Non-negotiable reliability semantics

These invariants come directly from the Spec and must never be violated by any module:

- **RAG is not verification (Spec §4.5).** Retrieving a document ("I found this document") is not
  proof; verification ("this document actually supports the claim") is a separate explicit step (M07).
- **Model agreement is not truth (Spec §4.6).** Consensus (M09) is one signal only; it must be
  combined with evidence, verification, source quality and calibration.
- **Raw confidence is not calibrated ECS (Spec §4.4).** M10 produces *raw* confidence only. A
  calibrated Epistemic Confidence Score is produced *only* by M11 after calibration against observed
  correctness.
- **No evidence → UNKNOWN, never SUPPORTED (Spec §4.9).** Verification must map absence of evidence
  to `UNKNOWN`.
- **Product layers stay thin (Spec §4.12).** API, SDK and Dashboard must not independently implement
  claim verification, confidence fusion, hallucination detection or risk/decision logic.

## 6. Approved technology stack (Spec §4.10, §4.11)

Python 3.12 · FastAPI · Uvicorn · FAISS · sentence-transformers · HuggingFace Transformers ·
PostgreSQL · SQLAlchemy 2 · Alembic · Streamlit · Plotly/Matplotlib · scikit-learn · Pandas · NumPy ·
HTTPX · Pydantic v2 · Ollama · Docker · Docker Compose · uv · pytest · Ruff · GitHub Actions.

**Do not over-engineer Prototype v1 (Spec §4.10).** Forbidden in v1: Kubernetes, Kafka,
microservices, Neo4j, Elasticsearch, custom fine-tuned models, complex agent frameworks, paid
observability platforms.

**Free-tier rule (Spec §4.11).** Ollama is the permanent zero-cost fallback. Gemini, Groq and
OpenRouter are optional providers via free quotas only; ECLAIR must not depend on temporary trials.

## 7. What must ultimately be demonstrated (Spec §7)

At the end of Prototype v1, one request must travel through the full reliability pipeline and produce
a traceable decision, and the **same result must be accessible through the REST API, the Python SDK,
and the ECLAIR Dashboard**. See `pipeline.md` for the end-to-end flow and `sequence_diagrams.md` for
the request-level flows.

## 8. Related documents

- `docs/architecture/pipeline.md` — the end-to-end integration flow (Spec §5, §7).
- `docs/architecture/component_diagram.md` — components and their contract-level relationships.
- `docs/architecture/sequence_diagrams.md` — request sequences (high-ECS, low-ECS reflection, etc.).
- `docs/modules/*.md` — per-module documentation (one file per reliability module).
- `docs/api/endpoints.md`, `docs/api/examples.md` — the six versioned endpoints (Spec §M15).

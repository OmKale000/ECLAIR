# ECLAIR — Component Diagram

> Derived only from the Spec (§1 folder structure, §2 modules, §4 rules). No invented components.
> Every component below maps to a real folder in `src/` per Spec §1.

## 1. Component map (folder ⇄ module)

```
src/eclair/
  __init__.py  config.py  exceptions.py  version.py        <- M01 Foundation
  contracts/        query claim evidence verification        <- M01 (owned)
                    confidence risk decision result
  engine/           eclair_engine  pipeline  orchestrator     <- Orchestration (owns flow, §4.2)
  llm/              base router factory ollama gemini groq     <- M02 LLM Gateway
                    openrouter
  claims/           extractor normalizer deduplicator          <- M03 Claim Extraction
                    classifier models
  ingestion/        loader pdf_loader text_loader              <- M04 Document Ingestion
                    markdown_loader metadata
  rag/              chunker embeddings index retriever          <- M05 RAG / Evidence Retrieval
                    reranker models
  evidence/         scorer authority freshness conflict         <- M06 Evidence Quality
                    models
  verification/     verifier nli llm_verifier aggregator        <- M07 Claim Verification
                    models
  hallucination/    detector signals scoring models             <- M08 Hallucination Detection
  consensus/        runner voting agreement diversity models    <- M09 Consensus
  confidence/       estimator signals fusion models             <- M10 Confidence Estimation
  calibration/      calibrator isotonic temperature metrics      <- M11 ECS Calibration
                    reliability models
  reflection/       controller critic rewriter stopping models  <- M12 Self-Reflection
  risk/             classifier policy thresholds decision        <- M13 Risk & Decision Engine
                    models
  provenance/       tracker audit service                        <- M14 Provenance
  database/         database session models/ repositories/       <- M14 Database
  api/              main dependencies middleware routes/          <- M15 REST API
                    schemas/

dashboard/          app api_client components/ pages/            <- M17 Dashboard
sdk/python/eclair/  client models exceptions utils              <- M16 Python SDK
evaluation/         datasets baselines runners metrics           <- M18 Evaluation
                    calibration reports notebooks
deployment/         Dockerfile.* nginx/ migrations/ scripts/     <- M18 Deployment
data/knowledge_base/ refund/customer/invoice/product/company      <- controlled KB (§4.7)
```

## 2. Contract-level relationships

Solid arrows are data flows carrying a shared contract (Spec §4.1). All flows pass through the
engine/orchestrator, which owns integration (Spec §4.2).

```
                         +----------------------+
                         |  engine/orchestrator |  (owns the flow, §4.2)
                         +----------+-----------+
                                    |
     +-----------+------------+-----+------+-------------+--------------+
     v           v            v            v             v              v
  M02 LLM     M03 Claims   M05 RAG      M07 Verify    M10 Confid.    M13 Risk/
  Gateway     (Claim)      (Evidence)   (Verif.Res.)  (ConfResult)   Decision
     |           |            |            ^   ^          ^   ^        (Decision
     |           |            v            |   |          |   |         Result)
     |           |         M06 Evidence ---+   |          |   |            |
     |           |         Quality             |          |   |            v
     |           |                             |          |   |        M12 Reflection
     |           +-----------------------------+          |   |        (re-verify)
     |                                        M08 Halluc.--+   |
     |                                        M09 Consensus----+
     |                                                             |
     +------------------- M14 Provenance & Database <--------------+
                          (persist all, keyed by query_id)
```

Producing interfaces (Spec §4.1, §4.3):

```
LLMProvider.generate(request) -> LLMResponse        # M02
ClaimExtractor.extract(text)  -> list[Claim]         # M03
Retriever.search(query, top_k) -> list[Evidence]     # M05
Verifier.verify(claim, evidence) -> VerificationResult   # M07
ConfidenceEstimator.calculate(signals) -> ConfidenceResult  # M10 (raw)
DecisionEngine -> DecisionResult                     # M13
Engine -> EclairResult                               # engine (final aggregate)
```

## 3. Product-layer components (thin — Spec §4.12)

```
external clients ──HTTP──> M15 REST API ──> engine ──> reliability modules
                              ^   ^
                              |   |
                 M16 SDK ─────+   +───── M17 Dashboard
             (EclairClient)         (Streamlit, api_client)
```

- M15 exposes six versioned endpoints (`/v1/ask`, `/v1/verify`, `/v1/explain/{query_id}`,
  `/v1/feedback`, `/v1/health`, `/v1/metrics`) and delegates to the engine.
- M16 wraps the REST API (`ask/verify/explain/feedback`) — no reliability logic.
- M17 consumes the REST API and visualizes results — no reliability logic.

## 4. Persistence & provenance (M14)

`M14` persists, keyed by `query_id`: Query, Claims, Evidence, Verification, Confidence, Consensus,
Risk, Decision, Final Answer, Feedback, Timestamp (Spec §M14). Database components:
`database/database.py`, `database/session.py`, `database/models/`, `database/repositories/`, with
Alembic migrations under `deployment/migrations/alembic/`.

## 5. Boundaries

- Only M01 owns `contracts/`, `config.py`, `exceptions.py`, `version.py`, `engine/` scaffolding.
- Each reliability module owns exactly one folder (M14 owns two: `provenance/` and `database/`).
- No component may reach into another module's folder or redefine a shared contract (Spec §4.1,
  `rules/COMMON_RULES.md` §3).

# M18 — Evaluation, Benchmarking & Deployment — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M18 — Evaluation, Benchmarking & Deployment
IDENTIFIER: M18

PURPOSE:
  Prove that ECLAIR improves reliability and make the project reproducible.

RESPONSIBILITY:
  - Compare LLM Only, LLM + RAG, LLM + Multi-Agent and ECLAIR across reliability and
    calibration metrics.
  - Metrics: Accuracy, Hallucination Rate, Unsupported Claim Rate, ECE, Brier Score,
    High-Confidence Error Rate, Correct Abstention Rate, Conflict Detection Rate,
    False Action Rate, Latency.
  - Provide reproducible build/deployment (Docker, Docker Compose, GitHub Actions).

NON-RESPONSIBILITY:
  - Does NOT modify or reimplement reliability modules; it runs and measures them.

LOCATION:
  evaluation/  and  deployment/
EXISTING FOLDERS USED:
  evaluation/  (datasets/, baselines/, runners/, metrics/, calibration/, reports/, notebooks/)
  deployment/  (Dockerfile.api, Dockerfile.dashboard, Dockerfile.worker, nginx/, migrations/, scripts/)
  .github/workflows/  (tests.yml, lint.yml, build.yml)
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: the integrated engine + all modules (as measured subjects); M11 calibration metrics.
  External: pytest, Pandas, scikit-learn, Matplotlib, Docker, Docker Compose, GitHub Actions.
  Configuration: via M01 config and deployment configs.

INPUTS:
  Source: benchmark datasets under evaluation/datasets/ and data/benchmark/; pipeline outputs.
  Format: datasets + engine results.
  Validation: validate datasets and metric inputs.

PROCESSING:
  New logic: run baselines + ECLAIR over datasets, compute metrics, generate reports;
    build/deploy via Docker/Compose and CI workflows.

OUTPUTS:
  Format: reproducible reports (evaluation/reports/) comparing approaches; runnable containers.
  Destination: team/stakeholders; Dashboard evaluation view (via API where applicable).

CONSUMERS:
  Module/service: team/stakeholders; CI.
  Expected contract: reproducible comparison report + reproducible builds.

INTEGRATION POINTS:
  APIs used: engine/API for ECLAIR runs. APIs exposed: none.
  Database: via engine/M14 where needed. Events/Queues: none.
  Configuration: M01 + deployment. Auth: as configured.

ERROR HANDLING: use M01 exceptions; report failures explicitly; do not fabricate metrics.
VALIDATION RULES: metrics computed on valid datasets; numbers must come from real runs.
INTEGRATION REQUIREMENTS: measures the integrated system without altering module logic.

DO NOT CHANGE: any reliability module's logic; M01 contracts; other module folders.
REUSE RULES: reuse existing metrics/runners; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only the listed baselines, metrics, reports, and deployment assets.
NO NEW DEPENDENCIES: stay within approved stack (no Kubernetes/Kafka/etc., Spec §4.10).
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: benchmarking, reporting, reproducible build/deploy.
  Does NOT handle: implementing/altering reliability logic.

VERIFICATION BEFORE COMPLETE:
  - A reproducible report compares LLM Only, LLM+RAG, LLM+Multi-Agent and ECLAIR on the metrics.
  - Docker/Compose build runs; CI workflows defined.
  - docs/deployment/*.md written as applicable.
```

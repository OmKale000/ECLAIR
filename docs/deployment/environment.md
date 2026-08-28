# ECLAIR — Environment & Configuration

> Derived only from the Spec (§M01, §M02, §M14, §4.7, §4.10, §4.11) and the repository. The
> repository's `.env.example` is currently an empty placeholder on the `Rules` branch, so this
> document describes **what must be configured** without inventing exact variable names. The concrete
> configuration keys are owned by **M01** (`src/eclair/config.py`) and, for providers/DB, delivered
> by M02/M14. Do not invent env var names — read them from `config.py` / `.env.example` once M01
> defines them.

## 1. Configuration mechanism (Spec §M01, §4.8 rules)
- The shared configuration mechanism is `src/eclair/config.py`, **owned by M01**.
- Modules **reuse** this mechanism; they do not add their own ad-hoc config systems
  (`rules/COMMON_RULES.md` §10).
- Do not hardcode values that belong in configuration; do not add env vars unless your module's
  contract requires it.
- Local overrides go in a `.env` file based on `.env.example` (root). `.python-version` pins
  Python 3.12.

## 2. What needs to be configured (by area)

### 2.1 LLM providers (M02, Spec §4.11)
- **Ollama** — the permanent zero-cost fallback; must always be configurable/reachable.
- **Gemini / Groq / OpenRouter** — optional providers via free quotas only. ECLAIR must not depend
  on paid or temporary trials. Provider credentials/endpoints are configured through the M01 config
  mechanism (keys owned by M02/M01).

### 2.2 Database (M14, Spec §4.10)
- **PostgreSQL** connection is configured via the config mechanism (used by SQLAlchemy 2 / Alembic).
  Migrations live under `deployment/migrations/alembic/`. Do not hardcode connection strings
  (`docs/modules/database.md`).

### 2.3 Controlled knowledge base (Spec §4.7)
- Prototype v1 uses the deterministic controlled knowledge base under `data/knowledge_base/`
  (`refund_policy`, `customer_policy`, `invoice_policy`, `product_policy`, `company_policy`). Seeded
  via `deployment/scripts/seed_knowledge_base.sh`. No live web-search dependence in v1.

### 2.4 Risk thresholds & confidence fusion weights
- M13 risk thresholds (`risk/thresholds.py`) and M10 confidence fusion weights are **configurable**
  via the M01 config mechanism (Spec §M10, §M13). Do not hardcode them.

## 3. Approved stack constraint (Spec §4.10)
Only the approved dependencies may be configured/used: Python 3.12, FastAPI, Uvicorn, FAISS,
sentence-transformers, Transformers, PostgreSQL, SQLAlchemy 2, Alembic, Streamlit, Plotly/Matplotlib,
scikit-learn, Pandas, NumPy, HTTPX, Pydantic v2, Ollama, Docker, Docker Compose, uv, pytest, Ruff,
GitHub Actions. Forbidden: Kubernetes, Kafka, microservices, Neo4j, Elasticsearch, fine-tuned models,
heavy agent frameworks, paid observability.

## 4. Secrets handling
- Store secrets (provider API keys, DB credentials) in the environment / `.env`, never in source.
- `.gitignore` (root) should keep `.env` out of version control. Do not commit real credentials.

## 5. Where the real keys live (once implemented)
- Canonical config keys: `src/eclair/config.py` (M01).
- Example values: root `.env.example` (currently an empty placeholder to be filled by M01).
- If you need a config value that is not defined there, STOP and raise it as a gap for M01
  (`rules/COMMON_RULES.md` §C) — do not invent it.

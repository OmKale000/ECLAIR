# ECLAIR — Docker Deployment

> Derived only from the Spec (§M18, §4.10, §1 folder structure) and the repository's `deployment/`
> layout. Owned by **M18** (Evaluation, Benchmarking & Deployment). No invented services. Approved
> stack fixes Docker + Docker Compose (Spec §4.10); do not add Kubernetes (Spec §4.10).

## 1. Ownership
- **Module:** M18 (`rules/M18_evaluation_deployment.md`).
- Deployment artifacts live under `deployment/` and the root `docker-compose.yml`.

## 2. Deployment artifacts (Spec §1)
```
docker-compose.yml                  # root — compose the services below
deployment/
  Dockerfile.api                    # ECLAIR REST API image (M15)
  Dockerfile.dashboard              # Streamlit dashboard image (M17)
  Dockerfile.worker                 # worker image
  nginx/  nginx.conf  README.md     # reverse proxy config (see nginx/README.md)
  migrations/alembic/               # DB migrations (M14): env.py, script.py.mako, versions/
  scripts/  start_api.sh  start_dashboard.sh  init_db.sh  seed_knowledge_base.sh
```

## 3. Images (Spec §1)
- **`Dockerfile.api`** — builds the FastAPI/Uvicorn REST API (M15) over the integrated engine.
- **`Dockerfile.dashboard`** — builds the Streamlit dashboard (M17) that consumes the REST API.
- **`Dockerfile.worker`** — builds the worker image.

Each image uses the approved stack only (Python 3.12, FastAPI/Uvicorn, Streamlit, FAISS,
sentence-transformers, Transformers, SQLAlchemy 2, etc. — Spec §4.10). No paid observability, no
Kubernetes, no microservice mesh (Spec §4.10).

## 4. Supporting services (from the folder layout)
- **PostgreSQL** — the persistence store for M14 (approved stack, Spec §4.10). Connection is
  configured via environment (see `docs/deployment/environment.md`).
- **nginx** — reverse proxy in front of the API/dashboard; configured by `deployment/nginx/nginx.conf`
  (see `deployment/nginx/README.md`).
- **Ollama** — the permanent zero-cost LLM fallback (Spec §4.11), reachable by the API/worker.

## 5. Startup & init scripts (Spec §1)
```
deployment/scripts/start_api.sh          # start the REST API
deployment/scripts/start_dashboard.sh    # start the dashboard
deployment/scripts/init_db.sh            # initialize the database / run migrations
deployment/scripts/seed_knowledge_base.sh# seed the controlled knowledge base (Spec §4.7)
```
The controlled knowledge base seeded here is `data/knowledge_base/` with the five policy folders:
`refund_policy`, `customer_policy`, `invoice_policy`, `product_policy`, `company_policy` (Spec §4.7).

## 6. Compose model
`docker-compose.yml` (root) orchestrates the API, dashboard, worker, PostgreSQL, and nginx for a
reproducible local/one-host deployment. Migrations run via `init_db.sh` (Alembic under
`deployment/migrations/alembic/`).

> Note: `docker-compose.yml`, the three Dockerfiles, `nginx.conf`, and the scripts are placeholder
> files on the `Rules` branch (no implementation yet). Their concrete contents are delivered by M18.
> This document defines what each artifact is for; it does not invent their contents.

## 7. Reproducibility (Spec §M18)
Docker and CI/CD provide reproducible build and deployment workflows so the ECLAIR reliability
pipeline and its evaluation can be reproduced. See `docs/deployment/ci_cd.md` and
`docs/deployment/environment.md`.

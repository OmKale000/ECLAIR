# ECLAIR — CI/CD

> Derived only from the Spec (§M18, §4.8, §4.10) and the repository's `.github/workflows/` layout.
> Owned by **M18**. Approved stack fixes **GitHub Actions** (Spec §4.10); no other CI system.

## 1. Ownership
- **Module:** M18 (`rules/M18_evaluation_deployment.md`).
- **Workflows:** `.github/workflows/` — `tests.yml`, `lint.yml`, `build.yml`.

## 2. Workflows (Spec §1)
```
.github/workflows/
  tests.yml    # run the pytest suite
  lint.yml     # run Ruff lint
  build.yml    # build the Docker images (Dockerfile.api / .dashboard / .worker)
```

### 2.1 `tests.yml`
Runs the pytest suite (approved test framework, Spec §4.10) across `tests/unit/`,
`tests/integration/`, `tests/api/`, and `tests/end_to_end/` (see `docs/development/testing.md`).
Tests and contract compatibility are part of the module deliverable (Spec §4.8).

### 2.2 `lint.yml`
Runs **Ruff** (approved linter, Spec §4.10). The Definition of Done requires Ruff to pass and the
diff to contain only files inside the module scope (`rules/COMMON_RULES.md` §D).

### 2.3 `build.yml`
Builds the Docker images defined under `deployment/` (`Dockerfile.api`, `Dockerfile.dashboard`,
`Dockerfile.worker`) to keep builds reproducible (Spec §M18, see `docs/deployment/docker.md`).

## 3. Purpose (Spec §M18)
Docker and CI/CD provide reproducible build and deployment workflows so that the ECLAIR reliability
pipeline and its evaluation can be reproduced. The evaluation compares baselines
(`LLM Only`, `LLM + RAG`, `LLM + Multi-Agent`, `ECLAIR`) across the reliability and calibration
metrics (Spec §M18, `docs/development/module_contracts.md` §8).

## 4. Gate alignment with Definition of Done (Spec §4.8)
CI enforces the module completion gate:
- Unit tests pass (`tests.yml`).
- Ruff lint passes (`lint.yml`).
- Images build (`build.yml`).
- The diff must not touch files outside the module scope or change shared contracts / folder
  ownership (`rules/COMMON_RULES.md` §D).

## 5. Constraints (Spec §4.10)
- CI system: GitHub Actions only. Do not add other CI/CD platforms.
- No paid observability platforms; no Kubernetes deployment pipelines in v1.

> Note: the workflow files are placeholders on the `Rules` branch (no implementation yet). Their
> concrete YAML is delivered by M18. This document defines what each workflow is for; it does not
> invent workflow contents.

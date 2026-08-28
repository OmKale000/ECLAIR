# ECLAIR — Development Workflow

> Derived only from the Spec (§4.2, §4.8, §6) and the repository's `rules/` files. This describes the
> multi-developer / multi-AI workflow the `Rules` branch exists to enforce.

## 1. Branch model
- `Rules` is the team's common base branch. It contains the agreed folder structure, module
  contracts, and documentation only — **no module implementation**.
- Each developer/AI creates a feature branch **from `Rules`** (e.g. `feature/rag`, `feature/llm-gateway`).
- Implementation happens on the feature branch, inside **only** the assigned module's folder.

## 2. Before writing any code (PRE-FLIGHT — `rules/COMMON_RULES.md` §A)
1. You are on a feature branch created from `Rules` (not on `Rules`/`main`).
2. You have read, in order: `rules/COMMON_RULES.md`, `rules/SHARED_CONTRACTS_REFERENCE.md`, your
   module's `rules/M<NN>_*.md`, and your `docs/modules/<module>.md`.
3. Your module ID and folder are confirmed from the module map.
4. Every shared contract / enum / interface / endpoint you will use already exists in
   `SHARED_CONTRACTS_REFERENCE.md`. If one is missing → STOP, do not invent it.
5. Upstream contracts you depend on already exist or are stubbed by M01 → otherwise STOP and report.

## 3. Recommended implementation order (Spec §6)
- **Wave 1 — Foundation:** M01, M02, M03
- **Wave 2 — Knowledge & Verification:** M04, M05, M06, M07
- **Wave 3 — Reliability:** M08, M09, M10, M11
- **Wave 4 — Decision & Audit:** M12, M13, M14
- **Wave 5 — Product Interfaces:** M15, M16, M17
- **Wave 6 — Proof & Release:** M18

This order is deliberate: API, SDK and Dashboard consume the integrated engine; they contain no
independent reliability implementations (Spec §6, §4.12).

## 4. Module ownership vs pipeline ownership (Spec §4.2)
You may own a module, but the overall pipeline/integration flow is owned by the engine/orchestrator
(`src/eclair/engine/`) during integration. Do not wire modules together outside your boundary unless
your module IS the engine/orchestrator.

## 5. Implementing a module
Use `rules/MODULE_PROMPT_TEMPLATE.md` as the prompt for your AI agent. Follow: **reuse → extend →
modify → create**. Work only inside your module folder(s), its `tests/unit/<module>/`, and its
`docs/modules/<module>.md`. Do not edit `contracts/`, `config.py`, `exceptions.py`, or root
`pyproject.toml`/`uv.lock` unless your module IS M01.

## 6. Definition of Done (Spec §4.8 — a branch is not done just because the code runs)
Ship all of:
- Implementation (inside the module folder only)
- Unit tests (in `tests/unit/<module>/`) that pass
- Sample input and sample output
- Module documentation (`docs/modules/<module>.md`)
- No breaking changes to shared contracts; existing functionality still works
- Ruff lint passes; the diff contains only files inside your module scope

See `docs/development/testing.md` for the test layout and `docs/development/module_contracts.md` for
the contract each module must satisfy.

## 7. Post-implementation report (`rules/COMMON_RULES.md` §17)
Report only:
- **Changes Made** — `<file/path> — what changed`
- **Why** — one line per change tied to the module requirement
- **Integration** — `Input Source → Module → Output → Consumer`
- **Verification** — exactly what was tested/verified

## 8. Tooling
- Package/deps: `uv` (root `pyproject.toml` / `uv.lock` owned by M01).
- Lint: Ruff. Tests: pytest. CI: GitHub Actions (`.github/workflows/` — see
  `docs/deployment/ci_cd.md`).
- Python: 3.12 (`.python-version`).

## 9. STOP conditions (halt and report — never guess)
A required input/contract/field/enum is undefined; two specs conflict; correct implementation would
require changing another module or a shared contract; a needed dependency is outside the approved
stack (Spec §4.10). In any of these, STOP and report the blocker.

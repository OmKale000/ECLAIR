# ECLAIR — Testing

> Derived only from the Spec (§4.8, §1 folder structure) and the repository's `tests/` layout. No
> invented test frameworks — the approved stack fixes **pytest** (Spec §4.10).

## 1. Testing is part of the deliverable (Spec §4.8)
A branch is **not** complete simply because the code runs. Unit tests and contract compatibility are
part of the module deliverable. Every module must ship:
- Implementation
- Unit tests
- Sample input
- Sample output
- Module documentation (`docs/modules/<module>.md`)

## 2. Test framework
- **pytest** (approved stack, Spec §4.10). No other test framework may be introduced.

## 3. Test layout (Spec §1)
```
tests/
  unit/                       # one folder per module — own your module's folder only
    contracts/  engine/  llm/  claims/  ingestion/  rag/  evidence/
    verification/  hallucination/  consensus/  confidence/  calibration/
    reflection/  risk/  provenance/  database/
  integration/                # cross-module pipelines
    test_llm_pipeline.py  test_rag_pipeline.py  test_verification_pipeline.py
    test_confidence_pipeline.py  test_decision_pipeline.py
  api/                        # REST endpoint tests (M15)
    test_ask.py  test_verify.py  test_explain.py  test_feedback.py
    test_health.py  test_metrics.py
  end_to_end/                 # full pipeline scenarios (Spec §5, §7)
    test_full_pipeline.py  test_high_confidence_flow.py
    test_low_confidence_reflection.py  test_abstention_flow.py
    test_human_review_flow.py
```

## 4. Scope rules
- A module's unit tests live in `tests/unit/<module>/` and are owned by that module.
- Do NOT create broad tests or infrastructure unrelated to your module
  (`rules/COMMON_RULES.md` §16 verification rule).
- Integration, API, and end-to-end tests exercise the integrated engine and are part of the
  integration phase (engine/orchestrator ownership, Spec §4.2).

## 5. What unit tests must confirm (per module — Spec §4.8, §4.9)
- The module's **input contract** matches `SHARED_CONTRACTS_REFERENCE.md` exactly.
- The module's **output contract** matches `SHARED_CONTRACTS_REFERENCE.md` exactly.
- Error cases behave per the module contract (use M01 exceptions; no invented formats).
- Reliability invariants where applicable, e.g. M07: no-evidence → `UNKNOWN` (Spec §4.9);
  M10 output is raw (not calibrated ECS); consensus is one signal only.

## 6. End-to-end scenarios (Spec §5, §7)
The end-to-end tests correspond to the pipeline decision branches:
- `test_full_pipeline.py` — Question → … → Final Answer/Abstain/Human Review (Spec §7).
- `test_high_confidence_flow.py` — HIGH ECS → `RETURN` (Spec §5).
- `test_low_confidence_reflection.py` — LOW ECS → reflection → re-verify (Spec §5, §M12).
- `test_abstention_flow.py` — unsupported/UNKNOWN → `ABSTAIN` (Spec §M13, §4.9).
- `test_human_review_flow.py` — escalation → `HUMAN_REVIEW` (Spec §M13).

## 7. Running tests
```bash
pytest                          # all tests
pytest tests/unit/<module>/     # your module's unit tests
```
CI runs tests via GitHub Actions (`.github/workflows/tests.yml`); see `docs/deployment/ci_cd.md`.

## 8. Lint
Ruff must pass, and the diff must contain only files inside your module scope
(`rules/COMMON_RULES.md` §D COMPLETION gate).

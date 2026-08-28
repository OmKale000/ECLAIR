# M13 — Risk & Decision Engine

> Module documentation (Spec §4.8). Derived only from the Spec (§M13, §5) and the repo. Authoritative
> rules: `rules/M13_risk_decision.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M13
- **Name:** Risk & Decision Engine
- **Folder:** `src/eclair/risk/`
- **Tests:** `tests/unit/risk/`

## Purpose (Spec §M13)
Determine the action ECLAIR should take after reliability analysis.

## Responsibility
Turn reliability signals and the calibrated ECS into an actionable decision using a risk-based policy
with configurable thresholds.

## Non-responsibility
- Does NOT compute confidence (M10) or calibrate (M11).
- Does NOT persist the decision (M14) or expose it over HTTP (M15).

## Files (Spec §M13)
```
src/eclair/risk/  classifier.py  policy.py  thresholds.py  decision.py  models.py
```

## Technology (Spec §M13)
Python, rule engine initially.

## Method (Spec §M13)
Risk-based policy using configurable thresholds.

## Required functionality — decision actions (Spec §M13, SHARED_CONTRACTS_REFERENCE §2)
```
RETURN
VERIFY_MORE
REGENERATE
ABSTAIN
HUMAN_REVIEW
BLOCK_ACTION
```

## Inputs / Outputs
- **Input:** calibrated ECS (M11) + reliability signals (verification M07, hallucination M08,
  consensus M09, evidence quality M06).
- **Output:** `RiskResult` (M01 `contracts/risk.py`) + `DecisionResult` (M01 `contracts/decision.py`).
  Interface: `DecisionEngine -> DecisionResult` (Spec §4.1).
- **Consumers:** engine (branches HIGH ECS → RETURN, LOW ECS → Reflection then ACCEPT/ABSTAIN),
  M14 Provenance (persists the decision), M15/M17 (surface it).

## Decision branch (Spec §5)
- HIGH ECS → `RETURN`.
- LOW ECS → reflection (M12) → re-verify → `ACCEPT`/`ABSTAIN`.
- Escalation → `HUMAN_REVIEW`; unsafe action → `BLOCK_ACTION`.

## Dependencies
- Internal: M01 contracts (`RiskResult`, `DecisionResult`); M11 ECS; signals from M06–M09.
- External: none beyond Python (rule engine initially).

## Configuration
Thresholds are configurable via the M01 config mechanism (`thresholds.py` reads them); do not
hardcode threshold values.

## Do not change
M01 `RiskResult` / `DecisionResult` contracts and the decision-action enum; any other module folder.

## Expected outcome (Spec §M13)
ECLAIR turns reliability signals and ECS into an actionable decision rather than returning a score
alone.

## Verification before complete (Spec §4.8)
- Given ECS + signals, the engine returns one of the six frozen decision actions; thresholds are
  configurable.
- `tests/unit/risk/` pass; sample input/output provided.

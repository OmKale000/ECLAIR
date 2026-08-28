# M09 — Multi-Agent / Multi-Model Consensus

> Module documentation (Spec §4.8). Derived only from the Spec (§M09, §4.6) and the repo.
> Authoritative rules: `rules/M09_consensus.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M09
- **Name:** Multi-Agent / Multi-Model Consensus
- **Folder:** `src/eclair/consensus/`
- **Tests:** `tests/unit/consensus/`

## Purpose (Spec §M09)
Determine whether independent model outputs agree.

## Responsibility
Run multiple independent model calls, compare their claims/answers, calculate an agreement score, and
report full or partial consensus.

## Non-responsibility
- Does NOT treat agreement as truth — **model agreement is not truth (Spec §4.6)**.
- Does NOT verify against evidence (M07) or make the decision (M13).

## Files (Spec §M09)
```
src/eclair/consensus/  runner.py  voting.py  agreement.py  diversity.py  models.py
```

## Technology (Spec §M09)
asyncio, LLM Gateway (M02), Pydantic.

## Method (Spec §M09)
Start with majority voting and an agreement score; later support weighted voting based on historical
model performance.

## Required functionality (Spec §M09)
- Run multiple independent model calls.
- Compare claims or answers.
- Calculate agreement score.
- Report full or partial consensus.

## Inputs / Outputs
- **Input:** a prompt/claims to be answered by multiple models (via M02).
- **Output:** agreement score + full/partial consensus level (SHARED_CONTRACTS_REFERENCE §2).
- **Consumers:** M08 Hallucination (model-disagreement signal), M10 Confidence, engine.

## Dependencies
- Internal: M02 LLM Gateway; M01 contracts.
- External: asyncio for concurrent model calls.

## Reliability semantic (Spec §4.6)
Three models agreeing does not prove a statement is true. Agreement must be combined with evidence,
verification, source quality and calibration. Consensus is one reliability signal only.

## Error handling
Use M01 exceptions. Handle partial model failures (a failed provider must not be counted as
agreement); rely on M02 fallback where appropriate.

## Do not change
M01 contracts; M02 interface; any other module folder.

## Expected outcome (Spec §M09)
Model agreement is one reliability signal and never treated as proof of truth.

## Verification before complete (Spec §4.8)
- Multiple model calls run, agreement score computed, full/partial consensus reported.
- `tests/unit/consensus/` pass; sample input/output provided.

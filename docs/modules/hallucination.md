# M08 — Hallucination Detection

> Module documentation (Spec §4.8). Derived only from the Spec (§M08) and the repo. Authoritative
> rules: `rules/M08_hallucination_detection.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M08
- **Name:** Hallucination Detection
- **Folder:** `src/eclair/hallucination/`
- **Tests:** `tests/unit/hallucination/`

## Purpose (Spec §M08)
Detect claims that appear fabricated, unsupported or contradicted.

## Responsibility
Combine reliability signals into a structured hallucination result for claims or responses.

## Non-responsibility
- Does NOT retrieve/verify evidence (M05/M07) or compute final confidence (M10).
- Does NOT make the risk decision (M13).

## Files (Spec §M08)
```
src/eclair/hallucination/  detector.py  signals.py  scoring.py  models.py
```

## Technology (Spec §M08)
NLI, embeddings, LLM, Python.

## Method (Spec §M08)
Combine signals: no evidence, contradictory evidence, low semantic support, model disagreement, and
numerical inconsistency.

## Required functionality (Spec §M08)
- Return hallucination probability.
- Return hallucination flag.
- Return reasons for the flag.

## Inputs / Outputs
- **Input:** claims (M03), their `VerificationResult` (M07), evidence quality signals (M06), and
  model-disagreement signals (M09).
- **Output:** structured hallucination result (probability + flag + reasons).
- **Consumers:** M10 Confidence, M13 Risk/Decision, engine.

## Dependencies
- Internal: M01 contracts; M07 verification; M06 evidence quality; M09 consensus signals.
- External: NLI / embeddings / LLM utilities (via M02 where LLM is used).

## Error handling
Use M01 exceptions. Absence of evidence is itself a hallucination signal, consistent with Spec §4.9
(no-evidence → UNKNOWN at verification).

## Do not change
M01 contracts; M06/M07/M09 folders; any other module folder.

## Expected outcome (Spec §M08)
A structured hallucination result is produced for claims or responses.

## Verification before complete (Spec §4.8)
- Hallucination probability, flag, and reasons are produced from the combined signals.
- `tests/unit/hallucination/` pass; sample input/output provided.

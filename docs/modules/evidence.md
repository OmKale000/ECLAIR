# M06 — Evidence Quality & Conflict Detection

> Module documentation (Spec §4.8). Derived only from the Spec (§M06) and the repo. Authoritative
> rules: `rules/M06_evidence_quality.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M06
- **Name:** Evidence Quality & Conflict Detection
- **Folder:** `src/eclair/evidence/`
- **Tests:** `tests/unit/evidence/`

## Purpose (Spec §M06)
Determine whether retrieved evidence is reliable enough to support verification.

## Responsibility
Score evidence quality combining relevance, source authority, freshness, completeness and conflict;
expose structured quality signals on each evidence item.

## Non-responsibility
- Does NOT retrieve evidence (M05).
- Does NOT decide SUPPORTED/CONTRADICTED/UNKNOWN — that is verification (M07).

## Files (Spec §M06)
```
src/eclair/evidence/  scorer.py  authority.py  freshness.py  conflict.py  models.py
```

## Technology (Spec §M06)
Python, metadata rules, semantic similarity.

## Method (Spec §M06)
Evidence score combines relevance, source authority, freshness, completeness and conflict.

## Required functionality (Spec §M06)
- Detect outdated documents.
- Detect duplicates.
- Detect conflicting documents.
- Detect low-quality sources.
- Detect insufficient evidence.

## Inputs / Outputs
- **Input:** `list[Evidence]` from M05.
- **Output:** quality-annotated `Evidence` exposing structured quality signals (relevance, authority,
  freshness, conflict).
- **Consumers:** M07 Verification, M08 Hallucination, engine.

## Dependencies
- Internal: M01 contracts (`Evidence`); M05 retrieved evidence.
- External: Python, semantic-similarity utilities.

## Error handling
Use M01 exceptions. Insufficient/low-quality evidence must be reported via the quality signals, not
hidden.

## Do not change
M01 `Evidence` contract; M05 folder; any other module folder.

## Expected outcome (Spec §M06)
Each evidence item can expose structured quality signals such as relevance, authority, freshness and
conflict.

## Verification before complete (Spec §4.8)
- Outdated, duplicate, conflicting, low-quality and insufficient evidence are detected and surfaced.
- `tests/unit/evidence/` pass; sample input/output provided.

# M06 — Evidence Quality & Conflict Detection — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M06 — Evidence Quality & Conflict Detection
IDENTIFIER: M06

PURPOSE:
  Determine whether retrieved evidence is reliable enough to support verification.

RESPONSIBILITY:
  - Score relevance, source authority, freshness, completeness and conflict.
  - Detect outdated documents, duplicates, conflicting documents, low-quality sources,
    and insufficient evidence.

NON-RESPONSIBILITY:
  - Does NOT retrieve evidence (M05) or verify claims (M07).
  - Does NOT compute confidence (M10) or decisions (M13).

LOCATION:
  src/eclair/evidence/
EXISTING FOLDERS USED:
  src/eclair/evidence/  (scorer.py, authority.py, freshness.py, conflict.py, models.py)
  tests/unit/evidence/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts (Evidence); M05 retrieved evidence.
  External: Python, metadata rules, semantic similarity.
  Configuration: via M01 config.

INPUTS:
  Source: list[Evidence] from M05.
  Format: Evidence objects (with metadata captured by M04).
  Validation: validate incoming Evidence objects.

PROCESSING:
  New logic: evidence score combines relevance, source authority, freshness, completeness
    and conflict.

OUTPUTS:
  Format: structured quality signals per evidence item (e.g. relevance, authority, freshness,
    conflict) attached per the M01/module contract.
  Destination: consumed by M07 Verification and M10 Confidence.

CONSUMERS:
  Module/service: M07, M10, engine.
  Expected contract: evidence items exposing structured quality signals.

INTEGRATION POINTS:
  APIs used: none. APIs exposed: internal scorer interface.
  Database: none. Events/Queues: none. Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; insufficient evidence is a signal, not a crash.
VALIDATION RULES: quality signals must be within defined ranges.
INTEGRATION REQUIREMENTS: signals feed verification and confidence, not decisions directly.

DO NOT CHANGE: M01 Evidence contract; M05/M07 folders; any other module.
REUSE RULES: reuse metadata from M04; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only scoring + conflict/quality detection.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: evidence quality/conflict scoring.
  Does NOT handle: retrieval, verification, confidence, decisions.

VERIFICATION BEFORE COMPLETE:
  - Each evidence item exposes relevance/authority/freshness/conflict signals.
  - Outdated/duplicate/conflicting/low-quality/insufficient cases detected.
  - tests/unit/evidence/ pass; sample input/output; docs/modules/evidence.md written.
```

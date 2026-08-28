# M03 — Claim Extraction — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M03 — Claim Extraction
IDENTIFIER: M03

PURPOSE:
  Break generated answers into atomic factual claims.

RESPONSIBILITY:
  - Convert one answer into multiple atomic claims.
  - Normalize equivalent phrasing.
  - Deduplicate semantically similar claims.
  - Assign claim IDs and claim types.

NON-RESPONSIBILITY:
  - Does NOT retrieve evidence, verify claims, score confidence, or decide actions.
  - Does NOT call providers directly (uses M02).

LOCATION:
  src/eclair/claims/
EXISTING FOLDERS USED:
  src/eclair/claims/  (extractor.py, normalizer.py, deduplicator.py, classifier.py, models.py)
  tests/unit/claims/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts (Claim); M02 LLM Gateway (structured output).
  External: LLM structured output, Pydantic, SentenceTransformers (semantic similarity).
  Configuration: via M01 config.

INPUTS:
  Source: a generated LLM answer (from engine / M02).
  Format: text string (answer). Module-local models.py may define request/interim types.
  Validation: validate via Pydantic.

PROCESSING:
  New logic: extract claims -> normalize wording -> remove duplicates -> classify claim type ->
    generate claim IDs.

OUTPUTS:
  Format: list[Claim] (shared contract from M01) with IDs and types.
  Destination: consumed downstream by evidence retrieval and verification.

CONSUMERS:
  Module/service: M05 RAG (per-claim retrieval), M07 Verification, M08 Hallucination, engine.
  Expected contract: list[Claim].

INTEGRATION POINTS:
  APIs used: M02 llm.generate (structured). APIs exposed: internal ClaimExtractor.extract(text)->list[Claim].
  Database: none. Events/Queues: none. Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; do not swallow errors; no invented fallback.
VALIDATION RULES: output must be valid Claim objects; deduplicate before returning.
INTEGRATION REQUIREMENTS: every downstream reliability component works claim-by-claim.

DO NOT CHANGE: M01 Claim contract; M02 interface; any other module folder.
REUSE RULES: reuse M02 + SentenceTransformers; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only extraction/normalization/dedup/classification/IDs.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: answer -> atomic claims.
  Does NOT handle: evidence, verification, confidence, decisions.

VERIFICATION BEFORE COMPLETE:
  - One answer yields multiple atomic Claim objects with IDs and types.
  - Duplicates removed; equivalent phrasing normalized.
  - tests/unit/claims/ pass; sample input/output; docs/modules/claims.md written.
```

# M03 — Claim Extraction

> Module documentation (Spec §4.8). Derived only from the Spec (§M03, §4.1) and the repo.
> Authoritative rules: `rules/M03_claim_extraction.md`, `rules/COMMON_RULES.md`. Do not invent fields
> or behavior.

## Identity
- **ID:** M03
- **Name:** Claim Extraction
- **Folder:** `src/eclair/claims/`
- **Tests:** `tests/unit/claims/`

## Purpose (Spec §M03)
Break generated answers into atomic factual claims.

## Responsibility
Extract claims, normalize wording, remove duplicates, classify claim type, and generate claim IDs.

## Non-responsibility
- Does NOT retrieve evidence (M05), verify claims (M07), or estimate confidence (M10).
- Does NOT generate the original answer (that is M02 via the engine).

## Files (Spec §M03)
```
src/eclair/claims/  extractor.py  normalizer.py  deduplicator.py  classifier.py  models.py
```

## Technology (Spec §M03)
LLM structured output (via M02), Pydantic, sentence-transformers for semantic similarity.

## Method (Spec §M03)
Extract claims → normalize wording → remove duplicates → classify claim type → generate claim IDs.

## Required functionality (Spec §M03)
- Convert one answer into multiple atomic claims.
- Normalize equivalent phrasing.
- Deduplicate semantically similar claims.
- Assign claim IDs and claim types.

## Inputs / Outputs
- **Input:** generated answer text (`str`) from M02 via the engine.
- **Output:** `list[Claim]` (M01 contract). Interface: `ClaimExtractor.extract(text) -> list[Claim]`
  (Spec §4.1, §4.3).
- **Consumers:** M05 RAG (retrieve evidence per claim), M07 Verification, M08 Hallucination, M09
  Consensus, M10 Confidence, and the engine.

## Dependencies
- Internal: M01 contracts (`Claim`); M02 LLM Gateway for structured extraction.
- External: sentence-transformers (semantic similarity), Pydantic.

## Error handling
Use M01 exceptions. Validate that produced claims conform to the `Claim` contract.

## Do not change
M01 `Claim` contract; M02 interface; any other module folder.

## Expected outcome (Spec §M03)
Every downstream reliability component can work claim by claim.

## Verification before complete (Spec §4.8)
- One answer yields multiple atomic, normalized, deduplicated, classified `Claim` objects with IDs.
- `tests/unit/claims/` pass; sample input/output provided.

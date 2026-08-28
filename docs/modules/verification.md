# M07 — Claim Verification

> Module documentation (Spec §4.8). Derived only from the Spec (§M07, §4.5, §4.9) and the repo.
> Authoritative rules: `rules/M07_claim_verification.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M07
- **Name:** Claim Verification
- **Folder:** `src/eclair/verification/`
- **Tests:** `tests/unit/verification/`

## Purpose (Spec §M07)
Determine whether evidence actually supports the claim.

## Responsibility
Verify each claim against evidence using NLI and optional LLM verification; assign a verification
status, attach supporting evidence, and return support and contradiction scores.

## Non-responsibility
- Does NOT retrieve evidence (M05) or score evidence quality (M06).
- Does NOT compute hallucination (M08), confidence (M10), or decisions (M13).

## Files (Spec §M07)
```
src/eclair/verification/  verifier.py  nli.py  llm_verifier.py  aggregator.py  models.py
```

## Technology (Spec §M07)
HuggingFace Transformers, an NLI model, LLM verification as a secondary method (via M02).

## Method (Spec §M07, §4.9)
Natural Language Inference: `Claim + Evidence → ENTAILMENT / CONTRADICTION / NEUTRAL`, mapped to:
```
ENTAILMENT     -> SUPPORTED
CONTRADICTION  -> CONTRADICTED
NEUTRAL        -> UNKNOWN
```
Optional LLM verification is a secondary method. Aggregate across evidence.

## Required functionality (Spec §M07)
- Assign verification status.
- Attach supporting evidence.
- Return support score.
- Return contradiction score.

## Inputs / Outputs
- **Input:** a `Claim` (M03) + `list[Evidence]` (M05/M06). No-evidence is a valid input.
- **Output:** `VerificationResult` (M01) with status, supporting evidence, support score,
  contradiction score. Interface: `Verifier.verify(claim, evidence) -> VerificationResult`.
- **Consumers:** M08 Hallucination, M10 Confidence, M12 Reflection, engine.

## Reliability semantics (non-negotiable)
- **Verification is explicit (Spec §4.5).** Retrieval alone is not verification.
- **No evidence → UNKNOWN, never SUPPORTED (Spec §4.9).** Absence of evidence must map to `UNKNOWN`.
- Status is restricted to the three frozen states: `SUPPORTED`, `CONTRADICTED`, `UNKNOWN`.

## Dependencies
- Internal: M01 contracts (`Claim`, `Evidence`, `VerificationResult`); M05/M06 evidence; M02
  (optional LLM verification).
- External: HuggingFace Transformers + an NLI model.

## Error handling
Use M01 exceptions; no-evidence maps to `UNKNOWN` (Spec §4.9); scores stay within valid range.

## Do not change
M01 `VerificationResult` contract; M05/M06 folders; any other module folder.

## Expected outcome (Spec §M07)
Each claim receives a structured verification result. No evidence means UNKNOWN rather than SUPPORTED.

## Verification before complete (Spec §4.8)
- Each claim receives a structured `VerificationResult`; no-evidence maps to UNKNOWN.
- `tests/unit/verification/` pass; sample input/output provided.

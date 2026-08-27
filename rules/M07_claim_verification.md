# M07 — Claim Verification — AI Development Rules

> Read `rules/COMMON_RULES.md` first. All common non-negotiables apply.

```text
MODULE: M07 — Claim Verification
IDENTIFIER: M07

PURPOSE:
  Determine whether evidence actually supports the claim.

RESPONSIBILITY:
  - Verify each claim against evidence using NLI and optional LLM verification.
  - Assign verification status, attach supporting evidence, return support score and
    contradiction score.

NON-RESPONSIBILITY:
  - Does NOT retrieve evidence (M05) or score evidence quality (M06).
  - Does NOT compute hallucination (M08), confidence (M10), or decisions (M13).

LOCATION:
  src/eclair/verification/
EXISTING FOLDERS USED:
  src/eclair/verification/  (verifier.py, nli.py, llm_verifier.py, aggregator.py, models.py)
  tests/unit/verification/
NEW FILES REQUIRED: none beyond existing placeholders.

DEPENDENCIES:
  Internal: M01 contracts (Claim, Evidence, VerificationResult); M05 evidence; M06 quality
    signals; M02 LLM Gateway (optional LLM verification).
  External: HuggingFace Transformers, an NLI model.
  Configuration: via M01 config.

INPUTS:
  Source: a Claim (M03) + list[Evidence] (M05/M06).
  Format: M01 Claim + Evidence contracts.
  Validation: validate inputs; no evidence is a valid input.

PROCESSING:
  New logic: NLI Claim + Evidence -> ENTAILMENT / CONTRADICTION / NEUTRAL,
    mapped to SUPPORTED / CONTRADICTED / UNKNOWN. Optional LLM verification as secondary method.
    Aggregate across evidence.

OUTPUTS:
  Format: VerificationResult (M01) with status, supporting evidence, support score,
    contradiction score.
  Destination: consumed by M08 Hallucination, M10 Confidence, engine.

CONSUMERS:
  Module/service: M08, M10, M12 Reflection, engine.
  Expected contract: VerificationResult with SUPPORTED / CONTRADICTED / UNKNOWN.

INTEGRATION POINTS:
  APIs used: M02 (optional). APIs exposed: Verifier.verify(claim, evidence)->VerificationResult.
  Database: none. Events/Queues: none. Configuration: M01. Auth: none.

ERROR HANDLING: use M01 exceptions; NO EVIDENCE MUST MAP TO UNKNOWN, never SUPPORTED (Spec §4.9).
VALIDATION RULES: status restricted to the three defined states; scores in valid range.
INTEGRATION REQUIREMENTS: verification is an explicit step; retrieval alone is not verification.

DO NOT CHANGE: M01 VerificationResult contract; M05/M06 folders; any other module.
REUSE RULES: reuse Transformers/NLI + M02; reuse → extend → modify → create.
NO UNREQUESTED FUNCTIONALITY: only verification + aggregation.
NO NEW DEPENDENCIES: stay within approved stack.
NO UNRELATED REFACTORING: none.

MODULE BOUNDARY:
  Handles: claim-vs-evidence verification.
  Does NOT handle: retrieval, quality scoring, hallucination, confidence, decisions.

VERIFICATION BEFORE COMPLETE:
  - Each claim receives a structured VerificationResult.
  - No-evidence maps to UNKNOWN.
  - tests/unit/verification/ pass; sample input/output; docs/modules/verification.md written.
```

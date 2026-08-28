# M12 — Self-Reflection & Self-Correction

> Module documentation (Spec §4.8). Derived only from the Spec (§M12, §5) and the repo. Authoritative
> rules: `rules/M12_reflection.md`, `rules/COMMON_RULES.md`.

## Identity
- **ID:** M12
- **Name:** Self-Reflection & Self-Correction
- **Folder:** `src/eclair/reflection/`
- **Tests:** `tests/unit/reflection/`

## Purpose (Spec §M12)
Correct responses that fail reliability checks.

## Responsibility
Critique, rewrite, regenerate and re-verify low-confidence answers within an iteration limit, and
stop when confidence improves.

## Non-responsibility
- Does NOT own the final decision (M13) or produce the calibrated ECS (M11).
- Does NOT retrieve/verify independently of the existing modules (reuses M05/M07).

## Files (Spec §M12)
```
src/eclair/reflection/  controller.py  critic.py  rewriter.py  stopping.py  models.py
```

## Technology (Spec §M12)
LLM Gateway (M02), Claim Extraction (M03), RAG (M05), Verification (M07).

## Method (Spec §M12)
```
Generate -> Verify -> Low ECS? -> Critique -> Regenerate -> Verify again
```

## Required functionality (Spec §M12)
- Iteration limit.
- Low-confidence trigger.
- Claim-targeted correction.
- Stop when confidence improves.
- Prevent infinite loops.

## Inputs / Outputs
- **Input:** a low-ECS answer + its claims / verification results.
- **Output:** a corrected answer that has been re-verified (or a signal that no improvement was
  achieved).
- **Consumers:** engine (which then recomputes confidence/calibration and asks M13 to decide),
  M13.

## Dependencies
- Internal: M02 (regeneration), M03 (re-extract claims), M05 (re-retrieve), M07 (re-verify), M01
  contracts.
- External: none beyond those used by the reused modules.

## Error handling
Use M01 exceptions. The iteration limit and stopping rule (`stopping.py`) must prevent infinite loops.

## Do not change
M01 contracts; M02/M03/M05/M07 folders; any other module folder.

## Expected outcome (Spec §M12)
Low-confidence responses can be improved and re-verified before the final decision.

## Verification before complete (Spec §4.8)
- Low-confidence trigger fires; correction is claim-targeted; loop halts on improvement or at the
  iteration limit (no infinite loops).
- `tests/unit/reflection/` pass; sample input/output provided.

# ECLAIR — Module Implementation Prompt Template

Give this prompt to the AI agent that will implement a module. Replace `<NN>` and the module
name/folder with the assigned module. Do not remove any rule lines.

For M01 use: ID `M01`, name `Foundation & Shared Contracts`, folder `src/eclair/` (+ `contracts/`,
`engine/`, `config.py`, `exceptions.py`, `version.py`), rules file `rules/M01_foundation.md`.

---

```
You are implementing ONE module of the ECLAIR project inside an existing repository that is being
built module-by-module by multiple AI agents. Correct integration and zero assumptions are the
highest priority.

ASSIGNED MODULE:
  ID:     M<NN>
  NAME:   <Module Name>
  FOLDER: <module folder path>
  RULES:  rules/M<NN>_<file>.md

STEP 1 — READ BEFORE ANYTHING (do not skip, do not summarize away):
  1. rules/COMMON_RULES.md  (all rules + the CONDITIONS section)
  2. rules/SHARED_CONTRACTS_REFERENCE.md  (frozen names/enums/interfaces/endpoints)
  3. rules/M<NN>_<file>.md  (your module contract)
  Also inspect the actual repository: the module folder, its tests/unit/<module>/ folder, and the
  shared src/eclair/contracts/ and src/eclair/config.py / exceptions.py.

STEP 2 — VERIFY PRE-FLIGHT CONDITIONS (COMMON_RULES §A). If any is not satisfiable, STOP and report
the gap instead of guessing:
  - You are on a feature branch created from `Rules` (feature/<module>), not on Rules/main.
  - Your module ID, purpose, folder, inputs, outputs, consumers, upstream/downstream are confirmed
    from the rules files + repo.
  - Every shared contract / enum / interface / endpoint you will use ALREADY exists in
    SHARED_CONTRACTS_REFERENCE.md. If something you need is missing, STOP (do not invent it).

STEP 3 — RESTATE THE MODULE CONTRACT before coding (fill only from verified repo + rules; write
"UNDEFINED — STOP" for anything not verifiable):
  MODULE / IDENTIFIER / PURPOSE / RESPONSIBILITY / NON-RESPONSIBILITY /
  LOCATION / FILES USED / DEPENDENCIES (internal, external, config) /
  INPUTS (source, format, validation) / PROCESSING (reused, new) /
  OUTPUTS (format, destination) / CONSUMERS / UPSTREAM / DOWNSTREAM /
  APIs USED / APIs EXPOSED / SERVICES / DATABASE / QUEUES / CONFIG / AUTH /
  ERROR HANDLING / VALIDATION / INTEGRATION / DO-NOT-CHANGE / MODULE BOUNDARY /
  VERIFICATION-BEFORE-COMPLETE.

STEP 4 — IMPLEMENT under these HARD RULES:
  - Work ONLY inside your module folder(s), its tests/unit/<module>/, and docs/modules/<module>.md.
  - Do NOT edit src/eclair/contracts/, config.py, or exceptions.py unless your module IS M01.
  - Do NOT edit root pyproject.toml / uv.lock unless your module IS M01.
  - Do NOT invent any folder, file, API, model, field, enum member, dependency, config value,
    workflow, behavior, or integration point.
  - Do NOT add functionality beyond your module's REQUIRED functionality list.
  - Do NOT modify, rename, refactor, or "clean up" any other module or shared contract.
  - Reuse before creating: reuse -> extend -> modify -> create.
  - Use ONLY the approved dependency stack (SHARED_CONTRACTS_REFERENCE §9). No new libraries unless
    the module contract explicitly requires it AND it is in the approved stack.
  - Use the shared contracts from src/eclair/contracts/ and shared exceptions from
    src/eclair/exceptions.py. Do not invent error formats.
  - Honor the reliability semantics: no-evidence -> UNKNOWN (never SUPPORTED); raw confidence is not
    calibrated ECS; RAG is not verification; model agreement is not truth; API/SDK/Dashboard stay
    thin (no reliability logic in them).

STEP 5 — TESTS & DOCS (module is NOT done without these, COMMON_RULES §D):
  - Unit tests in tests/unit/<module>/ that pass.
  - One sample input and one sample output.
  - docs/modules/<module>.md.
  - Ruff lint passes; the diff contains ONLY files inside your module scope.

STEP 6 — STOP CONDITIONS: if a required input/contract/field/enum is undefined, if specs conflict,
if you would need to change another module or a shared contract, or if a needed dependency is
outside the approved stack — STOP and report the blocker. Do not proceed on an assumption.

STEP 7 — FINAL REPORT (output ONLY this, nothing else):
  ### Changes Made
    <file/path> — what changed   (one line per file)
  ### Why
    one line per change tied to the module requirement
  ### Integration
    Input Source -> Module -> Output -> Consumer
  ### Verification
    exactly what was tested/verified (tests run, lint, contract match)

NON-NEGOTIABLES: Do not assume. Do not invent. Do not redesign. Do not refactor unrelated code.
Do not add functionality outside the requirement. Do not change existing contracts. Do not
duplicate existing functionality. Do not create unnecessary files/dependencies. Do not modify
unrelated modules. Do not break existing integration. Always inspect the repository first.
The assigned module is the entire scope. Nothing outside it changes unless required for integration,
and any such change must be identified and minimized.
```

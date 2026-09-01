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
- Does NOT call LLM providers directly — all LLM access goes through the M02 LLM Gateway.

## Files (Spec §M03)
```
src/eclair/claims/
  extractor.py     ClaimExtractor.extract(text) -> list[Claim]  (orchestration)
  normalizer.py    ClaimNormalizer  (deterministic text hygiene + comparison key)
  deduplicator.py  ClaimDeduplicator  (exact + semantic dedup, injectable encoder)
  classifier.py    ClaimClassifier  (heuristic ClaimType assignment)
  models.py        ExtractionResult  (interim parse container; not a shared contract)
  __init__.py      public surface
```

## Technology (Spec §M03)
LLM structured output (via M02 `LLMRouter`), Pydantic v2, `sentence-transformers==6.0.1`
(`all-MiniLM-L6-v2`) for semantic-similarity deduplication.

## Pipeline (Spec §M03)
```
answer (str)
  -> LLM structured extraction (M02, json_mode)   -> ["raw claim", ...]
  -> normalize wording (ClaimNormalizer)           -> cleaned display text
  -> deduplicate (ClaimDeduplicator)               -> exact key + cosine >= 0.9 semantic
  -> classify (ClaimClassifier)                    -> ClaimType per claim
  -> build Claim(text, claim_type) with auto claim_id
list[Claim]
```

### Stage details
- **Extraction:** the extractor sends `LLMRequest(prompt=..., json_mode=True)` through the injected
  LLM Gateway and parses the response's `structured` payload as `{"claims": ["...", ...]}` via the
  interim `ExtractionResult`. Missing/malformed structured output raises the shared `ModuleError`.
- **Normalization:** collapses whitespace, trims, and removes a single trailing terminal mark
  (`. ! ?`). A separate lowercase, punctuation-stripped **comparison key** is used only for exact
  dedup so that `"The sky is blue."`, `"the sky is blue"`, and `"THE  SKY   IS BLUE!!"` collapse to
  one claim.
- **Deduplication:** pass 1 removes exact duplicates by comparison key (keeping first occurrence);
  pass 2 removes semantic near-duplicates using embedding cosine similarity `>=` a configurable
  threshold (`DEFAULT_SIMILARITY_THRESHOLD = 0.9`). The encoder is **injectable**; when none is
  provided a `sentence-transformers` model is lazily constructed on first use.
- **Classification:** deterministic, rule-based, always returns a frozen `ClaimType` member.
  Precedence: `TEMPORAL` (year/date words) → `NUMERIC` (other numbers/percent/currency) →
  `ENTITY` (proper-noun phrase) → `FACTUAL` (alphabetic content) → `OTHER`.

## Inputs / Outputs
- **Input:** generated answer text (`str`) from M02 via the engine.
- **Output:** `list[Claim]` (M01 contract). Interface: `ClaimExtractor.extract(text) -> list[Claim]`
  (Spec §4.1, §4.3). Each `Claim` has an auto-generated `claim_id`, normalized `text`, and a
  `claim_type` (`ClaimType`).
- **Empty input:** empty or whitespace-only text returns `[]` (no LLM call).
- **Consumers:** M05 RAG (retrieve evidence per claim), M07 Verification, M08 Hallucination, M09
  Consensus, M10 Confidence, and the engine.

## Interface / construction
```python
from eclair.claims import ClaimExtractor
from eclair.config import load_config
from eclair.llm import LLMRouter

router = LLMRouter(load_config().llm)
extractor = ClaimExtractor(router)          # normalizer/deduplicator/classifier default internally
claims = extractor.extract(answer_text)      # -> list[Claim]
```
Collaborators (`normalizer`, `deduplicator`, `classifier`) and the LLM client are injectable, which
is how unit tests run fully offline with a fake LLM client and a fake encoder (no model downloads,
no network).

## Dependencies
- Internal: M01 contracts (`Claim`, `ClaimType`, `ModuleError`); M02 LLM Gateway
  (`LLMRouter`, `LLMRequest`, `LLMResponse`).
- External: `sentence-transformers` (semantic similarity), Pydantic v2.

## Error handling
Uses M01 `ModuleError` (no invented error format). LLM Gateway failures propagate unchanged.
Raises `ModuleError` when the LLM returns no structured output or a shape that does not match
`{"claims": [str, ...]}`, and when a produced claim fails `Claim` contract validation.

## Do not change
M01 `Claim`/`ClaimType` contract; M02 interface; any other module folder.

## Sample input / output

**Input (answer text):**
```
The Eiffel Tower is located in Paris. It was completed in 1889 and stands 330 meters tall.
```

**LLM structured output (via M02, json_mode):**
```json
{"claims": ["The Eiffel Tower is located in Paris.", "The tower was completed in 1889.", "It is 330 meters tall."]}
```

**Output (`list[Claim]` as JSON; `claim_id` values are illustrative):**
```json
[
  {"claim_id": "a1b2c3d4e5f6...", "text": "The Eiffel Tower is located in Paris", "claim_type": "ENTITY"},
  {"claim_id": "b2c3d4e5f6a1...", "text": "The tower was completed in 1889",     "claim_type": "TEMPORAL"},
  {"claim_id": "c3d4e5f6a1b2...", "text": "It is 330 meters tall",               "claim_type": "NUMERIC"}
]
```

## Verification before complete (Spec §4.8)
- One answer yields multiple atomic, normalized, deduplicated, classified `Claim` objects with IDs.
- `tests/unit/claims/` pass offline (`pytest tests/unit/claims/`) — 12 tests covering multi-claim
  extraction, `ClaimType` assignment, normalization/collapse, exact + semantic dedup, empty input,
  blank-claim dropping, output type, and `ModuleError` on bad LLM output.
- Ruff passes (`ruff check .`).

# ECLAIR — Reliability Pipeline

> Derived only from the Spec (§4, §5, §7). No invented steps. Read `rules/COMMON_RULES.md` and
> `docs/architecture/system_architecture.md` first.

## 1. Final ECLAIR integration flow (Spec §5)

The engine/orchestrator (`src/eclair/engine/`) owns this flow (Spec §4.2). Modules plug into it via
the shared contracts; they do not wire themselves together.

```
USER / APPLICATION
      |
      v
ECLAIR REST API                         (M15 — thin, delegates to engine)
      |
      v
ECLAIR ORCHESTRATOR                     (engine/ — owns the flow)
      |
      v
LLM GATEWAY                             (M02 — provider-agnostic generation)
      |
      v
GENERATED ANSWER
      |
      v
CLAIM EXTRACTION                        (M03 — answer -> list[Claim])
      |
   +--+--------------+----------------+
   |                 |                |
   v                 v                v
  RAG           CONSISTENCY      MULTI-MODEL
 (M05)                            CONSENSUS (M09)
   |                 |                |
   +--+--------------+----------------+
      |
      v
EVIDENCE QUALITY                        (M06 — relevance/authority/freshness/conflict)
      |
      v
CLAIM VERIFICATION                      (M07 — NLI; SUPPORTED/CONTRADICTED/UNKNOWN)
      |
      v
HALLUCINATION CHECK                     (M08 — hallucination probability + flag + reasons)
      |
      v
CONFIDENCE ESTIMATION                   (M10 — RAW confidence only)
      |
      v
ECS CALIBRATION                         (M11 — calibrated Epistemic Confidence Score)
      |
      v
RISK ASSESSMENT                         (M13 — risk classification + decision)
      |
   +--+----------+
   |            |
 HIGH ECS     LOW ECS
   |            |
 RETURN     REFLECTION                  (M12 — critique/rewrite/regenerate)
                |
                v
          RE-VERIFICATION               (re-run verification on corrected answer)
                |
                v
          ACCEPT / ABSTAIN
      |
      v
PROVENANCE                              (M14 — persist full lineage by query_id)
      |
      v
FINAL RESULT
    / | \
   v  v  v
  API SDK DASHBOARD                      (M15 / M16 / M17 — same result, three surfaces)
```

## 2. End-to-end demonstration path (Spec §7)

At the end of Prototype v1 a single request must produce a traceable decision along this path:

```
Question
  -> LLM Answer
  -> Claims
  -> Evidence
  -> Verification
  -> Hallucination Analysis
  -> Model Agreement
  -> Raw Confidence
  -> Calibrated ECS
  -> Risk Decision
  -> Final Answer / Abstain / Human Review
```

The same result must be accessible through the REST API, the Python SDK, and the ECLAIR Dashboard
(Spec §7). The outcome is a single modular product architecture, not three disconnected demos.

## 3. Stage-by-stage contract flow (Spec §4.1)

| Stage | Module | Input | Output (shared contract) |
|-------|--------|-------|--------------------------|
| Generation | M02 | `Query` / prompt | generated answer text |
| Claim extraction | M03 | answer text | `list[Claim]` |
| Retrieval | M05 | claim / query | `list[Evidence]` |
| Evidence quality | M06 | `list[Evidence]` | quality-annotated `Evidence` |
| Verification | M07 | `Claim` + `list[Evidence]` | `VerificationResult` |
| Hallucination | M08 | claims + verification + signals | hallucination result |
| Consensus | M09 | multiple model outputs | agreement score + full/partial consensus |
| Confidence | M10 | reliability signals | `ConfidenceResult` (raw) |
| Calibration | M11 | raw confidence + observed correctness | calibrated ECS |
| Reflection | M12 | low-ECS answer + claims | corrected answer (then re-verified) |
| Risk / decision | M13 | ECS + reliability signals | `RiskResult` + `DecisionResult` |
| Provenance | M14 | all of the above, keyed by `query_id` | persisted lineage + audit trail |
| Aggregate | engine | all stage outputs | `EclairResult` |

Canonical producing interfaces (Spec §4.1):

```
ClaimExtractor      -> list[Claim]
Retriever           -> list[Evidence]
Verifier            -> VerificationResult
ConfidenceEstimator -> ConfidenceResult
DecisionEngine      -> DecisionResult
```

## 4. Decision branch semantics (Spec §M13, §5)

After risk assessment the pipeline branches on the calibrated ECS and risk signals:

- **HIGH ECS →** `RETURN` the answer.
- **LOW ECS →** enter **Reflection (M12)**: critique → regenerate → re-verify, within an iteration
  limit, then **ACCEPT** or **ABSTAIN**.
- The Risk & Decision Engine (M13) may select any of: `RETURN`, `VERIFY_MORE`, `REGENERATE`,
  `ABSTAIN`, `HUMAN_REVIEW`, `BLOCK_ACTION`.

## 5. Invariants that constrain the pipeline

- Retrieval alone is never treated as proof — verification is explicit (Spec §4.5).
- Consensus is one signal, not truth (Spec §4.6).
- Confidence produced by M10 is raw; only M11 output is a calibrated ECS (Spec §4.4).
- No evidence maps to `UNKNOWN`, never `SUPPORTED` (Spec §4.9).
- Every request that completes the pipeline is persisted by M14 so the decision path can be
  reconstructed from its `query_id` (Spec §M14).

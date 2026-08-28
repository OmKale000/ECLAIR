# ECLAIR — Sequence Diagrams

> Derived only from the Spec (§5 integration flow, §7 demonstration path, §M13 decisions) and the
> repository's end-to-end test names (`tests/end_to_end/`). No invented steps or endpoints. Read
> `docs/architecture/pipeline.md` first.

The scenarios below correspond to the repository's end-to-end tests:
`test_full_pipeline.py`, `test_high_confidence_flow.py`, `test_low_confidence_reflection.py`,
`test_abstention_flow.py`, `test_human_review_flow.py`.

## 1. Full pipeline — `POST /v1/ask` (Spec §5, §7)

```
Client        API(M15)     Engine        M02    M03    M05/M06   M07    M08   M09   M10   M11   M13   M14
  |  POST /v1/ask |            |           |      |       |        |      |     |     |     |     |     |
  |-------------->|            |           |      |       |        |      |     |     |     |     |     |
  |              | ask(query) |           |      |       |        |      |     |     |     |     |     |
  |              |----------->|           |      |       |        |      |     |     |     |     |     |
  |              |            | generate  |      |       |        |      |     |     |     |     |     |
  |              |            |---------->|      |       |        |      |     |     |     |     |     |
  |              |            |<--answer--|      |       |        |      |     |     |     |     |     |
  |              |            | extract claims   |       |        |      |     |     |     |     |     |
  |              |            |----------------->|       |        |      |     |     |     |     |     |
  |              |            |<--list[Claim]----|       |        |      |     |     |     |     |     |
  |              |            | retrieve evidence        |        |      |     |     |     |     |     |
  |              |            |------------------------->|        |      |     |     |     |     |     |
  |              |            |<--list[Evidence](scored)-|        |      |     |     |     |     |     |
  |              |            | verify(claim, evidence)           |      |     |     |     |     |     |
  |              |            |---------------------------------->|      |     |     |     |     |     |
  |              |            |<--VerificationResult--------------|      |     |     |     |     |     |
  |              |            | hallucination check                     |      |     |     |     |     |
  |              |            |---------------------------------------->|      |     |     |     |     |
  |              |            | consensus (multi-model agreement)               |     |     |     |     |
  |              |            |----------------------------------------------->|     |     |     |     |
  |              |            | confidence (RAW)                                       |     |     |     |
  |              |            |----------------------------------------------------->|     |     |     |
  |              |            | calibrate -> ECS                                              |     |     |
  |              |            |----------------------------------------------------------->|     |     |
  |              |            | risk + decision                                                     |     |
  |              |            |----------------------------------------------------------------->|     |
  |              |            | persist lineage (query_id)                                              |
  |              |            |---------------------------------------------------------------------->|
  |              |<--EclairResult (answer/abstain/human_review, ECS, decision, query_id)---------------|
  |<--response---|            |
```

Invariant reminders on this path: RAG is not verification (§4.5); consensus is not truth (§4.6);
M10 confidence is raw, only M11 yields calibrated ECS (§4.4); no-evidence → UNKNOWN (§4.9).

## 2. High-confidence flow — `test_high_confidence_flow.py` (Spec §5)

```
... pipeline as above ...
Engine: calibrated ECS is HIGH
Engine -> M13: risk assessment
M13 -> Engine: DecisionResult = RETURN
Engine -> M14: persist
Engine -> API -> Client: answer RETURNED with ECS + provenance query_id
```

No reflection loop is entered when ECS is high (Spec §5 "HIGH ECS -> RETURN").

## 3. Low-confidence reflection — `test_low_confidence_reflection.py` (Spec §5, §M12)

```
... pipeline until calibrated ECS ...
Engine: calibrated ECS is LOW
Engine -> M13: risk assessment -> REGENERATE / VERIFY_MORE
Engine -> M12 Reflection:
        loop (bounded by iteration limit, Spec §M12):
          critic       : critique low-confidence / unsupported claims
          rewriter     : regenerate answer (claim-targeted correction)
          re-verify    : M07 verify corrected claims against evidence
          stopping     : stop when confidence improves OR iteration limit reached
Engine: recompute confidence (M10) -> recalibrate (M11)
Engine -> M13: final decision -> ACCEPT / ABSTAIN
Engine -> M14: persist full lineage including reflection iterations
Engine -> API -> Client: final result
```

Reflection must prevent infinite loops via the iteration limit and the stopping rule (Spec §M12).

## 4. Abstention flow — `test_abstention_flow.py` (Spec §M13, §4.9)

```
... pipeline ...
Verification: claims UNKNOWN (e.g. no supporting evidence -> UNKNOWN, §4.9)
Confidence/ECS: remains LOW after any reflection
M13: DecisionResult = ABSTAIN
Engine -> M14: persist (decision = ABSTAIN, reasons)
Engine -> API -> Client: ABSTAIN (no unsupported answer returned)
```

## 5. Human-review flow — `test_human_review_flow.py` (Spec §M13)

```
... pipeline ...
M13: risk signals warrant escalation -> DecisionResult = HUMAN_REVIEW
Engine -> M14: persist (decision = HUMAN_REVIEW)
Engine -> API -> Client: HUMAN_REVIEW (answer withheld pending review)
```

## 6. Explain — `GET /v1/explain/{query_id}` (Spec §M14, §M15)

```
Client -> API(M15): GET /v1/explain/{query_id}
API -> Engine/M14: fetch persisted lineage for query_id
M14 -> API: Query, Claims, Evidence, Verification, Confidence, Consensus,
            Risk, Decision, Final Answer, Feedback, Timestamp
API -> Client: reconstructed decision path (audit trail)
```

## 7. Feedback — `POST /v1/feedback` (Spec §M15, §M14)

```
Client -> API(M15): POST /v1/feedback (query_id + feedback)
API -> Engine/M14: persist feedback against query_id
API -> Client: acknowledgement
```

Feedback is persisted as part of the provenance lineage (Spec §M14 lists Feedback as a stored field)
and can later inform calibration (M11) against observed correctness. All product-layer surfaces stay
thin — they never compute reliability themselves (Spec §4.12).

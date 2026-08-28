# ECLAIR — Module Contracts

> Derived only from the Spec (§2, §3, §4.1, §4.3) and `rules/SHARED_CONTRACTS_REFERENCE.md`. This is
> the single-page contract summary every module must satisfy. It restates frozen values only; it
> does not invent fields. The authoritative per-module contracts are in `rules/M<NN>_*.md`.

## 1. Contract-first rule (Spec §4.9)
Define the module contract before coding:
```
INPUT -> PROCESSING -> OUTPUT -> ERROR CASES
```
Example (Spec §4.9): the Verifier accepts `Claim + Evidence[]` and returns a `VerificationResult`
with `SUPPORTED`, `CONTRADICTED`, or `UNKNOWN`; no evidence maps to `UNKNOWN`, not `SUPPORTED`.

## 2. Shared contracts (owned by M01 — Spec §4.1)
| Contract | File | Produced by |
|----------|------|-------------|
| `Query` | `contracts/query.py` | API / engine entry |
| `Claim` | `contracts/claim.py` | M03 |
| `Evidence` | `contracts/evidence.py` | M05 (annotated by M06) |
| `VerificationResult` | `contracts/verification.py` | M07 |
| `ConfidenceResult` | `contracts/confidence.py` | M10 (raw) / M11 (calibrated ECS) |
| `RiskResult` | `contracts/risk.py` | M13 |
| `DecisionResult` | `contracts/decision.py` | M13 |
| `EclairResult` | `contracts/result.py` | engine |

## 3. Producing interfaces (Spec §4.1, §4.3)
```
LLMProvider.generate(request) -> LLMResponse            # M02
ClaimExtractor.extract(text) -> list[Claim]             # M03
Retriever.search(query, top_k=5) -> list[Evidence]      # M05
Verifier.verify(claim, evidence) -> VerificationResult  # M07
ConfidenceEstimator.calculate(signals) -> ConfidenceResult  # M10 (raw)
DecisionEngine -> DecisionResult                        # M13
Engine -> EclairResult                                  # engine (final aggregate)
```

## 4. Per-module input → output map
| Module | Input | Output | Consumers |
|--------|-------|--------|-----------|
| M01 Foundation | — | contracts, config, exceptions, version, engine scaffolding | all |
| M02 LLM Gateway | `LLMRequest` | `LLMResponse` (text / structured JSON) | M03, M07, M08, M09, M12, engine |
| M03 Claim Extraction | answer text | `list[Claim]` | M05, M07, M08, M09, M10, engine |
| M04 Ingestion | PDF/TXT/MD files | standardized documents + metadata | M05 |
| M05 RAG | claim/query | `list[Evidence]` (ranked) | M06, M07, engine |
| M06 Evidence Quality | `list[Evidence]` | quality-annotated `Evidence` | M07, M08, engine |
| M07 Verification | `Claim` + `list[Evidence]` | `VerificationResult` (SUPPORTED/CONTRADICTED/UNKNOWN) | M08, M10, M12, engine |
| M08 Hallucination | claims + verification + signals | hallucination probability + flag + reasons | M10, M13, engine |
| M09 Consensus | multi-model outputs | agreement score + full/partial consensus | M08, M10, engine |
| M10 Confidence | reliability signals | `ConfidenceResult` (RAW) | M11, M13, M12, engine |
| M11 Calibration | raw confidence + observed correctness | calibrated ECS + ECE/Brier + reliability diagrams | M13, engine, M18 |
| M12 Reflection | low-ECS answer + claims | corrected + re-verified answer | engine, M13 |
| M13 Risk & Decision | ECS + reliability signals | `RiskResult` + `DecisionResult` (6 actions) | engine, M14, M15, M17 |
| M14 Provenance & DB | all stage outputs (keyed by `query_id`) | persisted lineage + audit trail | engine, M15 explain, M17, M18 |
| M15 REST API | HTTP request | HTTP response (six `/v1` endpoints) | M16, M17, external apps |
| M16 Python SDK | SDK call | typed result over REST | applications |
| M17 Dashboard | REST responses | visual views | end users |
| M18 Evaluation/Deploy | pipeline outputs / datasets | metrics, reports, reproducible build | team |

## 5. Frozen enums (do not add/rename — Spec §M07, §M13, §4.9)
- Verification status: `SUPPORTED`, `CONTRADICTED`, `UNKNOWN`
  (NLI map: `ENTAILMENT→SUPPORTED`, `CONTRADICTION→CONTRADICTED`, `NEUTRAL→UNKNOWN`; no-evidence→UNKNOWN).
- Decision actions: `RETURN`, `VERIFY_MORE`, `REGENERATE`, `ABSTAIN`, `HUMAN_REVIEW`, `BLOCK_ACTION`.
- Consensus level: full or partial consensus + numeric agreement score.

## 6. Frozen REST endpoints (Spec §M15) & SDK surface (Spec §M16)
```
POST /v1/ask   POST /v1/verify   GET /v1/explain/{query_id}
POST /v1/feedback   GET /v1/health   GET /v1/metrics

EclairClient.ask / verify / explain / feedback
```

## 7. Provenance lineage fields (Spec §M14, keyed by `query_id`)
```
Query, Claims, Evidence, Verification, Confidence, Consensus, Risk, Decision,
Final Answer, Feedback, Timestamp
```

## 8. Evaluation metric set (Spec §M18)
```
Accuracy, Hallucination Rate, Unsupported Claim Rate, ECE, Brier Score,
High-Confidence Error Rate, Correct Abstention Rate, Conflict Detection Rate,
False Action Rate, Latency
```
Baselines compared: `LLM Only`, `LLM + RAG`, `LLM + Multi-Agent`, `ECLAIR`.

> If a field/enum/interface you need is not on this page or in `rules/SHARED_CONTRACTS_REFERENCE.md`,
> it does not exist yet — raise it as a gap for M01, do not invent it.

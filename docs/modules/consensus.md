# M09 — Multi-Agent / Multi-Model Consensus

> Module documentation (Spec §4.8). Derived only from the Spec (§M09, §4.6) and repository contracts.
> Authoritative rules: `rules/M09_consensus.md`, `rules/COMMON_RULES.md`, `rules/SHARED_CONTRACTS_REFERENCE.md`.

## 1. Identity & Purpose

- **Module ID:** `M09`
- **Module Name:** Multi-Agent / Multi-Model Consensus
- **Module Folder:** `src/eclair/consensus/`
- **Unit Tests:** `tests/unit/consensus/`
- **Purpose:** Determine whether independent model outputs agree on a query or claims.

## 2. Responsibilities & Non-Responsibilities

### Responsibilities
- Execute multiple independent model generation requests concurrently via the M02 LLM Gateway.
- Perform deterministic majority voting across valid outputs, clustering semantically equivalent answers.
- Calculate a bounded cross-model agreement score in `[0.0, 1.0]`.
- Report consensus level using the frozen `ConsensusLevel` enum (`FULL` or `PARTIAL`).
- Measure output and architectural provider diversity.
- Handle partial provider failures gracefully without crashing or fabricating fake votes.

### Non-Responsibilities
- **Model Agreement is NOT Proof of Truth (Spec §4.6):** Consensus produces a single reliability signal; three models agreeing does not prove factual truth.
- Does NOT perform claim extraction (M03).
- Does NOT retrieve evidence (M05).
- Does NOT verify claims against evidence (M07).
- Does NOT fuse overall confidence (M10).
- Does NOT calibrate ECS (M11).
- Does NOT make system actions or risk decisions (M13).
- Does NOT persist records directly to the database (M14).

## 3. Architecture & File Structure

```
src/eclair/consensus/
├── __init__.py      # Module exports
├── models.py        # ConsensusResult, VotingResult, AgreementResult, DiversityResult, ModelOutput, ModelCallConfig
├── runner.py        # ConsensusRunner (concurrent async orchestration via M02)
├── voting.py        # MajorityVoter (deterministic clustering, vote shares, majority winning answer)
├── agreement.py     # AgreementCalculator (pairwise similarity, fused score, FULL vs PARTIAL categorization)
└── diversity.py     # DiversityCalculator (cluster count, pairwise distance, provider architecture diversity)
```

## 4. Method & Algorithms

1. **Concurrent Execution:** Dispatches model requests in parallel via `asyncio.to_thread` / `asyncio.gather`, using M02's `build_provider` or injected `LLMRouter`.
2. **Error Isolation & Graceful Degradation:** Catches individual provider errors (`ModuleError`, timeouts) and records them in `failed_models`. Successful outputs continue to voting. If all fail, raises `ModuleError(code="consensus_all_models_failed")`.
3. **Majority Voting:** Normalizes text, computes token Jaccard similarity, clusters equivalent responses, and computes vote counts and shares.
4. **Agreement Scoring:** Combines mean pairwise similarity $\bar{S}$ (token Jaccard + sequence alignment ratio) and majority vote share $R$:
   $$\text{agreement\_score} = \alpha \cdot R + (1 - \alpha) \cdot \bar{S} \quad (\text{clamped to } [0.0, 1.0])$$
5. **Consensus Classification:**
   - `ConsensusLevel.FULL`: Unanimous agreement or agreement score $\ge 0.85$ with strict majority.
   - `ConsensusLevel.PARTIAL`: Divergent models, split votes, or lower agreement.
6. **Diversity Metrics:** Quantifies answer dispersion and provider architectural diversity.

## 5. Integration

```
M01 Query / Text
       │
       ▼
M09 ConsensusRunner ──► M02 LLM Gateway (Independent Provider Calls: Ollama, Gemini, Groq, OpenRouter)
       │
       ├─► MajorityVoter (Vote clusters, winning answer)
       ├─► AgreementCalculator (agreement_score, ConsensusLevel)
       └─► DiversityCalculator (diversity_score, provider count)
       │
       ▼
ConsensusResult (agreement_score, consensus_level, majority_answer, is_truth=False)
       │
       ├─► M08 Hallucination Detection (model_disagreement_score = 1.0 - agreement_score)
       ├─► M10 Confidence Estimation (raw confidence signal)
       └─► Engine / Orchestrator
```

## 6. Sample Input & Output

### Sample Input

```python
from eclair.consensus import ConsensusRunner, ModelCallConfig

runner = ConsensusRunner()

query = "What is the company refund window?"
models = [
    ModelCallConfig(provider="ollama", model="llama3"),
    ModelCallConfig(provider="gemini", model="gemini-1.5-flash"),
    ModelCallConfig(provider="groq", model="llama3-70b-8192"),
]

result = runner.run(query=query, models=models)
```

### Sample Output

```json
{
  "query": "What is the company refund window?",
  "agreement_score": 1.0,
  "consensus_level": "FULL",
  "majority_answer": "Customers may request a full refund within 30 calendar days of initial purchase.",
  "model_outputs": [
    {
      "model": "llama3",
      "provider": "ollama",
      "text": "Customers may request a full refund within 30 calendar days of initial purchase.",
      "success": true,
      "latency_seconds": 0.42
    },
    {
      "model": "gemini-1.5-flash",
      "provider": "gemini",
      "text": "Customers may request a full refund within 30 calendar days of initial purchase.",
      "success": true,
      "latency_seconds": 0.31
    },
    {
      "model": "llama3-70b-8192",
      "provider": "groq",
      "text": "Customers may request a full refund within 30 calendar days of initial purchase.",
      "success": true,
      "latency_seconds": 0.18
    }
  ],
  "successful_models": [
    "ollama:llama3",
    "gemini:gemini-1.5-flash",
    "groq:llama3-70b-8192"
  ],
  "failed_models": [],
  "voting": {
    "majority_answer": "Customers may request a full refund within 30 calendar days of initial purchase.",
    "winning_vote_count": 3,
    "total_votes": 3,
    "majority_ratio": 1.0,
    "has_majority": true,
    "unanimous": true,
    "clusters": [
      {
        "representative_text": "Customers may request a full refund within 30 calendar days of initial purchase.",
        "vote_count": 3,
        "vote_share": 1.0,
        "model_names": ["llama3", "gemini-1.5-flash", "llama3-70b-8192"]
      }
    ],
    "vote_counts": {
      "Customers may request a full refund within 30 calendar days ...": 3
    }
  },
  "agreement": {
    "agreement_score": 1.0,
    "consensus_level": "FULL",
    "mean_pairwise_similarity": 1.0,
    "pairwise_similarities": [1.0, 1.0, 1.0],
    "unanimous": true
  },
  "diversity": {
    "diversity_score": 0.0,
    "unique_answer_count": 1,
    "mean_pairwise_distance": 0.0,
    "provider_diversity_count": 3
  },
  "is_truth": false
}
```

## 7. Reliability Semantics & Boundary Invariants

- **Agreement $\neq$ Truth:** `is_truth` is always `False`. Agreement is strictly one reliability signal.
- **Absence / Degradation:** Failed model calls do not fabricate agreement or crash execution; they are isolated into `failed_models`.
- **Thin Interface:** M09 implements agreement measurement and multi-model dispatch only.

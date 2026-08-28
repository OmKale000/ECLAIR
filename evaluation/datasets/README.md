# ECLAIR — Evaluation Datasets

> Derived only from the Spec (§M18, §1 folder structure, §4.7) and the repository. Owned by **M18**
> (Evaluation, Benchmarking & Deployment). No invented datasets or metrics. Read
> `rules/M18_evaluation_deployment.md` first.

## Purpose (Spec §M18)
These datasets support benchmarking ECLAIR's reliability and calibration so that the project can be
reproduced and its improvement over baselines demonstrated.

## Layout (Spec §1)
```
evaluation/datasets/
  README.md          # this file
  factuality/        # factual-accuracy evaluation data
  hallucination/     # hallucination-detection evaluation data
  confidence/        # confidence-estimation evaluation data
  calibration/       # calibration (ECS) evaluation data
```

## Dataset categories
Each folder holds evaluation data for one reliability dimension the pipeline is measured on:
- **factuality/** — cases used to measure Accuracy and Unsupported Claim Rate.
- **hallucination/** — cases used to measure Hallucination Rate and Conflict Detection Rate.
- **confidence/** — cases used to measure confidence quality feeding calibration.
- **calibration/** — raw-confidence-vs-observed-correctness data used to fit and evaluate the
  calibrated ECS (ECE, Brier Score, reliability diagrams — Spec §M11, §M18).

## How the datasets are used (Spec §M18)
The runners under `evaluation/runners/` (`benchmark_runner.py`, `evaluation_runner.py`,
`calibration_runner.py`) run the baselines under `evaluation/baselines/`
(`llm_only.py`, `rag_only.py`, `multi_agent.py`) and ECLAIR against these datasets, then compute the
metrics under `evaluation/metrics/`:
```
accuracy · hallucination_rate · unsupported_claim_rate · ece · brier ·
high_confidence_error · abstention · conflict_detection · false_action · latency
```
Baselines compared (Spec §M18): `LLM Only`, `LLM + RAG`, `LLM + Multi-Agent`, `ECLAIR`.
Reports are generated under `evaluation/reports/` (`generate_report.py`, `outputs/`).

## Relationship to the controlled knowledge base (Spec §4.7)
Evaluation is designed to be reproducible and benchmarkable, consistent with the controlled
knowledge base approach (`data/knowledge_base/`). These evaluation datasets are separate from the
runtime knowledge base and are used only for measuring reliability.

## Status
These dataset folders are placeholders on the `Rules` branch (they contain `.gitkeep`). The concrete
datasets are added by M18. Do not invent dataset contents here; add them as part of the M18 module
deliverable.

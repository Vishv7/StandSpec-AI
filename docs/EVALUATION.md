# StandSpec AI — Benchmark & Evaluation Methodology
## Phase P1-D: Authoritative Evaluation & Adversarial Hardening

---

## 1. Unified Evaluation Library (`src/evaluation/metrics.py`)

All evaluation scripts (`evaluate_recommendation.py`, `run_retrieval_ablation.py`) use the single, canonical metrics library in `src/evaluation/metrics.py`.

### 1.1 The Three Distinct Top-1 Metrics
To prevent ambiguity between retrieval ranking, decision filtering, and final recommendation, the system computes three distinct Top-1 metrics:

1. **`RAW_RETRIEVAL_TOP1`**:
   - Evaluated strictly on the raw Top-1 candidate from the retrieval pipeline before any applicability filtering, lifecycle resolution, or abstention policies.
   - Measures raw retrieval channel power.

2. **`EFFECTIVE_CANDIDATE_TOP1`**:
   - Evaluated on the highest viable candidate emitted by the pipeline (either `primary_recommendation` or `review_candidate`).
   - Measures candidate discovery rate across both automated and human-in-the-loop workflows.

3. **`VERIFIED_PRIMARY_TOP1`**:
   - Evaluated strictly on the verified `primary_recommendation`.
   - Any query where the engine rightfully abstained or withheld primary recommendation yields 0 for this metric.
   - Measures pure automated recommendation precision.

### 1.2 Comprehensive Metric Definitions
- **Recall@K (K=1, 3, 5, 10)**: Fraction of queries where at least one gold standard appears in Top-K candidates.
- **MRR (Mean Reciprocal Rank)**: Position-sensitive candidate ranking quality.
- **Safe Decision Accuracy**: Accuracy evaluated against the evidence-grounded safe expected decision (verifies appropriate abstention when gold standards are unverified or queries lack specifications).
- **Unsafe Primary Promotion Rate**: Frequency of promoting an unverified candidate to primary recommendation (Target: 0.00%).
- **Hard Negative Rejection Rate (HNRR@1)**: Proportion of queries where hard negative standards are kept off rank 1.
- **Hard Negative Intrusion Rate (@5 / @10)**: Proportion of queries where a hard negative penetrates the top candidate list.
- **Statistical Calibration (ECE & Brier Score)**: Reliability diagnostic of output confidence probabilities.

---

## 2. Benchmark Suite Overview

The benchmark suite consists of targeted datasets strictly isolated to prevent data leakage:

| Benchmark Dataset | Queries | Negatives | Primary Purpose |
|:---|:---:|:---:|:---|
| `data/benchmarks/test.jsonl` | 13 | 27 | Authoritative benchmark covering CED & ETD products |
| `data/benchmarks/val.jsonl` | 13 | 26 | Tuning and retrieval ablation benchmark |
| `data/benchmarks/adversarial.jsonl` | 32 | 64 | Adversarial safety benchmark covering all HN1–HN8 failure modes |
| `data/benchmarks/coverage_boundary.jsonl` | 10 | 20 | Out-of-scope non-CED/ETD procurement requests expecting safe abstention |
| `data/benchmarks/challenge.jsonl` | 10 | 20 | Multi-attribute, cross-domain, and historical edition challenge cases |
| `data/benchmarks/train.jsonl` | 24 | 48 | Calibrator fitting and parameter exploration |

### 2.1 Adversarial Taxonomy Coverage (HN1–HN8)
The adversarial benchmark explicitly tests:
- **HN1 (Close Product Sub-type Confusion)**: UPVC vs CPVC vs HDPE pipes.
- **HN2 (Part / Section Confusion)**: IS 1239 Part 1 (tubes) vs Part 2 (fittings).
- **HN3 (Standard Role Confusion)**: Product standard vs test method (IS 10810) vs design code (IS 800, IS 16231).
- **HN4 (Domain Crossover Confusion)**: Civil structural steel vs electrical conduit.
- **HN5 (Material / Substrate Confusion)**: Ductile iron (IS 8329) vs cast iron (IS 1536).
- **HN6 (Lifecycle / Supersession Confusion)**: Pre-revision tender specification requesting superseded edition.
- **HN7 (Voltage / Application Mismatch)**: Low-voltage PVC (IS 1554 Part 1) vs high-voltage XLPE (IS 7098 Part 2).
- **HN8 (Explicit Wrong Designation Trap)**: Explicit citation of a contradictory standard (e.g. `"Supply of uPVC pipes as per IS 1180 Part 1"`).

---

## 3. Evaluation Artifacts

All evaluation runs generate machine-readable JSON artifacts in `data/evaluations/`:
- `data/evaluations/test_evaluation.json`: Test suite evaluation report.
- `data/evaluations/val_evaluation.json`: Validation suite evaluation report.
- `data/evaluations/adversarial_evaluation.json`: Adversarial safety evaluation report.
- `data/evaluations/coverage_boundary_evaluation.json`: Boundary abstention evaluation report.
- `data/evaluations/retrieval_ablation.json`: Multi-channel retrieval ablation diagnostic.

Every artifact includes SHA-256 integrity digests, environment metadata, and complete per-query diagnostic logs.

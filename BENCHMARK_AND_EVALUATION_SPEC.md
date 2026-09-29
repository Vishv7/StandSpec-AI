# BENCHMARK_AND_EVALUATION_SPEC.md — Benchmark & Evaluation Specification
## StandSpec AI — Zero-Leakage Benchmark Architecture, Maturity Tiers, and Multi-Gold Metric Protocols

---

## 1. Executive Summary

This specification governs the evaluation methodology for StandSpec AI. Correct evaluation of an Indian Standards recommendation engine requires that benchmark datasets reflect the genuine ambiguity, multilingual phrasing, and technical complexity of real government tenders without allowing test data leakage.

---

## 2. Benchmark Maturity Tiers

To prevent confusion between initial schema templates and full held-out evaluation corpora, StandSpec AI establishes 3 formal maturity tiers:

| Tier | Name | Query Count | Requirements | Operational Use |
|---|---|---|---|---|
| **Tier 1** | `TIER_1_SCHEMA_VALID` | >= 1 | Valid against `schemas/procurement_ground_truth.schema.json`. | Schema compliance validation. |
| **Tier 2** | `TIER_2_PROTOTYPE_TEMPLATE_VALID` | 4 – 19 | Schema valid, includes gold standards, multiple HN classes, and 5-dimension stratification. | Prototype end-to-end regression testing & CI validation. |
| **Tier 3** | `TIER_3_EVALUATION_READY` | >= 20 (Target 100+) | >= 20 queries, >= 50% implicit queries, all 8 HN classes represented, multi-annotator agreement, temporal split, held-out test split. | Formal competitive benchmarking, ablations, and SIH jury defense. |

---

## 3. The 7-Dimension Zero-Leakage Split Policy

Any split between training/tuning data (Datasets A/B) and held-out evaluation sets (Datasets C/D) must enforce zero leakage across 7 orthogonal dimensions:

1. **Exact Standard Isolation:** A standard designation appearing in the test set gold list must never appear in the training set gold list.
2. **Base Family Isolation:** Part variations of a standard (e.g. `IS 7098 Part 1` vs `IS 7098 Part 2`) must not cross the train-test boundary. Base number `IS 7098` belongs to one split only.
3. **Product Family Stratification:** Product categories (e.g., XLPE cables vs PVC conduits) are clustered to prevent domain familiarity bias.
4. **Procuring Agency Isolation:** Tenders from the same procuring division are grouped to prevent stylistic lexical leakage.
5. **Strict Lexical Isolation:** Implicit queries in the test set must never contain the verbatim base standard number in their query text.
6. **Graph Neighborhood Isolation:** 2-hop knowledge graph clusters of test gold standards must not overlap with train gold standards by Jaccard similarity > 0.50.
7. **Hard Negative Independence:** A test query's hard negative standard must not be an active gold target in the training set.

---

## 4. Multi-Gold Evaluation Metrics & Mathematical Definitions

Because a procurement tender can validly require multiple interrelated standards (e.g., product specification + conductor material + type test methods), single-gold top-1 accuracy is scientifically invalid. StandSpec AI implements mathematically rigorous multi-gold metrics:

### 4.1 Multi-Gold Recall@K
$$\text{Recall@K} = \frac{|\text{Retrieved@K} \cap \text{GoldStandards}|}{|\text{GoldStandards}|}$$

Where:
- Evaluates the fraction of all necessary standards retrieved in the top $K$ candidates.
- A query requiring 3 standards where 1 is retrieved in top 10 receives Recall@10 = $0.333$, strictly not a binary $1.0$.

### 4.2 Full-Gold IDCG for Normalized Discounted Cumulative Gain (NDCG@K)
$$\text{DCG@K} = \sum_{i=1}^{K} \frac{r_i}{\log_2(i + 1)}$$
$$\text{IDCG@K} = \sum_{i=1}^{\min(K, |\text{GoldStandards}|)} \frac{1}{\log_2(i + 1)}$$
$$\text{NDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}$$

Where:
- Ideal DCG (IDCG) is computed over the **entire set of gold standards**, ensuring missing gold standards properly penalize the ranking score.

### 4.3 Mean Reciprocal Rank (MRR)
$$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_{\text{first\_gold}}(q)}$$

Measures the rank of the first relevant gold standard in the recommendation list.

---

## 5. CLI Verification Commands

### 5.1 Validate Benchmark Schema, Tiers & Lexical Isolation
```bash
python scripts/validate_benchmark.py --input data/benchmarks/procurement_benchmark_template.jsonl --strict-isolation
```

### 5.2 Validate Zero-Leakage Between Train and Test Splits
```bash
python scripts/validate_benchmark.py --leakage-check \
    --train data/benchmarks/train.jsonl \
    --test data/benchmarks/test.jsonl \
    --graph data/processed/standards_graph.json \
    --temporal-split
```

### 5.3 Evaluate Information Retrieval Baseline (BM25)
```bash
python scripts/evaluate_retrieval.py \
    --benchmark data/benchmarks/procurement_benchmark_template.jsonl \
    --standards data/processed/FAD/FAD_standards.jsonl
```

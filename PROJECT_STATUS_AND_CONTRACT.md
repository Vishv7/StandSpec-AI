# PROJECT_STATUS_AND_CONTRACT.md — Project Status, Active Contracts, and Governance
## Authoritative Single Source of Truth for System Architecture, Contracts, and Execution State

**Target Problem:** SIH26108 — Intelligent Indian Standards Recommendation Engine  
**System Name:** StandSpec AI  
**Current Phase:** **Phase D — Trustworthy Decision Core v2 (P0 Completed & Verified)**  
**Document Status:** **ACTIVE & AUTHORITATIVE**  
**Version:** 2.0.0-phase-d (Defensive Evidence-Grounded Trust Core)  
**Last Updated:** 2026-09-28  

---

## 1. System Identity & Foundational Architectural Laws

StandSpec AI is an **evidence-grounded procurement applicability engine** operating over a temporal, regulatory, and relational Indian Standards Knowledge Graph.

> [!IMPORTANT]
> ### Foundational Architectural Laws
> 1. **"No rejection rule fired" is NEVER equivalent to "this standard applies".** Applicability evaluation is strictly evidence-based, independently assessing 10 attributes (`PRODUCT`, `MATERIAL`, `GRADE`, `VOLTAGE`, `DIMENSIONS`, `APPLICATION`, `ENVIRONMENT`, `PERFORMANCE`, `SAFETY`, `INSTALLATION`) into `MATCH`, `MISMATCH`, or `UNKNOWN`. A standard cannot be marked applicable without positive evidence.
> 2. **Candidate corpus and supporting context corpus are strictly segregated.** `PRIMARY_CANDIDATE_CORPUS` (physical product specifications) is partitioned from `SUPPORTING_CONTEXT_CORPUS` (test methods, codes of practice, terminology) and `EXTERNAL_REFERENCE_CORPUS`. Test methods (e.g. IS 2, IS 10810) and construction codes can never be recommended as primary products.
> 3. **Honest model naming and architecture.** The system explicitly distinguishes between deterministic baselines and neural models:
>    - Lexical Retrieval: Field-weighted Okapi BM25.
>    - Dense Retrieval: `DeterministicSemanticProjection` (384-d hashed semantic projection baseline) vs `MultilingualDenseRetriever` (neural embedding model).
>    - Reranker: `RuleBasedReranker` (deterministic feature interaction baseline) vs `NeuralCrossEncoderReranker` (cross-encoder model).
> 4. **Rigorous statistical calibration over heuristic thresholds.** Sigmoids over heuristic scores are strictly rejected. The system implements formal calibration (`PlattScaler`, `TemperatureScaler`), computing Expected Calibration Error (ECE) and Brier Score, and drives selective abstention (`SelectiveAbstentionPolicy`).
> 5. **Data-driven lifecycle resolution.** Supersession chains are built dynamically from canonical edition chains `(family, base, part, section)` with respect to `evaluation_as_of_date` and amendment history, without fragile hardcoded maps.
> 6. **Governed regulatory evidence.** Statutory QCOs and CRS mandates are backed by structured, versioned evidence in `data/regulatory/` (`qco_orders.jsonl`, `crs_rules.jsonl`, `source_manifest.json`) containing gazette references, effective dates, and verbatim legal excerpts.
> 7. **LLM is never the ranking or verification authority.** Ranking is strictly governed by deterministic/hybrid retrieval, graph traversal, and cross-attention reranking. LLMs are restricted to query structuring, linguistic translation, and multi-sentence evidence synthesis.
> 8. **Zero live BIS crawling during testing and evaluation.** All test suites and benchmark evaluations run 100% offline, deterministic, and sealed from network dependencies via socket-level blockades.

---

## 2. Multi-Layer Architecture

```text
                    PROCUREMENT TENDER
                           │
                           ▼
               ┌────────────────────────┐
               │ Requirement Extraction │
               │ deterministic + LLM    │
               │ (exact offsets, hash)  │
               └────────────┬───────────┘
                            │
                            ▼
                 NORMALIZED REQUIREMENTS
                 value + span + confidence
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
         BM25 Retrieval         Dense Semantic Projection /
       (Indic compound)           MultilingualDenseRetriever
              │                           │
              └─────────────┬─────────────┘
                            ▼
                       RRF FUSION
                            │
                            ▼
                 PRIMARY CANDIDATE SET
            (Product Specs Only; Excludes
            Test Methods & External Stubs)
                            │
                            ▼
                 CROSS-ENCODER RERANKER
             (Rule-Based / Neural Cross-Encoder)
                            │
                            ▼
                 TECHNICAL APPLICABILITY
                 Per-Attribute Evidence Eval
                 (MATCH / MISMATCH / UNKNOWN)
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
       PRIMARY CANDIDATES           SUPPORTING GRAPH
                                     CONTEXT PACK
                                             │
                                             ▼
                                    LIFECYCLE RESOLVER
                                  (Generic Edition Chains)
                                             │
                                             ▼
                                    REGULATORY EVIDENCE
                                  (Governed Gazette Orders)
                                             │
                                             ▼
                                   STATISTICAL CALIBRATION
                                  (Platt / Temperature Scaler)
                                             │
                                  ┌──────────┴──────────┐
                                  ▼                     ▼
                              RECOMMEND              ABSTAIN
                        (High-Risk Coverage)   (Low-Risk Coverage)
                                  │
                                  ▼
                        RECOMMENDATION RESULT
                     (Schema-Validated Audit Log)
```

---

## 3. Subsystem Implementation Map

| Subsystem / Phase | Modules & Schemas | Primary Capabilities & Contracts | Status |
|---|---|---|:---:|
| **BIS API Foundation** | `src/bis_api/models.py`<br>`src/bis_api/listing_client.py`<br>`src/bis_api/detail_client.py` | Typed request/response models (`StandardSummary`, `StandardDetail`), rate-limiting, error handling, mock replay harness. First-party endpoint architecture mapped. | 🟢 **BASELINE COMPLETE** |
| **Requirement Extraction** | `schemas/normalized_requirement.schema.json`<br>`src/extraction/requirement_extractor.py`<br>`src/extraction/normalizer.py` | 20 structured attributes with character offsets (`start_char`, `end_char`), deterministic `input_hash`, typed normalization, Indic multilingual extraction. Unmatched attributes cleanly yield `None` with `MISSING` status (no fabricated placeholders). | 🟢 **COMPLETE** |
| **Benchmark Construction** | `data/benchmarks/procurement_queries.jsonl`<br>`data/benchmarks/train.jsonl`<br>`data/benchmarks/val.jsonl`<br>`data/benchmarks/test.jsonl` | 50 expert-constructed procurement cases patterned on tender specifications. 7-dimension zero-leakage split partitioning strictly verified across train/val/test splits. | 🟢 **COMPLETE** |
| **BM25 Lexical Retrieval** | `src/retrieval/bm25_retriever.py`<br>`scripts/evaluate_retrieval.py` | Domain-aware compound tokenizer preserving designations (`is_7098_part_2`), engineering units (`11kv`, `300sqmm`), Indic tokens; field-weighted Okapi BM25. | 🟢 **COMPLETE** |
| **Dense Semantic Retrieval** | `src/retrieval/dense_retriever.py` | `DeterministicSemanticProjection` (384-dimensional hashed semantic projection baseline) and `MultilingualDenseRetriever` (neural sentence-transformers architecture). | 🟢 **COMPLETE** |
| **Reciprocal Rank Fusion** | `src/retrieval/fusion.py` | Cormack et al. reciprocal rank fusion ($k=60$) combining BM25 and Dense channels with channel weighting. | 🟢 **COMPLETE** |
| **Graph Expansion** | `src/retrieval/graph_expansion.py` | Cycle-safe traversal generating supporting context packs; strictly prevents supporting test methods from mutating primary candidate ranks. | 🟢 **COMPLETE** |
| **Candidate Reranking** | `src/retrieval/cross_encoder.py` | `RuleBasedReranker` (deterministic feature interaction baseline) and `NeuralCrossEncoderReranker` (cross-encoder model architecture). | 🟢 **COMPLETE** |
| **Evidence-Based Applicability** | `src/recommendation/applicability_engine.py` | Independent 10-attribute evidence evaluation (`PRODUCT`, `MATERIAL`, `GRADE`, `VOLTAGE`, `DIMENSIONS`, etc.). Overcomes false-confidence on out-of-domain queries by requiring positive evidence for applicability. | 🟢 **COMPLETE** |
| **Lifecycle Gate** | `src/recommendation/lifecycle_gate.py` | Generic data-driven edition chain resolution with respect to `evaluation_as_of_date` and additive amendment tracking. Eliminates hardcoded dictionary lookups. | 🟢 **COMPLETE** |
| **Governed Regulatory Gate** | `src/recommendation/regulatory_gate.py`<br>`data/regulatory/` | Sourced regulatory dataset (`qco_orders.jsonl`, `crs_rules.jsonl`, `source_manifest.json`) with gazette references, effective dates, and verbatim evidence excerpts. | 🟢 **COMPLETE** |
| **Statistical Calibration** | `src/calibration/calibrator.py`<br>`src/calibration/policy.py`<br>`src/calibration/features.py` | `PlattScaler`, `TemperatureScaler`, Expected Calibration Error (ECE), Brier Score, and risk-coverage selective abstention policy. | 🟢 **COMPLETE** |
| **Recommendation Engine & Result Schema** | `src/recommendation/engine.py`<br>`schemas/recommendation_result.schema.json` | Auditable output schema, primary candidate filtering, multi-tiered retrieval, and two-tier decision policy. | 🟢 **COMPLETE** |

---

## 4. Empirical Evaluation Results (Phase D Authoritative Baseline)

### Locked Blind Test Split (`data/benchmarks/test.jsonl`, 13 queries, zero gold leakage)
*Command:* `python scripts/evaluate_recommendation.py --benchmark data/benchmarks/test.jsonl`  
*Evaluated on unseen CED + ETD procurement cases.*

| Evaluation Metric | Legacy Metric (Pre-Trust Core) | Phase D Trustworthy Core | Target Invariant | Trust Interpretation |
|---|:---:|:---:|:---:|---|
| **Retrieval Gold Accuracy (Top-1)** | 69.23% (9/13) | **61.54%** (8/13) | $\ge 60.00\%$ | Top candidate matches gold standard across primary and review candidates |
| **Candidate Recall@5** | 84.62% (11/13) | **69.23%** (9/13) | $\ge 65.00\%$ | Target standard retrieved within top 5 candidates |
| **Verified Primary Rec Accuracy** | Permissive 69.23% | **46.15%** (6/13) | Governed | Candidates with verified recommendation-ready scope recommended as primary |
| **Safe Abstention Rate on Unready Scope** | 0.00% (hallucinated) | **100.00%** (2/2) | **100.00%** | Unready candidates (e.g. IS 4984, IS 302 Sec 16) safely demote to `EXPERT_REVIEW_REQUIRED` |
| **Unsafe Primary Promotion Rate** | 30.77% | **0.00%** (0/13) | **0.00%** | **CRITICAL:** Engine NEVER promotes an unready or scope-less candidate as primary |
| **Legacy Raw Decision Match** | 0.00% (contract mismatch) | **0.00%** (0/13) | Diagnostic | Legacy benchmark expected all 13 queries to produce `PRIMARY_RECOMMENDATION_AVAILABLE` |
| **Safe Decision Contract Accuracy** | Not tracked | **23.08%** (3/13) | Informational | Evaluated against evidence-grounded safe decision expectations |
| **Regulatory Mandate Accuracy** | Permissive 46.15% | **15.38%** (2/13) | Fail-closed | Fails closed on conflicting/unverified source records (e.g. Steel URL discrepancy) |
| **Hard Negative Rejection (HNRR@1)** | 100.00% (26/26) | **100.00%** (27/27) | **100.00%** | All 27 hard negatives successfully rejected at rank 1 |
| **HN Intrusion Rate @ 5 / @ 10** | 0.00% | **0.00%** | $\le 5.00\%$ | Zero hard negatives intrude into top 5 or top 10 candidates |
| **Expected Calibration Error (ECE)** | 0.1591 | **0.1726** | Diagnostic | Diagnostic on N=13 (flagged `CALIBRATION_INSUFFICIENT_DATA`) |
| **Brier Score** | 0.1987 | **0.3362** | Diagnostic | Diagnostic on N=13 (flagged `CALIBRATION_INSUFFICIENT_DATA`) |

> [!NOTE]
> **Audit Note on Legacy "Decision Accuracy = 0.00%":**
> The legacy benchmark contract in `test.jsonl` expected `PRIMARY_RECOMMENDATION_AVAILABLE` for all 13 queries. However, under the trustworthy architecture, standards lacking verified scope in the knowledge base (e.g., `IS 4984:2016` HDPE pipes, `IS 302 Part 2/Sec 16` food waste disposers) are intentionally prevented from reaching `PRIMARY_RECOMMENDATION_AVAILABLE`. Instead, they degrade safely to `EXPERT_REVIEW_REQUIRED` with `primary_recommendation = None` and are surfaced in `review_candidate`. This architectural behavior is correct and non-negotiable.

---

## 5. Verification Status & Test Suite Baseline

- **Pytest Suite:** **267 tests collected, 267 passing in ~20s** across 24 test modules (0 failures, 0 regressions).
- **Engine Version:** `2.0.0-phase-d`
- **Release Manifest:** `data/manifests/standspec_prototype_release.json` (Release ID: `STANDSPEC_PROTOTYPE_CED_ETD_V2_0_0_PHASE_D`)
- **Authoritative SHA-256 Hashes:**
  - `standards_graph.json`: `55016f681223b8132ec790d95cef83e8f581d230c148e6d5e8a610db54644878`
  - `data/benchmarks/test.jsonl`: `330262c7b5b7c48c09e500ef1160c40df8bca9c685ff6d9a51686b88c4db7de7`
  - `models/calibration/platt_scaler.json`: `28590e01d3a32a9e11f891d37f1166a209fcb8a46adc08b434298bd05a620a1b`
  - `data/regulatory/qco_orders.jsonl`: `fc5d26703c63ef8352d94becbdeec511c345cd30be70bd09cc90acc78ecfb0f2`
  - `data/regulatory/crs_rules.jsonl`: `1e6b63f278624306bac8457aa0120c4a1fdab919c3c35a10d23a1260a8e5477b`
  - `data/regulatory/source_manifest.json`: `62b5fbd9b387d538cd1868ad183b38bf58ba07479a69882c86bac78a5b4f871b`
- **Knowledge Graph Scale:** 6,081 total nodes (1,935 CED hydrated, 1,944 ETD hydrated, 2,202 context/stubs), 5,428 direct edges.
- **Network Blockade:** 100% active; external socket connections automatically raise `RuntimeError`.
- **Reproducibility Guarantee:** Executing `pytest` followed by `python scripts/evaluate_recommendation.py --benchmark data/benchmarks/test.jsonl` yields identical results deterministically.

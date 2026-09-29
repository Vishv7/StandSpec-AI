# StandSpec AI — Operations & Verification Manual
## Phase P1-D: Standard Operational Runbook & Verification Gates

---

## 1. The 9 Core Verification Gates

Every pull request, model update, or certified release MUST pass all 9 verification gates sequentially:

```bash
# Gate 1: Full Hermetic Test Suite (300+ tests, offline)
python -m pytest -q

# Gate 2: Release Manifest Cryptographic Check
python scripts/generate_release_manifest.py --check

# Gate 3: Knowledge Graph Topological Invariants
python scripts/validate_graph_invariants.py --graph data/processed/standards_graph.json

# Gate 4: Benchmark Dataset Schema & Leakage Isolation (Test & Val)
python scripts/validate_benchmark.py --input data/benchmarks/test.jsonl --strict-isolation
python scripts/validate_benchmark.py --input data/benchmarks/val.jsonl --strict-isolation

# Gate 5: Regulatory Source & Manifest Cross-Validation
python scripts/validate_regulatory_sources.py

# Gate 6: Authoritative Test Recommendation Evaluation
python scripts/evaluate_recommendation.py --benchmark data/benchmarks/test.jsonl --output-json data/evaluations/test_evaluation.json

# Gate 7: Validation Set Recommendation Evaluation
python scripts/evaluate_recommendation.py --benchmark data/benchmarks/val.jsonl --output-json data/evaluations/val_evaluation.json

# Gate 8: Adversarial & Boundary Safety Verification
python scripts/evaluate_recommendation.py --benchmark data/benchmarks/adversarial.jsonl --output-json data/evaluations/adversarial_evaluation.json
python scripts/evaluate_recommendation.py --benchmark data/benchmarks/coverage_boundary.jsonl --output-json data/evaluations/coverage_boundary_evaluation.json

# Gate 9: Re-generate Release Manifest with Fresh Evaluation Metrics & Hashes
python scripts/generate_release_manifest.py
```

---

## 2. Additional Diagnostic Pipelines

```bash
# Multi-channel retrieval ablation across BM25, Dense, and Hybrid modes
python scripts/run_retrieval_ablation.py --benchmark data/benchmarks/val.jsonl

# Re-build knowledge graph from raw collector data
python scripts/build_knowledge_graph.py

# Benchmark validation on adversarial, challenge, and coverage datasets
python scripts/validate_benchmark.py --input data/benchmarks/adversarial.jsonl
python scripts/validate_benchmark.py --input data/benchmarks/coverage_boundary.jsonl
python scripts/validate_benchmark.py --input data/benchmarks/challenge.jsonl
```

---

## 3. Environment Specifications

- **OS**: Windows / Linux / macOS compatible
- **Python**: 3.10+ (Certified on Python 3.14.6)
- **Pytest**: 9.1.1+
- **Network Isolation**: By default, no network calls are required. Socket-level blockades succeed hermetically.

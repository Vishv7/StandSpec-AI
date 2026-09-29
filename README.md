# StandSpec AI — Evidence-Grounded Indian Standards Recommendation Engine
## Smart India Hackathon — Problem Statement SIH26108

[![Tests](https://img.shields.io/badge/Tests-Passing%20(100%25%20Hermetic)-brightgreen.svg)]()
[![Network Isolation](https://img.shields.io/badge/Network-Socket%20Blockade%20Active-blue.svg)]()
[![Knowledge Graph](https://img.shields.io/badge/Graph-6081%20Nodes%20%7C%205428%20Edges-purple.svg)]()

---

## 1. Executive Overview

**StandSpec AI** is an evidence-grounded recommendation system engineered for Indian Public Procurement (GeM, IREPS, Defence CPP). It accepts natural-language procurement requirements, technical specifications, and tender schedules, and accurately identifies:

1. **Applicable Primary Indian Standards (IS)** covering the product or service.
2. **Allied Standards** including normative references, mandatory test methods, raw material specifications, and installation guidelines.
3. **Current Lifecycle Status**, ensuring superseded revisions are flagged and active editions are recommended.
4. **Statutory Regulatory Mandates**, verifying governed Quality Control Orders (QCOs) and Compulsory Registration Scheme (CRS) requirements.
5. **Traceable Verbatim Evidence** with calibrated selective abstention when tender specifications lack discriminating technical parameters or lack positive product grounding.

> [!IMPORTANT]
> ### Core Engineering Law
> **The Large Language Model (LLM) is NEVER the unconstrained ranking authority.**  
> Candidate recall, ranking, graph traversal, and legal obligation verification are executed by deterministic graph algorithms, calibrated rerankers, and regulatory rule engines. The LLM is restricted to evidence synthesis, structured translation, and explanation generation under strict verification gates.

---

## 2. Multi-Layer System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: DATA PREPARATION & NORMALIZATION (COLLECTOR)                       │
│ Excel Reader → Cached HTML Parser → Structured V1.2 JSONL                   │
│ Snapshot Mode & Invalidation Engine • 100% Offline • Socket Blockade Active │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│ KNOWLEDGE BASE LAYERS (LAYERS 2, 3, 4)                                      │
│ ├─ Layer 2: Lifecycle Knowledge Layer (Generic edition chains, validity)   │
│ ├─ Layer 3: Regulatory & Conformity Layer (Governed QCO/CRS JSONL datasets) │
│ └─ Layer 4: Relational Knowledge Graph (6,081 nodes, 5,428 direct edges)     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│ LAYER 5: RECOMMENDATION & EVALUATION PIPELINE                               │
│ ├─ Hybrid Retrieval (Okapi BM25 + Dense Semantic Projection via RRF)        │
│ ├─ Primary Candidate Corpus Segregation (Product specs vs supporting only)  │
│ ├─ Cycle-Safe Graph Expansion Pack (Normative references, test methods)     │
│ ├─ Multi-Signal Cross-Encoder Reranker                                      │
│ ├─ Evidence-Based Applicability Engine (MATCH/MISMATCH/UNKNOWN)             │
│ └─ Two-Tier Decision Engine with Calibrated Selective Abstention            │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│ LAYER 6: LLM-POWERED AGENTIC RAG DECISION ENGINE (STANDSPEC AGENT v3.0.0)    │
│ ├─ Natural Language Understanding & Complex Query Decomposition             │
│ ├─ 7 Deterministic BIS Tools (search, evidence, applicability, lifecycle...) │
│ ├─ Multi-Step Candidate Comparison & Clarification Question Formulation    │
│ ├─ Deterministic Safety Validator (Anti-hallucination veto authority)       │
│ └─ Dual Output Format: Machine JSON (agent_final_answer) + Officer Summary  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Authoritative Documentation

| Document | Primary Focus |
|:---|:---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Complete multi-tier architecture and pipeline workflow |
| [`docs/DATA_CONTRACTS.md`](docs/DATA_CONTRACTS.md) | JSON schemas, standards node structures, and evidence bundle contracts |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Benchmark suites, evaluation metrics, and machine-readable artifacts |
| [`docs/OPERATIONS.md`](docs/OPERATIONS.md) | Developer CLI manual, verification commands, and test workflows |
| [`docs/LLM_INTEGRATION.md`](docs/LLM_INTEGRATION.md) | Bounded LLM provider architecture and evidence grounding |
| [`docs/RELEASES.md`](docs/RELEASES.md) | Version identity, release manifest, and component version contracts |

---

## 4. Quickstart & Verification Commands

### 4.1 Run StandSpec Agent CLI Demo
Execute single queries or launch an interactive procurement officer session:
```bash
# Standard procurement query
python scripts/run_agent.py --query "Supply of 1.1 kV XLPE insulated three-core power cables"

# Adversarial conflict check (IS 1180 vs uPVC pipes) with full tool execution trace
python scripts/run_agent.py --query "Supply of uPVC pipes as per IS 1180 Part 1" --trace

# Interactive procurement assistant session
python scripts/run_agent.py --interactive

# Machine JSON output format
python scripts/run_agent.py --query "Supply of 1.1 kV XLPE insulated three-core power cables" --json
```

### 4.2 Run Hermetic Test Suite
The entire test suite executes hermetically with an autouse socket blockade guaranteeing zero external network requests:
```bash
python -m pytest -q
```

### 4.3 Verify Release Manifest Integrity
Validate that all files, benchmark counts, and evaluation artifacts match committed cryptographic hashes:
```bash
python scripts/generate_release_manifest.py --check
```

### 4.4 Validate Knowledge Graph Invariants
Verify graph connectivity, node properties, and department isolation:
```bash
python scripts/validate_graph_invariants.py --graph data/processed/standards_graph.json
```

### 4.5 Validate Regulatory Source Registry
Verify QCO and CRS records against the authoritative source manifest with fail-closed consistency:
```bash
python scripts/validate_regulatory_sources.py
```

### 4.6 Run End-to-End Evaluation & Safety Benchmarks
Evaluate recommendation accuracy, safe decision contracts, and adversarial robustness across all benchmark suites:
```bash
# Agent Open-World Comparative Evaluation (Deterministic vs LLM-Assisted)
python scripts/evaluate_agent.py

# Authoritative Test Suite
python scripts/evaluate_recommendation.py --benchmark data/benchmarks/test.jsonl --output-json data/evaluations/test_evaluation.json

# Adversarial Safety Benchmark (32 queries covering HN1-HN8)
python scripts/evaluate_recommendation.py --benchmark data/benchmarks/adversarial.jsonl --output-json data/evaluations/adversarial_evaluation.json

# Coverage Boundary Benchmark (Non-CED/ETD out-of-domain queries)
python scripts/evaluate_recommendation.py --benchmark data/benchmarks/coverage_boundary.jsonl --output-json data/evaluations/coverage_boundary_evaluation.json
```

---

## 5. Technology Stack & Prerequisites

- **Python Version:** 3.10+ (Tested on Python 3.14)
- **Core Dependencies:** Listed in `requirements.txt` (offline, deterministic)
- **Optional LLM Dependencies:** Listed in `requirements-llm.txt`
- **Testing Framework:** `pytest` with autouse socket blockade in `tests/conftest.py`

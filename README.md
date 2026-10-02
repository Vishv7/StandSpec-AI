# StandSpec AI — Evidence-Grounded Indian Standards Recommendation Engine
## Smart India Hackathon — Problem Statement SIH26108

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=for-the-badge&logo=vercel)](https://stand-spec-ai.vercel.app)
[![API Gateway](https://img.shields.io/badge/API%20Gateway-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://standspec-ai.onrender.com)
[![Swagger Docs](https://img.shields.io/badge/Interactive%20Docs-Swagger-85EA2D?style=for-the-badge&logo=swagger&logoColor=black)](https://standspec-ai.onrender.com/docs)
[![Tests](https://img.shields.io/badge/Tests-721%20Passed-brightgreen.svg?style=for-the-badge)]()
[![Knowledge Graph](https://img.shields.io/badge/Graph-6082%20Nodes%20%7C%205428%20Edges-purple.svg?style=for-the-badge)]()

---

### 🌐 Live Production Deployments

| Component | Platform | Live URL | Description |
| :--- | :--- | :--- | :--- |
| **Frontend Web Studio** | **Vercel** | **[https://stand-spec-ai.vercel.app](https://stand-spec-ai.vercel.app)** | Live Query Studio, Tender PDF Studio, Standards Explorer |
| **Backend API Gateway** | **Render** | **[https://standspec-ai.onrender.com](https://standspec-ai.onrender.com)** | High-throughput FastAPI decision & recommendation engine |
| **Interactive API Docs** | **Swagger UI** | **[https://standspec-ai.onrender.com/docs](https://standspec-ai.onrender.com/docs)** | Interactive Swagger / OpenAPI testing portal |
| **System Health API** | **REST** | **[https://standspec-ai.onrender.com/api/v1/health](https://standspec-ai.onrender.com/api/v1/health)** | Live system readiness and indexed standards telemetry |

---

## 1. Executive Overview

**StandSpec AI** is an evidence-grounded recommendation system engineered for Indian Public Procurement (GeM, IREPS, Defence CPP). It accepts natural-language procurement requirements, technical specifications, and tender schedules, and accurately identifies:

1. **Applicable Primary Indian Standards (IS)** covering the product or service within the current CED + ETD prototype scope.
2. **Allied Standards** including normative references, mandatory test methods, raw material specifications, and installation guidelines.
3. **Current Lifecycle Status**, ensuring superseded revisions are flagged and active editions are recommended with amendment data.
4. **Regulatory Evidence**, verifying indexed Quality Control Orders (QCOs) and Compulsory Registration Scheme (CRS) requirements without fabricating legal authority.
5. **Traceable Verbatim Evidence** with calibrated selective abstention when tender specifications lack discriminating technical parameters or contain contradictory requirements.

> [!NOTE]
> ### Prototype Scope & Corpus Boundaries
> - **Department Scope:** The current production prototype covers **Civil Engineering (CED)** and **Electrotechnical (ETD)** departments only. Architecture is extensible to other BIS departments, but standards outside CED/ETD appear as supporting/context evidence and cannot become primary recommendations.
> - **Knowledge Graph Scale:** **6,082 indexed knowledge-graph nodes** (comprising **5,604 Indian-standard nodes** plus supporting and context nodes) with 5,428 direct edges.
> - **Regulatory Data Scope:** Covers indexed BIS Product Certification and CRS records for CED/ETD. Hallmarking regulatory data is not represented in the current prototype corpus.
> - **Decision-Support Notice:** StandSpec AI is a procurement decision-support system. It is not an official BIS database, legal authority, statutory compliance certificate generator, or a substitute for expert procurement officer review.

> [!IMPORTANT]
> ### Core Engineering Law
> **The Large Language Model (LLM) is NEVER the unconstrained ranking authority.**  
> Candidate recall, ranking, graph traversal, and regulatory verification are executed by deterministic graph algorithms, calibrated rerankers, and deterministic gates. The LLM is restricted to requirement extraction, multilingual normalization, and evidence-grounded explanation under strict verification gates.

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
│ └─ Layer 4: Relational Knowledge Graph (6,082 nodes, 5,428 direct edges)     │
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

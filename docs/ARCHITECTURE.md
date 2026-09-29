# StandSpec AI — System Architecture Specification
## Phase P1-D: Trust Gate Integrity & Evidence-Grounded Decision Architecture

---

## 1. Core Operating Philosophy

```
FIND → VERIFY → QUALIFY EVIDENCE → DECIDE OR ABSTAIN
(Never: RETRIEVE → GUESS → RECOMMEND)
```

StandSpec AI operates strictly as a defensive, evidence-grounded recommendation system for Indian Standards in Civil Engineering (CED) and Electrotechnical (ETD) domains. The system prioritizes legal and engineering safety above coverage: an unverified standard must NEVER be recommended.

---

## 2. End-to-End Pipeline Workflow

```text
                    ┌──────────────────────────────────────────────┐
                    │     Procurement Requirement Text (Tender)    │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │       Bounded Requirement Extractor          │
                    │   (Deterministic regex + LLM-assist fallback)│
                    │    Strict verbatim substring span verification│
                    └──────────────────────┬───────────────────────┘
                                           │ Normalized Requirements
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │            Hybrid Multi-Channel Retrieval    │
                    │   Okapi BM25 + Dense Semantic Representation │
                    │      Reciprocal Rank Fusion (RRF k=60)       │
                    │   Transparent fallback: HASHED_FALLBACK      │
                    └──────────────────────┬───────────────────────┘
                                           │ Initial Top Candidates
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │        Knowledge Graph Expansion Pack        │
                    │  Cycle-safe BFS traversal (2 hops max)       │
                    │  Captures amendments, supersessions, parts   │
                    └──────────────────────┬───────────────────────┘
                                           │ Expanded Candidates
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │      Decoupled Multi-Signal Reranker         │
                    │   12 Generic Features + CED/ETD Domain Rules │
                    │   Cross-Encoder or Rule-Based Fallback       │
                    │   Transparent mode: RULE_BASED_FALLBACK      │
                    └──────────────────────┬───────────────────────┘
                                           │ Re-Ranked Candidates
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │     Authoritative EvidenceBundle Gate        │
                    │  Sole authority for recommendation readiness │
                    │  PRODUCT=UNKNOWN can NEVER reach verified    │
                    │  Evaluates identity, scope, domain, role     │
                    └──────────────────────┬───────────────────────┘
                                           │ Evidence Qualified
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │    Lifecycle & Regulatory Provenance Gate    │
                    │  Data-driven edition chain resolution        │
                    │  Governed QCO/CRS source manifest integrity  │
                    │  Fail-closed on temporal or source conflicts │
                    └──────────────────────┬───────────────────────┘
                                           │ Legally Validated
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │         Two-Tier Decision Engine             │
                    │  Primary Recommendation vs Review Candidate  │
                    │  Platt-calibrated selective abstention       │
                    │  Monotonic 14-stage DecisionTrace execution  │
                    └──────────────────────┬───────────────────────┘
                                           │ RecommendationResult
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │     Evidence-Grounded Explainer              │
                    │  Grounded strictly in ExplanationFacts       │
                    │  Null-primary safety: NEVER invents standard │
                    │  Deterministic template fallback on error    │
                    └──────────────────────────────────────────────┘
```

---

## 3. Core Architectural Subsystems

### 3.1 Bounded Requirement Extractor (`src/llm/structured_extractor.py`)
- Extracts technical procurement specifications: product, material, grade, dimensions, voltage, capacity, application, installation.
- Enforces strict JSON schema validation (`schemas/llm_extraction.schema.json`, `additionalProperties = false`).
- Verifies character spans (`start_char`, `end_char`) against the raw tender text with verbatim substring matching. Weak token overlap fallback is strictly prohibited.
- Automatically falls back to deterministic extraction (`RequirementExtractor`) if LLM is unavailable, times out, or fails verification.

### 3.2 Transparent Hybrid Retrieval (`src/retrieval/`)
- Combines Okapi BM25 and multilingual dense embeddings via Reciprocal Rank Fusion (RRF).
- Transparent Mode Factory: when neural embeddings cannot be loaded in an offline environment, the retriever explicitly reports `effective_mode = HASHED_FALLBACK` with `model_loaded = False`, `fallback_used = True`, and the exact `fallback_reason`.

### 3.3 Decoupled Reranker Features & Scoring Policy (`src/retrieval/reranker_features.py`)
Features are decoupled from scoring rules into 12 generic extractors:
1. `DesignationAlignment`: Exact or base standard designation match.
2. `PartSectionAlignment`: Multi-part standard number and section fidelity.
3. `RoleAlignment`: Discriminated product vs test method vs design code.
4. `ProductCategoryAlignment`: Target commodity taxonomy match.
5. `MaterialAlignment`: Substrate compatibility (e.g. uPVC vs HDPE, mild steel vs stainless steel).
6. `ApplicationAlignment`: Procurement intent alignment (water supply, drainage, structural).
7. `TechnologyModifierAlignment`: Special technology variants (e.g. static vs smart prepayment meters).
8. `ScopeBoundary`: Domain constraints (preventing pipe vs fitting, civil vs electrotechnical confusion).
9. `Specificity`: Penalty for generic fallback standards when specific ones exist.
10. `CandidateEvidenceAvailability`: Verification readiness of standard data.
11. `ProcurementIntentAlignment`: Fit with procurement contract type.
12. `ContradictionPenalty`: Severe penalty for mutually exclusive specifications.

Scoring policies produce structured explanations (`why_ranked_above`, `explain_ranking`). When neural cross-encoder weights are unavailable, the reranker reports `effective_mode = RULE_BASED_FALLBACK`.

### 3.4 Authoritative EvidenceBundle (`src/recommendation/evidence_bundle.py`)
- `EvidenceBundle` is the **sole authority** for recommendation claim readiness.
- Evaluates 5 readiness dimensions: `identity_ready`, `scope_ready`, `applicability_ready`, `lifecycle_ready`, `provenance_ready`.
- Criteria for `PRIMARY_RECOMMENDATION_CLAIM`:
  - `PRODUCT != UNKNOWN` (mandatory positive product grounding).
  - No hard technical mismatches.
  - Standard role compatible with procurement type (test methods, codes cannot become primary product recommendations unless explicitly requested).
  - Full provenance tracking with explicit `EvidenceGapCode` reporting.

### 3.5 Lifecycle & Regulatory Gate (`src/recommendation/`)
- Data-driven lifecycle state model (`data/regulatory/lifecycle_curated.json`): resolves canonical states (`VERIFIED_ACTIVE`, `VERIFIED_SUPERSEDED`, `VERIFIED_WITHDRAWN`, `HISTORICAL_VALID`, `FUTURE_NOT_VALID`, `LIFECYCLE_UNVERIFIED`).
- Regulatory Gating: cross-validates records in `qco_orders.jsonl` and `crs_rules.jsonl` against authoritative `source_manifest.json` by `source_id`, gazette ID, title, URL, and standard coverage.
- Fail-closed on conflicting source identities: marks standards as `CONFLICTING_EVIDENCE` and prevents mandatory endorsement.

### 3.6 Two-Tier Decision Engine (`src/recommendation/engine.py`)
- Tier 1: **Primary Recommendation** emitted only when all trust gates pass and calibrated confidence exceeds $\tau_{\text{recommend}}$.
- Tier 2: **Review Candidate** emitted when a strong candidate exists but has evidentiary gaps or unhydrated scope, clearly stating missing gaps and diagnostics.
- Tier 3: **Selective Abstention** (`NO_CONFIDENT_MATCH`, `INSUFFICIENT_INFORMATION`, `OUTSIDE_PROTOTYPE_COVERAGE`) with explicit root-cause explanation.
- Produces an authoritative 14-stage `DecisionTrace` with strictly monotonic claim levels (`VERIFIED_FOR_RECOMMENDATION` > `CONDITIONALLY_SUPPORTED` > `REVIEW_REQUIRED` > `ABSTAINED`).

### 3.7 Evidence-Grounded Explainer (`src/llm/explanation.py`)
- Synthesizes user-facing explanations grounded strictly in `ExplanationFacts`.
- Null-primary safety guarantee: when `primary_recommendation = null`, LLM output claiming a recommended standard is strictly rejected, falling back to deterministic explanation.
- Guarantees designation and regulatory fidelity without hallucination.

### 3.8 LLM-Powered Agentic RAG Decision Engine (`src/agent/agent.py`)
- **Interactive Multi-Step Orchestration**:
  - Procurement officers submit natural language queries.
  - LLM understands intent, decomposing complex specifications.
  - LLM actively dispatches 7 deterministic BIS tools (`search_standards`, `get_standard_evidence`, `check_applicability`, `check_lifecycle`, `check_regulatory`, `check_prototype_coverage`, `get_standard_relationships`).
  - LLM synthesizes evidence, generates targeted clarifications, or compares technical trade-offs.
- **Deterministic Validator with Veto Authority (`src/agent/validator.py`)**:
  - Intercepts every LLM proposal prior to response delivery.
  - Enforces 7 safety gates: anti-hallucination, role correctness, applicability parameter fidelity, requested standard conflict veto, lifecycle validity, statutory QCO truthfulness, and abstention purity.
  - Prompts LLM for bounded revision on rejection, or falls back to the deterministic baseline.
- **Dual Output Formats**:
  - Machine JSON conforming to `schemas/agent_final_answer.schema.json`.
  - Rich human-readable explanations formatted for procurement officers.


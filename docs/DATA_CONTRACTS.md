# StandSpec AI — Data Contracts and Schemas
## Phase P1-D: Schema Governance & Authoritative Contracts

---

## 1. Schema Registry

All schemas are maintained in the `/schemas` directory and validated using Draft 2020-12 / Draft 7 standards:

| Contract Name | Schema File | Version | Scope |
|:---|:---|:---|:---|
| **Standards Graph** | `schemas/standards_graph.schema.json` | 2.1 | Graph representation of BIS standards, editions, supersessions, cross-references, roles |
| **Recommendation Result** | `schemas/recommendation_result.schema.json` | 3.0 | Output structure including primary recommendation, review candidate, evidence bundle, trace, agent metadata, tool calls |
| **Normalized Requirement** | `schemas/normalized_requirement.schema.json` | 2.1 | Structured attributes extracted from raw procurement queries with offsets and sufficiency |
| **Benchmark Ground Truth** | `schemas/procurement_ground_truth.schema.json` | 2.1 | Evaluation benchmark schema supporting positive, adversarial, boundary, and challenge queries |
| **Regulatory Source** | `schemas/regulatory_source.schema.json` | 1.1 | QCO orders, CRS rules, gazette references, and mandatory `source_id` matching manifest |
| **LLM Extraction** | `schemas/llm_extraction.schema.json` | 1.0 | Bounded technical requirement extraction with strict `additionalProperties: false` |
| **Agent Action** | `schemas/agent_action.schema.json` | 3.0 | Structured actions (TOOL_CALL, ASK_CLARIFICATION, FINAL_PROPOSAL) emitted by StandSpecAgent |
| **Agent Final Answer** | `schemas/agent_final_answer.schema.json` | 3.0 | Strict dual-format agent final proposal and machine response prior to and post validator gate |
| **Collector Manifest** | `schemas/manifest.schema.json` | 1.2 | Raw scraped data and department ingest audit manifest |

---

## 2. Key Contract Enforcements

### 2.1 Regulatory Source Record (`schemas/regulatory_source.schema.json`)
- `source_id`: Mandatory unique string (`^REG_[A-Z0-9_]+$`) referencing an authoritative entry in `data/regulatory/source_manifest.json`.
- `order_title`: Official Quality Control Order title.
- `gazette_reference`: Official Gazette S.O. number (e.g. `S.O. 4531(E)`).
- `publication_date` & `effective_date`: Valid `YYYY-MM-DD` strings enforcing `publication_date <= effective_date`.
- `standard_designations`: Non-empty list of covered Indian Standards.
- `scheme`: Conformity assessment scheme (`Scheme-I (ISI Mark)` or `Scheme-II (CRS)`).

### 2.2 LLM Extraction Contract (`schemas/llm_extraction.schema.json`)
- Strict `additionalProperties: false` at root and field definitions.
- Supported attributes: `product`, `material`, `grade`, `dimensions`, `voltage`, `capacity`, `application`, `installation`, `domain`.
- Grounded field structure:
  - `value`: Extracted technical term.
  - `evidence_text`: Verbatim substring from the tender query.
  - `start_char` & `end_char`: Exact 0-indexed character offsets in the query string.
  - `confidence`: Numeric score between 0.0 and 1.0.

### 2.3 Benchmark Ground Truth Contract (`schemas/procurement_ground_truth.schema.json`)
- Supports four benchmark tiers:
  - Tier 1: Schema-valid structure.
  - Tier 2: Prototype template valid.
  - Tier 3: Evaluation-ready with validated ground truth.
- Supports negative and abstention queries:
  - `minItems: 0` for `gold_standards` and `hard_negatives` (for outside-domain or contradictory queries).
  - Explicit `expected_safe_decision` contract: allows `PRIMARY_RECOMMENDATION_AVAILABLE`, `EXPERT_REVIEW_REQUIRED`, `INSUFFICIENT_INFORMATION`, `NO_CONFIDENT_MATCH`, and `OUTSIDE_PROTOTYPE_COVERAGE`.

### 2.4 Recommendation Result Contract (`schemas/recommendation_result.schema.json`)
- Top-level properties:
  - `query`: Raw query text, query ID, language, domain.
  - `normalized_requirements`: Structured attributes with character offsets and confidence.
  - `decision_state`: Authoritative decision state enum.
  - `claim_level`: Monotonic claim level (`VERIFIED_FOR_RECOMMENDATION`, `CONDITIONALLY_SUPPORTED`, `REVIEW_REQUIRED`, `ABSTAINED`).
  - `primary_recommendation`: Fully qualified standard candidate or `null`.
  - `review_candidate`: Candidate requiring human review with full evidentiary diagnostics or `null`.
  - `decision_trace`: 14-stage execution trace with explicit stage states (`PASS`, `FAIL`, `BLOCKED`, `CONFLICT`, `SKIPPED`).
  - `natural_language_explanation`: Anti-hallucination grounded summary synthesized by `EvidenceGroundedExplainer`.
  - `provenance`: Engine version, release ID, retriever mode, reranker mode, and timestamps.
  - `agent_metadata`: Step count, latency, search/revision rounds, execution mode, and deterministic validator status.
  - `tool_calls`: Audit trace of tool invocations dispatched during agent orchestration.

### 2.5 Agent Action Contract (`schemas/agent_action.schema.json`)
- Dictates discrete planner actions emitted during LLM-powered orchestration:
  - `action`: Enum (`TOOL_CALL`, `ASK_CLARIFICATION`, `FINAL_PROPOSAL`).
  - `tool`: Target tool name when action is `TOOL_CALL` (one of the 7 BIS tools).
  - `arguments`: Structured arguments payload for the invoked tool.
  - `thought`: Technical reasoning string for the selected step.
  - `question`: Clarification question posed to officer when action is `ASK_CLARIFICATION`.
  - `clarification_reason`: Structured category for missing specification.
  - `answer`: Proposed final response object when action is `FINAL_PROPOSAL`.

### 2.6 Agent Final Answer Contract (`schemas/agent_final_answer.schema.json`)
- Strict `additionalProperties: false` machine-readable output contract:
  - `decision_state`: 9-state decision enum.
  - `primary_recommendation`: Grounded candidate with designation, title, applicability, claim level, and evidence IDs (or `null`).
  - `alternative_standards`: Grounded list of plausible alternate standards with evidence IDs.
  - `review_candidate`: Candidate requiring manual engineering review or `null`.
  - `clarifications_needed`: List of targeted clarification questions.
  - `lifecycle`: Active lifecycle status, recommended edition, superseding standard, and evidence list.
  - `regulatory`: Mandate status, governing QCO order number, gazette SO number, and statutory statement.
  - `confidence`: Confidence enum (`HIGH`, `MEDIUM`, `LOW`, `UNVERIFIED`).
  - `natural_language_explanation`: Evidence-grounded natural language officer summary.
  - `agent_metadata` & `tool_calls`: Orchestration audit trace and validator acceptance status.


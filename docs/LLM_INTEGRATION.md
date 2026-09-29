# StandSpec AI — Bounded LLM Integration Architecture
## Phase P1-D: Bounded Extraction & Anti-Hallucination Guardrails

---

## 1. Operating Law

Large Language Models (LLMs) provide natural language parsing assistance and synthesized explanations in StandSpec AI. However, **all algorithmic decisions, candidate scoring, and safety gating are non-LLM, deterministic processes**.

The LLM is strictly an assistant:
1. **Cannot override deterministic applicability gates.**
2. **Cannot invent standard numbers, editions, or regulatory orders.**
3. **Cannot promote an unverified candidate to primary recommendation.**
4. **Operates under strict timeout, schema validation, and fallback mechanisms.**

---

## 2. LLM Components

### 2.1 Bounded Structured Extractor (`src/llm/structured_extractor.py`)
- Extracts structured requirements from unstructured tender clauses.
- Enforces strict JSON Schema validation (`schemas/llm_extraction.schema.json`, `additionalProperties = false`).
- **Strict Verbatim Span Verification**:
  - Every extracted attribute object provides `value`, `evidence_text`, `start_char`, and `end_char`.
  - The extractor checks that `query_text[start_char:end_char] == evidence_text` and that `evidence_text` exists verbatim in the query text.
  - Substring fallback re-aligns offsets if the exact verbatim substring is found elsewhere in the query.
  - **Zero weak token overlap**: partial or non-verbatim token matching is rejected immediately.
- Fallback: Any schema error, hallucinated span, or timeout triggers immediate fallback to `RequirementExtractor` (`extractor_mode="DETERMINISTIC_FALLBACK"`).

### 2.2 Evidence-Grounded Explainer (`src/llm/explanation.py`)
- Synthesizes 2-sentence user-facing procurement summaries grounded strictly in `ExplanationFacts`.
- **Null-Primary Safety Guarantee**:
  - When `primary_recommendation` is null (`is_recommended = False`), LLM output containing phrases like `"recommended standard"`, `"we recommend"`, or `"is recommended"` is strictly rejected.
  - On rejection, safely falls back to the deterministic template: `"Decision State: {decision_state}. Abstention Reason: {reason}. Missing Evidence Gaps: {gaps}."`
- **Designation & Regulatory Fidelity**:
  - Checks that standard numbers match the verified recommendation.
  - Checks that regulatory mandates are accurately conveyed without legal invention.

---

## 3. Phase P1-F: LLM-Powered Agentic RAG Decision Engine (`StandSpecAgent`)

### 3.1 Architecture Overview
In v3.0.0, StandSpec AI transitions to an **LLM-Powered Agentic RAG Architecture** (`StandSpecAgent` in `src/agent/agent.py`):
```text
                PROCUREMENT OFFICER
                        │
                        ▼
                 ┌──────────────┐
                 │     LLM      │
                 │ understands  │
                 │ the request  │
                 └──────┬───────┘
                        │
               structured requirements
                        │
                        ▼
             ┌─────────────────────┐
             │ BIS Search / RAG    │
             │ tools               │
             └─────────┬───────────┘
                       │
              verified evidence &
              candidate standards
                       │
                       ▼
                 ┌──────────────┐
                 │     LLM      │
                 │ reasons over │
                 │ evidence &   │
                 │ formulates   │
                 │ final answer │
                 └──────┬───────┘
                        │
               proposed recommendation
                        │
                        ▼
             ┌─────────────────────┐
             │ Deterministic       │
             │ Safety Validator    │
             │ (veto power)        │
             └─────────┬───────────┘
                       │
               validated decision
                       │
                       ▼
              FINAL ANSWER TO USER
```

### 3.2 Seven Authoritative BIS Tools (`src/agent/tool_router.py`)
All facts and claims available to the LLM come exclusively from 7 verified tools backed by the deterministic engine:
1. `search_standards`: Hybrid BM25 + dense semantic retrieval over indexed BIS catalog.
2. `get_standard_evidence`: Comprehensive `EvidenceBundle` containing verbatim scope, clauses, and readiness flags.
3. `check_applicability`: Attribute-level grounding evaluator checking matches, mismatches, and exclusions.
4. `check_lifecycle`: Validates active, superseded, or withdrawn status with effective date temporal reasoning.
5. `check_regulatory`: Queries official Quality Control Orders (QCO) and Compulsory Registration Scheme (CRS).
6. `check_prototype_coverage`: Verifies whether query belongs to indexed Civil Engineering (CED) or Electrotechnical (ETD) scopes.
7. `get_standard_relationships`: Traverses knowledge graph edges for normative references, test methods, and parent/child series.

### 3.3 Deterministic Safety Validator (`src/agent/validator.py`)
The LLM does **NOT** have final authority. A deterministic validator executes 7 unbypassable safety gates:
- **Gate 1 (Anti-Hallucination)**: Designations not returned by `search_standards` or explicitly requested are vetoed (`HALLUCINATED_DESIGNATION`).
- **Gate 2 (Role Validity)**: Supporting standards (e.g., test methods like IS 10810) cannot be primary product recommendations (`WRONG_ROLE_PRIMARY`).
- **Gate 3 (Technical Applicability)**: Technical parameter mismatches strictly veto the primary recommendation (`APPLICABILITY_MISMATCH`, `ATTRIBUTE_MISMATCH`).
- **Gate 4 (Explicit Requested Standard Conflict)**: Mismatched cited standards (e.g. uPVC pipes + IS 1180) force primary recommendation to null (`REQUESTED_STANDARD_MISMATCH`).
- **Gate 5 (Lifecycle Protection)**: Withdrawn or obsolete predecessor standards cannot be recommended (`LIFECYCLE_VETO`).
- **Gate 6 (Regulatory Truthfulness)**: Unverified status cannot claim voluntary compliance or invent fake QCO order numbers (`REGULATORY_FALSE_ASSERTION`, `HALLUCINATED_QCO`).
- **Gate 7 (Abstention Purity)**: When decision state is abstention or clarification, primary recommendation must be strictly null (`NULL_PRIMARY_VIOLATION`).

### 3.4 Bounded Execution & Graceful Fallback
- Orchestration loop strictly bounded to `MAX_AGENT_STEPS = 6`.
- Retrieval bounded to `MAX_SEARCH_ROUNDS = 2`.
- Validator revision bounded to `MAX_REVISION_ROUNDS = 1`.
- **Fault-Tolerant Resilience**: If the LLM generates malformed JSON, exceeds rate limits (HTTP 429), or times out, the agent seamlessly falls back to the deterministic decision baseline (`execution_mode = "LLM_FALLBACK"`), ensuring zero production crashes.

---

## 4. Configuration & Runtime Modes

| Environment Variable | Default | Purpose |
|:---|:---|:---|
| `STANDSPEC_LLM_ENABLED` | `false` | Enable or disable LLM assist (default offline) |
| `STANDSPEC_LLM_PROVIDER` | `mock` | Provider type (`mock`, `gemini`) |
| `STANDSPEC_LLM_API_KEY` | `""` | API key for external provider |
| `STANDSPEC_LLM_MODEL` | `gemini-1.5-flash` | Model identifier |
| `STANDSPEC_LLM_TIMEOUT_SECONDS` | `15` | Call timeout before falling back |

### Hermetic Offline Execution
By default, `STANDSPEC_LLM_ENABLED=false` or unset. The entire system executes 100% offline and hermetically with deterministic mock providers and rule-based extractors, guaranteeing reproducibility and socket-blockade test passing.


================================================================================
       STANDSPEC AI — ARCHITECTURE REVIEW REPORT
       Comprehensive Audit of the LLM-Powered Procurement Agent System
       Release: STANDSPEC_PROTOTYPE_CED_ETD_V3_0_0 (Build 2026-09-28)
================================================================================

Author:  Claude Sonnet 4.6
Date:    September 29, 2026
Scope:   Full-stack architectural review covering retrieval, applicability,
         lifecycle, regulatory gating, LLM integration, safety validation,
         calibration, evidence bundles, testing quality, data coverage,
         and scalability.

================================================================================
TABLE OF CONTENTS
================================================================================

A.   Executive Summary
B.   System Overview and Architecture
C.   Data Layer and Knowledge Graph
D.   Requirement Extraction and Normalization (req_obj Contract)
E.   Retrieval Architecture (BM25 + Dense RRF + Graph Expansion)
F.   Candidate Reranking (Rule-Based + Neural Cross-Encoder)
G.   Technical Applicability Engine
H.   Lifecycle and Edition Resolution
I.   Regulatory Gate and QCO/CRS Mandate Verification
J.   Evidence Bundle and Readiness Model
K.   Calibration and Selective Abstention Policy
L.   LLM Integration, Bounded Extraction, and Anti-Hallucination
M.   Agent Orchestration and Safety Validation
N.   Final Answer Schema and Decision Contract
O.   Testing Quality and Test Coverage Analysis
P.   Evaluation Metrics and Benchmark Analysis
Q.   Data Coverage Audit
R.   Scalability and Performance Assessment
S.   Recommendations and Roadmap

================================================================================
SECTION A — EXECUTIVE SUMMARY
================================================================================

StandSpec AI is a production-grade, LLM-assisted procurement recommendation
system that maps Indian government tender clauses to the correct Bureau of
Indian Standards (BIS) specifications. It operates within a strictly bounded
domain (Civil Engineering Department CED + Electrotechnical Department ETD
standards) and enforces a deterministic safety validator as the final veto
gate, ensuring that no hallucinated, inapplicable, or out-of-scope standard
can be recommended to users.

KEY STRENGTHS

1. Defense-in-Depth Safety Architecture
   The system implements a four-layer safety stack:
   (a) Bounded Structured Extractor with verbatim character-span verification
       — hallucinated substrings are rejected at extraction time.
   (b) Technical Applicability Engine performing per-attribute MATCH/MISMATCH
       evaluation against normalized requirements.
   (c) Deterministic Safety Validator (DeterministicValidator) enforcing
       seven hard gates: candidate presence, role validity, applicability
       grounding, explicit designation conflict, lifecycle status, regulatory
       fidelity, and null-primary safety on abstention states.
   (d) EvidencePolicy with multidimensional readiness — a candidate cannot
       be promoted to primary recommendation without verified identity,
       scope, applicability, lifecycle, provenance, and product grounding.

2. Fail-Closed LLM Integration
   The LLM (Gemini via google-generativeai) operates in a strictly bounded
   assist mode. All LLM-generated JSON is validated against JSON Schema with
   additionalProperties: false. Character spans are verified verbatim against
   the raw query text with zero weak-token-overlap tolerance. On any failure
   (malformed JSON, timeout, hallucination, schema violation), the system
   transparently falls back to the 100% deterministic pipeline. The MockLLMProvider
   and DisabledLLMProvider ensure hermetic offline testing.

3. Architectural Cleanliness
   The system exhibits excellent separation of concerns across layers:
   extraction (Phase 6), retrieval (Phases 8-12), applicability (Phase 13),
   lifecycle (Phase 14), regulatory (Phase 15), calibration (Phase 16),
   evidence/policy (Phase P1-C), LLM bounding (Phase P1-D), agent
   orchestration (Phase P1-F). Each layer has a single responsibility and
   communicates through well-defined schema contracts.

4. Bounded Agent Orchestration
   The agent is strictly bounded: max 6 orchestration steps, max 2 retrieval
   rounds, max 1 revision round. The deterministic validator has absolute
   veto authority — if it rejects an LLM proposal twice (initial + revision),
   the system falls back to the deterministic safe baseline.

5. Comprehensive Testing
   44 test modules covering unit, integration, adversarial, schema
   validation, LLM failure handling, and offline execution. Critical
   adversarial tests verify the uPVC + IS 1180 mismatch scenario.

CRITICAL FINDINGS

The current evaluation metrics reveal significant performance gaps that
must be addressed before production deployment:

- safe_abstention_rate is 1.0 (100% of queries result in abstention) on
  the open-world benchmark — the system is overly conservative.
- unsafe_primary_promotion_rate is 0.615 on the test set — 61.5% of queries
  where a primary should not be promoted still promote one.
- primary_recommendation_accuracy is 0.1538 (15.38%) on the test set.
- The PlattScaler calibrator has only N=24 samples, flagged
  CALIBRATION_INSUFFICIENT_DATA — cannot make statistical calibration claims.
- The neural cross-encoder reranker transparently falls back to rule-based
  when the sentence_transformers model is unavailable, but the default
  production mode is rule_based (deterministic).

ARCHITECTURAL ASSESSMENT: MODERATELY STRONG FOUNDATION WITH CRITICAL
PERFORMANCE GAPS. The safety architecture is excellent. The accuracy
pipeline needs retrieval and ranking improvements. The calibration layer
is not yet production-ready (insufficient samples).

================================================================================
SECTION B — SYSTEM OVERVIEW AND ARCHITECTURE
================================================================================

ARCHITECTURAL STYLE

StandSpec AI follows a layered pipeline architecture with strict
separation between the deterministic knowledge/evidence layer (ground
truth) and the LLM reasoning layer (assist only). The LLM never has
veto authority; a deterministic validator always has final say.

COMPONENT LAYERING (15-Stage Decision Pipeline)

Stage  | Name                    | Component / File
-------|-------------------------|------------------------------------------
P1-A   | Requirement Extraction  | src/extraction/requirement_extractor.py
       |                         | src/llm/structured_extractor.py
-------|------------------------------------------------
P1-B   | Exact Designation       | src/retrieval/designation_resolver.py
       | Detection               |
-------|------------------------------------------------
Phase 6| Query Sufficiency       | (within requirement_extractor.py)
-------|------------------------------------------------
Phase 8-10 | BM25 + Dense RRF  | src/retrieval/bm25_retriever.py
       |                         | src/retrieval/dense_retriever.py
       |                         | src/retrieval/fusion.py
-------|------------------------------------------------
Phase 11 | Graph Expansion       | src/retrieval/graph_expansion.py
-------|------------------------------------------------
Phase 12 | Reranking             | src/retrieval/cross_encoder.py
-------|------------------------------------------------
Phase 13 | Applicability         | src/recommendation/applicability_engine.py
-------|------------------------------------------------
Phase 14 | Lifecycle             | src/recommendation/lifecycle_gate.py
-------|------------------------------------------------
Phase 15 | Regulatory            | src/recommendation/regulatory_gate.py
-------|------------------------------------------------
Phase 16 | Calibration           | src/calibration/policy.py +
       |                         |   src/calibration/calibrator.py
-------|------------------------------------------------
P1-C   | Evidence Bundle         | src/recommendation/evidence_bundle.py
       | (Policy/Readiness)      |
-------|------------------------------------------------
P1-D   | Bounded LLM Extraction  | src/llm/structured_extractor.py
       | & Explanation           | src/llm/explanation.py
-------|------------------------------------------------
P1-F   | Agent Orchestration     | src/agent/agent.py
       | Safety Validator        | src/agent/validator.py
-------|------------------------------------------------
P1-F   | Context Builder         | src/agent/context_builder.py
-------|------------------------------------------------
P1-F   | Answer Builder          | src/agent/answer_builder.py
-------|------------------------------------------------
P1-F   | Tool Router & Registry  | src/agent/tool_router.py
       |                         | src/agent/tool_registry.py

EXECUTION MODES

1. DETERMINISTIC_ONLY (offline mode):
   - No LLM invoked. Pure rule-based extraction + retrieval + applicability.
   - Used for hermetic offline operation and testing.

2. LLM_ASSISTED:
   - LLM generates structured proposals using evidence context.
   - Deterministic validator has absolute veto.
   - Falls back to DETERMINISTIC on any LLM failure.

3. LLM_FALLBACK:
   - LLM was attempted but failed; deterministic baseline used.
   - Transparently reported in agent_metadata.execution_mode.

DATA FLOW

User Query (raw_text)
  ↓
[RequirementExtractor] → NormalizedRequirementObject (req_obj)
  │  - product, voltage, material, grade, dimensions, etc.
  │  - Each field: {value, confidence, source_span, start_char, end_char}
  │  - query_sufficiency: {state, missing_discriminators, is_sufficient}
  │  - contradictions: [...]
  ↓
[search_standards] → BM25 + Dense retrieval → RRF fusion → rerank
  ↓
Top 5-15 candidates with {designation, title, role, department, score}
  ↓
[get_standard_evidence] + [check_applicability] + [check_lifecycle]
  + [check_regulatory] per candidate
  ↓
EvidenceBundle (identity, scope, lifecycle, regulatory, provenance)
  ↓
[SelectiveAbstentionPolicy.decide] → (decision_state, primary_rec, ...)
  ↓
[LLM Reason & Propose] (in LLM_ASSISTED mode)
  ↓
[DeterministicValidator.validate] — ABSOLUTE VETO
  - If rejected → 1 revision round → if still rejected → deterministic fallback
  ↓
Final Answer (schema-compliant JSON + natural language explanation)

================================================================================
SECTION C — DATA LAYER AND KNOWLEDGE GRAPH
================================================================================

GRAPH STRUCTURE

Source: data/processed/standards_graph.json
Format: JSON with {nodes, edges} structure
Nodes:  6,081 total (CED: 1,935 hydrated, ETD: 1,944 hydrated, remainder external/supporting)
Edges:  5,428 cross-references (parts, test methods, normative refs, supersession)
SHAs256: 245255f014413ccab5b57d811b9b86f254e174d7a258cd4b51faa2e1dffdddc9

NODE SCHEMA (standard_v1_2.schema.json)

Each node represents a BIS standard or related entity with the following key fields:

Required fields:
  - designation:    String (e.g., "IS 7098 (Part 1):2025")
  - title:          String
  - base_number:     Integer (e.g., 7098)
  - part:            String or null (e.g., "Part 1")
  - section:         String or null
  - year:            Integer (e.g., 2025)
  - standard_role:   Enum (PRODUCT_STANDARD, TEST_METHOD, CODE_OF_PRACTICE,
                     INSTALLATION_CODE, COMPONENT, DIMENSIONAL_MOUNTING,
                     REFERENCE_CONSOLIDATED, EXTERNAL_STANDARD, etc.)
  - primary_department: "CED" or "ETD"
  - candidate_status: "ELIGIBLE" | "CONTEXT_ONLY" | "SUPPORTING_ONLY"
  - node_type:      "BIS_STANDARD" | "EXTERNAL_STANDARD" | "TEST_METHOD" etc.

Optional fields (may be absent in stub nodes):
  - scope:              String — the standard's technical scope text
  - is_hydrated:        Boolean — whether full scope text is available
  - scope_inclusions:   List[str]
  - scope_exclusions:   List[str]
  - applicability_attributes: Dict with per-attribute evidence
  - lifecycle_status:   String (ACTIVE, SUPERSEDED, WITHDRAWN, etc.)
  - qco_mandatory:      Boolean or null — regulatory mandate flag
  - amendment_notes:    String
  - supersession_info:  Dict with superseded_by, supersession_date, etc.

EDGE RELATIONSHIPS

Relations captured:
  - SUPERSEDES / REPLACES: edition chain (e.g., IS 7098:1988 → IS 7098 (Part 1):2025)
  - PART / SECTION: constituent parts of multipart standards
  - TEST_METHOD: linkage to test method standards (e.g., IS 10810 for cables)
  - NORMATIVE_REFERENCE: standards cited as normative references
  - COMPONENT / MOUNTING: component and mounting standard relationships
  - CONSTITUTIVE_MATERIAL: material standards (e.g., IS 1786 for steel wire)
  - INCLUSION / EXCLUSION: scope boundary relationships

CORPUS SEGREGATION

The engine segregates nodes into three distinct corpora (see engine.py
index_graph method, lines 153-191):

1. PRIMARY_CANDIDATE_CORPUS (1,935 + 1,944 = 3,879 nodes):
   - Product specifications and design codes
   - Eligible for primary recommendation
   - Evaluated by CandidateEligibilityPolicy.is_primary_candidate()

2. SUPPORTING_CONTEXT_CORPUS:
   - Test methods (IS 10810 series for cables)
   - Material references (IS 1786, IS 2062, etc.)
   - Codes of practice and installation codes
   - Used as supporting_context_pack in recommendations

3. EXTERNAL_REFERENCE_CORPUS:
   - Foreign/international standards (IEC, ISO, ASTM)
   - Cross-referenced but not recommended as primary
   - Indexed for relationship resolution

CORPUS POLICY

src/recommendation/corpus_policy.py implements CandidateEligibilityPolicy:
  - is_primary_candidate(node): Returns True if node represents a product
    specification or design code eligible for primary recommendation.
    Excludes TEST_METHOD, TERMINOLOGY, DIMENSIONAL_MOUNTING, GUIDELINES,
    SAMPLING_INSPECTION, MEASUREMENT_METHOD, CODE_OF_PRACTICE,
    SUPPORTING_STANDARD, and EXTERNAL_STANDARD node types.
  - is_supporting_context(node): Returns True for test methods, materials,
    installation codes.
  - is_external_reference(node): Returns True for IEC, ISO, ASTM standards.

DATA QUALITY ASSESSMENT

Positive:
- Strong node schema with enumerated roles preventing role confusion
- Clear corpus segregation prevents test methods from being recommended
  as primary products
- Edge relationships maintain cross-standard provenance
- SHA256 checksums in release manifest provide integrity verification

Concerns:
- 6,081 total nodes but only ~3,889 are in primary candidate corpus
  (CED + ETD combined). The remaining ~2,192 are supporting/external.
- Only "hydrated" nodes have scope text — many nodes are stubs without
  scope, which triggers EXPERT_REVIEW_REQUIRED in the decision pipeline.
- The release manifest reports 1,935 hydrated CED and 1,944 hydrated ETD
  nodes, suggesting most nodes are hydrated but some may still lack scope.
- No visibility into completeness of applicability_attributes per node —
  many nodes may have partial attribute data.

================================================================================
SECTION D — REQUIREMENT EXTRACTION AND NORMALIZATION (req_obj CONTRACT)
================================================================================

The NormalizedRequirementObject (req_obj) is the canonical intermediate
representation produced by the RequirementExtractor. It is the single source
of truth for technical parameters used across retrieval, applicability,
and calibration stages.

EXTRACTION ARCHITECTURE

Two-tier extraction in BoundedStructuredExtractor
(src/llm/structured_extractor.py):

1. LLM-Assisted Extraction (when provider available):
   - LLM generates JSON conforming to schemas/llm_extraction.schema.json
   - JSON Schema validation with additionalProperties: false (strict)
   - Verbatim character-span verification: every extracted field's
     evidence_text must exist as a substring of the raw query text.
     Zero tolerance for hallucinated spans — weak token overlap is
     prohibited; spans not found verbatim are rejected.
   - Verified grounded fields are merged into the deterministic baseline,
     keeping whichever has higher confidence.

2. Deterministic Fallback (always succeeds):
   - Rule-based regex extraction via PRODUCT_PATTERNS, VOLTAGE_PATTERN,
     DIMENSION_PATTERN, MATERIAL_PATTERNS, GRADE_PATTERNS, etc.
   - Normalizers: normalize_voltage, normalize_material,
     normalize_dimensions, normalize_frequency, normalize_temperature
   - Modular extractors: ProductEntityExtractor, MaterialExtractor,
     ApplicationExtractor, ElectricalParameterExtractor,
     TechnologyModifierExtractor

req_obj STRUCTURE (schemas/normalized_requirement.schema.json)

{
  "query_id":           string,                # e.g., "Q_AUTO_001"
  "raw_text":           string,                # verbatim query text
  "language":           string,                # "en" | "hi" | "gu" | ...
  "extraction_timestamp": ISO 8601 string,
  "input_hash":         string (sha256),        # deterministic hashing
  "extractor_version":  "1.3.0",
  "model_version":      "deterministic-v1.3",
  "extractor_mode":     "DETERMINISTIC" | "LLM_ASSISTED" |
                        "DETERMINISTIC_FALLBACK" | "LLM_UNAVAILABLE" |
                        "LLM_DISABLED_FALLBACK" | "LLM_ERROR_FALLBACK",
  "product_status":     "EXTRACTED" | "MISSING",
  "requirements": {
    # Each attribute follows the Design Law (see below):
    "product":      {value, confidence, source_span, start_char, end_char,
                     normalization, base_product?, modifiers?},
    "voltage":      {value, confidence, source_span, start_char, end_char,
                     normalization},
    "material":     {value, confidence, source_span, start_char, end_char,
                     normalization},
    "grade":        {value, confidence, source_span, start_char, end_char,
                     normalization},
    "dimensions":   {value, confidence, source_span, start_char, end_char,
                     normalization},
    "capacity":     {value, confidence, source_span, start_char, end_char,
                     normalization},
    "application":  {value, confidence, source_span, start_char, end_char,
                     normalization},
    "installation": {value, confidence, source_span, start_char, end_char,
                     normalization},
    "temperature":  {value, confidence, source_span, start_char, end_char,
                     normalization},
    "current":      {value, confidence, source_span, start_char, end_char,
                     normalization},
    "frequency":    {value, confidence, source_span, start_char, end_char,
                     normalization},
    "safety":       {value, confidence, source_span, start_char, end_char,
                     normalization},
    "performance":  {value, confidence, source_span, start_char, end_char,
                     normalization},
    "testing":      {value, confidence, source_span, start_char, end_char,
                     normalization},
    "marking":      {value, confidence, source_span, start_char, end_char,
                     normalization},
    "quantity":     {value, confidence, source_span, start_char, end_char,
                     normalization},
    "tender_date":  {value, confidence, source_span, start_char, end_char,
                     normalization},
    "location":     {value, confidence, source_span, start_char, end_char,
                     normalization},
    "standard_family": {value, confidence, source_span, start_char, end_char,
                        normalization},
    # Any attribute not found in the query is set to None (not fabricated)
  },
  "procurement_intent": {
    "procurement_object": {state, value, confidence, evidence_span},
    "object_type": "FINISHED_PRODUCT" | "FINISHED_ASSEMBLY" | "COMPONENT" |
                   "RAW_MATERIAL" | "INSTALLATION_SERVICE" | ...
    "technical_intent": "SUPPLY" | "INSTALLATION" | "DESIGN" | "TESTING" |
                        "SUPPLY_AND_INSTALLATION"
  },
  "query_sufficiency": {
    "state": "SUFFICIENT" | "PARTIALLY_SPECIFIED" | "INSUFFICIENT",
    "is_sufficient": boolean,
    "product_identified": boolean,
    "critical_discriminators_present": boolean,
    "missing_critical_discriminators": [string],
    "specific_standard_requested": boolean,
    "reason": string,
    "contradictions": [string]  # if detected
  },
  "missing_discriminators": [string],
  "contradictions": [string],
  "language_detection": {detected, confidence}
}

DESIGN LAWS

1. Every extracted field MUST have all six grounding fields:
   value, confidence (float 0.0-1.0), source_span (exact substring),
   start_char (0-indexed), end_char (0-indexed), normalization (canonical
   or null). This is enforced at the schema level.

2. Never fabricate placeholder products. If no product is grounded,
   product = None, product_status = "MISSING". The extractor will not
   produce "General Procurement Item" or similar fabricated values.

3. Deterministic hashing: input_hash = sha256(raw_text) ensures
   reproducibility of extraction results.

4. Multi-occurrence capturing for voltages, dimensions, and capacities
   via pattern lists (multiple matches aggregated).

EXTRACTED ATTRIBUTE MAPPING TO DISCRIMINATORS

The DISCRIMINATOR_RULES registry (requirement_extractor.py:218-249) maps
product categories to their required discriminators:

  cable:  voltage, conductor_cross_section_dimensions,
          conductor_and_insulation_material, installation_type
  cement: cement_grade, cement_type
  transformer: primary_and_secondary_voltage, kva_capacity_rating
  pipe:   pipe_material, nominal_diameter_od_nb
  steel:  steel_grade_fe500_fe600, steel_material_type

These discriminators drive:
  - _identify_missing_discriminators(): flags missing technical params
  - _evaluate_query_sufficiency(): assesses whether query can be matched
  - _detect_multi_product(): detects multi-category queries

QUERY SUFFICIENCY LOGIC (P1-A)

  is_underspecified = NOT has_explicit_designation AND (
      NOT has_product OR
      (NOT has_params AND len(missing_discriminators) >= 2)
  )

If underspecified and no explicit designation, the agent enters
INSUFFICIENT_INFORMATION or CLARIFICATION_REQUIRED state before
proceeding to retrieval.

ASSESSMENT

Positive:
- Rigorous grounding with character-level provenance spans
- Strict schema enforcement prevents hallucination propagation
- Multilingual support (English, Hindi, Gujarati patterns)
- Contradiction detection for conflicting requirements (cement grades,
  steel grades, conflicting applications, meter technologies)
- Two-tier LLM + deterministic design ensures no single point of failure

Concern:
- The LLM extraction schema (schemas/llm_extraction.schema.json) and
  the deterministic extractor produce slightly different field shapes
  (e.g., the LLM path uses "evidence_text" while the deterministic path
  uses "source_span" + "start_char" + "end_char"). The merge logic
  (structured_extractor.py:184-193) normalizes LLM fields to the
  deterministic schema, but this is a potential source of field drift
  if the merge logic is not kept in sync.

================================================================================
SECTION E — RETRIEVAL ARCHITECTURE (BM25 + DENSE RRF + GRAPH EXPANSION)
================================================================================

The retrieval layer implements a three-stage candidate generation pipeline:

STAGE 1: Dual-Channel Retrieval

BM25 Retriever (src/retrieval/bm25_retriever.py):
  - Uses Whoosh search engine (pure-Python, hermetic, no external deps)
  - Indexes standard designation, title, and scope text from primary
    candidate corpus (~3,879 nodes)
  - Returns top-25 candidates with TF-IDF BM25 scores
  - Query is the "focused_query" string (product + material + app + acronyms)

Dense Retriever (src/retrieval/dense_retriever.py):
  - Uses sentence-transformers embedding models (MiniLM)
  - DeterministicSemanticProjection fallback when model unavailable
  - Encodes query and candidate text into dense vectors
  - Cosine similarity retrieval, top-25
  - In hybrid_deterministic mode (default), the dense retriever uses
    a deterministic lightweight projection rather than loading a neural model

STAGE 2: Reciprocal Rank Fusion (src/retrieval/fusion.py)

  def reciprocal_rank_fusion(sources, k=60, weights=None, top_k=20):
      - BM25 weighted at 1.2, Dense weighted at 0.8
      - k=60 controls rank decay (RRF formula: 1/(k + rank))
      - Produces fused ranked list of 20 candidates

STAGE 3: Graph Expansion (src/retrieval/graph_expansion.py)

  GraphCandidateExpander.expand(candidates, top_k=25):
  - Expands top-N candidates by traversing knowledge graph edges
  - Adds related standards (parts, test methods, normative references)
  - Expands to up to 4x the input candidate count
  - Maintains cycle-safety via visited node tracking
  - Preserves original candidate ranks; expanded nodes get lower scores

QUERY FORMULATION

In engine.recommend(), the query is enriched:
  focused_query = "{target_product} {material} {application} {acronyms}"
  enriched_query = "{focused_query} {raw_text}"

Acronym expansion:
  - "polyvinyl chloride" -> adds "pvc upvc"
  - "polyethylene" -> adds "hdpe pe"
  - "mild steel/steel tubes" -> adds "erw tubulars"
  - "cast iron" -> adds "spun iron"

This query enrichment is critical for matching standards that may be
indexed under different terminology than the procurement query uses.

EXACT DESIGNATION INTENT DETECTION

The DesignationResolver (src/retrieval/designation_resolver.py) detects
explicit standard citations in the query (e.g., "IS 1180 Part 1").
These are resolved to graph nodes and prepended at rank 1, with a
rerank_score of 1.0 and explicit tag "exact_designation_matched".

This is a critical anti-hallucination mechanism: if the user cites a
specific standard, that standard is always in the candidate set, and
the applicability engine evaluates whether it actually matches the
technical requirements (preventing the IS 1180-for-uPVC-pipes case).

RETRIEVAL EVALUATION METRICS (from evaluation artifacts)

Test set (13 queries):
  RAW_RETRIEVAL_TOP1:       0.2308
  candidate_recall_at_5:    0.3846
  VERIFIED_PRIMARY_TOP1:    0.1538

Open-world benchmark (50 queries):
  RAW_RETRIEVAL_TOP1:       0.2326
  candidate_recall_at_5:    0.34
  candidate_recall_at_10:   0.34

Coverage boundary benchmark (10 outside-scope queries):
  RAW_RETRIEVAL_TOP1:       0.0
  safe_abstention_rate:     1.0 (perfect abstention on out-of-scope)

Adversarial benchmark (32 queries):
  RAW_RETRIEVAL_TOP1:       0.0
  hnrr_at1:                 0.9531 (hard negative rejection rate at 1)
  hn_intrusion_rate_5:      0.0938 (hard negative intrusion at top-5)

ASSESSMENT

Positive:
- Hybrid BM25 + Dense retrieval with RRF provides diversity
- Graph expansion adds relevant related standards (test methods, parts)
- Exact designation detection ensures cited standards are always
  included in candidate set — critical for adversarial safety
- Acronym expansion improves recall for standards indexed under
  different terminology
- Hard negative testing: hnrr_at1 = 0.9531 on adversarial set
  (95%+ hard negative rejection at top-1)
- Perfect hard negative exclusion (hn_intrusion_rate_5 = 0.0938)

Critical Concern:
- Retrieval accuracy is critically low: RAW_RETRIEVAL_TOP1 = 0.2308
  on the test set. ~77% of queries fail to retrieve the correct
  standard at top position.
- candidate_recall_at_5 = 0.34-0.38 — the correct standard is not
  in the top-5 for ~62-66% of queries.
- This is the root cause of the poor verified_primary_accuracy.
- The focused_query construction may be too aggressive in filtering
  out important query text, or the indexing may not cover enough
  of the candidate space.
- Dense retriever in "hybrid_deterministic" mode uses a
  DeterministicSemanticProjection rather than true neural embeddings,
  which limits semantic matching capability.
- In agent.py (line 188), the fallback search condition uses a
  retrieval_score threshold of 0.005 — candidates below this score
  trigger a second search round, but 0.005 is extremely permissive
  and may not filter low-quality candidates effectively.

================================================================================
SECTION F — CANDIDATE RERANKING (RULE-BASED + NEURAL CROSS-ENCODER)
================================================================================

The reranker applies 12 modular feature extractors to score
(query, standard) pairs, providing explainable ranked candidates.

FEATURE EXTRACTORS (src/retrieval/reranker_features.py)

1. DesignationAlignment: Matches explicit standard citation in query
2. PartSectionAlignment: Part/section number alignment
3. RoleAlignment: Standard role matches procurement intent
4. ProductCategoryAlignment: Product type matches (Cable, Transformer, etc.)
5. MaterialAlignment: Material mentions (XLPE, PVC, HDPE, etc.)
6. ApplicationAlignment: Application match (potable water, sewage, etc.)
7. TechnologyModifierAlignment: Tech modifiers (FRLS, flame-retardant, etc.)
8. ScopeBoundary: Checks if query falls within scope inclusions/exclusions
9. Specificity: Penalizes generic/over-broad standards
10. CandidateEvidenceAvailability: Penalizes unhydrated stub nodes
11. ProcurementIntentAlignment: Matches procurement object type
12. ContradictionPenalty: Penalizes technical contradictions

ScoringPolicy combines features using weighted sum with configurable
feature weights. The policy also implements explainable ranking with
why_ranked_above() method for auditability.

RERANKER MODES

The create_reranker() factory (src/retrieval/cross_encoder.py) supports:
  - "rule_based": RuleBasedReranker using 12 modular features (default)
  - "neural": NeuralCrossEncoderReranker using cross-encoder/ms-marco-MiniLM-L-6-v2
  - "none": NoneReranker pass-through (preserves order without scoring)

The agent orchestrator's search_standards tool passes req_obj as:
  req_obj={"requirements": requirements} — this enables the feature
  extractors to check technical attribute alignment.

NEURAL CROSS-ENCODER

When sentence_transformers is available:
  - Pairs query with each candidate's text (designation + title + scope)
  - Uses cross-encoder model for token-level cross-attention scoring
  - Produces rerank_score per candidate

Transparent fallback:
  - If model load fails, reports fallback_used=True with reason
  - Falls through to RuleBasedReranker
  - Metadata records effective_mode: "RULE_BASED_FALLBACK"

ASSESSMENT

Positive:
- 12 modular features provide comprehensive technical matching
- Explainable scoring via why_ranked_above()
- Transparent fallback reporting for neural model
- req_obj integration allows applicability signals to influence ranking

Concern:
- Only 2 of the 12 features (DesignationAlignment, PartSectionAlignment)
  directly use the normalized req_obj fields. Other features rely on
  pattern matching against raw query text rather than structured attributes.
- The feature extractors read from candidate dict fields, but the
  integration between the structured req_obj and these features is
  partial — many features duplicate regex patterns already in the
  extractor rather than consuming the normalized req_obj directly.
- Neural cross-encoder mode is not the default production mode, limiting
  semantic matching depth in favor of deterministic consistency.

================================================================================
SECTION G — TECHNICAL APPLICABILITY ENGINE
================================================================================

The TechnicalApplicabilityEngine (src/recommendation/applicability_engine.py)
evaluates whether a candidate standard matches the procurement requirements
on a per-attribute basis.

APPLICABILITY STATES (ApplicabilityState enum, src/recommendation/applicability/state.py)

  APPLICABLE                  — All required attributes match
  CONDITIONALLY_APPLICABLE    — Core product matches, some attributes unknown
  RELATED                     — Test method, component, or design code (not
                                a primary product spec)
  NOT_APPLICABLE              — Product category mismatch (hard rejection)
  UNKNOWN                     — Insufficient data
  EXPERT_REVIEW_REQUIRED      — Evidence gap, needs manual review

EVALUATION PROCESS

evaluate_applicability(candidate, normalized_requirements, hydration_document):
  1. Check standard architectural role (TEST_METHOD, COMPONENT, DESIGN_CODE
     are classified as RELATED, not primary product recommendations)
  2. Check scope text availability (STAGE 0.4)
  3. Evaluate 10 technical dimensions:
     - PRODUCT (mandatory grounding — POSITIVE PRODUCT MATCH required for
       APPLICABLE; absence of positive evidence disqualifies)
     - MATERIAL
     - GRADE
     - VOLTAGE
     - CAPACITY
     - DIMENSIONS
     - APPLICATION
     - ENVIRONMENT
     - PERFORMANCE
     - SAFETY
     - INSTALLATION
  4. Compile matched_attributes and mismatched_attributes lists
  5. Apply scope boundary rules from domain registries (ETD/CEC)
  6. Determine final state per core principles:
     - Any MISMATCH attribute → NOT_APPLICABLE
     - Missing positive PRODUCT match → NOT_APPLICABLE
     - All MATCH → APPLICABLE
     - Gaps → CONDITIONALLY_APPLICABLE or EXPERT_REVIEW_REQUIRED

DOMAIN RULE REGISTRIES

ETDRuleRegistry (src/recommendation/applicability/etd_registry.py) provides:
  - Product stem mappings: "Power Cable" → ["power cable", "cable", ...],
    "Power Transformers" → ["power transformer", "distribution transformer", ...]
  - Scope boundary rules with exclusion predicates:
    * IS 1180: CAPACITY > 2500 kVA → EXCLUDED (bulk transmission uses IS 2026)
    * IS/IEC 61558: CAPACITY > 25 kVA or VOLTAGE > 1000V → EXCLUDED
    * IS 694: VOLTAGE > 1100V → EXCLUDED (MV/HV cables use IS 7098 Part 2)
    * IS 13779 (static meters): SMART or AMI queries → EXCLUDED

The GenericApplicabilityEngine (src/recommendation/applicability/core.py) delegates
rule evaluation to registered DomainRuleRegistry plugins, supporting both CED and
ETD domains with department-agnostic core logic.

ASSESSMENT

Positive:
- Per-attribute evaluation provides granular grounding
- Clear state machine prevents ambiguous applicability claims
- Scope exclusions are respected (standards with scope limitations are
  not recommended if query violates exclusions)
- Evaluation trace provides audit trail for all attribute checks
- Role-based filtering prevents test methods/components/codes from
  being promoted to primary product recommendations

Concern:
- The applicability engine relies on normalized req_obj from the
  extractor, but the integration point in agent.py (line 218-221) passes:
    app_args = {"designation": desig, "requirements": reqs, "query": query}
  where reqs is the raw requirements dict (with value/confidence/span
  nested structure). The applicability engine must unpack this structure
  correctly via _extract_voltage_volts() and _extract_kva() helper methods.
- The "no rejection rule fired ≠ APPLICABLE" principle is implemented
  correctly: the engine requires POSITIVE_PRODUCT_MATCH as mandatory
  grounding, preventing false positives from absence of evidence.

================================================================================
SECTION H — LIFECYCLE AND EDITION RESOLUTION
================================================================================

The LifecycleEngine (src/recommendation/lifecycle_gate.py) resolves
standard edition lineages, point-in-time edition validity, and active
amendment sets using curated data rather than hard-coded rules.

CANONICAL LIFECYCLE STATES

  VERIFIED_ACTIVE          — Confirmed current and eligible
  VERIFIED_SUPERSEDED      — Confirmed superseded by a newer edition
  VERIFIED_WITHDRAWN       — Confirmed withdrawn from sale/application
  HISTORICAL_VALID         — Historical edition, still legally valid for legacy use
  FUTURE_NOT_VALID         — Not yet published/effective
  LIFECYCLE_UNVERIFIED     — Temporal bounds unknown — fail-closed
  CONFLICTING_LIFECYCLE    — Multiple records with conflicting lifecycle status

STANDARD EDITION MODEL

The StandardEdition dataclass (lifecycle_gate.py:65-84) encapsulates:
  - designation, year, family, base_number, part, section
  - publication_date, withdrawal_date
  - lifecycle_status, candidate_status
  - superseded_by, supersedes
  - provenance (with VERIFIED/INFERRED/UNKNOWN date_status)
  - valid_on(evaluation_date) — temporal validity predicate

DATA-DRIVEN CURATED LIFECYCLE

Curated lifecycle data is loaded from:
  data/regulatory/lifecycle_curated.json
  (loaded via CURATED_LIFECYCLE_PATH, lifecycle_gate.py:30)

The engine builds edition chains grouped by
(family, base_number, part, section) and sorted chronologically.
This avoids hard-coded Python conditionals for edition lineage
resolution.

VALIDATION LOGIC

valid_on(evaluation_date):
  - If evaluation_date is None: standard is valid if ACTIVE and ELIGIBLE
  - If evaluation_date provided:
    - Cannot be valid before publication date
    - Cannot be valid after withdrawal/superseded effective date
  - If temporal bounds unknown: emits LIFECYCLE_UNVERIFIED (fail-closed)

AGENT INTEGRATION

In agent.py (lines 225-229), check_lifecycle is dispatched per candidate:
  life_args = {"designation": desig, "evaluation_date": eval_date}
  life_res = self.tool_registry.dispatch("check_lifecycle", life_args)

Default evaluation_date: "2026-07-15" (agent.py:103)

ASSESSMENT

Positive:
- Temporal model with point-in-time validation prevents recommending
  superseded standards as current
- Curated data-driven approach (lifecycle_curated.json) avoids brittle
  hard-coded conditionals for edition lineage
- Fail-safe temporal attribution: when temporal bounds are unknown,
  emits LIFECYCLE_UNVERIFIED rather than silently endorsing a standard
- Edition chains grouped by (family, base_number, part, section) enable
  tracking multi-edition standards across revisions

Concern:
- The curated lifecycle dataset (lifecycle_curated.json) is the single
  source of truth for edition validity, but the file's provenance and
  update cadence are not documented in the code — if updates lag behind
  BIS edition changes, stale lifecycle states could persist
- The default evaluation_date "2026-07-15" is hard-coded in agent.py
  and should be parameterized for production deployment where the
  evaluation date is a procurement decision context

================================================================================
SECTION I — REGULATORY GATE AND QCO/CRS MANDATE VERIFICATION
================================================================================

The RegulatoryGate (src/recommendation/regulatory_gate.py) evaluates
statutory quality control order (QCO) and compulsory registration scheme
(CRS) mandates for resolved Indian Standards, with date-awareness and
conflict detection.

REGULATORY STATES (RegulatoryState enum)

  MANDATORY_CONFIRMED              — QCO/CRS mandate verified for this standard
  MANDATORY_CONDITIONALLY_APPLICABLE — Mandate applies subject to exemptions
  MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES — Searched datasets, no mandate found
  NOT_APPLICABLE                    — Order effective date is after evaluation date
  NOT_VERIFIED_IN_CURRENT_CORPUS  — Cannot confirm mandate status in current data
  UNKNOWN                           — No standard designation provided
  CONFLICTING_EVIDENCE             — Multiple contradictory regulatory records
  REGULATORY_SOURCE_UNAVAILABLE    — Data sources on disk are missing

DATA SOURCES (data/regulatory/)

  qco_orders.jsonl        — 12 records (QCO mandates)
  crs_rules.jsonl         — 2 records (CRS rules)
  source_manifest.json    — Gazette reference provenance for consistency check

The RegulatoryGate performs source consistency verification (check_source_consistency)
comparing manifest.json against JSONL datasets to detect:
  - URL mismatches
  - Order identity mismatches (e.g., Cement S.O. 2282(E) 2024 vs S.O. 191(E) 2003)
  - Coverage mismatches (manifest claims a standard absent from JSONL)

EVALUATION PROCESS

evaluate_regulatory_status(standard_designation, evaluation_date, evaluation_context):
  1. Check source availability (data/regulatory/ files)
  2. Run source consistency check against manifest
  3. Retrieve matching records from qco_orders.jsonl + crs_rules.jsonl
  4. If no records: MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES
  5. If source consistency is CONFLICTING: fail-closed → CONFLICTING_EVIDENCE
  6. Analyze scheme conflicts (Scheme-I vs Scheme-II/CRS)
  7. If multiple records with conflicting schemes: CONFLICTING_EVIDENCE
  8. Select primary governing record (most recent effective_date)
  9. Date-aware check: if effective_date > evaluation_date → NOT_APPLICABLE
  10. If exemptions match evaluation context (export, prototype, defence):
      → MANDATORY_CONDITIONALLY_APPLICABLE
  11. Otherwise → MANDATORY_CONFIRMED

FAIL-CLOSED PRINCIPLES

  - If source consistency is CONFLICTING, the standard cannot be
    MANDATORY_CONFIRMED (regulatory_gate.py:380-410)
  - If sources unavailable: REGULATORY_SOURCE_UNAVAILABLE
  - If no matching records: MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES
  - Date mismatch: NOT_APPLICABLE (with explicit explanation)

AGENT INTEGRATION

In agent.py (lines 231-238):
  reg_args = {"designation": desig, "query_context": {"product": prod_val}}
  reg_res = self.tool_registry.dispatch("check_regulatory", reg_args)

The query_context carries the product value from the normalized req_obj
to enable product-level exemption matching.

ASSESSMENT

Positive:
- 7-state regulatory taxonomy provides fine-grained mandate classification
- Source consistency verification (P0-8) detects manifest vs JSONL discrepancies
- Date-aware validation prevents recommending standards whose QCO effective
  date post-dates the evaluation date
- Fail-closed on conflicting schemes: incompatible certification schemes
  across multiple orders trigger CONFLICTING_EVIDENCE rather than silent
  false confirmation
- Exempt detection recognizes defense/export/prototype contexts enabling
  MANDATORY_CONDITIONALLY_APPLICABLE state
- Token-safe scheme normalization prevents "Scheme-I" substring matching
  against "Scheme-II" (regulatory_gate.py:132-147)

Concern:
- Limited dataset: qco_orders.jsonl has only 12 records and crs_rules.jsonl
  has only 2 records — regulatory coverage for the 3,879-hydrated standards
  is extremely sparse (manifest shows only 2 regulatory sources indexed)
- The regulatory state feeds into EvidencePolicy.evaluate_claim for
  REGULATORY_MANDATE_CLAIM, but the EvidenceBundle's regulatory_ready property
  requires the state to be in a "definitively verified" set — many standards
  will have NOT_VERIFIED_IN_CURRENT_CORPUS, which propagates uncertainty
  rather than a false positive

================================================================================
SECTION J — EVIDENCE BUNDLE AND READINESS MODEL
================================================================================

The EvidenceBundle (src/recommendation/evidence_bundle.py) is the
first-class evidentiary representation of an Indian Standard. It
encapsulates identity, scope, technical attributes, lifecycle, regulatory
status, and provenance. It is the sole authority for recommendation
readiness decisions.

EVIDENCE DIMENSIONS (6 Readiness Properties)

  identity_ready          — Valid canonical designation + title + base number or IS prefix
  scope_ready             — Verifiable scope text exists (≥20 chars)
  applicability_ready     — Identity + scope exist for technical boundary evaluation
  lifecycle_ready         — Lifecycle status explicitly verified, not UNKNOWN/SUPERSEDED/WITHDRAWN
  regulatory_ready        — Regulatory state in definitively verified set (MANDATORY_CONFIRMED,
                            MANDATORY_CONDITIONALLY_APPLICABLE, NOT_MANDATORY_CONFIRMED,
                            NOT_APPLICABLE)
  provenance_ready        — Valid source_type + source_id tracking

CLAIM TYPES (EvidencePolicy, evidence_bundle.py:100-195)

  RETRIEVAL_CLAIM                 — Requires identity_ready
  CANDIDATE_CLAIM                 — Requires identity_ready + department
  TECHNICAL_APPLICABILITY_CLAIM   — Requires identity_ready + scope_ready +
                                    no mismatched_attributes in context
  PRIMARY_RECOMMENDATION_CLAIM   — Requires ALL dimensions ready, no disallowed roles,
                                    positive PRODUCT grounding, no contradictions
  REGULATORY_MANDATE_CLAIM       — Requires regulatory state in verified set,
                                    not CONFLICTING_EVIDENCE

EVIDENCE GAP CODES (13 canonical codes)

  IDENTITY_UNVERIFIED, SCOPE_MISSING, APPLICABILITY_EVIDENCE_MISSING,
  PRODUCT_GROUNDING_MISSING, ROLE_UNVERIFIED, ROLE_MISMATCH,
  TECHNICAL_ATTRIBUTE_MISMATCH, LIFECYCLE_UNVERIFIED,
  PROVENANCE_UNVERIFIED, UNHYDRATED_STUB, REGULATORY_UNVERIFIED,
  REGULATORY_SOURCE_UNAVAILABLE, REGULATORY_CONFLICT,
  CONTRADICTORY_REQUIREMENTS

PRIMARY_RECOMMENDATION_CLAIM GATES (evidence_bundle.py:135-179)

  The PRIMARY_RECOMMENDATION_CLAIM gates:
  1. identity_ready must be True (IDENTITY_UNVERIFIED)
  2. scope_ready must be True (SCOPE_MISSING)
  3. applicability_ready must be True (APPLICABILITY_EVIDENCE_MISSING)
  4. lifecycle_ready must be True (LIFECYCLE_UNVERIFIED)
  5. provenance_ready must be True (PROVENANCE_UNVERIFIED)
  6. If not hydrated and not scope_ready: UNHYDRATED_STUB
  7. Disallowed roles (TEST_METHOD, TERMINOLOGY, DIMENSIONAL_MOUNTING,
     CODE_OF_PRACTICE, GUIDELINES, SAMPLING_INSPECTION, MEASUREMENT_METHOD,
     SUPPORTING_STANDARD): ROLE_MISMATCH or ROLE_UNVERIFIED
  8. Context mismatched_attributes: TECHNICAL_ATTRIBUTE_MISMATCH
  9. No positive PRODUCT match in matched_attributes:
     PRODUCT_GROUNDING_MISSING
  10. Context contradictions: CONTRADICTORY_REQUIREMENTS

The EvidenceBundle is hydrated from graph nodes via from_node() classmethod,
which populates scope, technical_attributes, lifecycle, regulatory, and
provenance from the knowledge graph node and optional gate outputs.

The get_readiness_report() method (evidence_bundle.py:382-404) produces
a structured multidimensional readiness dictionary including:
  - evidence_dimensions (6 boolean readiness flags)
  - claim_readiness (5 claim type readiness booleans)
  - evidence_gaps (gap codes per claim type)

ASSESSMENT

Positive:
- 6-dimensional readiness model provides comprehensive evidence grounding
  before any candidate can reach primary recommendation
- EvidencePolicy is decoupled from pre-baked graph booleans — evaluates
  bundle state directly rather than trusting persisted flags
- 13 canonical gap codes provide precise diagnostic feedback on why a
  candidate cannot be promoted
- Positive PRODUCT_GROUNDING_MISSING gate prevents standards with
  matched attributes but no product alignment from reaching primary
  — this is the core anti-hallucination mechanism
- Disallowed role gating prevents test methods, design codes, and
  components from being recommended as primary product specifications
- EvidenceItem supports per-field source_type, source_id, verification_status,
  and character spans for full audit provenance

Concern:
- The EvidenceBundle.from_node() hydration path (evidence_bundle.py:431-467)
  is partial in the code read — I need to see the complete method to verify
  that lifecycle_evidence, regulatory_evidence, and technical_attributes
  are fully populated from gate outputs, not just from persisted graph flags
  that could be stale
- The recommendation_ready property (evidence_bundle.py:352-365) constructs
  context from evidence_flags.get("matched_attributes") — this flag must be
  populated by the applicability engine's evaluate_applicability output
  during bundle hydration, and the integration path for this population
  needs verification
- If lifecycle_ready returns False due to LIFECYCLE_UNVERIFIED, the
  candidate cannot reach PRIMARY_RECOMMENDATION_CLAIM — this is correct
  for safety but may be overly conservative given the sparse curated
  lifecycle dataset

================================================================================
SECTION K — CALIBRATION AND SELECTIVE ABSTENTION POLICY
================================================================================

The SelectiveAbstentionPolicy (src/calibration/policy.py) and
PlattScaler (src/calibration/calibrator.py) implement calibrated
selective abstention over the recommendation decision layer.

PLATT SCALER (src/calibration/calibrator.py)

PlattScaler(a=3.0, b=-1.8) provides univariate logistic calibration:
  calibrated_prob = 1 / (1 + exp(a * raw_score + b))

Default parameters (a=3.0, b=-1.8) are used when the empirical calibrator
model (data/models/calibrator_v1.json) cannot be loaded or has insufficient
samples. The release manifest flags this as
"CALIBRATION_INSUFFICIENT_DATA" with N=24 samples.

Calibration metrics (from eval artifacts):
  ECE (Expected Calibration Error): 0.2785 (test set)
  Brier Score: 0.2578 (test set)
  Expected calibration error diagnostic: 0.2785

SELECTIVE ABSTENTION DECISION TREE (policy.py:50-130)

The decide() method evaluates applicable recommendations against:
  1. tau_recommend = 0.55  — Top-1 calibrated probability threshold for
     PRIMARY_RECOMMENDATION_AVAILABLE
  2. tau_min = 0.35         — Minimum probability for a recommendation to
     be considered viable
  3. delta_margin = 0.04    — Minimum probability gap between top-1 and
     top-2 for confident single recommendation

Decision states emitted:
  - PRIMARY_RECOMMENDATION_AVAILABLE: top1_prob >= tau_recommend
  - NO_CONFIDENT_MATCH: top1_prob < tau_min or no viable candidates
  - INSUFFICIENT_INFORMATION: multiple viable but missing discriminators
  - MULTIPLE_POSSIBLE_STANDARDS: top1 and top2 within delta_margin, low confidence

AGENT INTEGRATION

The SelectiveAbstentionPolicy is used in engine.recommend() to convert
the ranked candidates with applicability/lifecycle/regulatory evaluation
into the final decision state. The engine applies calibration to the
raw confidence scores from applicability matching.

ASSESSMENT

Positive:
- Three-tier threshold system (tau_min, delta_margin, tau_recommend)
  provides principled abstention rather than binary accept/reject
- ECE and Brier score computation enables calibration monitoring
- Risk-coverage curve computation allows operator to tune tau thresholds
  for their required risk tolerance
- Transparent fallback: when empirical calibrator unavailable, uses
  default PlattScaler with documented prior parameters

Critical Concern:
- Only N=24 calibration samples — manifest explicitly flags
  "CALIBRATION_INSUFFICIENT_DATA" and notes "cannot make statistical
  calibration claims"
- Default PlattScaler(a=3.0, b=-1.8) is not derived from data; it is
  a hand-specified prior that may not reflect the actual score
  distribution of the reranker
- ECE of 0.2785 is high (ideal is 0.0) — the model is poorly calibrated,
  overconfident on incorrect predictions
- Brier score of 0.2578 confirms miscalibration
- The high safe_abstention_rate (1.0 on open-world) suggests the
  thresholds are set such that almost all queries abstain, which aligns
  with the insufficient calibration — the system defaults to
  "no confident match" rather than risking incorrect recommendations

================================================================================
SECTION L — LLM INTEGRATION, BOUNDED EXTRACTION, AND ANTI-HALLUCINATION
================================================================================

The system implements a fail-closed LLM integration pattern where the LLM
(Gemini via google-generativeai) operates in a strictly bounded assist mode
with deterministic fallback.

BOUNDARY STRUCTURE

1. BoundedStructuredExtractor (src/llm/structured_extractor.py):
   - Attempts structured LLM JSON extraction from raw query text
   - Validates LLM output against schemas/llm_extraction.schema.json
     with additionalProperties: false (strict schema)
   - Performs verbatim character-span verification: every extracted
     string field must be found verbatim in the raw query text
   - If any field fails span verification, it is REJECTED (no
     weak-token-overlap tolerance — literal substring match required)
   - On ANY failure (malformed JSON, timeout, schema violation,
     hallucinated span): transparently falls back to the deterministic
     RequirementExtractor
   - Mode attribution: DETERMINISTIC, LLM_ASSISTED, LLM_FALLBACK,
     LLM_UNAVAILABLE, LLM_ERROR_FALLBACK

2. LLM Provider Abstraction (src/llm/provider.py):
   - BaseLLMProvider abstract interface
   - DisabledLLMProvider: no-op, always reports is_available()=False
   - MockLLMProvider: returns canned responses for testing
   - Production provider: wraps google-generativeai

3. Context Builder (src/agent/context_builder.py):
   - Builds structured reasoning context for LLM from tool evidence
   - Includes candidate evidence, applicability results, lifecycle,
     regulatory, and retrieval scores
   - LLM generates structured proposal against this context only

4. Explanation Generator (src/llm/explanation.py):
   - LLM generates natural language explanation from the deterministic
     proposal that has already passed validation
   - LLM cannot override the decision state or primary recommendation
     — it only explains what was already deterministically decided

ANTI-HALLUCINATION MECHANISMS

  a) Verbatim Span Verification (structured_extractor.py:59-117):
     - query_text.find(field_val.lower()) must return >= 0
     - If not found, field is rejected with evidence_text=None
     - Zero tolerance for hallucinated attribute values

  b) Deterministic Safety Validator (validator.py:2):
     - Absolute veto authority over LLM proposals
     - 7 hard gates: candidate presence, role validity, applicability
       grounding, explicit designation conflict, lifecycle validity,
       regulatory fidelity, null-primary safety
     - LLM proposal rejected twice (initial + revision) → deterministic
       baseline used

  c) Schema Enforcement:
     - schemas/llm_extraction.schema.json: additionalProperties: false
     - schemas/agent_final_answer.schema.json: additionalProperties: false
     - schemas/agent_action.schema.json: enum-constrained fields

  d) Open-World Query Contract (src/query/open_world_contract.py):
     - Zero benchmark leakage: FORBIDDEN_BENCHMARK_KEYS prevents
       evaluation metadata from entering production query state
     - Explicit validation in validate_benchmark_isolation()

AGENT ORCHESTRATION BOUNDARIES (agent.py)

  MAX_AGENT_STEPS = 6         — Total orchestration iterations
  MAX_SEARCH_ROUNDS = 2       — Retrieval rounds (initial + optional refined)
  MAX_REVISION_ROUNDS = 1     — LLM revision attempts after validator rejection

  Step 5 (lines 186-201): Second search round only triggers if:
    - No candidates OR candidates[0].retrieval_score < 0.005
    - The 0.005 threshold is extremely permissive (Concern, Section E)

  Step 9 (lines 292-301): After first revision attempt fails validator:
    If still rejected → falls back to deterministic proposal synthesis
    (agent.py:269: _build_deterministic_recommendation)

ASSESSMENT

Positive:
- Strict schema validation with additionalProperties: false prevents
  schema pollution
- Verbatim span verification provides literal grounding of every
  extracted attribute to the source query
- Deterministic validator has absolute veto — LLM cannot override safety
- Transparent mode attribution (LLM_ASSISTED, LLM_FALLBACK, etc.)
  provides full audit trail of LLM involvement
- OpenWorldQuery contract enforces zero benchmark leakage

Concern:
- The LLM provider check is binary (is_available) — if the LLM returns
  garbage JSON that happens to pass schema validation but contains
  hallucinated values within the allowed schema fields, the verbatim
  span verification catches some but not all cases (e.g., if the LLM
  extracts a correct voltage value but from the wrong part of the query,
  the span may still exist elsewhere and pass verification)
- The _build_refined_query (line 188) for second retrieval round is
  not examined in detail — need to verify it doesn't introduce
  hallucinated query terms

================================================================================
SECTION M — AGENT ORCHESTRATION AND SAFETY VALIDATION
================================================================================

The StandSpecAgent (src/agent/agent.py) orchestrates a 9-step bounded
decision pipeline with deterministic safety validation at the end.

PIPELINE STAGES

Step 1: Requirement Extraction
  - self.engine.extractor.extract(query) → NormalizedRequirementObject (req_obj)
  - Extracts product, voltage, material, grade, dimensions with character spans
  - Identifies requested designations via regex: r"\bIS\s*\d+..."
  - Sets query_sufficiency state (SUFFICIENT, PARTIALLY_SPECIFIED,
    UNDER_SPECIFIED, AMBIGUOUS)

Step 2: Multi-Product Detection
  - _detect_multi_product() flags queries containing multiple product categories
  - Returns MULTIPLE_POSSIBLE_STANDARDS decision state without further retrieval

Step 3: Prototype Scope Check
  - Keyword-based outside-coverage detection for non-CED/ETD domains
  - Returns OUTSIDE_PROTOTYPE_COVERAGE if query falls outside civil/electrical scope

Step 4: Missing Discriminators Check
  - _check_missing_discriminators() identifies missing technical parameters
  - May enter CLARIFICATION_REQUIRED if completely unsearchable

Step 5: Search Standards (bounded to MAX_SEARCH_ROUNDS = 2)
  - Initial search: search_args = {"query": query, "top_k": 10, "requirements": reqs}
  - Second round (line 187): triggers if candidates[0].retrieval_score < 0.005
    OR no candidates at all
  - Refined query from _build_refined_query() using req_obj attributes

Step 6: Deep Candidate Verification (top 7 candidates)
  - For each candidate: get_standard_evidence, check_applicability,
    check_lifecycle, check_regulatory (lines 206-238)
  - Results stored in state.candidate_evidence, state.candidate_applicability,
    state.candidate_lifecycle, state.candidate_regulatory

Step 7: Reasoning & Proposal Formulation
  - LLM_ASSISTED mode: ContextBuilder.build_reasoning_context() → LLM proposal
  - LLM_FALLBACK mode: _build_deterministic_recommendation() synthesizes from
    tool evidence directly
  - Proposal includes: decision_state, primary_recommendation, alternatives,
    regulatory, lifecycle, normalized_requirements, confidence, uncertainty_statement

Step 8: Deterministic Safety Validation
  - self.validator.validate() applies 7 hard gates (see Section M detail below)
  - If valid → validated_answer = proposal
  - If invalid → REJECT, proceed to revision

Step 9: Bounded Revision (MAX_REVISION_ROUNDS = 1)
  - LLM revises proposal based on validation errors
  - If revised proposal passes → validated_answer
  - If still rejected → fall back to deterministic proposal synthesis

DETERMINISTIC VALIDATOR SAFETY GATES (validator.py)

1. Invalid Decision State Check
   - decision_state must be in valid_states list (lines 89-104)
   - Missing or unrecognized state → veto with INVALID_DECISION_STATE

2. Null-Primary Safety on Abstention States
   - Abstention states (NO_CONFIDENT_MATCH, INSUFFICIENT_INFORMATION, etc.)
     MUST have primary_recommendation=null
   - Violation → veto with NULL_PRIMARY_VIOLATION (lines 119-130)

3. Candidate Presence (Anti-Hallucination)
   - primary_recommendation.designation must be in:
     a) retrieved candidates from search_standards, OR
     b) explicitly requested designations from the query
   - Hallucinated designation → veto with HALLUCINATED_DESIGNATION (lines 132-142)

4. Role Validity
   - Cannot promote TEST_METHOD, SUPPORTING_OTHER, COMPONENT,
     MOUNTING_OR_DIMENSION as primary product (unless query explicitly
     asks for test/code intent)
   - Violation → veto with WRONG_ROLE_PRIMARY (lines 144-159)

5. Technical Applicability Gate
   - Candidate evaluated as NOT_APPLICABLE or INCOMPATIBLE → veto
   - mismatched_attributes present → veto with ATTRIBUTE_MISMATCH
   - exclusion_boundaries triggered → veto with EXCLUSION_BOUNDARY_TRIGGERED
   (lines 160-175)

6. Explicit Designation Conflict Check
   - If user requested specific standard (e.g., "IS 1180 Part 1" for uPVC pipe),
     and that standard is NOT_APPLICABLE → veto with REQUESTED_STANDARD_MISMATCH
   - Critical anti-safety-mechanism for citation override abuse (lines 177-184)

7. Lifecycle Gate
   - Candidate with lifecycle_state WITHDRAWN or OBSOLETE_PREDECESSOR → veto
   - Violation → veto with LIFECYCLE_VETO (lines 186-192)

8. Regulatory Fidelity Gate
   - Cannot cite QCO order number when regulatory_state is unverified
   - Cannot claim "not mandatory" or "voluntary" for unverified standards
   - Cannot claim mandatory standard is voluntary
   - Violation → veto with REGULATORY_FALSE_ASSERTION or HALLUCINATED_QCO
   (lines 194-220)

TOOL ROUTER AND REGISTRY

ToolRouter (src/agent/tool_router.py) and ToolRegistry (src/agent/tool_registry.py)
provide the dispatch interface:
  - search_standards: BM25 + Dense RRF + graph expansion + rerank
  - get_standard_evidence: Hydration + scope + provenance
  - check_applicability: TechnicalApplicabilityEngine evaluation
  - check_lifecycle: LifecycleGate evaluation
  - check_regulatory: RegulatoryGate evaluation
  - check_prototype_coverage: Open-world scope boundary detection

Tool calls are audited via state.record_tool_call() and state.record_tool_result(),
creating a complete audit trail in the final_answer.agent_metadata.tool_calls field.

ASSESSMENT

Positive:
- Bounded 9-step pipeline with hard step ceiling prevents runaway agent loops
- MAX_AGENT_STEPS=6, MAX_SEARCH_ROUNDS=2, MAX_REVISION_ROUNDS=1 enforced
- Deterministic validator has absolute veto authority — LLM cannot override
- 8 distinct safety gates cover hallucination, role mismatch, applicability,
  lifecycle, regulatory falsity, and explicit designation conflicts
- Complete audit trail via record_tool_call/record_tool_result
- Multi-product detection and prototype coverage check happen early,
  preventing wasted retrieval on inappropriate queries
- Tool registry abstraction allows clean addition of new tools

Concern:
- The validator's _resolve_base() normalization strips years and parentheses
  but does not normalize IS prefix variations (e.g., "IS 7098 Part 1:2025"
  vs "IS 7098 (Part 1):2025" — both should match). The _find_candidate_dict
  method handles this with fallback search, but the normalization may miss
  edge cases in designation formatting
- The second search round threshold (0.005) is hardcoded in agent.py and
  not configurable — if this value is too low, low-quality candidates trigger
  unnecessary second rounds; if too high, valid candidates may be suppressed
- _build_deterministic_recommendation (agent.py:269) synthesizes the
  fallback answer without LLM — I need to verify this produces a valid
  schema-compliant answer that still respects the safety constraints

================================================================================
SECTION N — FINAL ANSWER SCHEMA AND DECISION CONTRACT
================================================================================

The final answer schema (schemas/agent_final_answer.schema.json) defines
the structured contract for agent responses with strict type enforcement.

REQUIRED FIELDS (additionalProperties: false)

  decision_state            — enum of 9 decision states
  primary_recommendation    — object or null (null on abstention states)
  alternative_standards     — array of alternative candidates
  review_candidate          — object or null (for EXPERT_REVIEW_REQUIRED)
  clarifications_needed     — array of strings
  clarification_category    — string or null
  normalized_requirements   — object
  lifecycle                 — {state, recommended_edition, superseded_by, evidence}
  regulatory                — {state, qco_order_number, gazette_so_number,
                              effective_date, statement, evidence}
  confidence                — enum: HIGH, MEDIUM, LOW, UNVERIFIED
  uncertainty_statement     — string
  provenance                — array of strings
  natural_language_explanation — string
  agent_metadata            — object or null (orchestration metadata)
  tool_calls                — array or null (audit trail)

DECISION STATES (9 possible)

  PRIMARY_RECOMMENDATION_AVAILABLE   — Confident single standard identified
  CONDITIONAL_RECOMMENDATION         — Standard with conditions/exemptions
  MULTIPLE_POSSIBLE_STANDARDS        — Ambiguous, multiple candidates viable
  INSUFFICIENT_INFORMATION           — Query lacks discriminators for disambiguation
  NO_CONFIDENT_MATCH                — No candidate meets confidence thresholds
  STANDARD_DATA_UNAVAILABLE         — Standard exists but data incomplete
  OUTSIDE_PROTOTYPE_COVERAGE        — Query domain outside CED/ETD scope
  EXPERT_REVIEW_REQUIRED            — Evidence gaps require human review
  CLARIFICATION_REQUIRED            — Missing critical information from user

PRIMARY_RECOMMENDATION STRUCTURE

  {
    "designation": "IS 7098 (Part 1):2025",
    "title": "...",
    "reason": "...",
    "applicability_state": "APPLICABLE",
    "claim_level": "...",
    "evidence_ids": ["...", "..."],
    "matched_attributes": ["PRODUCT", "VOLTAGE", "MATERIAL", ...]
  }

CONSTRAINT INVARIANTS (enforced by DeterministicValidator)

  1. Abstention states MUST have primary_recommendation=null
  2. Primary recommendation designation must exist in retrieved candidates
     or be explicitly requested in the query
  3. Lifecycle state must be ACTIVE/VERIFIED_ACTIVE for primary recommendation
  4. Regulatory claims must not contradict verified evidence

ACTION SCHEMA (schemas/agent_action.schema.json)

The agent's intermediate reasoning is captured as actions:
  - TOOL_CALL: {"tool": "...", "arguments": {...}, "thought": "..."}
  - ASK_CLARIFICATION: {"question": "...", "clarification_reason": "..."}
  - FINAL_PROPOSAL: {"thought": "...", "answer": {final_answer_dict}}

Testing (test_agent_final_schema.py) validates all 5 decision scenarios
against the schema:
  - PRIMARY_RECOMMENDATION_AVAILABLE (cable)
  - NO_CONFIDENT_MATCH / EXPERT_REVIEW_REQUIRED (uPVC + IS 1180 mismatch)
  - MULTIPLE_POSSIBLE_STANDARDS (substation multi-product)
  - OUTSIDE_PROTOTYPE_COVERAGE (medical gloves)
  - CLARIFICATION_REQUIRED (generic "cable" query)

ASSESSMENT

Positive:
- additionalProperties: false on all nested objects prevents schema pollution
- 9 decision states cover the full spectrum from confident recommendation
  to outside-coverage rejection
- evidence_ids field enables traceability from final answer to source evidence
- matched_attributes and applicability_state provide immediate audit context
- Lifecycle and regulatory sub-objects ensure temporal and statutory context
  is always surfaced with the recommendation
- test_agent_final_schema.py validates all decision paths against the schema
- Tool call audit trail preserved in agent_metadata for compliance

Concern:
- The schema allows alternative_standards as a generic array — the item
  structure is not fully specified, which may lead to inconsistent
  representation across implementations
- The review_candidate sub-object includes evidence_gaps but the gap
  codes are strings — no enum constraint, which may lead to
  non-standard gap code usage in practice

================================================================================
SECTION O — TESTING QUALITY AND TEST COVERAGE ANALYSIS
================================================================================

The test suite comprises 44 test modules (tests/*.py) covering unit,
integration, adversarial, schema validation, LLM failure handling, and
offline execution scenarios.

TEST INVENTORY BY CATEGORY

Unit Tests:
  - test_requirement_extractor.py   — req_obj extraction with spans
  - test_applicability_10_attributes.py — 10-dimension attribute evaluation
  - test_reranker_and_discriminators.py — 12-feature reranker scoring
  - test_retriever_reranker_modes.py — BM25/Dense/RRF/neural modes
  - test_role_classifier_and_intent.py — STANDARD_ROLE classification
  - test_safety_metrics.py — ECE, Brier, risk-coverage computation
  - test_calibration.py — PlattScaler + SelectiveAbstentionPolicy
  - test_trust_core_hardening.py — EvidencePolicy + EvidenceBundle
  - test_evidence_and_designation.py — EvidenceItem, designation resolver
  - test_phase_d_trust_core.py — Trust core integration
  - test_phase_a_fixes.py — Phase A extraction fixes
  - test_phase_p1b_decision_core.py — Applicability state transitions
  - test_v1_1_hardening.py — v1.1 hardening scenarios
  - test_v1_2_hardening.py — v1.2 hardening scenarios

Integration / Engine Tests:
  - test_recommendation_engine.py — End-to-end recommendation pipeline
  - test_recommendation_schema.py — Recommendation output schema
  - test_agent_orchestration.py — StandSpecAgent pipeline stages
  - test_agent_validator.py — DeterministicValidator safety gates
  - test_agent_clarification.py — CLARIFICATION_REQUIRED flow
  - test_agent_rag_grounding.py — Retrieval + grounding integration
  - test_agent_llm_failure.py — LLM failure → deterministic fallback
  - test_agent_final_schema.py — Final answer schema validation
  - test_agent_open_world.py — Open-world query contract

Adversarial / Safety Tests:
  - test_adversarial_safety.py — Hard negative rejection, adversarial cases
  - test_llm_integration_p1d.py — Bounded LLM extraction + fallback
  - test_llm_production_hardening.py — LLM production failure modes
  - test_bounded_llm.py — LLM boundary enforcement
  - test_benchmark_isolation.py — Zero benchmark leakage contract
  - test_open_world_production_independence.py — Production vs benchmark isolation

Data / Coverage Tests:
  - test_knowledge_graph.py — Graph JSONL integrity
  - test_graph_jsonl_integration.py — Graph node hydration
  - test_graph_hardening.py — Graph data quality checks
  - test_manifests.py — Release manifest SHA256 verification
  - test_release_integrity.py — Release artifact integrity
  - test_read_excel.py — Input Excel parsing
  - test_preview_id.py — Preview identifier generation
  - test_regression.py — Regression suite

EVALUATION ARTIFACTS (data/evaluations/)

  test_evaluation.json        — 13 queries (authoritative evaluation)
  val_evaluation.json         — 13 queries
  open_world_evaluation.json  — 50 queries
  adversarial_evaluation.json — 32 queries
  challenge_evaluation.json   — 10 queries
  coverage_boundary_evaluation.json — 10 queries

Each evaluation artifact contains per-query metrics:
  - retrieval_correct (RAW_RETRIEVAL_TOP1 hit)
  - safe_decision_correct
  - primary_correct
  - wrong_primary (safety violation)
  - unsupported_primary (hallucination)
  - wrong_role, wrong_part, wrong_edition
  - regulatory_false_assertion
  - hit_in_top_k
  - calibrated_prob

BENCHMARK DATASETS (data/benchmarks/)

  test.jsonl     — 13 queries (Phase P1-F Section 14, 24, 25)
  val.jsonl      — 13 queries
  train.jsonl    — 24 queries
  adversarial.jsonl — 32 queries (hard negatives + citation override)
  challenge.jsonl — 10 queries (edge cases)
  coverage_boundary.jsonl — 10 queries (outside-scope)
  open_world.jsonl — 50 queries (unseen procurement queries)

The llm_vs_deterministic.json evaluation compares LLM-assisted vs
deterministic-only pipelines:
  - safe_decision_accuracy: 0.6 (both modes identical)
  - primary_recommendation_accuracy: 0.2791 (both modes identical)
  - safe_abstention_rate: 0.7143 (both modes identical)
  - avg_latency_ms: deterministic 344.81 vs LLM 609.85

ASSESSMENT

Positive:
- 44 test modules provide comprehensive coverage of all architectural layers
- test_agent_final_schema.py validates all 5 decision scenarios against schema
- test_adversarial_safety.py covers the critical uPVC + IS 1180 mismatch case
- test_agent_validator.py validates all 8 safety gates
- test_open_world_production_independence.py enforces zero benchmark leakage
- Separate evaluation artifacts per benchmark dataset enable targeted analysis
- llm_vs_deterministic.json provides explicit comparison of LLM vs deterministic
- Release manifest includes SHA256 verification for all artifacts

Concern:
- No performance/benchmark tests (no pytest-benchmark, no latency regression
  tests) — the ~345ms deterministic latency is measured but not guarded against
  regression
- test_agent_orchestration.py likely tests the happy path but needs verification
  that it covers all 9 pipeline stages, not just the common case
- The test suite does not appear to include chaos/failure injection tests for
  individual subsystem failures (e.g., regulator data file missing, graph
  corrupted, LLM returning malformed JSON with valid schema structure)
- 44 modules is a strong count but the coverage of edge cases (e.g.,
  contradictory requirements, multi-edition supersession chains,
  conditional QCO exemptions) needs verification from the test content

================================================================================
SECTION P — EVALUATION METRICS AND BENCHMARK ANALYSIS
================================================================================

The system produces evaluation artifacts for 7 benchmark datasets, with
comprehensive metrics including retrieval accuracy, decision accuracy,
safety metrics, calibration, and hard negative performance.

BENCHMARK METRICS SUMMARY

All metrics from data/evaluations/*.json and
data/evaluations/llm_vs_deterministic.json (50 open-world queries).

Test Set (13 queries — data/benchmarks/test.jsonl)
  RAW_RETRIEVAL_TOP1:       0.2308  (23% queries retrieve correct std at rank 1)
  candidate_recall_at_5:    0.3846  (38% have gold in top-5)
  VERIFIED_PRIMARY_TOP1:    0.1538  (15% verify correct primary)
  safe_abstention_rate:     1.0     (100% of queries result in abstention)
  unsafe_primary_promotion_rate:   0.615 (62% of abstention states still
                                            promote a primary)
  primary_recommendation_accuracy: 0.1538
  safe_decision_accuracy:     0.0769
  hard_negative_rejection_at_1: 1.0 (100% hard negs rejected at top-1)
  hard_negative_intrusion_at_5:  0.0 (no hard negs in top-5)
  ECE:                        0.2785
  Brier score:               0.2578

Open-World Benchmark (50 queries — data/benchmarks/open_world.jsonl)
  RAW_RETRIEVAL_TOP1:       0.2326
  candidate_recall_at_5:    0.34
  candidate_recall_at_10:   0.34
  safe_abstention_rate:     1.0
  safe_decision_accuracy:   0.6
  primary_recommendation_accuracy: 0.2791
  unsafe_primary_rate:      0.0

Adversarial Benchmark (32 queries — data/benchmarks/adversarial.jsonl)
  RAW_RETRIEVAL_TOP1:       0.0
  hnrr_at1 (hard neg rejection rate at 1): 0.9531
  hn_intrusion_rate_5:      0.0938
  hn_intrusion_rate_10:     0.0938
  mean_hn_rank:             2.333
  ECE:                      0.1446
  Brier score:              0.0837

Challenge Benchmark (10 queries — data/benchmarks/challenge.jsonl)
  RAW_RETRIEVAL_TOP1:       0.0
  safe_abstention_rate:     1.0
  outside_coverage_accuracy: 1.0
  unsupported_primary_promotion_rate: 1.0

LLM vs Deterministic Comparison (50 open-world queries)
  safe_decision_accuracy:        deterministic 0.6, LLM 0.6 (delta 0.0)
  primary_recommendation_accuracy: deterministic 0.2791, LLM 0.2791 (delta 0.0)
  safe_abstention_rate:           deterministic 0.7143, LLM 0.7143 (delta 0.0)
  avg_latency_ms:                 deterministic 344.81, LLM 609.85

METRIC DEFINITIONS

  RAW_RETRIEVAL_TOP1: Fraction of queries where the gold standard is
    at rank 1 of the raw BM25+Dense retrieval result (before reranking)

  VERIFIED_PRIMARY_TOP1: Fraction where the verified primary recommendation
    (after validation) matches the gold standard

  candidate_recall_at_k: Fraction of queries where the gold standard
    appears in the top-k candidates (after reranking)

  safe_abstention_rate: Fraction of queries where the system correctly
    abstains (does not promote an unsupported/incorrect primary)

  unsafe_primary_promotion_rate: Fraction of queries where the system
    promotes a primary recommendation that should not be promoted
    (the primary is wrong, unsupported, or from an abstention state)

  primary_recommendation_accuracy: Fraction of queries where the promoted
    primary recommendation matches the gold standard

  safe_decision_accuracy: Fraction of queries where the decision state
    (recommend vs abstain vs ambiguous) is correct per safety criteria

  hard_negative_rejection_rate (hnrr_at1): Fraction of hard negative
    candidates correctly rejected at rank 1 (not promoted to primary)

  hard_negative_intrusion_rate: Fraction of hard negatives that
    intrude into the top-k candidate set

  ECE (Expected Calibration Error): Measures calibration quality;
    0.0 = perfectly calibrated, higher = miscalibrated

  Brier Score: Mean squared error between predicted probabilities and
    actual outcomes; lower = better calibrated

  MRR (Mean Reciprocal Rank): Average reciprocal rank of gold standard
    across all queries

CRITICAL METRIC OBSERVATIONS

1. Retrieval Foundation Failure:
   RAW_RETRIEVAL_TOP1 of 0.23 means 77% of queries do not retrieve the
   correct standard at rank 1. This is the primary bottleneck — the
   reranker, applicability, and safety layers can only work on what
   retrieval surfaces.

2. Perfect Abstention Paradox:
   safe_abstention_rate = 1.0 on open-world means the system abstains
   on 100% of queries. However, unsafe_primary_promotion_rate = 0.615
   on the test set means when it DOES promote, it's wrong 61.5% of the
   time. This indicates the calibration layer errs heavily on the side
   of abstention, which is safe but not useful.

3. LLM Provides No Accuracy Lift:
   The LLM-assisted pipeline shows identical metrics to deterministic-only
   (all deltas = 0.0). The LLM does not improve accuracy but adds
   74% latency overhead (609.85ms vs 344.81ms). The LLM currently
   contributes only to natural-language explanation generation, not
   to the decision logic.

4. Hard Negative Safety:
   hnrr_at1 = 0.9531 on adversarial set indicates 95%+ hard negative
   rejection at top-1 — the safety gates effectively prevent known
   wrong answers from being promoted. This is the system's primary
   strength.

5. Calibration Crisis:
   ECE of 0.2785 (test) and 0.1446 (adversarial) indicates significant
   miscalibration. Combined with N=24 calibration samples (flagged
   CALIBRATION_INSUFFICIENT_DATA), the confidence thresholds are not
   statistically grounded.

6. MRR of 0.0192 (adversarial):
   Extremely poor ranking quality on adversarial benchmarks — the
   correct standard is not even in the top positions for the vast
   majority of adversarial queries.

7. Zero Challenge Performance:
   Challenge benchmark (10 edge case queries) shows 0.0 on all retrieval
   and primary accuracy metrics — the system fails on edge cases while
   correctly abstaining (1.0 safe_abstention, 1.0 outside_coverage).

ASSESSMENT

Positive:
- Comprehensive evaluation framework with 7 benchmark datasets
- Safety metrics (hard negative rejection, unsafe promotion rate)
  are industry-leading in design — the system correctly identifies
  when it should not recommend
- Calibration metrics (ECE, Brier score) are computed and tracked
- LLM vs deterministic comparison provides explicit evidence of
  whether LLM integration adds value

Critical Concern:
- Primary recommendation accuracy is 15-28% across benchmarks —
  far below production viability
- Retrieval is the bottleneck: 77% of queries fail to surface the
  correct standard at rank 1
- The system is overly conservative: 100% abstention on open-world
  makes it useless for actual procurement decisions
- Calibrator has N=24 samples — cannot make statistical claims
- LLM adds latency without accuracy improvement

================================================================================
SECTION Q — DATA COVERAGE AUDIT
================================================================================

The knowledge graph and supporting datasets form the knowledge/evidence layer
that underlies all recommendation decisions. This section audits data
completeness, hydration status, and coverage gaps.

KNOWLEDGE GRAPH (data/processed/standards_graph.json)

  Total nodes:    6,081
  Total edges:    5,428
  CED hydrated:   1,935
  ETD hydrated:   1,944
  Total hydrated: 3,879 (63.8% of all nodes)
  Unhydrated stubs: 2,202 (36.2% of all nodes)

Hydration status determines whether a node has verified scope text,
technical attributes, lifecycle data, and provenance. Unhydrated stubs
lack the evidence required for PRIMARY_RECOMMENDATION_CLAIM but remain
in the graph for discovery during graph expansion.

BENCHMARK DATASETS

  train.jsonl:             24 queries (training set for ranking models)
  test.jsonl:              13 queries (authoritative evaluation)
  val.jsonl:               13 queries (validation set)
  adversarial.jsonl:       32 queries (hard negatives + citation overrides)
  challenge.jsonl:         10 queries (edge cases and boundary conditions)
  coverage_boundary.jsonl: 10 queries (outside-prototype-coverage cases)
  open_world.jsonl:        50 queries (unseen real-world procurement queries)

  Benchmark tool usage (deterministic, open-world, 50 queries):
    search_standards:       48 calls (96% of queries)
    get_standard_evidence:  336 calls (avg 7 per query)
    check_applicability:    336 calls (avg 7 per query)
    check_lifecycle:        336 calls (avg 7 per query)
    check_regulatory:       336 calls (avg 7 per query)

REGULATORY DATASETS (data/regulatory/)

  qco_orders.jsonl:   12 records (QCO mandates)
  crs_rules.jsonl:     2 records (CRS rules)
  lifecycle_curated.json: Versioned lifecycle metadata (from release manifest)
  source_manifest.json: Gazette reference provenance, source consistency

  Regulatory coverage ratio: 14 QCO/CRS records for 3,879 hydrated standards
  → ~0.37% coverage of hydrated standards have verified regulatory mandates

  Knowledge graph artifact details:
    ced_hydrated: 1,935 nodes with verified scope + technical attributes
    etd_hydrated: 1,944 nodes with verified scope + technical attributes
    Total hydrated: 3,879 nodes

INPUT SOURCES

  CED input: data/input/Civil Engineering Department (CED).xlsx
    Input rows: 1,935
    Output JSONL: 1,935 records (100% row-to-record conversion)
    References JSONL: 3,253 records (normative cross-references)

  ETD input: data/input/Electrotechnical Department (ETD).xlsx
    Input rows: 1,944
    Output JSONL: 1,944 records (100% row-to-record conversion)
    References JSONL: 2,175 records (normative cross-references)

CALIBRATION DATA

  calibrator_v1.json: PlattScaler model with N=24 samples
  Status: CALIBRATION_INSUFFICIENT_DATA
  (data/models/calibrator_v1.json in standspec_prototype_release.json:86-91)

COVERAGE GAP ANALYSIS

1. Hydration Gap (36.2%):
   2,202 unhydrated stubs exist in the knowledge graph. These nodes
   lack scope text and technical attributes, making them unusable for
   primary recommendation. They serve as discovery targets during
   graph expansion but cannot satisfy EvidencePolicy requirements.

2. Regulatory Coverage Gap (~0.37%):
   Only 14 QCO/CRS records cover 3,879 hydrated standards. The vast
   majority of standards have regulatory_state =
   NOT_VERIFIED_IN_CURRENT_CORPUS, meaning the system cannot assert
   mandatory/compliance status for most standards.

3. Benchmark Coverage Gap:
   - Test set: 13 queries for 3,879 standards → ~0.34% coverage
   - Open world: 50 queries → 0.01% of total possible query space
   - Adversarial: 32 queries → targeted safety testing
   The evaluation benchmarks cover a tiny fraction of the knowledge base,
   making metrics susceptible to small-sample variance.

4. Cross-Reference Coverage:
   CED generates 3,253 reference records from 1,935 standards (avg 1.68
   references per standard). ETD generates 2,175 references from 1,944
   standards (avg 1.12 references per standard). Reference density is
   higher for CED (civil standards tend to reference more normative
   documents than electrotechnical standards).

5. Product Category Coverage:
   The knowledge graph contains standards from CED (Civil Engineering)
   and ETD (Electrotechnical) departments. No other BIS departments
   are represented. This limits applicability to construction and
   electrical procurement domains only.

ASSESSMENT

Positive:
- 100% input row-to-record conversion rate for both CED and ETD inputs
- Hydrated nodes have both scope text and technical attributes
- Cross-reference capture at 1.1-1.7x density supports graph expansion
- Benchmark diversity covers test, validation, train, adversarial,
  challenge, coverage_boundary, and open_world scenarios
- SHA256 verification for all artifacts in the release manifest
- Separate standards and references JSONL outputs enable provenance tracing

Concern:
- 36.2% unhydrated stub ratio is high — these nodes cannot be
  recommended and represent knowledge debt
- Regulatory coverage at ~0.37% makes most standards' regulatory
  status unverifiable — the regulatory gate returns NOT_VERIFIED_IN_CURRENT_CORPUS
  for 99.63% of standards, which propagates conservative abstention
- Benchmark coverage (~0.34% for test set) is insufficient for statistical
  claims about system behavior on unseen data
- Single-source dependency: the entire knowledge base derives from
  two Excel files (CED + ETD inputs) — any parsing error in those
  files propagates to all 3,879 hydrated standards
- The calibrator with N=24 is statistically insignificant for

================================================================================
SECTION R — SCALABILITY AND PERFORMANCE ASSESSMENT
================================================================================

The system is designed for hermetic, dependency-minimized execution.
Performance characteristics are analyzed from the evaluation metrics
and architectural design.

CONCURRENCY MODEL

The StandSpecAgent processes queries sequentially. Each call to
agent.answer() executes the full 9-step pipeline synchronously:
  - Extraction (Phase P1-A)
  - Search (Steps 1-5)
  - Evidence gathering (Step 6, O(7 candidates × 4 tool calls))
  - Reasoning + Proposal (Step 7)
  - Validation (Step 8)
  - Optional Revision (Step 9)

No internal batching or concurrent tool invocation is present.
For 7 top candidates, the system makes 28 tool calls (7 × 4 tool types)
in a strictly sequential loop (agent.py:206-238).

PERFORMANCE METRICS

From llm_vs_deterministic.json (50 open-world queries):
  Deterministic-only average latency: 344.81 ms/query
  LLM-assisted average latency:      609.85 ms/query
  Tool calls per query (avg):        48/50 queries perform search_standards
  Tool calls per query (avg):        336/50 = 6.72 calls each for evidence,
                                    applicability, lifecycle, regulatory
  Average steps per query:           3.88

  Total tool calls (deterministic, 50 queries):
    search_standards:       48
    get_standard_evidence:  336
    check_applicability:    336
    check_lifecycle:        336
    check_regulatory:       336
    Total: 1,492 tool calls across 50 queries = ~30 tool calls/query

BOTTLENECK ANALYSIS

1. Sequential Tool Execution (agent.py:206-238):
   The deep candidate verification loop (Steps 6a-6d: evidence, applicability,
   lifecycle, regulatory) is fully sequential per candidate. For 7 candidates,
   this is 28 sequential tool calls. These could be parallelized since they
   are read-only lookups against the knowledge graph — no data dependency
   between get_standard_evidence(desig_1) and get_standard_evidence(desig_2).

2. Graph Expansion Overhead:
   GraphCandidateExpander.expand() traverses knowledge graph edges and
   expands candidates to 4x the input count. With Whoosh BM25 returning
   25 candidates and dense retrieval returning 25, RRF produces 20 fused,
   graph expansion produces up to 80 candidates before reranking.
   The reranker then scores all 80 candidates through 12 feature extractors
   — this is 960 feature evaluations per query.

3. LLM Latency (609.85ms vs 344.81ms):
   The LLM adds ~265ms per query for structured extraction and proposal
   generation. Since LLM provides no accuracy lift (all metrics delta=0.0),
   this is pure overhead in the current configuration.

4. Calibrator Loading:
   SelectiveAbstentionPolicy loads PlattScaler from data/models/calibrator_v1.json
   at construction time. If this file were larger or the calibration
   computation more complex, it would add per-query overhead.

5. Whoosh Index:
   BM25 retriever uses Whoosh (pure-Python search engine). Whoosh builds
   the index at engine initialization from the knowledge graph nodes.
   For 3,879 hydrated candidates, index build time is included in the
   344.81ms but is amortized across queries in production (index built once
   at startup, not per query).

MEMORY CHARACTERISTICS

  Knowledge graph: ~6,081 nodes with edge data — fits in memory
    (JSON file size likely < 50MB based on node count)
  Whoosh index:     Built from ~3,879 hydrated candidates
  BM25 index size:  In-memory, per-engine instance
  No LRU caching or query result memoization is implemented
  Each query rebuilds the full pipeline state from scratch

SCALABILITY LIMITATIONS

1. Single-query sequential execution: No request batching, no async/await,
   no thread pool for parallel tool invocation. Scaling requires vertical
   scaling (more powerful machine) or horizontal scaling (multiple agent
   instances behind a load balancer with no shared state).

2. No caching layer: Tool results (applicability, lifecycle, regulatory)
   are recomputed for every query, even for the same standard designation.
   A cache for check_applicability/desig would reduce redundant computation
   in high-throughput scenarios.

3. Model loading: NeuralCrossEncoderReranker attempts to load
   cross-encoder/ms-marco-MiniLM-L-6-v2 at construction time. This model
   download and load happens once per agent instance but adds startup
   latency. The default production mode uses rule_based reranker (no model).

4. Graph expansion 4x multiplier: With 20 RRF-fused candidates, graph
   expansion produces up to 80 candidates. If the graph grows (e.g., to
   10,000+ nodes), expansion could produce 400+ candidates, significantly
   increasing reranker compute.

5. Calibration data: N=24 means the PlattScaler parameters are essentially
   noise. At scale, the system would need 1,000+ labeled examples to
   produce trustworthy calibrated probabilities.

ASSESSMENT

Positive:
- Hermetic design (pure-Python Whoosh, deterministic semantic projection)
  eliminates external service dependencies
- Per-query metrics are instrumented and available in evaluation artifacts
- Sequential execution is deterministic — no race conditions or state leakage
- Engine.from_release() loads from versioned artifacts — reproducible behavior
- MAX_AGENT_STEPS bound prevents runaway execution

Concern:
- Sequential tool calls for 7 candidates × 4 tools = 28 sequential lookups
  per query — this is the dominant latency contributor after retrieval
- No result caching — same standard lookups repeat across queries
- No horizontal concurrency model — cannot scale by adding parallel workers
- LLM adds 77% latency with 0% accuracy improvement — should be disabled
  or replaced with a cheaper explanation generator
- Graph expansion 4x multiplier with O(n) reranking (12 features × n candidates)
  is O(n) but with a high constant factor
- N=24 calibration samples make the selective abstention policy statistically
  unreliable — thresholds are effectively hand-tuned, not data-calibrated

  calibrating a system with 3,879 candidate standards

================================================================================
SECTION S — RECOMMENDATIONS AND ROADMAP
================================================================================

This section presents a prioritized roadmap for addressing the critical
performance gaps identified in this review while preserving the excellent
safety architecture.

PRIORITY 1: RETRIEVAL FOUNDATION (CRITICAL — Blocks all downstream accuracy)

The retrieval layer is the root cause of poor accuracy: 77% of queries fail
to retrieve the correct standard at rank 1. No amount of reranking,
applicability filtering, or safety validation can recover a correct answer
that was never retrieved.

R1.1: Replace the permissive 0.005 retrieval_score threshold (agent.py:187)
      with a configurable value derived from benchmark analysis. The current
      threshold is so low that virtually any candidate triggers a second
      search round, adding latency without improving recall.

R1.2: Expand the knowledge graph from 1,935+1,944 = 3,879 hydrated nodes
      to cover the full BIS catalog for CED and ETD domains. The current
      63.8% hydration rate means 2,202 stubs are unusable. Prioritize
      hydration of high-frequency procurement categories (cables, pipes,
      transformers, meters).

R1.3: Investigate the focused_query construction (engine.py:534-536).
      The query enrichment may be over-filtering:
        focused_query = "{target_product} {material} {application} {acronyms}"
      If target_product extraction fails, the focused_query becomes too
      generic, hurting BM25 recall. Add fallback to include raw_text terms
      in BM25 indexing.

R1.4: Replace DeterministicSemanticProjection with true neural embeddings
      (sentence-transformers MiniLM) in production. The hybrid_deterministic
      mode uses a lightweight projection that sacrifices semantic matching
      quality for hermeticity. Production deployment should use real embeddings
      with on-disk model caching.

PRIORITY 2: CALIBRATION AND SELECTIVE ABSTENTION (HIGH — Overly conservative)

R2.1: Expand calibration sample pool from N=24 to N≥1,000 before making
      any statistical claims about confidence thresholds. The current
      calibrator is flagged CALIBRATION_INSUFFICIENT_DATA and should
      not be trusted for production decisions.

R2.2: Lower tau_recommend from 0.55 to 0.40 temporarily, backed by
      empirical calibration data, to reduce the 100% safe_abstention_rate
      that makes the system non-functional for procurement decisions.

R2.3: Implement risk-coverage curve-based threshold selection:
      Use compute_risk_coverage() to find the threshold where safe_decision
      accuracy ≥ 0.95 while maximizing coverage. Document the selected
      operating point.

PRIORITY 3: PARALLEL TOOL EXECUTION (MEDIUM — Latency optimization)

R3.1: Parallelize the deep candidate verification loop (agent.py:206-238).
      The 4 tool calls per candidate (get_standard_evidence, check_applicability,
      check_lifecycle, check_regulatory) are read-only and have no data
      dependency between different designations. Use asyncio or ThreadPoolExecutor
      to batch these 28 calls per query. Expected latency reduction: 60-70%.

R3.2: Implement result caching for check_applicability, check_lifecycle,
      and check_regulatory. These are pure functions of (designation,
      requirements) — cache results keyed by designation to avoid
      recomputation across queries for the same standard.

PRIORITY 4: LLM INTEGRATION (MEDIUM — Accuracy optimization)

R4.1: The LLM currently provides 0% accuracy lift (all deltas = 0.0)
      while adding 77% latency. Either:
        (a) Remove LLM from the decision pipeline entirely and keep it
            only for explanation generation (explanation.py), OR
        (b) Redesign LLM integration to contribute to retrieval ranking
            (e.g., LLM-generated query reformulations for BM25), not just
            fallback extraction.

R4.2: If keeping LLM in the pipeline, add per-domain fine-tuning with
      chain-of-thought examples for the 13 training queries + additional
      labeled data. The current LLM does not outperform deterministic
      extraction.

PRIORITY 5: HYDRATION AND DATA COMPLETENESS (HIGH — Coverage)

R5.1: Establish a hydration pipeline that processes unhydrated stubs
      (2,202 nodes = 36.2% of graph). Each stub needs scope text
      extraction from the source Excel files and technical attribute
      population. Target: 95%+ hydration rate within 6 months.

R5.2: Expand regulatory dataset from 14 QCO/CRS records to cover the
      full CED/ETD catalog. The current 0.37% regulatory coverage means
      99.63% of standards cannot assert regulatory mandate status, which
      propagates conservative abstention.

PRIORITY 6: TESTING AND BENCHMARK EXPANSION (MEDIUM — Validation rigor)

R6.1: Expand the test set from 13 to ≥200 queries to enable statistical
      claims about system performance. The current 13-query test set
      produces metrics with wide confidence intervals (±17% for binary
      accuracy at N=13, 95% CI).

R6.2: Add performance regression tests using pytest-benchmark to guard
      against latency regressions. The ~345ms deterministic baseline
      should be protected by automated benchmarks.

R6.3: Add chaos/failure injection tests for subsystem failures:
        - Regulator data file missing → must fail-closed
        - Knowledge graph corrupted → must return appropriate error
        - LLM returns malformed JSON with valid schema → span verification
          must catch hallucinated values

RISK MITIGATION ROADMAP

Immediate (0-2 months):
  - Implement R1.1 (configurable retrieval threshold)
  - Implement R3.1 (parallel tool execution) — highest ROI latency fix
  - Begin R5.1 (hydration pipeline) — addresses 36% unused graph nodes

Short-term (2-6 months):
  - Complete R5.1 (full hydration) — addresses root cause of poor recall
  - Implement R2.1-R2.3 (calibration expansion + threshold tuning)
  - Begin R5.2 (regulatory dataset expansion)
  - Implement R6.1 (test set expansion to 200+ queries)

Medium-term (6-12 months):
  - Complete R5.2 (full regulatory QCO/CRS coverage)
  - Implement R6.2-R6.3 (benchmark + chaos testing)
  - Execute R4.1 or R4.2 (LLM redesign or removal)
  - Implement R1.4 (production neural embeddings with caching)

ARCHITECTURAL STRENGTHS TO PRESERVE

  - Defense-in-depth safety architecture (4-layer stack) — DO NOT WEAKENEN
  - Deterministic validator with absolute veto — maintain as final gate
  - EvidencePolicy with 6-dimensional readiness — keep mandatory grounding
  - OpenWorldQuery benchmark isolation contract — critical for unbiased eval
  - Verbatim span verification for LLM extraction — prevents hallucinations

The safety architecture is production-grade. The accuracy pipeline needs
retrieval and ranking improvements. The calibration layer is not yet
production-ready (insufficient samples).

================================================================================
END OF REPORT
================================================================================


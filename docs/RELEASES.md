# StandSpec AI — Release History & Version Policy
## Phase P1-D: Release Lineage & Governance

---

## 1. Versioning Scheme

StandSpec AI adheres to semantic versioning with decoupled component identifiers declared authoritatively in `src/version.py`:

- **Core Engine Version** (`ENGINE_VERSION`): `2.0.0-phase-d`
- **Release ID** (`RELEASE_ID`): `STANDSPEC_PROTOTYPE_CED_ETD_V2_0_0_PHASE_D`
- **Collector & Parser Versions**: `1.2.1`
- **Schema Contracts**: Version 2.1 across graph, recommendation result, and benchmark schemas; Version 1.1 for regulatory sources.

---

## 2. Release Lineage & Milestone History

### Phase P1-D: Trust Gate Integrity + Adversarial Verification + Repository Finalization
- **Authoritative EvidenceBundle**: Sole authority for recommendation readiness; blocks unverified candidates and requires positive product grounding (`PRODUCT != UNKNOWN`).
- **Explicit Designation Bug Resolution**: Fixed explicit designation override bug (`"Supply of uPVC pipes as per IS 1180 Part 1"` now results in `primary_recommendation = null`, `decision_state = NO_CONFIDENT_MATCH`).
- **Decoupled Reranking Features & Scoring Policy**: 12 modular feature extractors producing structured explainability signals.
- **Transparent Mode Reporting**: Explicit fallback metadata (`effective_mode = RULE_BASED_FALLBACK`, `effective_mode = HASHED_FALLBACK`) when offline.
- **Unified Evaluation Library**: Standardized top-1 calculation (`RAW_RETRIEVAL_TOP1`, `EFFECTIVE_CANDIDATE_TOP1`, `VERIFIED_PRIMARY_TOP1`).
- **Comprehensive Benchmarks**: `adversarial.jsonl` (32 queries covering HN1–HN8), `coverage_boundary.jsonl` (10 out-of-domain queries), `challenge.jsonl` (10 complex queries).
- **Regulatory Manifest Consistency**: Required `source_id` referencing `data/regulatory/source_manifest.json`, with fail-closed consistency validator.
- **Bounded LLM Integration**: Strict verbatim character-span verification and anti-hallucination explainer with null-primary safety guarantee.

### Phase P1-C: Foundation Hardening & Evaluation Metrics
- Ground truth schema tiering (Tiers 1, 2, 3).
- Platt scaling calibrator with sample-size qualification (minimum 100 samples).
- Two-tier recommendation output (`primary_recommendation` vs `review_candidate`).

### Phase P1-B: Decision Core & Role Classification
- Standard role persistence in graph nodes (`PRIMARY_PRODUCT`, `AUXILIARY_COMPONENT`, `TEST_METHOD`, `DESIGN_CODE`, `MATERIAL_SPECIFICATION`, `UNKNOWN_ROLE`).
- Date-aware temporal lifecycle gate and supersession resolution.

### Phase P1-A: Exact Designation Intent & Retrieval Foundation
- Dual-channel hybrid retrieval (BM25 + Dense Semantic Projection) with RRF fusion.
- Query sufficiency and contradiction detection.

---

## 3. Release Manifest

The authoritative release manifest is at `data/manifests/standspec_prototype_release.json`.
Generated and validated via:

```bash
python scripts/generate_release_manifest.py --check
```

The manifest records:
- SHA-256 digests of all datasets, knowledge graph, calibrators, and evaluation runs.
- Machine-calculated evaluation metrics from `data/evaluations/test_evaluation.json`.
- Complete record counts and department ingestion summaries.

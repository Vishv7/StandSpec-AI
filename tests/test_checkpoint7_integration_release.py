"""
Regression Tests for Checkpoint 7: Integration / Release Manifest
PS 26108 Phases 16-17.

Phase 16: Integration Testing (cross-checkpoint verification)
Phase 17: Release Manifest (system integrity check)
"""

import pytest
from src.evaluation.system_integrity import (
    run_integrity_check,
    generate_component_registry,
    IntegrityReport,
    IntegrityCheck,
    CHECKPOINT_MODULES,
    CORE_MODULES,
)


# ============================================================================
# Phase 16: Cross-Checkpoint Integration Tests
# ============================================================================

class TestCrossCheckpointIntegration:
    """
    Integration tests verifying contracts between checkpoint modules.
    Each test exercises a cross-module data flow.
    """

    def test_cp1_evidence_state_used_by_cp4_decision_machine(self):
        """CP1 EvidenceState → CP4 DecisionState contract."""
        from src.recommendation.evidence_bundle import EvidencePolicy, ClaimType
        from src.recommendation.decision_state_machine import DecisionState, get_claim_level

        # EvidencePolicy claim types must map to decision states
        claim = ClaimType.REVIEW_CANDIDATE_CLAIM
        assert claim.value == "REVIEW_CANDIDATE_CLAIM"

        # Decision state for review must return REVIEW_REQUIRED claim
        level = get_claim_level("EXPERT_REVIEW_REQUIRED")
        assert level == "REVIEW_REQUIRED"

    def test_cp2_material_taxonomy_used_by_cp3_error_labels(self):
        """CP2 material concepts → CP3 error taxonomy integration."""
        from src.recommendation.applicability.material_concepts import MaterialFamily
        from src.evaluation.error_taxonomy import ErrorLabel

        # Material family mismatch label must exist
        assert hasattr(ErrorLabel, "MATERIAL_FAMILY_MISMATCH")
        assert hasattr(ErrorLabel, "PRODUCT_FAMILY_MISMATCH")

        # Material families must be defined
        assert MaterialFamily.FERROUS_METAL is not None
        assert MaterialFamily.NON_FERROUS_METAL is not None

    def test_cp3_fusion_metadata_compatible_with_cp4_explanation(self):
        """CP3 fusion metadata → CP4 explanation templates compatibility."""
        from src.retrieval.fusion import reciprocal_rank_fusion, FusionAgreement
        from src.recommendation.explanation_templates import generate_explanation

        # RRF produces fusion metadata
        bm25 = [{"designation": "IS 4984", "title": "HDPE", "score": 25.0}]
        dense = [{"designation": "IS 4984", "title": "HDPE", "score": 0.95}]
        fused = reciprocal_rank_fusion({"bm25": bm25, "dense": dense}, k=60)
        assert fused[0]["retrieval_metadata"]["retrieval_agreement"] == FusionAgreement.STRONG

        # Explanation templates can consume the fused output
        result = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": {
                "standard_designation": "IS 4984:2016",
                "title": "HDPE Pipes",
                "calibrated_confidence": 0.82,
                "applicability": {"matched_attributes": ["product"]},
                "regulatory": {},
                "lifecycle": {},
            },
        }
        exp = generate_explanation(result)
        assert exp.standard_designation == "IS 4984:2016"

    def test_cp4_decision_state_used_by_cp5_safety_invariants(self):
        """CP4 decision states → CP5 safety invariants contract."""
        from src.recommendation.decision_state_machine import DecisionState
        from src.agent.safety_invariants import check_abstention_honesty

        # All abstention states must be caught by safety invariants
        abstention_states = [
            DecisionState.NO_CONFIDENT_MATCH,
            DecisionState.INSUFFICIENT_INFORMATION,
            DecisionState.OUTSIDE_PROTOTYPE_COVERAGE,
            DecisionState.CONTRADICTORY_SPECIFICATIONS,
        ]

        for state in abstention_states:
            response = {
                "decision_state": state.value,
                "primary_recommendation": {"standard_designation": "IS 4984"},
            }
            violations = check_abstention_honesty(response)
            assert len(violations) > 0, f"Abstention state {state.value} with primary should violate INV-5"

    def test_cp5_multilingual_normalizer_feeds_extraction(self):
        """CP5 multilingual normalizer → extraction pipeline compatibility."""
        from src.extraction.multilingual_normalizer import normalize_multilingual_query
        from src.extraction.normalizer import normalize_material

        # Hindi query normalized to English
        result = normalize_multilingual_query("एचडीपीई पाइप")
        assert "HDPE" in result.normalized_text

        # Normalized text can be consumed by material normalizer
        mat = normalize_material(result.normalized_text)
        assert mat is not None
        assert "HDPE" in mat or "Polyethylene" in mat

    def test_cp6_benchmark_validator_validates_cp4_metrics_format(self):
        """CP6 benchmark validator → CP4 metrics format compatibility."""
        from src.evaluation.benchmark_validator import validate_benchmark_results
        from src.evaluation.metrics import compute_comprehensive_metrics

        # Simulate a mini-benchmark
        queries = [
            {"gold_standards": [{"standard_designation": "IS 4984:2016"}]},
        ]
        outputs = [
            {
                "primary_recommendation": {"standard_designation": "IS 4984:2016"},
                "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
                "candidate_recommendations": [{"standard_designation": "IS 4984:2016"}],
            },
        ]
        metrics = compute_comprehensive_metrics(queries, outputs)

        # Benchmark validator should work on the metrics format
        result = validate_benchmark_results(metrics, total_queries=1)
        assert result.is_valid is True

    def test_cp1_to_cp4_evidence_to_explanation_pipeline(self):
        """Full pipeline: CP1 evidence → CP4 explanation."""
        from src.recommendation.evidence_bundle import EvidenceBundle, EvidencePolicy, ClaimType
        from src.recommendation.explanation_templates import generate_explanation

        # Build evidence bundle (CP1)
        bundle = EvidenceBundle(
            designation="IS 4984:2016",
            title="HDPE Pipes for Potable Water Supply",
        )

        # Generate explanation (CP4)
        result = {
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "primary_recommendation": {
                "standard_designation": "IS 4984:2016",
                "title": "HDPE Pipes",
                "calibrated_confidence": 0.82,
                "applicability": {"matched_attributes": ["product", "material"]},
                "regulatory": {"regulatory_state": "VOLUNTARY"},
                "lifecycle": {"recommended_edition": "2016"},
            },
        }
        exp = generate_explanation(result)
        assert exp.claim_level == "VERIFIED_FOR_RECOMMENDATION"
        assert exp.confidence_pct == 82.0
        assert len(exp.evidence_points) > 0

    def test_all_checkpoint_modules_importable(self):
        """Verify all modules from all checkpoints can be imported."""
        import importlib
        failures = []
        for cp_id, cp_info in CHECKPOINT_MODULES.items():
            for mod_path in cp_info["modules"]:
                try:
                    importlib.import_module(mod_path)
                except Exception as e:
                    failures.append(f"{mod_path}: {e}")

        assert len(failures) == 0, f"Import failures: {failures}"


# ============================================================================
# Phase 17: System Integrity Check
# ============================================================================

class TestSystemIntegrityCheck:
    """Tests for the system integrity checker."""

    def test_integrity_check_passes(self):
        """Full integrity check must pass on current codebase."""
        report = run_integrity_check()
        assert report.total > 0
        assert report.failed == 0, (
            f"Integrity check failed with {report.failed} failures: "
            + "; ".join(c.message for c in report.checks if c.status == "FAIL")
        )
        assert report.is_release_ready is True

    def test_integrity_report_has_version(self):
        report = run_integrity_check()
        version_checks = [c for c in report.checks if c.check_id == "VERSION-ENGINE"]
        assert len(version_checks) > 0
        assert version_checks[0].status == "PASS"
        assert "3.0.0" in version_checks[0].message

    def test_integrity_report_has_decision_contract(self):
        report = run_integrity_check()
        contract_checks = [c for c in report.checks if c.check_id == "CONTRACT-DECISION"]
        assert len(contract_checks) > 0
        assert contract_checks[0].status == "PASS"

    def test_integrity_report_has_taxonomy(self):
        report = run_integrity_check()
        taxonomy_checks = [c for c in report.checks if c.check_id == "TAXONOMY-PHASE7"]
        assert len(taxonomy_checks) > 0
        assert taxonomy_checks[0].status == "PASS"

    def test_integrity_report_has_template_coverage(self):
        report = run_integrity_check()
        template_checks = [c for c in report.checks if c.check_id == "TEMPLATE-COVERAGE"]
        assert len(template_checks) == 8  # 8 decision states
        assert all(c.status == "PASS" for c in template_checks)

    def test_integrity_report_serializable(self):
        report = run_integrity_check()
        d = report.to_dict()
        assert "total_checks" in d
        assert "is_release_ready" in d
        assert isinstance(d["checks"], list)

    def test_integrity_check_result_structure(self):
        """IntegrityReport data structures work correctly."""
        report = IntegrityReport()
        report.add(IntegrityCheck(
            check_id="TEST",
            component="test",
            status="PASS",
            message="Test passed",
        ))
        assert report.total == 1
        assert report.passed == 1

        report.add(IntegrityCheck(
            check_id="TEST-FAIL",
            component="test",
            status="FAIL",
            message="Test failed",
        ))
        assert report.total == 2
        assert report.failed == 1


class TestComponentRegistry:
    """Tests for component registry generation."""

    def test_registry_has_all_checkpoints(self):
        registry = generate_component_registry()
        assert "checkpoints" in registry
        assert "CP1" in registry["checkpoints"]
        assert "CP2" in registry["checkpoints"]
        assert "CP3" in registry["checkpoints"]
        assert "CP4" in registry["checkpoints"]
        assert "CP5" in registry["checkpoints"]
        assert "CP6" in registry["checkpoints"]

    def test_registry_modules_importable(self):
        registry = generate_component_registry()
        for cp_id, cp_info in registry["checkpoints"].items():
            for mod in cp_info["modules"]:
                assert mod["importable"] is True, \
                    f"Module {mod['module']} in {cp_id} not importable"

    def test_registry_has_exports(self):
        registry = generate_component_registry()
        # At least some modules should have exports
        has_exports = False
        for cp_id, cp_info in registry["checkpoints"].items():
            for mod in cp_info["modules"]:
                if mod.get("exports"):
                    has_exports = True
                    break
        assert has_exports

    def test_registry_timestamp(self):
        registry = generate_component_registry()
        assert "generated_at" in registry
        assert len(registry["generated_at"]) > 0


class TestVersionConsistency:
    """Tests for version token consistency."""

    def test_engine_version_format(self):
        from src.version import ENGINE_VERSION
        parts = ENGINE_VERSION.split(".")
        assert len(parts) == 3  # SemVer: MAJOR.MINOR.PATCH
        assert all(p.isdigit() for p in parts)

    def test_release_id_contains_version(self):
        from src.version import ENGINE_VERSION, RELEASE_ID
        version_digits = ENGINE_VERSION.replace(".", "_")
        assert version_digits in RELEASE_ID.replace(".", "_")

    def test_all_version_tokens_present(self):
        from src.version import (
            ENGINE_VERSION, RELEASE_ID, COLLECTOR_VERSION,
            FORMAT_VERSION, SCHEMA_VERSION, EVALUATOR_VERSION,
        )
        assert ENGINE_VERSION
        assert RELEASE_ID
        assert COLLECTOR_VERSION
        assert FORMAT_VERSION
        assert SCHEMA_VERSION
        assert EVALUATOR_VERSION

    def test_schema_versions_are_semver_or_dotted(self):
        from src.version import (
            FORMAT_VERSION, SCHEMA_VERSION, COLLECTOR_SCHEMA_VERSION,
            GRAPH_SCHEMA_VERSION, RECOMMENDATION_RESULT_SCHEMA_VERSION,
        )
        for v in [FORMAT_VERSION, SCHEMA_VERSION, COLLECTOR_SCHEMA_VERSION,
                   GRAPH_SCHEMA_VERSION, RECOMMENDATION_RESULT_SCHEMA_VERSION]:
            parts = v.split(".")
            assert len(parts) >= 2, f"Version {v} should be dotted"

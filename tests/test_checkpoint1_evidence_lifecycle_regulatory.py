"""
Regression Tests for Checkpoint 1: Evidence + Lifecycle + Regulatory Truth
PS 26108 Phases 1-3.

Phase 1: Evidence State Semantics
Phase 2: Lifecycle Gate Fix (B1 + B2)
Phase 3: Regulatory Semantics Fix
"""

import pytest
from src.recommendation.evidence_bundle import (
    EvidenceBundle,
    EvidenceItem,
    EvidencePolicy,
    EvidenceState,
    ClaimType,
    EvidenceGapCode,
)
from src.recommendation.lifecycle_gate import (
    LifecycleGate,
    LifecycleState,
    StandardEdition,
)
from src.recommendation.regulatory_gate import RegulatoryState
from src.evaluation.metrics import compute_safety_metrics


# ============================================================================
# Phase 1: Evidence State Semantics
# ============================================================================

class TestEvidenceStateEnum:
    """Tests that EvidenceState enum exists and has all required states."""

    def test_evidence_state_has_all_values(self):
        assert EvidenceState.VERIFIED == "VERIFIED"
        assert EvidenceState.PARTIAL == "PARTIAL"
        assert EvidenceState.INFERRED == "INFERRED"
        assert EvidenceState.NOT_VERIFIED == "NOT_VERIFIED"
        assert EvidenceState.UNAVAILABLE == "UNAVAILABLE"
        assert EvidenceState.CONFLICTING == "CONFLICTING"

    def test_claim_type_has_review_candidate(self):
        """REVIEW_CANDIDATE_CLAIM must exist as a claim level."""
        assert ClaimType.REVIEW_CANDIDATE_CLAIM == "REVIEW_CANDIDATE_CLAIM"

    def test_evidence_gap_codes_include_lifecycle_inferred(self):
        """New gap code for inferred-but-not-verified lifecycle."""
        assert EvidenceGapCode.LIFECYCLE_INFERRED_NOT_VERIFIED == "LIFECYCLE_INFERRED_NOT_VERIFIED"

    def test_evidence_gap_codes_include_regulatory_domain(self):
        """New gap code for regulatory domain not in corpus."""
        assert EvidenceGapCode.REGULATORY_DOMAIN_NOT_IN_CORPUS == "REGULATORY_DOMAIN_NOT_IN_CORPUS"


class TestEvidencePolicyGuards:
    """Tests that EvidencePolicy enforces absence-of-evidence guards."""

    def _make_bundle(self, lifecycle_ev_status="VERIFIED", lifecycle_status="VERIFIED_ACTIVE",
                     scope="This is a test scope that meets the minimum 20 character requirement",
                     department="CED", role="PRODUCT_STANDARD", hydrated=True):
        b = EvidenceBundle(
            designation="IS 4984:1995",
            title="Test Standard for HDPE Pipes",
            department=department,
            base_number=4984,
            standard_role=role,
        )
        if scope:
            b.raw_scope = scope
            b.scope_evidence_items.append(EvidenceItem(
                source_type="TEST", source_id="IS 4984:1995",
                field="scope", evidence_text=scope[:200],
            ))
        b.lifecycle_evidence = {
            "status": lifecycle_status,
            "lifecycle_state": lifecycle_status,
            "lifecycle_evidence_status": lifecycle_ev_status,
            "is_superseded": False,
            "is_valid_on_date": True,
        }
        b.provenance_metadata = {
            "source_type": "BIS_PORTAL_EXCEL",
            "source_id": "IS 4984:1995",
            "is_hydrated": hydrated,
        }
        return b

    def test_inferred_lifecycle_blocks_primary_recommendation(self):
        """PS §5: INFERRED lifecycle MUST NOT satisfy PRIMARY_RECOMMENDATION."""
        bundle = self._make_bundle(lifecycle_ev_status="INFERRED", lifecycle_status="VERIFIED_ACTIVE")
        context = {"matched_attributes": ["PRODUCT"], "target_product": "HDPE pipe"}
        satisfied, gaps = EvidencePolicy.evaluate_claim(
            ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle, context=context
        )
        # Must NOT be ready for primary recommendation with only inferred lifecycle
        assert not satisfied, "INFERRED lifecycle should block PRIMARY_RECOMMENDATION"
        inferred_gaps = [g for g in gaps if "LIFECYCLE" in g or "INFERRED" in g]
        assert len(inferred_gaps) > 0, "Must have lifecycle-related gap"

    def test_verified_lifecycle_allows_primary_recommendation(self):
        """Verified lifecycle should allow primary recommendation (when all other evidence is present)."""
        bundle = self._make_bundle(lifecycle_ev_status="VERIFIED", lifecycle_status="VERIFIED_ACTIVE")
        context = {"matched_attributes": ["PRODUCT"], "target_product": "HDPE pipe"}
        satisfied, gaps = EvidencePolicy.evaluate_claim(
            ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle, context=context
        )
        assert satisfied, f"Fully verified bundle should satisfy PRIMARY_RECOMMENDATION. Gaps: {gaps}"

    def test_missing_scope_blocks_primary(self):
        """Missing scope MUST NOT be interpreted as generic scope."""
        bundle = self._make_bundle(scope=None)
        context = {"matched_attributes": ["PRODUCT"], "target_product": "HDPE pipe"}
        satisfied, gaps = EvidencePolicy.evaluate_claim(
            ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle, context=context
        )
        assert not satisfied
        assert EvidenceGapCode.SCOPE_MISSING.value in gaps

    def test_missing_applicability_not_assumed_applicable(self):
        """Missing applicability evidence MUST NOT become APPLICABLE."""
        bundle = self._make_bundle(scope=None)  # No scope → no applicability
        context = {"matched_attributes": [], "target_product": "HDPE pipe"}
        satisfied, gaps = EvidencePolicy.evaluate_claim(
            ClaimType.PRIMARY_RECOMMENDATION_CLAIM, bundle, context=context
        )
        assert not satisfied
        # Should have scope or applicability gaps
        has_scope_or_app_gap = any(
            g in (EvidenceGapCode.SCOPE_MISSING.value, EvidenceGapCode.APPLICABILITY_EVIDENCE_MISSING.value)
            for g in gaps
        )
        assert has_scope_or_app_gap

    def test_lifecycle_ready_rejects_inferred(self):
        """lifecycle_ready property must return False when evidence is INFERRED."""
        bundle = self._make_bundle(lifecycle_ev_status="INFERRED", lifecycle_status="VERIFIED_ACTIVE")
        assert not bundle.lifecycle_ready, "INFERRED lifecycle must not be ready"

    def test_lifecycle_ready_accepts_verified(self):
        """lifecycle_ready property must return True when evidence is VERIFIED."""
        bundle = self._make_bundle(lifecycle_ev_status="VERIFIED", lifecycle_status="VERIFIED_ACTIVE")
        assert bundle.lifecycle_ready, "VERIFIED lifecycle must be ready"

    def test_review_candidate_claim_requires_identity(self):
        """REVIEW_CANDIDATE_CLAIM requires identity."""
        bundle = EvidenceBundle(designation="", title="", standard_role="PRODUCT_STANDARD")
        satisfied, gaps = EvidencePolicy.evaluate_claim(ClaimType.REVIEW_CANDIDATE_CLAIM, bundle)
        assert not satisfied
        assert EvidenceGapCode.IDENTITY_UNVERIFIED.value in gaps

    def test_review_candidate_claim_passes_with_scope(self):
        """REVIEW_CANDIDATE_CLAIM passes with identity + scope."""
        bundle = self._make_bundle()
        satisfied, gaps = EvidencePolicy.evaluate_claim(ClaimType.REVIEW_CANDIDATE_CLAIM, bundle)
        assert satisfied

    def test_review_candidate_claim_passes_with_product_match(self):
        """REVIEW_CANDIDATE_CLAIM passes with identity + product match (even without scope)."""
        bundle = self._make_bundle(scope=None)
        context = {"matched_attributes": ["PRODUCT"]}
        satisfied, gaps = EvidencePolicy.evaluate_claim(
            ClaimType.REVIEW_CANDIDATE_CLAIM, bundle, context=context
        )
        assert satisfied


# ============================================================================
# Phase 2: Lifecycle Gate Fix (B1 + B2)
# ============================================================================

class TestLifecycleGateB1:
    """Fix B1: Missing lifecycle must not default to ACTIVE."""

    def test_standard_edition_default_is_lifecycle_unverified(self):
        """StandardEdition default lifecycle_status must be LIFECYCLE_UNVERIFIED, not ACTIVE."""
        edition = StandardEdition(designation="IS 999:2020", year=2020)
        assert edition.lifecycle_status == "LIFECYCLE_UNVERIFIED"

    def test_missing_lifecycle_in_graph_becomes_unverified(self):
        """A node with no lifecycle_status in the graph must become LIFECYCLE_UNVERIFIED."""
        graph = {
            "nodes": [
                {
                    "designation": "IS 999:2020",
                    "title": "Test Standard",
                    "year": 2020,
                    "base_number": "999",
                    # NO lifecycle_status field
                }
            ],
            "edges": []
        }
        gate = LifecycleGate(graph)
        result = gate.resolve_edition("IS 999:2020", evaluation_date="2025-01-01")
        # With no lifecycle evidence, state must be LIFECYCLE_UNVERIFIED
        assert result["lifecycle_state"] == LifecycleState.LIFECYCLE_UNVERIFIED.value, \
            f"Expected LIFECYCLE_UNVERIFIED, got {result['lifecycle_state']}"


class TestLifecycleGateB2:
    """Fix B2: Inferred publication year must not produce VERIFIED_ACTIVE."""

    def test_publication_year_only_is_lifecycle_unverified(self):
        """A standard with only a publication year must NOT become verified current/active."""
        graph = {
            "nodes": [
                {
                    "designation": "IS 1234:2010",
                    "title": "Test Standard with Year Only",
                    "year": 2010,
                    "base_number": "1234",
                    # No publication_date (only year → inferred)
                    # No lifecycle_status
                }
            ],
            "edges": []
        }
        gate = LifecycleGate(graph)
        result = gate.resolve_edition("IS 1234:2010", evaluation_date="2025-01-01")
        assert result["lifecycle_state"] != "VERIFIED_ACTIVE", \
            "Standard with only publication year must NOT be VERIFIED_ACTIVE"
        assert result["lifecycle_evidence_status"] == "INFERRED"

    def test_verified_publication_date_can_be_active(self):
        """A standard with verified publication_date AND explicit ACTIVE status CAN become VERIFIED_ACTIVE."""
        graph = {
            "nodes": [
                {
                    "designation": "IS 5678:2015",
                    "title": "Test Standard with Verified Date",
                    "year": 2015,
                    "base_number": "5678",
                    "publication_date": "2015-06-15",
                    "lifecycle_status": "ACTIVE",
                }
            ],
            "edges": []
        }
        gate = LifecycleGate(graph)
        result = gate.resolve_edition("IS 5678:2015", evaluation_date="2025-01-01")
        assert result["lifecycle_state"] == "VERIFIED_ACTIVE", \
            f"Expected VERIFIED_ACTIVE for verified+active standard, got {result['lifecycle_state']}"
        assert result["lifecycle_evidence_status"] == "VERIFIED"

    def test_explicit_supersession_produces_verified_superseded(self):
        """Explicit supersession edge must produce VERIFIED_SUPERSEDED."""
        graph = {
            "nodes": [
                {"designation": "IS 100:1990", "title": "Old Standard", "year": 1990, "base_number": "100", "publication_date": "1990-01-01", "lifecycle_status": "ACTIVE"},
                {"designation": "IS 100:2010", "title": "New Standard", "year": 2010, "base_number": "100", "publication_date": "2010-01-01", "lifecycle_status": "ACTIVE"},
            ],
            "edges": [
                {"source": "IS 100:1990", "target": "IS 100:2010", "relationship": "superseded_by"}
            ]
        }
        gate = LifecycleGate(graph)
        result = gate.resolve_edition("IS 100:1990", evaluation_date="2025-01-01")
        assert result["is_superseded"] is True
        assert result["lifecycle_state"] == "VERIFIED_SUPERSEDED"

    def test_lifecycle_provenance_included(self):
        """resolve_edition must include lifecycle_provenance field."""
        graph = {
            "nodes": [
                {"designation": "IS 456:2000", "title": "Plain Concrete", "year": 2000, "base_number": "456"}
            ],
            "edges": []
        }
        gate = LifecycleGate(graph)
        result = gate.resolve_edition("IS 456:2000")
        assert "lifecycle_provenance" in result
        assert result["lifecycle_provenance"]["source"] == "BIS_KNOWLEDGE_GRAPH"
        assert result["lifecycle_provenance"]["verification_state"] in ("VERIFIED", "INFERRED", "UNKNOWN")


# ============================================================================
# Phase 3: Regulatory Semantics Fix
# ============================================================================

class TestRegulatoryStateEnum:
    """Tests that RegulatoryState has all required states."""

    def test_regulatory_states_complete(self):
        assert RegulatoryState.DATA_UNAVAILABLE == "DATA_UNAVAILABLE"
        assert RegulatoryState.REGULATORY_DOMAIN_NOT_IN_CURRENT_CORPUS == "REGULATORY_DOMAIN_NOT_IN_CURRENT_CORPUS"
        assert RegulatoryState.NOT_MANDATORY_CONFIRMED == "NOT_MANDATORY_CONFIRMED"
        assert RegulatoryState.MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES == "MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES"


class TestRegulatoryEvaluatorFix:
    """Fix: 'no regulatory claim' must not be treated as 'false regulatory assertion'."""

    def test_gold_mandatory_no_claim_is_not_false_assertion(self):
        """
        Gold = MANDATORY, Output = no regulatory claim
        → coverage/abstention issue, NOT false assertion.
        """
        queries = [{
            "gold_standards": [{"standard_designation": "IS 1234"}],
            "expected_regulatory_status": "MANDATORY",
            "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        }]
        outputs = [{
            "primary_recommendation": {
                "standard_designation": "IS 1234",
                "evidence_bundle": {
                    "scope_ready": True, "applicability_ready": True,
                    "lifecycle_ready": True, "provenance_ready": True,
                    "standard_role": "PRODUCT_STANDARD",
                    "readiness": {"evidence_dimensions": {
                        "scope_ready": True, "applicability_ready": True,
                        "lifecycle_ready": True, "provenance_ready": True,
                    }},
                },
                "lifecycle": {"status": "VERIFIED_ACTIVE", "lifecycle_state": "VERIFIED_ACTIVE", "is_superseded": False},
                "regulatory": {
                    # No definitive claim — just NOT_VERIFIED_IN_CURRENT_CORPUS
                    "regulatory_state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
                },
            },
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "candidate_recommendations": [],
        }]
        result = compute_safety_metrics(queries, outputs)
        assert result["regulatory_false_assertions"] == 0, \
            "No-claim output for MANDATORY gold must NOT count as false assertion"

    def test_gold_mandatory_output_voluntary_is_false_assertion(self):
        """
        Gold = MANDATORY, Output = VOLUNTARY
        → FALSE ASSERTION (system actively contradicted the mandate).
        """
        queries = [{
            "gold_standards": [{"standard_designation": "IS 1234"}],
            "expected_regulatory_status": "MANDATORY",
            "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        }]
        outputs = [{
            "primary_recommendation": {
                "standard_designation": "IS 1234",
                "evidence_bundle": {
                    "scope_ready": True, "applicability_ready": True,
                    "lifecycle_ready": True, "provenance_ready": True,
                    "standard_role": "PRODUCT_STANDARD",
                    "readiness": {"evidence_dimensions": {
                        "scope_ready": True, "applicability_ready": True,
                        "lifecycle_ready": True, "provenance_ready": True,
                    }},
                },
                "lifecycle": {"status": "VERIFIED_ACTIVE", "lifecycle_state": "VERIFIED_ACTIVE", "is_superseded": False},
                "regulatory": {
                    "regulatory_state": "VOLUNTARY",  # Active contradiction
                },
            },
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "candidate_recommendations": [],
        }]
        result = compute_safety_metrics(queries, outputs)
        assert result["regulatory_false_assertions"] > 0, \
            "VOLUNTARY output for MANDATORY gold MUST count as false assertion"

    def test_gold_mandatory_output_mandatory_is_correct(self):
        """
        Gold = MANDATORY, Output = MANDATORY_CONFIRMED → correct.
        """
        queries = [{
            "gold_standards": [{"standard_designation": "IS 1234"}],
            "expected_regulatory_status": "MANDATORY",
            "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        }]
        outputs = [{
            "primary_recommendation": {
                "standard_designation": "IS 1234",
                "evidence_bundle": {
                    "scope_ready": True, "applicability_ready": True,
                    "lifecycle_ready": True, "provenance_ready": True,
                    "standard_role": "PRODUCT_STANDARD",
                    "readiness": {"evidence_dimensions": {
                        "scope_ready": True, "applicability_ready": True,
                        "lifecycle_ready": True, "provenance_ready": True,
                    }},
                },
                "lifecycle": {"status": "VERIFIED_ACTIVE", "lifecycle_state": "VERIFIED_ACTIVE", "is_superseded": False},
                "regulatory": {
                    "regulatory_state": "MANDATORY_CONFIRMED",
                    "order_name": "QCO Test Order",
                    "order_number": "QCO-001",
                },
            },
            "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
            "candidate_recommendations": [],
        }]
        result = compute_safety_metrics(queries, outputs)
        assert result["regulatory_false_assertions"] == 0, \
            "MANDATORY_CONFIRMED matching gold MANDATORY must NOT be a false assertion"

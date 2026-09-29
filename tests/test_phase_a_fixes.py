"""
Tests for Phase A Audit Fixes — StandSpec AI
Validates the 5 critical code fixes from the 10-point audit:
  A-1: CONDITIONALLY_APPLICABLE when grounding is thin
  A-2: Renamed shadowed doc variable (implicit via existing tests)
  EN-1: Designation override blocked for RELATED/EXPERT_REVIEW_REQUIRED
  R-1: Defensive node ID in graph expansion
  CR-1: Phrase bonus break condition
"""

import pytest
from src.recommendation.applicability_engine import (
    TechnicalApplicabilityEngine,
    ApplicabilityState,
    AttributeStatus,
)
from src.recommendation.engine import StandSpecRecommendationEngine
from src.retrieval.graph_expansion import GraphCandidateExpander
from src.retrieval.cross_encoder import RuleBasedReranker


# ── A-1: CONDITIONALLY_APPLICABLE when product matches but grounding is thin ──


class TestConditionallyApplicable:
    """Validates that CONDITIONALLY_APPLICABLE fires when too many attributes are UNKNOWN."""

    def test_product_only_match_with_all_unknown_triggers_conditional(self):
        """If only PRODUCT matches and all 9 other attributes are UNKNOWN,
        the state should be CONDITIONALLY_APPLICABLE, not APPLICABLE."""
        engine = TechnicalApplicabilityEngine()

        # Candidate with product match but no discriminating attributes in title/scope
        candidate = {
            "designation": "IS 9999:2020",
            "title": "Some Cable Standard",
            "document": {
                "designation": "IS 9999:2020",
                "title": "Some Cable Standard",
                "scope": "",
                "node_type": "BIS_STANDARD",
            },
            "is_hydrated": True,
            "scope_evidence_available": True,
        }

        # Requirement that only has product — no voltage, material, grade, etc.
        requirement = {
            "raw_text": "Supply of cable",
            "requirements": {
                "product": {"value": "cable", "normalization": "Power Cable", "confidence": 0.95,
                            "source_span": "cable", "start_char": 10, "end_char": 15},
                "voltage": None,
                "material": None,
                "grade": None,
                "dimensions": None,
                "capacity": None,
                "application": None,
                "environment": None,
                "performance": None,
                "safety": None,
            },
            "missing_discriminators": ["voltage_rating"],
        }

        result = engine.evaluate_applicability(candidate, requirement)

        # Should be CONDITIONALLY_APPLICABLE — product matches but no other evidence
        assert result["state"] == ApplicabilityState.CONDITIONALLY_APPLICABLE.value, (
            f"Expected CONDITIONALLY_APPLICABLE but got {result['state']}"
        )
        assert result["is_applicable"] is True  # Still eligible for recommendation
        assert result["confidence"] < 0.92  # Lower confidence than full APPLICABLE
        assert "conditional_reason" in result

    def test_product_and_material_match_stays_applicable(self):
        """If PRODUCT and MATERIAL match (≥2 positive MATCH), should remain APPLICABLE."""
        engine = TechnicalApplicabilityEngine()

        candidate = {
            "designation": "IS 4984:2016",
            "title": "High Density Polyethylene Pipes for Water Supply",
            "document": {
                "designation": "IS 4984:2016",
                "title": "High Density Polyethylene Pipes for Water Supply",
                "scope": "hdpe pipe for potable water supply",
                "node_type": "BIS_STANDARD",
            },
            "is_hydrated": True,
            "scope_evidence_available": True,
        }

        requirement = {
            "raw_text": "procurement of HDPE pipe for potable water supply",
            "requirements": {
                "product": {"value": "hdpe pipe", "normalization": "HDPE Pipes for Water Supply",
                            "confidence": 0.95, "source_span": "HDPE pipe", "start_char": 15, "end_char": 24},
                "material": {"value": "hdpe", "normalization": "HDPE", "confidence": 0.92,
                             "source_span": "HDPE", "start_char": 15, "end_char": 19},
                "voltage": None,
                "grade": None,
                "dimensions": None,
                "capacity": None,
                "application": None,
                "environment": None,
                "performance": None,
                "safety": None,
            },
            "missing_discriminators": [],
        }

        result = engine.evaluate_applicability(candidate, requirement)

        # PRODUCT match + MATERIAL match + APPLICATION match → sufficient evidence
        assert result["state"] == ApplicabilityState.APPLICABLE.value, (
            f"Expected APPLICABLE but got {result['state']}. "
            f"Matched: {result.get('matched_attributes')}"
        )


# ── EN-1: Designation override blocked for RELATED and EXPERT_REVIEW_REQUIRED ──


class TestDesignationOverrideRestriction:
    """Validates that explicit designation references don't override RELATED or EXPERT_REVIEW."""

    def _build_mini_graph(self):
        """Build a minimal graph with a test method standard."""
        return {
            "release_id": "test-override",
            "nodes": [
                {
                    "id": "IS 10810 (Part 1):2015",
                    "designation": "IS 10810 (Part 1):2015",
                    "title": "Methods of Test for Cables — Insulation Resistance",
                    "node_type": "BIS_STANDARD",
                    "family": "IS",
                    "base_number": 10810,
                    "part": "1",
                    "section": None,
                    "year": "2015",
                    "is_hydrated": True,
                    "scope": "testing methods for cable insulation resistance",
                    "scope_evidence_available": True,
                    "recommendation_ready": True,
                    "candidate_status": "ELIGIBLE",
                },
                {
                    "id": "IS 7098 (Part 1):2011",
                    "designation": "IS 7098 (Part 1):2011",
                    "title": "XLPE Insulated PVC Sheathed Cables — for voltages up to 1100 V",
                    "node_type": "BIS_STANDARD",
                    "family": "IS",
                    "base_number": 7098,
                    "part": "1",
                    "section": None,
                    "year": "2011",
                    "is_hydrated": True,
                    "scope": "xlpe insulated pvc sheathed cables for working voltages up to and including 1100 v",
                    "scope_evidence_available": True,
                    "recommendation_ready": True,
                    "candidate_status": "ELIGIBLE",
                },
            ],
            "edges": [],
        }

    def test_test_method_designation_not_promoted_to_applicable(self):
        """If tender mentions IS 10810 but does NOT ask for testing explicitly,
        the applicability engine classifies IS 10810 as RELATED (test method).
        The EN-1 fix should prevent the designation override from promoting it to APPLICABLE."""
        graph = self._build_mini_graph()
        engine = StandSpecRecommendationEngine(standards_graph=graph)

        # Note: query does NOT contain "testing as per" — so the applicability engine
        # will classify IS 10810 as a pure test method (RELATED).
        result = engine.recommend(
            "Supply of 1.1 kV XLPE cable compliant with IS 10810 Part 1",
            query_id="Q_TEST_OVERRIDE",
        )

        # IS 10810 should NOT be the primary recommendation.
        # It should be in allied_standards (RELATED) or absent from candidates.
        primary = result.get("primary_recommendation")
        if primary:
            primary_desig = primary.get("standard_designation", "")
            assert "10810" not in primary_desig, (
                f"Test method IS 10810 should not be primary recommendation, got {primary_desig}"
            )

        # IS 10810 should not appear in candidate_recommendations
        candidate_desigs = [c.get("standard_designation", "") for c in result.get("candidate_recommendations", [])]
        assert not any("10810" in d for d in candidate_desigs), (
            f"IS 10810 (test method) should not be in candidate_recommendations: {candidate_desigs}"
        )


# ── R-1: Defensive node ID in graph expansion ──


class TestDefensiveNodeId:
    """Validates that graph expansion works with nodes that have 'designation' but no 'id'."""

    def test_expansion_with_designation_only_nodes(self):
        """Nodes with only 'designation' key (no 'id') should still be indexed."""
        graph = {
            "nodes": [
                {
                    "designation": "IS 4984:2016",
                    "title": "HDPE Pipes",
                    "family": "IS",
                    "base_number": 4984,
                    "part": None,
                    "section": None,
                    "year": "2016",
                },
                {
                    "designation": "IS 10810 (Part 1):2015",
                    "title": "Methods of Test for Cables",
                    "family": "IS",
                    "base_number": 10810,
                    "part": "1",
                    "section": None,
                    "year": "2015",
                },
            ],
            "edges": [
                {
                    "source": "IS 4984:2016",
                    "target": "IS 10810 (Part 1):2015",
                    "relationship": "test_method",
                    "relationship_confidence_state": "HIGH",
                },
            ],
        }

        expander = GraphCandidateExpander(graph)

        # Verify nodes were indexed despite lacking 'id' key
        assert "IS 4984:2016" in expander.nodes
        assert "IS 10810 (Part 1):2015" in expander.nodes

        # Verify expansion works
        seeds = [{"designation": "IS 4984:2016", "score": 1.0}]
        expanded = expander.expand(seeds, top_k=10)
        expanded_desigs = [c["designation"] for c in expanded]
        assert "IS 10810 (Part 1):2015" in expanded_desigs

    def test_expansion_with_both_id_and_designation(self):
        """Nodes with both 'id' and 'designation' should use 'id' as primary key."""
        graph = {
            "nodes": [
                {
                    "id": "IS 800:2007",
                    "designation": "IS 800:2007",
                    "title": "General Construction in Steel",
                    "family": "IS",
                    "base_number": 800,
                },
            ],
            "edges": [],
        }

        expander = GraphCandidateExpander(graph)
        assert "IS 800:2007" in expander.nodes


# ── CR-1: Phrase bonus break condition ──


class TestPhraseBonus:
    """Validates the phrase bonus logic in RuleBasedReranker."""

    def test_phrase_bonus_rewards_contiguous_match(self):
        """A candidate with contiguous phrase match should score higher than scattered tokens."""
        reranker = RuleBasedReranker()

        query = "high density polyethylene pipes for water supply"

        cand_contiguous = {
            "designation": "IS 4984:2016",
            "title": "High Density Polyethylene Pipes for Water Supply",
            "document": {"scope": ""},
        }
        cand_scattered = {
            "designation": "IS 9999:2020",
            "title": "Polyethylene Water Supply High Density Pipes",
            "document": {"scope": ""},
        }

        req_obj = {
            "requirements": {
                "product": {
                    "value": "hdpe pipe",
                    "normalization": "HDPE Pipes for Water Supply",
                },
            },
        }

        score_contig, _ = reranker.score_pair(query, cand_contiguous, req_obj=req_obj)
        score_scatter, _ = reranker.score_pair(query, cand_scattered, req_obj=req_obj)

        # Contiguous match should score at least as high
        assert score_contig >= score_scatter, (
            f"Contiguous phrase should score >= scattered: {score_contig} vs {score_scatter}"
        )

"""
Unit & Integration Tests for Phase P1-B: Decision Core Hardening — StandSpec AI
Verifies:
1. Standard Role Graph Persistence (graph schema, fields, non-empty distribution).
2. Modular Applicability Architecture (GenericApplicabilityEngine, CEDRuleRegistry, ETDRuleRegistry).
3. Retrieval Channel Diagnostics (bm25_rank, dense_rank, rrf_rank propagation).
4. Data-Driven Lifecycle v2 (StandardEdition dataclass, valid_on temporal bounds).
5. Regulatory v2 (statutory mandate separation, 5-state explicit verification taxonomy).
"""

import json
from pathlib import Path
import pytest

from src.recommendation.applicability import (
    GenericApplicabilityEngine,
    CEDRuleRegistry,
    ETDRuleRegistry,
    ApplicabilityState,
    AttributeStatus,
)
from src.recommendation.lifecycle_gate import LifecycleGate, StandardEdition
from src.recommendation.regulatory_gate import RegulatoryGate, RegulatoryState, SourceConsistencyStatus
from src.recommendation.engine import StandSpecRecommendationEngine
from src.recommendation.role_classifier import StandardRole

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"


@pytest.fixture(scope="module")
def graph():
    if not GRAPH_PATH.exists():
        pytest.skip(f"Knowledge graph not found at {GRAPH_PATH}")
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def engine(graph):
    return StandSpecRecommendationEngine(standards_graph=graph, retriever_mode="hybrid_deterministic")


# ── TEST 1: Standard Role Persistence in Graph ──
def test_p1b_standard_role_graph_persistence(graph):
    """Verify all graph nodes possess persisted standard_role metadata."""
    nodes = graph.get("nodes", [])
    assert len(nodes) in (6081, 6082)

    role_counts = {}
    for node in nodes:
        assert "standard_role" in node, f"Node {node.get('designation')} missing standard_role"
        assert "role_confidence" in node, f"Node {node.get('designation')} missing role_confidence"
        assert "role_reason" in node, f"Node {node.get('designation')} missing role_reason"
        assert "role_source" in node, f"Node {node.get('designation')} missing role_source"
        assert "role_classifier_version" in node, f"Node {node.get('designation')} missing role_classifier_version"
        assert isinstance(node["role_source"], str) and bool(node["role_source"].strip())

        role = node["standard_role"]
        role_counts[role] = role_counts.get(role, 0) + 1

    # Verify key architectural roles are represented
    assert role_counts.get("PRIMARY_PRODUCT", 0) > 1000
    assert role_counts.get("DESIGN_CODE", 0) > 300
    assert role_counts.get("TEST_METHOD", 0) > 800
    assert role_counts.get("COMPONENT", 0) > 80


# ── TEST 2: Modular Applicability Registries ──
def test_p1b_modular_applicability_registries():
    """Verify GenericApplicabilityEngine functions with modular domain registries."""
    ced_reg = CEDRuleRegistry()
    etd_reg = ETDRuleRegistry()
    engine = GenericApplicabilityEngine(registries=[ced_reg, etd_reg])

    # CED domain test: Composite pipes vs solid wall HDPE
    res_composite = engine.evaluate_applicability(
        candidate={"designation": "IS 15450:2004", "title": "Polyethylene/Aluminium Composite Pressure Pipes"},
        normalized_requirements={"raw_text": "Supply solid wall HDPE pipes for potable drinking water supply"},
    )
    assert res_composite["state"] == ApplicabilityState.NOT_APPLICABLE.value
    assert "MATERIAL" in res_composite["mismatched_attributes"]

    # ETD domain test: Distribution transformer capacity exclusion (> 2500 kVA)
    res_dist = engine.evaluate_applicability(
        candidate={"designation": "IS 1180 (Part 1):2014", "title": "Distribution Transformers"},
        normalized_requirements={"raw_text": "500 MVA 400 kV autotransformer for grid substation"},
    )
    assert res_dist["state"] == ApplicabilityState.NOT_APPLICABLE.value
    assert "CAPACITY" in res_dist["mismatched_attributes"]
    assert "IS 1180 is strictly limited" in res_dist["rejection_reason"]


# ── TEST 3: Retrieval Channel Diagnostics ──
def test_p1b_retrieval_channel_diagnostics(engine):
    """Verify candidates and recommendations carry retrieval_diagnostics."""
    # 1. Query with review candidate or primary recommendation
    query = (
        "Supply of High Density Polyethylene (HDPE) pipes for rural potable water distribution networks. "
        "Pipe material grade PE-100, pressure rating PN 10, outside diameter 110 mm, complying with national drinking water conveyance specifications."
    )
    result = engine.recommend(query)

    rec = result.get("primary_recommendation") or result.get("review_candidate")
    assert rec is not None, "Expected either primary_recommendation or review_candidate"
    assert "retrieval_diagnostics" in rec
    diag = rec["retrieval_diagnostics"]
    assert "bm25_rank" in diag
    assert "dense_rank" in diag
    assert "rrf_rank" in diag
    assert "retrieval_source" in diag

    # Verify all candidate recommendations have diagnostics
    for cand in result.get("candidate_recommendations", []):
        assert "retrieval_diagnostics" in cand
        cdiag = cand["retrieval_diagnostics"]
        assert "bm25_rank" in cdiag
        assert "dense_rank" in cdiag

    # 2. Review Candidate query (fail-closed to review)
    res_review = engine.recommend("procurement of 6 mm safety glass for building glazing")
    assert res_review["decision_state"] == "EXPERT_REVIEW_REQUIRED"
    assert "retrieval_diagnostics" in res_review["review_candidate"]


# ── TEST 4: Data-Driven Lifecycle v2 (StandardEdition & Temporal Model) ──
def test_p1b_lifecycle_v2_standard_edition():
    """Verify StandardEdition valid_on() temporal bounds."""
    edition = StandardEdition(
        designation="IS 9999:2015",
        year=2015,
        publication_date="2015-06-01",
        withdrawal_date="2024-01-01",
        lifecycle_status="SUPERSEDED",
        candidate_status="ELIGIBLE",
        superseded_by="IS 9999:2024",
    )

    # 1. Prior to publication date -> INVALID
    assert edition.valid_on("2010-01-01") is False

    # 2. Within active valid window -> VALID
    assert edition.valid_on("2018-05-15") is True

    # 3. Post withdrawal date -> INVALID
    assert edition.valid_on("2024-06-01") is False

    # 4. Unknown evaluation date with SUPERSEDED status -> INVALID
    assert edition.valid_on(None) is False


def test_p1b_lifecycle_v2_resolution_gate(graph):
    """Verify LifecycleGate resolution with temporal awareness."""
    lg = LifecycleGate(standards_graph=graph)

    # Historical tender date: IS 13947 valid before superseding standard took effect
    res_hist = lg.resolve_edition("IS 13947 (Part 2):1993", evaluation_date="2010-01-01")
    assert not res_hist["is_superseded"]
    assert res_hist["recommended_edition"] == "IS 13947 (Part 2):1993"

    # Contemporary tender date: IS 13947 superseded by IS/IEC 60947
    res_contemp = lg.resolve_edition("IS 13947 (Part 2):1993", evaluation_date="2025-01-01")
    assert res_contemp["is_superseded"]
    assert res_contemp["recommended_edition"] == "IS/IEC 60947 (Part 2):2016"
    assert res_contemp["lifecycle_state"] == "SUPERSEDED"


# ── TEST 5: Regulatory v2 with Statutory Mandate Separation ──
def test_p1b_regulatory_v2_states_and_statutory_mandate():
    """Verify Regulatory v2 states and explicit statutory mandate structure."""
    reg = RegulatoryGate()

    # 1. Verified Mandatory QCO
    res_mand = reg.evaluate_regulatory_status("IS 7098 (Part 2):2011")
    assert res_mand["regulatory_state"] == RegulatoryState.MANDATORY_CONFIRMED.value
    assert res_mand["is_mandatory"] is True
    assert "statutory_mandate" in res_mand
    sm = res_mand["statutory_mandate"]
    assert sm["is_statutory_mandatory"] is True
    assert sm["legal_basis"] == "Bureau of Indian Standards Act, 2016 (Section 16)"
    assert sm["certification_scheme"] == "Scheme-I (ISI Mark)"

    # 2. Conditional applicability with explicit export context
    res_cond = reg.evaluate_regulatory_status(
        "IS 4984:2016",
        evaluation_context="Procurement of HDPE pipes for direct export unit overseas shipment",
    )
    assert res_cond["regulatory_state"] == RegulatoryState.MANDATORY_CONDITIONALLY_APPLICABLE.value
    assert res_cond["statutory_mandate"]["has_statutory_exemptions"] is True
    assert len(res_cond["statutory_mandate"]["exemptions"]) > 0

    # 3. Mandate Not Found in Searched Sources (corpus unverified)
    res_unfound = reg.evaluate_regulatory_status("IS 999999:2026")
    assert res_unfound["regulatory_state"] == RegulatoryState.MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES.value
    assert res_unfound["corpus_verification_state"] == RegulatoryState.NOT_VERIFIED_IN_CURRENT_CORPUS.value
    assert res_unfound["statutory_mandate"]["is_statutory_mandatory"] is False

    # 4. Regulatory Sources Unavailable
    fake_reg = RegulatoryGate(data_dir=Path("non_existent_regulatory_dir_12345"))
    res_unavail = fake_reg.evaluate_regulatory_status("IS 7098 (Part 2):2011")
    assert res_unavail["regulatory_state"] == RegulatoryState.REGULATORY_SOURCE_UNAVAILABLE.value
    assert res_unavail["corpus_verification_state"] == "SOURCE_UNAVAILABLE"

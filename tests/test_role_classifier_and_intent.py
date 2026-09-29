"""
Tests for Standard Role Classifier & Procurement Intent Alignment (Phase C / C-1, C-2, C-3).
Verifies that:
1. RoleClassifier correctly categorizes standards into canonical roles (PRIMARY_PRODUCT, COMPONENT, DIMENSIONAL_MOUNTING, TEST_METHOD, INSTALLATION_CODE).
2. RequirementExtractor produces structured procurement_intent (procurement_object, object_type, technical_intent) at top-level.
3. RuleBasedReranker rewards role-aligned candidates and penalizes role-mismatched auxiliary candidates.
4. ApplicabilityEngine gates intermediate components and mounting rail standards to RELATED when finished assembly or apparatus is procured.
5. End-to-end engine resolves user-flagged role confusion regressions:
   - uPVC doors/windows query chooses IS 19609 assembly over IS 17953 profile.
   - MCCB/ACB switchgear query chooses IS/IEC 60947-2 breaker over IS/IEC 60715 mounting rail.
"""

import pytest
from src.recommendation.role_classifier import RoleClassifier, StandardRole
from src.extraction.requirement_extractor import RequirementExtractor
from src.retrieval.cross_encoder import RuleBasedReranker
from src.recommendation.applicability_engine import TechnicalApplicabilityEngine, ApplicabilityState
from src.recommendation.engine import StandSpecRecommendationEngine


# ── 1. RoleClassifier Archetype Tests ──

def test_role_classifier_archetypes():
    # Primary Products / Assemblies
    assert RoleClassifier.classify({
        "designation": "IS 19609:2026",
        "title": "Unplasticized Polyvinyl Chloride (uPVC) Profile Framed Doors, Windows and Sliders - Specification"
    }) == StandardRole.PRIMARY_PRODUCT

    assert RoleClassifier.classify({
        "designation": "IS/IEC 60947-2:2016",
        "title": "Low-voltage switchgear and controlgear - Part 2: Circuit-breakers"
    }) == StandardRole.PRIMARY_PRODUCT

    assert RoleClassifier.classify({
        "designation": "IS 7098 (Part 2):2011",
        "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables"
    }) == StandardRole.PRIMARY_PRODUCT

    # Intermediate Component / Feedstock
    assert RoleClassifier.classify({
        "designation": "IS 17953:2023",
        "title": "Unplasticized polyvinyl chloride (uPVC) profiles for the manufacture of windows and doors - Specification"
    }) == StandardRole.COMPONENT

    assert RoleClassifier.classify({
        "designation": "IS 8130:2013",
        "title": "Conductors for insulated electric cables and flexible cords - Specification"
    }) == StandardRole.COMPONENT

    # Dimensional / Mounting
    assert RoleClassifier.classify({
        "designation": "IS/IEC 60715:2017",
        "title": "Dimensions of low-voltage switchgear and controlgear - Standardized mounting on rails for mechanical support"
    }) == StandardRole.DIMENSIONAL_MOUNTING

    # Test Methods
    assert RoleClassifier.classify({
        "designation": "IS 10810 (Part 53):1984",
        "title": "Methods of test for cables: Part 53 Flammability test"
    }) == StandardRole.TEST_METHOD

    assert RoleClassifier.classify({
        "designation": "IS 516 (Part 1/Sec 1):2021",
        "title": "Hardened Concrete - Methods of Test: Part 1 Testing of Strength of Hardened Concrete"
    }) == StandardRole.TEST_METHOD

    # Installation Codes
    assert RoleClassifier.classify({
        "designation": "IS 1255:1983",
        "title": "Code of practice for installation and maintenance of power cables up to and including 33 kV rating"
    }) == StandardRole.INSTALLATION_CODE

    # Terminology
    assert RoleClassifier.classify({
        "designation": "IS 1885 (Part 32):2019",
        "title": "Electrotechnical vocabulary: Part 32 Electric cables"
    }) == StandardRole.TERMINOLOGY


# ── 2. Requirement Extractor Procurement Intent Tests ──

def test_procurement_intent_extraction():
    extractor = RequirementExtractor()

    # Finished Assembly tender
    res_upvc = extractor.extract("Supply of uPVC doors and windows for residential quarters conforming to BIS")
    intent_upvc = res_upvc.get("procurement_intent", {})
    assert intent_upvc.get("object_type") == "FINISHED_ASSEMBLY"
    assert intent_upvc.get("technical_intent") == "SUPPLY"
    assert "procurement_intent" not in res_upvc["requirements"]  # Invariant check

    # Finished Product tender
    res_mccb = extractor.extract("Supply of low voltage circuit breaker 415V MCCB 630A for substation panel")
    intent_mccb = res_mccb.get("procurement_intent", {})
    assert intent_mccb.get("object_type") == "FINISHED_PRODUCT"
    assert intent_mccb.get("technical_intent") == "SUPPLY"

    # Installation Service tender
    res_install = extractor.extract("Laying and installation of 11 kV power cables in trenches")
    intent_install = res_install.get("procurement_intent", {})
    assert intent_install.get("technical_intent") == "INSTALLATION"


# ── 3. RuleBasedReranker Role Alignment Tests ──

def test_reranker_upvc_assembly_over_component_profile():
    reranker = RuleBasedReranker()
    query = "Supply of uPVC doors and windows for residential building"
    req_obj = {
        "requirements": {
            "product": {"value": "uPVC Doors and Windows", "normalization": "uPVC Doors and Windows"},
        },
        "procurement_intent": {
            "procurement_object": "uPVC Doors and Windows",
            "object_type": "FINISHED_ASSEMBLY",
            "technical_intent": "SUPPLY",
        }
    }
    cand_profile = {
        "designation": "IS 17953:2023",
        "title": "Unplasticized polyvinyl chloride (uPVC) profiles for the manufacture of windows and doors - Specification",
        "scope": "Prescribes requirements for uPVC profiles for windows and doors.",
    }
    cand_assembly = {
        "designation": "IS 19609:2026",
        "title": "Unplasticized Polyvinyl Chloride (uPVC) Profile Framed Doors, Windows and Sliders - Specification",
        "scope": "Prescribes requirements for uPVC framed doors, windows and sliders.",
    }

    reranked = reranker.rerank(query, [cand_profile, cand_assembly], req_obj=req_obj, top_k=2)
    assert reranked[0]["designation"] == "IS 19609:2026"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]
    assert reranked[0]["standard_role"] == "PRIMARY_PRODUCT"
    assert reranked[1]["standard_role"] == "COMPONENT"


def test_reranker_circuit_breaker_over_mounting_rail():
    reranker = RuleBasedReranker()
    query = "Supply of low voltage circuit breakers 415V MCCB 630A"
    req_obj = {
        "requirements": {
            "product": {"value": "Low-Voltage Switchgear and Controlgear", "normalization": "Low-Voltage Switchgear and Controlgear"},
            "voltage": {"value": "415 V"},
        },
        "procurement_intent": {
            "procurement_object": "Low-Voltage Switchgear and Controlgear",
            "object_type": "FINISHED_PRODUCT",
            "technical_intent": "SUPPLY",
        }
    }
    cand_rail = {
        "designation": "IS/IEC 60715:2017",
        "title": "Dimensions of low-voltage switchgear and controlgear - Standardized mounting on rails for mechanical support",
        "scope": "Specifies dimensions and mounting of low-voltage switchgear on standardized rails.",
    }
    cand_mccb = {
        "designation": "IS/IEC 60947-2:2016",
        "title": "Low-voltage switchgear and controlgear - Part 2: Circuit-breakers",
        "scope": "Applies to circuit-breakers whose main contacts are intended to be connected to circuits.",
    }

    reranked = reranker.rerank(query, [cand_rail, cand_mccb], req_obj=req_obj, top_k=2)
    assert reranked[0]["designation"] == "IS/IEC 60947-2:2016"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]
    assert reranked[0]["standard_role"] == "PRIMARY_PRODUCT"
    assert reranked[1]["standard_role"] == "DIMENSIONAL_MOUNTING"


# ── 4. TechnicalApplicabilityEngine Role Gating Tests ──

def test_applicability_gates_profile_when_procuring_assembly():
    engine = TechnicalApplicabilityEngine()
    req = {
        "raw_text": "Supply of uPVC doors and windows for residential quarters",
        "requirements": {
            "product": {"value": "uPVC Doors and Windows", "normalization": "uPVC Doors and Windows"},
        },
        "procurement_intent": {
            "procurement_object": "uPVC Doors and Windows",
            "object_type": "FINISHED_ASSEMBLY",
            "technical_intent": "SUPPLY",
        }
    }
    cand_profile = {
        "designation": "IS 17953:2023",
        "title": "Unplasticized polyvinyl chloride (uPVC) profiles for the manufacture of windows and doors - Specification",
        "scope": "Prescribes requirements for uPVC profiles.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    cand_assembly = {
        "designation": "IS 19609:2026",
        "title": "Unplasticized Polyvinyl Chloride (uPVC) Profile Framed Doors, Windows and Sliders - Specification",
        "scope": "Prescribes requirements for complete doors, windows and sliders.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }

    res_profile = engine.evaluate_applicability(cand_profile, req)
    res_assembly = engine.evaluate_applicability(cand_assembly, req)

    assert res_profile["is_applicable"] is False
    assert res_profile["state"] == ApplicabilityState.RELATED.value
    assert "COMPONENT" in res_profile["rejection_reason"]
    assert res_assembly["is_applicable"] is True
    assert res_assembly["state"] in (ApplicabilityState.APPLICABLE.value, ApplicabilityState.CONDITIONALLY_APPLICABLE.value)


def test_applicability_gates_rail_when_procuring_switchgear():
    engine = TechnicalApplicabilityEngine()
    req = {
        "raw_text": "Supply of low-voltage switchgear 415 V circuit breaker",
        "requirements": {
            "product": {"value": "Low-Voltage Switchgear and Controlgear", "normalization": "Low-Voltage Switchgear and Controlgear"},
            "voltage": {"value": "415 V"},
        },
        "procurement_intent": {
            "procurement_object": "Low-Voltage Switchgear and Controlgear",
            "object_type": "FINISHED_PRODUCT",
            "technical_intent": "SUPPLY",
        }
    }
    cand_rail = {
        "designation": "IS/IEC 60715:2017",
        "title": "Dimensions of low-voltage switchgear and controlgear - Standardized mounting on rails",
        "scope": "Specifies dimensional standardized mounting on rails for switchgear.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    cand_mccb = {
        "designation": "IS/IEC 60947-2:2016",
        "title": "Low-voltage switchgear and controlgear - Part 2: Circuit-breakers",
        "scope": "Applies to circuit-breakers for rated voltages up to 1000 V AC.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }

    res_rail = engine.evaluate_applicability(cand_rail, req)
    res_mccb = engine.evaluate_applicability(cand_mccb, req)

    assert res_rail["is_applicable"] is False
    assert res_rail["state"] == ApplicabilityState.RELATED.value
    assert "DIMENSIONAL_MOUNTING" in res_rail["rejection_reason"]
    assert res_mccb["is_applicable"] is True
    assert res_mccb["state"] in (ApplicabilityState.APPLICABLE.value, ApplicabilityState.CONDITIONALLY_APPLICABLE.value)


# ── 5. End-to-End Pipeline Role Conflict Regression Tests ──

import json
from pathlib import Path

GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "standards_graph.json"


@pytest.fixture(scope="module")
def full_engine():
    if not GRAPH_PATH.exists():
        pytest.skip(f"Knowledge graph not found at {GRAPH_PATH}")
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    return StandSpecRecommendationEngine(graph)


def test_e2e_upvc_doors_windows_never_recommends_profile(full_engine):
    """uPVC doors and windows procurement must never recommend component profile IS 17953 as primary."""
    res = full_engine.recommend("Supply of uPVC doors and windows for residential quarters conforming to BIS")
    if res.get("primary_recommendation"):
        desig = res["primary_recommendation"]["standard_designation"]
        assert "17953" not in desig, f"IS 17953 profile standard wrongly selected as primary: {desig}"


def test_e2e_circuit_breaker_never_recommends_mounting_rail(full_engine):
    """MCCB / circuit breaker procurement must never recommend DIN rail mounting IS/IEC 60715 as primary."""
    res = full_engine.recommend("Supply of low-voltage switchgear 415 V air circuit breaker / MCCB")
    if res.get("primary_recommendation"):
        desig = res["primary_recommendation"]["standard_designation"]
        assert "60715" not in desig, f"IS/IEC 60715 mounting standard wrongly selected as primary: {desig}"

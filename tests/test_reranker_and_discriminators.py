"""
Unit tests for modular reranker features, declarative discriminators, and contradiction detection (Phase P1-C.4).
"""

import pytest
from src.retrieval.reranker_features import (
    DesignationAlignmentFeature,
    ProductCategoryFeature,
    ScopeCoverageFeature,
    MaterialAlignmentFeature,
    SpecificityFeature,
    RoleAlignmentFeature,
)
from src.retrieval.cross_encoder import RuleBasedReranker
from src.extraction.requirement_extractor import RequirementExtractor, DISCRIMINATOR_RULES


def test_designation_alignment_feature():
    ext = DesignationAlignmentFeature()
    cand = {"designation": "IS 694:2010", "title": "PVC Insulated Cables"}
    
    # Exact base match with matching part
    deltas = ext.extract("IS 694 cable", cand)
    assert deltas["exact_desig_match"] >= 10.0
    assert deltas["scope_penalty"] == 0.0

    # Base match with conflicting base requested
    deltas_mismatch = ext.extract("IS 1554 cable", cand)
    assert deltas_mismatch["scope_penalty"] < 0.0


def test_product_category_feature():
    ext = ProductCategoryFeature()
    cand = {
        "designation": "IS 7098 (Part 2):2011",
        "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables",
        "document": {"scope": "Specification for electric cables"}
    }
    req_obj = {
        "requirements": {
            "product": {"value": "Crosslinked Polyethylene Cable", "normalization": "crosslinked polyethylene cable"}
        }
    }
    deltas = ext.extract("XLPE cable", cand, req_obj=req_obj)
    assert deltas["title_match"] > 2.0


def test_scope_coverage_feature():
    ext = ScopeCoverageFeature()
    cand = {
        "designation": "IS 4984:2016",
        "document": {"scope": "High density polyethylene pipes for water supply. Excludes gas supply."}
    }
    req_obj = {
        "requirements": {
            "product": {"value": "gas supply", "normalization": "gas supply"}
        }
    }
    deltas = ext.extract("HDPE pipe for gas supply", cand, req_obj=req_obj)
    # Target product "gas supply" matches scope explicit exclusion
    assert deltas["scope_penalty"] <= -6.0


def test_material_and_specificity_features():
    mat_ext = MaterialAlignmentFeature()
    spec_ext = SpecificityFeature()
    cand = {
        "designation": "IS 16444 (Part 1):2015",
        "title": "A.C. Static Direct Connected Watt-hour Smart Meter Class 1 and 2",
        "document": {"scope": "Smart meter specification"}
    }
    deltas_mat = mat_ext.extract("smart electricity meter 415 V", cand)
    deltas_spec = spec_ext.extract("smart electricity meter", cand)

    assert deltas_spec["attribute_match"] >= 3.0


def test_rule_based_reranker_composition():
    reranker = RuleBasedReranker()
    cand = {
        "designation": "IS 7098 (Part 2):2011",
        "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables Part 2 for Working Voltages from 3.3 kV up to and including 33 kV",
        "document": {"scope": "Crosslinked polyethylene cables for electricity supply"}
    }
    score, signals = reranker.score_pair("11 kV XLPE cable", cand)
    assert 0.0 <= score <= 1.0
    assert "exact_desig_match" in signals
    assert "title_match" in signals
    assert "role_alignment" in signals


def test_declarative_discriminator_rules():
    extractor = RequirementExtractor()
    assert "cable" in DISCRIMINATOR_RULES
    assert "cement" in DISCRIMINATOR_RULES
    assert "pipe" in DISCRIMINATOR_RULES

    # Incomplete cable tender
    res = extractor.extract("Supply of electric power cables for commercial complex")
    assert "voltage_rating" in res["missing_discriminators"]
    assert "conductor_and_insulation_material" in res["missing_discriminators"]
    assert res["query_sufficiency"]["state"] == "INSUFFICIENT"


def test_contradiction_detection():
    extractor = RequirementExtractor()
    
    # Conflicting cement grades
    res_cement = extractor.extract("Supply of 43 grade and 53 grade cement for structural columns")
    assert len(res_cement["contradictions"]) > 0
    assert any("Conflicting cement grades" in c for c in res_cement["contradictions"])

    # Conflicting applications
    res_app = extractor.extract("HDPE pipes for potable drinking water and sewage drainage line")
    assert len(res_app["contradictions"]) > 0
    assert any("potable water supply vs sewage/drainage" in c for c in res_app["contradictions"])

    # Consistent tender has no contradictions
    res_clean = extractor.extract("Supply of 11 kV 3-core 185 sq mm XLPE insulated aluminium power cables")
    assert res_clean["contradictions"] == []


def test_technical_parameters_alignment_feature():
    from src.retrieval.reranker_features import TechnicalParametersAlignment, FeatureState

    ext = TechnicalParametersAlignment()
    cand_lv = {
        "designation": "IS 7098 (Part 1):1988",
        "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 1 For Working Voltage Up to and Including 1100 V",
        "document": {"scope": "Specification for working voltages up to and including 1100 V"},
    }
    cand_hv = {
        "designation": "IS 7098 (Part 2):2011",
        "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 2 For Working Voltages from 3.3 kV up to and including 33 kV",
        "document": {"scope": "Specification for working voltages from 3.3 kV up to and including 33 kV"},
    }

    # Query requests 1100 V
    req_lv = {"requirements": {"voltage": {"value": "1100 V", "normalization": "1100 V"}}}
    res_match = ext.evaluate("1100 V XLPE cable", cand_lv, req_obj=req_lv)
    assert res_match.state == FeatureState.MATCH
    assert res_match.score_delta > 0

    res_mismatch = ext.evaluate("1100 V XLPE cable", cand_hv, req_obj=req_lv)
    assert res_mismatch.state == FeatureState.MISMATCH
    assert res_mismatch.score_delta < 0

    # Query requests 11 kV
    req_hv = {"requirements": {"voltage": {"value": "11 kV", "normalization": "11 kV"}}}
    res_hv_match = ext.evaluate("11 kV XLPE cable", cand_hv, req_obj=req_hv)
    assert res_hv_match.state == FeatureState.MATCH

    res_hv_mismatch = ext.evaluate("11 kV XLPE cable", cand_lv, req_obj=req_hv)
    assert res_hv_mismatch.state == FeatureState.MISMATCH


def test_engine_lifecycle_and_regulatory_caching():
    from src.recommendation.engine import StandSpecRecommendationEngine

    engine = StandSpecRecommendationEngine.from_release()
    assert len(engine._lifecycle_cache) == 0
    assert len(engine._regulatory_cache) == 0

    # Run recommendation
    out1 = engine.recommend("Supply of Fe 500 TMT steel rebars for bridge construction")
    cache_len_life1 = len(engine._lifecycle_cache)
    cache_len_reg1 = len(engine._regulatory_cache)
    assert cache_len_life1 > 0
    assert cache_len_reg1 > 0

    # Run another recommendation that touches the same standard (IS 1786)
    out2 = engine.recommend("Supply of Fe 500 TMT steel rebars for residential building")
    # Cache should hit without recomputing from scratch
    assert any("IS 1786" in k[0] for k in engine._lifecycle_cache.keys())
    assert any("IS 1786:2008" in k[0] for k in engine._regulatory_cache.keys())


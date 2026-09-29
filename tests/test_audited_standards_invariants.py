"""
Unit Tests for User-Audited Standards & Domain Invariants (Part 2 Verification)
Verifies that:
1. Lifecycle supersessions are strictly enforced:
   - IS 1139:1966 is SUPERSEDED by IS 1786:2008 and EXCLUDED from recommendations.
   - IS 1180 (Part 2):1989 is WITHDRAWN / merged into IS 1180 (Part 1):2014 and EXCLUDED.
   - IS 12615:2026 is registered as PUBLISHED_CURRENT and MANDATORY.
2. Roles adhere strictly to engineering classification:
   - IS 650:1991 is TEST_METHOD (testing sand, not primary product).
   - IS 456:2000 is DESIGN_CODE with specialised structure limitations.
   - IS 5831, IS 1778, IS 1709, IS 8783 Part 1 are COMPONENT standards.
   - IS 2026 Part 2 & Part 3 are TEST_METHOD standards.
3. Guardrails against hallucinated attributes:
   - IS 12818:2010 diameter/slot range remains None/unverified.
   - IS 16651:2017 steel grades remain None/unverified.
   - IS 16415:2015 contains authentic verified blend limits (fly ash 10-25%, slag 25-40%).
"""

import json
import pytest
from pathlib import Path
from src.recommendation.role_classifier import RoleClassifier, StandardRole
from src.recommendation.corpus_policy import CandidateEligibilityPolicy

GRAPH_PATH = Path("data/processed/standards_graph.json")


@pytest.fixture(scope="module")
def graph_node_map():
    assert GRAPH_PATH.exists(), f"Graph file missing at {GRAPH_PATH}"
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    return {n.get("id"): n for n in graph.get("nodes", [])}


def test_is_1139_superseded_by_is_1786(graph_node_map):
    node = graph_node_map.get("IS 1139:1966")
    assert node is not None, "IS 1139:1966 missing from graph"
    assert node.get("status") == "SUPERSEDED"
    assert node.get("superseded_by") == "IS 1786:2008"
    assert node.get("candidate_status") == "EXCLUDED"
    assert not node.get("is_recommendation_eligible")
    assert not CandidateEligibilityPolicy.is_primary_candidate(node)


def test_is_1180_part_2_withdrawn_and_merged(graph_node_map):
    part1 = graph_node_map.get("IS 1180 (Part 1):2014")
    assert part1 is not None, "IS 1180 (Part 1):2014 missing from graph"
    assert "IS 1180 (Part 2):1989" in part1.get("supersedes", [])
    assert "IS 1180 (Part 2):1989" in part1.get("merged_standards", [])
    assert part1.get("mandatory_certification") is True


def test_is_12615_2026_published_current_and_mandatory(graph_node_map):
    node = graph_node_map.get("IS 12615:2026")
    assert node is not None, "IS 12615:2026 missing from graph"
    assert node.get("lifecycle_status") == "PUBLISHED_CURRENT"
    assert node.get("mandatory_certification") is True
    assert node.get("recommend_as_current") is True
    assert node.get("supersedes") == "IS 12615:2018"
    assert CandidateEligibilityPolicy.is_primary_candidate(node)


def test_role_reclassifications_cement_and_components(graph_node_map):
    # IS 650 is standard sand for testing cement
    is_650 = graph_node_map.get("IS 650:1991")
    assert is_650 is not None
    assert is_650.get("standard_role") == "TEST_METHOD"
    assert RoleClassifier.classify(is_650) == StandardRole.TEST_METHOD

    # IS 456 is a structural design code
    is_456 = graph_node_map.get("IS 456:2000")
    assert is_456 is not None
    assert is_456.get("standard_role") == "DESIGN_CODE"
    assert "specialised standards" in is_456.get("special_structure_rule", "").lower()

    # Intermediate components
    components = ["IS 5831:1984", "IS 1778:1980", "IS 1709:1984", "IS 8783 (Part 1):1995"]
    for desig in components:
        n = graph_node_map.get(desig)
        assert n is not None, f"{desig} missing"
        assert n.get("standard_role") == "COMPONENT", f"{desig} expected COMPONENT role"

    # Test codes for transformers
    test_codes = ["IS 2026 (Part 2):2010", "IS 2026 (Part 3):2018"]
    for desig in test_codes:
        n = graph_node_map.get(desig)
        assert n is not None, f"{desig} missing"
        assert n.get("standard_role") == "TEST_METHOD", f"{desig} expected TEST_METHOD role"


def test_unverified_attributes_remain_null_to_prevent_hallucinations(graph_node_map):
    # IS 12818 diameter/slot must be null until official standard document verification
    is_12818 = graph_node_map.get("IS 12818:2010")
    assert is_12818 is not None
    attrs = is_12818.get("technical_attributes", {})
    assert attrs.get("diameter_range") is None
    assert attrs.get("screen_slot_range") is None
    assert is_12818.get("scope_status") == "official_title_verified"

    # IS 16651 steel grades must be null until official standard document verification
    is_16651 = graph_node_map.get("IS 16651:2017")
    assert is_16651 is not None
    attrs_ss = is_16651.get("technical_attributes", {})
    assert attrs_ss.get("steel_grades") is None

    # IS 16415 composite cement has verified blend limits
    is_16415 = graph_node_map.get("IS 16415:2015")
    assert is_16415 is not None
    blend = is_16415.get("technical_attributes", {})
    assert blend.get("fly_ash_percentage_by_mass", {}).get("min") == 10
    assert blend.get("fly_ash_percentage_by_mass", {}).get("max") == 25
    assert blend.get("granulated_slag_percentage_by_mass", {}).get("min") == 25
    assert blend.get("granulated_slag_percentage_by_mass", {}).get("max") == 40


def test_batch_2_cables_and_conductors(graph_node_map):
    # IS 1554 Part 2: heavy duty cable 3.3 to 11 kV
    is_1554_2 = graph_node_map.get("IS 1554 (Part 2):1988")
    assert is_1554_2 is not None
    attrs = is_1554_2.get("technical_attributes", {})
    assert attrs.get("voltage_minimum_kv", {}).get("value") == 3.3
    assert attrs.get("voltage_maximum_kv", {}).get("value") == 11.0
    assert attrs.get("armoured", {}).get("value") is True
    assert attrs.get("unarmoured", {}).get("value") is None

    # IS 398 Part 4: AAAC overhead transmission
    is_398_4 = graph_node_map.get("IS 398 (Part 4):1994")
    assert is_398_4 is not None
    attrs_4 = is_398_4.get("technical_attributes", {})
    assert attrs_4.get("abbreviation") == "AAAC"
    assert attrs_4.get("maximum_actual_stranded_area_mm2", {}).get("value") == 767

    # IS 398 Part 5: EHV ACSR 400 kV+ with amalgamation warning
    is_398_5 = graph_node_map.get("IS 398 (Part 5):1992")
    assert is_398_5 is not None
    attrs_5 = is_398_5.get("technical_attributes", {})
    assert attrs_5.get("minimum_voltage_kv", {}).get("value") == 400.0
    assert "IS 398 Part 2:2025" in is_398_5.get("lifecycle_warning", "")

    # IS 731: Porcelain insulators > 1000 V
    is_731 = graph_node_map.get("IS 731:1971")
    assert is_731 is not None
    attrs_731 = is_731.get("technical_attributes", {})
    assert attrs_731.get("nominal_voltage_condition") == "> 1000 V"
    assert attrs_731.get("pin_disc_classification", {}).get("value") is None


def test_batch_2_piping_negative_and_boundary_rules(graph_node_map):
    # IS 651: Glazed stoneware pipes strictly NOT for potable water
    is_651 = graph_node_map.get("IS 651:2007")
    assert is_651 is not None
    assert is_651.get("potable_water") is False
    attrs_651 = is_651.get("technical_attributes", {})
    assert attrs_651.get("potable_water", {}).get("value") is False
    assert 100 in attrs_651.get("internal_diameter_mm", [])

    # IS 13592: PVC-U soil/waste pipes NOT for potable water, Type A/B boundaries
    is_13592 = graph_node_map.get("IS 13592:2013")
    assert is_13592 is not None
    assert is_13592.get("potable_water") is False
    attrs_13592 = is_13592.get("technical_attributes", {})
    assert attrs_13592.get("type_A", {}).get("nominal_outside_diameter_mm") == "40–160"
    assert attrs_13592.get("type_B", {}).get("nominal_outside_diameter_mm") == "40–315"

    # IS 1592: Asbestos cement pressure pipes verified classes
    is_1592 = graph_node_map.get("IS 1592:2003")
    assert is_1592 is not None
    attrs_1592 = is_1592.get("technical_attributes", {})
    assert attrs_1592.get("pressure_classes_verified") == [10, 15, 20, 25]
    assert attrs_1592.get("potable_water_status", {}).get("value") is None


def test_batch_2_masonry_attributes_and_guardrails(graph_node_map):
    # IS 2185 Part 1: Hollow/Solid concrete blocks Grade A/B/C
    is_2185 = graph_node_map.get("IS 2185 (Part 1):2005")
    assert is_2185 is not None
    attrs_2185 = is_2185.get("technical_attributes", {})
    assert 15.0 in attrs_2185.get("hollow_block_grades", {}).get("A_MPa", [])
    assert 5.0 in attrs_2185.get("solid_block_grades", {}).get("C_MPa", [])

    # IS 14862: Fibre-cement sheets thickness 3 to 30 mm
    is_14862 = graph_node_map.get("IS 14862:2000")
    assert is_14862 is not None
    attrs_14862 = is_14862.get("technical_attributes", {})
    assert attrs_14862.get("thickness_range_mm", {}).get("min") == 3
    assert attrs_14862.get("thickness_range_mm", {}).get("max") == 30
    assert attrs_14862.get("internal_external_exposure", {}).get("value") is None

    # IS 16720: Fly ash-cement bricks min 35% fly ash
    is_16720 = graph_node_map.get("IS 16720:2018")
    assert is_16720 is not None
    attrs_16720 = is_16720.get("technical_attributes", {})
    assert attrs_16720.get("fly_ash_minimum_percent_by_mass", {}).get("value") == 35
    assert 15 in attrs_16720.get("wet_compressive_strength_classes_MPa", [])

    # IS 16526: APP membrane with glass fibre reinforcement
    is_16526 = graph_node_map.get("IS 16526:2017")
    assert is_16526 is not None
    attrs_16526 = is_16526.get("technical_attributes", {})
    assert attrs_16526.get("reinforcement", {}).get("value") == "glass fibre"
    assert attrs_16526.get("thickness_range", {}).get("value") is None


def test_batch_3_structural_steel_and_fasteners(graph_node_map):
    # IS 2062:2011 structural steel
    is_2062 = graph_node_map.get("IS 2062:2011")
    assert is_2062 is not None
    assert is_2062.get("standard_role") == "PRIMARY_PRODUCT"
    attrs_2062 = is_2062.get("technical_attributes", {})
    assert "E250" in attrs_2062.get("grades", [])
    assert "E650" in attrs_2062.get("grades", [])
    assert attrs_2062.get("qualities", {}).get("E250") == ["A", "BR", "B0", "C"]
    assert attrs_2062.get("qualities", {}).get("E350") == ["A", "BR"]
    assert is_2062.get("mandatory_certification") is True

    # Fasteners: IS 1363 and IS 1367 classified as COMPONENT
    is_1363 = graph_node_map.get("IS 1363")
    assert is_1363 is not None
    assert is_1363.get("standard_role") == "COMPONENT"

    is_1367 = graph_node_map.get("IS 1367")
    assert is_1367 is not None
    assert is_1367.get("standard_role") == "COMPONENT"


def test_batch_3_sanitary_and_switchgear(graph_node_map):
    # IS 2556 Part 2:2024 Washdown WC
    is_2556_2 = graph_node_map.get("IS 2556 (Part 2):2024")
    assert is_2556_2 is not None
    assert is_2556_2.get("standard_role") == "PRIMARY_PRODUCT"
    assert "IS 2556 (Part 2):2004" in is_2556_2.get("supersedes", [])

    # IS 2556 Part 3:2024 Squatting pans
    is_2556_3 = graph_node_map.get("IS 2556 (Part 3):2024")
    assert is_2556_3 is not None
    assert is_2556_3.get("standard_role") == "PRIMARY_PRODUCT"
    assert "IS 2556 (Part 3):2004" in is_2556_3.get("supersedes", [])

    # IS/IEC 60898-1:2015 MCB
    mcb = graph_node_map.get("IS/IEC 60898-1:2015")
    assert mcb is not None
    assert mcb.get("standard_role") == "PRIMARY_PRODUCT"
    attrs_mcb = mcb.get("technical_attributes", {})
    assert attrs_mcb.get("rated_voltage_max_v") == 440
    assert attrs_mcb.get("rated_current_max_a") == 125
    assert attrs_mcb.get("rated_short_circuit_capacity_max_a") == 25000
    assert attrs_mcb.get("frequency_hz") == 50

    # IS 3043:2018 Earthing Code
    earthing = graph_node_map.get("IS 3043:2018")
    assert earthing is not None
    assert earthing.get("standard_role") == "DESIGN_CODE"
    assert earthing.get("product_standard") is False


def test_batch_4_switchgear_pipes_and_rmc(graph_node_map):
    # IS/IEC 60947-2:2016 Industrial Circuit Breakers
    mccb = graph_node_map.get("IS/IEC 60947-2:2016")
    assert mccb is not None
    assert mccb.get("standard_role") == "PRIMARY_PRODUCT"
    attrs_mccb = mccb.get("technical_attributes", {})
    assert "MCCB" in attrs_mccb.get("product_family", [])
    assert "ACB" in attrs_mccb.get("product_family", [])
    assert attrs_mccb.get("voltage_max_ac_v") == 1000
    assert attrs_mccb.get("voltage_max_dc_v") == 1500
    assert attrs_mccb.get("certification_scheme") == "Scheme X"

    # IS 4985:2021 Potable Water uPVC Pipes
    upvc = graph_node_map.get("IS 4985:2021")
    assert upvc is not None
    assert upvc.get("standard_role") == "PRIMARY_PRODUCT"
    attrs_upvc = upvc.get("technical_attributes", {})
    assert attrs_upvc.get("application") == "potable-water supply"
    assert upvc.get("mandatory_certification") is True

    # IS 383:2016 Coarse and Fine Concrete Aggregates (Material Specification / Component)
    agg = graph_node_map.get("IS 383:2016")
    assert agg is not None
    assert agg.get("standard_role") == "COMPONENT"
    attrs_agg = agg.get("technical_attributes", {})
    assert "Zone I" in attrs_agg.get("fine_aggregate_grading_zones", [])
    assert 20 in attrs_agg.get("coarse_aggregate_graded_sizes_mm", [])

    # IS 12615:2026 Three-Phase AC Motors (IE2/IE3/IE4)
    motor_2026 = graph_node_map.get("IS 12615:2026")
    assert motor_2026 is not None
    assert motor_2026.get("standard_role") == "PRIMARY_PRODUCT"
    assert motor_2026.get("status") == "PUBLISHED_CURRENT"
    assert "IS 12615:2018" in motor_2026.get("supersedes", [])

    motor_2018 = graph_node_map.get("IS 12615:2018")
    assert motor_2018 is not None
    assert motor_2018.get("status") == "SUPERSEDED"

    # IS 4926:2003 Ready-Mixed Concrete Production & Supply Code of Practice
    rmc = graph_node_map.get("IS 4926:2003")
    assert rmc is not None
    assert rmc.get("standard_role") in ("DESIGN_CODE", "PRIMARY_PRODUCT")




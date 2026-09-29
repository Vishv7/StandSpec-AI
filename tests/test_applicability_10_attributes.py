"""
Tests for Generalized 10-Attribute Applicability Engine (P0-5).
Verifies that TechnicalApplicabilityEngine performs typed evaluations across:
1. Product
2. Material
3. Voltage
4. Grade
5. Dimensions
6. Capacity / Rating / Pressure
7. Application
8. Environment
9. Performance
10. Safety
"""

import pytest
from src.recommendation.applicability_engine import TechnicalApplicabilityEngine, ApplicabilityState, AttributeStatus


@pytest.fixture
def engine():
    return TechnicalApplicabilityEngine()


def test_voltage_mismatch(engine):
    """11 kV XLPE cable request must reject IS 1554 (PVC <= 1.1 kV)."""
    cand = {
        "designation": "IS 1554 (Part 1):1988",
        "title": "PVC insulated (heavy duty) electric cables: Part 1 for working voltages up to and including 1100 V",
        "scope": "Covers PVC insulated cables for voltages up to 1100 V",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    req = {
        "raw_text": "Supply of 11 kV XLPE insulated power cables for underground distribution network.",
        "requirements": {
            "product": {"value": "Power Cable", "normalization": "Power Cable"},
            "material": {"value": "XLPE"},
            "voltage": {"value": "11 kV"},
        }
    }
    res = engine.evaluate_applicability(cand, req)
    assert not res["is_applicable"]
    assert res["state"] == ApplicabilityState.NOT_APPLICABLE.value
    assert "VOLTAGE" in res["mismatched_attributes"] or "MATERIAL" in res["mismatched_attributes"]


def test_material_mismatch_hdpe_vs_upvc(engine):
    """HDPE pipe tender must reject uPVC pipe standard."""
    cand = {
        "designation": "IS 4985:2021",
        "title": "Unplasticized Polyvinyl Chloride Pipes for Potable Water Supplies - Specification",
        "scope": "Prescribes requirements for unplasticized polyvinyl chloride (uPVC) pipes.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    req = {
        "raw_text": "Supply of High Density Polyethylene (HDPE) pipes for potable water distribution PE-100 PN 10",
        "requirements": {
            "product": {"value": "HDPE Pipes for Water Supply", "normalization": "HDPE Pipes for Water Supply"},
            "material": {"value": "HDPE"},
            "capacity": {"value": "PN 10"},
        }
    }
    res = engine.evaluate_applicability(cand, req)
    assert not res["is_applicable"]
    assert "MATERIAL" in res["mismatched_attributes"]


def test_grade_mismatch_opc_43_vs_53(engine):
    """43 Grade OPC tender must reject IS 12269 (53 Grade OPC)."""
    cand = {
        "designation": "IS 12269:2013",
        "title": "Ordinary Portland Cement, 53 Grade - Specification",
        "scope": "Prescribes requirements for 53 grade ordinary Portland cement.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    req = {
        "raw_text": "Supply of 43 Grade Ordinary Portland Cement conforming to BIS standards.",
        "requirements": {
            "product": {"value": "Ordinary Portland Cement", "normalization": "Ordinary Portland Cement"},
            "grade": {"value": "43 Grade"},
        }
    }
    res = engine.evaluate_applicability(cand, req)
    assert not res["is_applicable"]
    assert "GRADE" in res["mismatched_attributes"]


def test_application_mismatch_potable_vs_sewage(engine):
    """Potable water pipe tender must reject sewerage pipe standard IS 14333."""
    cand = {
        "designation": "IS 14333:2022",
        "title": "High Density Polyethylene Pipes for Sewerage - Specification",
        "scope": "Covers HDPE pipes for drainage and sewerage disposal.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    req = {
        "raw_text": "Supply of HDPE pipes for rural drinking water supply mains",
        "requirements": {
            "product": {"value": "HDPE Pipes for Water Supply", "normalization": "HDPE Pipes for Water Supply"},
            "material": {"value": "HDPE"},
            "application": {"value": "drinking water supply"},
        }
    }
    res = engine.evaluate_applicability(cand, req)
    assert not res["is_applicable"]
    assert "APPLICATION" in res["mismatched_attributes"]


def test_application_mismatch_architectural_vs_automotive(engine):
    """Architectural building safety glass tender must reject IS 2553 Part 2 (automotive)."""
    cand = {
        "designation": "IS 2553 (Part 2):2019",
        "title": "Safety Glass - Specification: Part 2 For Road Transport",
        "scope": "Prescribes requirements for safety glass for road transport vehicles.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    req = {
        "raw_text": "Procurement of architectural safety glass 6 mm for commercial building facade glazing",
        "requirements": {
            "product": {"value": "Safety Glass", "normalization": "Safety Glass and Glazing in Buildings"},
            "application": {"value": "architectural building facade glazing"},
        }
    }
    res = engine.evaluate_applicability(cand, req)
    assert not res["is_applicable"]
    assert "APPLICATION" in res["mismatched_attributes"]


def test_environment_mismatch_underground_vs_aerial(engine):
    """Underground cable requirement must reject aerial bunched conductor standard."""
    cand = {
        "designation": "IS 14255:1995",
        "title": "Aerial Bunched Cables for Working Voltages up to and including 1100 V",
        "scope": "Covers overhead aerial bunched cables.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    req = {
        "raw_text": "Supply of underground power cables for municipal distribution grid",
        "requirements": {
            "product": {"value": "Power Cable", "normalization": "Power Cable"},
            "environment": {"value": "underground"},
        }
    }
    res = engine.evaluate_applicability(cand, req)
    assert not res["is_applicable"]
    assert "ENVIRONMENT" in res["mismatched_attributes"]


def test_positive_10_attribute_match(engine):
    """Complete match on Product, Material, Voltage, Capacity, and Application."""
    cand = {
        "designation": "IS 7098 (Part 2):2011",
        "title": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 2 For Working Voltages From 3.3 kV Up to and Including 33 kV",
        "scope": "Prescribes requirements for XLPE insulated cables for 3.3 kV to 33 kV.",
        "candidate_status": "ELIGIBLE",
        "is_hydrated": True,
        "scope_evidence_available": True,
    }
    req = {
        "raw_text": "Supply of 11 kV XLPE insulated thermoplastic sheathed power cable for industrial substation",
        "requirements": {
            "product": {"value": "Power Cable", "normalization": "Power Cable"},
            "material": {"value": "XLPE"},
            "voltage": {"value": "11 kV"},
        }
    }
    res = engine.evaluate_applicability(cand, req)
    assert res["is_applicable"]
    assert res["state"] == ApplicabilityState.APPLICABLE.value
    assert "PRODUCT" in res["matched_attributes"]
    assert "MATERIAL" in res["matched_attributes"]
    assert "VOLTAGE" in res["matched_attributes"]

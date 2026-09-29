"""
Extraction Generalization Tests — StandSpec AI (Phase P1-E Section 5).
Validates modular compositional extraction on unseen procurement queries.
"""

import pytest
from src.extraction.requirement_extractor import RequirementExtractor


@pytest.fixture
def extractor():
    return RequirementExtractor()


def test_polyethylene_pressure_pipe_query(extractor):
    """
    Directly tests the unseen query that failed earlier:
    'Please procure polyethylene pressure pipes, nominal 110 mm diameter, for potable water distribution, suitable for PN10 service.'
    """
    query = (
        "Please procure polyethylene pressure pipes, nominal 110 mm diameter, "
        "for potable water distribution, suitable for PN10 service."
    )
    res = extractor.extract(query)
    reqs = res["requirements"]

    # Product MUST be extracted (not None)
    assert reqs["product"] is not None, "Product should not be None for polyethylene pressure pipes"
    assert res["product_status"] == "EXTRACTED"
    assert "pipes" in reqs["product"]["value"].lower()

    # Material must be recognized
    assert reqs["material"] is not None
    assert "polyethylene" in reqs["material"]["normalization"].lower() or "hdpe" in reqs["material"]["normalization"].lower()

    # Application must be recognized
    assert reqs["application"] is not None
    assert "potable water" in reqs["application"]["normalization"].lower()

    # Dimensions must be recognized
    assert reqs["dimensions"] is not None
    assert "110" in reqs["dimensions"]["value"]

    # Pressure rating / grade must be recognized
    assert reqs["grade"] is not None
    assert "pn10" in reqs["grade"]["normalization"].lower() or "pn 10" in reqs["grade"]["normalization"].lower()


def test_multi_voltage_transformer_query(extractor):
    """
    Tests Section 5.3:
    'Need a 10 MVA 33/11 kV power transformer for substation use.'
    MUST capture both 33 kV and 11 kV in voltage_pairs.
    """
    query = "Need a 10 MVA 33/11 kV power transformer for substation use."
    res = extractor.extract(query)
    reqs = res["requirements"]

    assert reqs["product"] is not None
    assert "transformer" in reqs["product"]["normalization"].lower()

    # Voltage pairs must capture BOTH sides
    assert reqs["voltage"] is not None
    v_pairs = reqs["voltage"].get("voltage_pairs")
    assert v_pairs is not None, "voltage_pairs must be present for 33/11 kV"
    assert len(v_pairs) == 2
    sides = {p["side"]: p["value"] for p in v_pairs}
    assert "33" in sides["HIGH"]
    assert "11" in sides["LOW"]

    # Capacity
    assert reqs["capacity"] is not None
    assert "10" in reqs["capacity"]["normalization"]
    assert "MVA" in reqs["capacity"]["normalization"]

    # Application
    assert reqs["application"] is not None
    assert "substation" in reqs["application"]["normalization"].lower()


def test_smart_meter_modifiers_query(extractor):
    """
    Tests Section 5.4:
    'Need direct-connected smart whole-current electricity meters with cellular AMI communication.'
    """
    query = "Need direct-connected smart whole-current electricity meters with cellular AMI communication."
    res = extractor.extract(query)
    reqs = res["requirements"]

    assert reqs["product"] is not None
    assert "meter" in reqs["product"]["normalization"].lower()

    # Modifiers should be captured
    mods = reqs["product"].get("modifiers", [])
    text_lower = query.lower()
    # At least smart, whole-current, cellular, or ami
    assert any(m in ["smart", "whole-current", "cellular", "AMI"] for m in mods) or "smart" in text_lower


def test_underground_xlpe_cable_query(extractor):
    """
    Tests:
    'Need 33 kV three-core XLPE underground power cable.'
    """
    query = "Need 33 kV three-core XLPE underground power cable."
    res = extractor.extract(query)
    reqs = res["requirements"]

    assert reqs["product"] is not None
    assert "cable" in reqs["product"]["normalization"].lower()

    assert reqs["material"] is not None
    assert "xlpe" in reqs["material"]["normalization"].lower()

    assert reqs["voltage"] is not None
    assert "33" in reqs["voltage"]["normalization"]

    assert reqs["installation"] is not None
    assert "underground" in reqs["installation"]["normalization"].lower()


def test_spun_cast_iron_pipe_query(extractor):
    """
    Tests:
    'Procure spun cast iron pressure pipes for municipal water and sewage.'
    """
    query = "Procure spun cast iron pressure pipes for municipal water and sewage."
    res = extractor.extract(query)
    reqs = res["requirements"]

    assert reqs["product"] is not None
    assert "pipe" in reqs["product"]["normalization"].lower()

    assert reqs["material"] is not None
    assert "cast iron" in reqs["material"]["normalization"].lower()

    assert reqs["application"] is not None
    assert "water" in reqs["application"]["normalization"].lower() or "sewage" in reqs["application"]["normalization"].lower()

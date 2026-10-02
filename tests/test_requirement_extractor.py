"""
Tests for Procurement Requirement Extraction Subsystem (Phase 6).
Verifies schema compliance, source-span grounding, normalization, and multilingual detection.
"""

import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

from src.extraction.requirement_extractor import RequirementExtractor
from src.extraction.normalizer import (
    detect_language,
    normalize_voltage,
    normalize_frequency,
    normalize_dimensions,
)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "normalized_requirement.schema.json"


@pytest.fixture
def requirement_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_extraction_produces_valid_schema(requirement_schema):
    """Extracted NormalizedRequirementObject must validate against its JSON schema."""
    extractor = RequirementExtractor()
    tender_text = (
        "Supply of 11 kV Grade XLPE Insulated Aluminium Conductor Power Cable "
        "size 3 x 300 sq.mm for underground direct burial with FRLS outer sheath, "
        "routine testing as per IS 10810, required for 50 Hz substation on 2026-05-10."
    )
    result = extractor.extract(tender_text, query_id="Q_ETD_001")

    validator = Draft202012Validator(requirement_schema)
    errors = list(validator.iter_errors(result))
    assert len(errors) == 0, f"Schema validation failed: {[e.message for e in errors]}"


def test_every_field_has_source_span():
    """Every extracted technical attribute MUST contain an exact source_span found in raw_text."""
    extractor = RequirementExtractor()
    tender_text = (
        "Supply of 33 kV XLPE insulated copper cable 3 x 240 sq.mm for underground feeder."
    )
    result = extractor.extract(tender_text, query_id="Q_TEST_001")
    reqs = result["requirements"]

    for field_name, field_obj in reqs.items():
        if field_obj is not None:
            assert "value" in field_obj
            assert "confidence" in field_obj
            assert "source_span" in field_obj
            assert field_obj["source_span"] in tender_text, (
                f"Field '{field_name}' source_span '{field_obj['source_span']}' not found in raw text!"
            )


def test_voltage_normalization():
    """kV and V representations must normalize accurately to numeric volts."""
    assert normalize_voltage("11 kV grade") == "11000 V"
    assert normalize_voltage("33 kV") == "33000 V"
    assert normalize_voltage("415 V") == "415 V"
    assert normalize_voltage("1.1 kV") == "1100 V"


def test_dimension_normalization():
    """Dimensions should be normalized to canonical mm² notation."""
    assert normalize_dimensions("3 x 300 sq.mm") == "3x300 mm²"
    assert normalize_dimensions("4 core 16 sqmm") == "4core*16 mm²" or "16 mm²" in normalize_dimensions("4 core 16 sqmm")


def test_multilingual_language_detection():
    """Language detector must correctly classify English, Hindi, Gujarati, and Hinglish."""
    # English
    en_meta = detect_language("Supply of 11 kV XLPE cable for substation.")
    assert en_meta["detected"] == "en"

    # Hindi (Devanagari)
    hi_meta = detect_language("11 केवी एक्सएलपीई अंडरग्राउंड केबल की आपूर्ति")
    assert hi_meta["detected"] == "hi"
    assert hi_meta["contains_hindi"] is True

    # Gujarati
    gu_meta = detect_language("11 કેવી અંડરગ્રાઉન્ડ કેબલ સપ્લાય ટેન્ડર")
    assert gu_meta["detected"] == "gu"
    assert gu_meta["contains_gujarati"] is True

    # Hinglish
    hinglish_meta = detect_language("Substation ke liye 11 kV underground taar chahiye.")
    assert hinglish_meta["detected"] == "hinglish"
    assert hinglish_meta["contains_hinglish"] is True


def test_missing_discriminator_detection():
    """Missing critical attributes must be flagged in missing_discriminators."""
    extractor = RequirementExtractor()
    # Incomplete cable description: mentions cable but no voltage or dimensions
    ambiguous_text = "Supply of electric power cable for general project."
    result = extractor.extract(ambiguous_text, query_id="Q_AMBIG_001")

    missing = result["missing_discriminators"]
    assert "voltage_rating" in missing
    assert "conductor_cross_section_dimensions" in missing


def test_offsets_grounding_invariant():
    """start_char and end_char must exactly slice the source_span from raw_text."""
    extractor = RequirementExtractor()
    tender_text = "Supply of 33 kV Grade XLPE Insulated Aluminium Conductor Power Cable 3 x 240 sq.mm for underground installation."
    result = extractor.extract(tender_text)
    reqs = result["requirements"]

    for field_name, field_obj in reqs.items():
        if field_obj is not None:
            s = field_obj.get("start_char")
            e = field_obj.get("end_char")
            assert s is not None and e is not None, f"Offsets missing for {field_name}"
            assert tender_text[s:e] == field_obj["source_span"], (
                f"Offset slice '{tender_text[s:e]}' does not match source_span '{field_obj['source_span']}'"
            )


def test_out_of_domain_product_missing():
    """Out-of-domain query must NOT fabricate a placeholder product like 'General Procurement Item'."""
    extractor = RequirementExtractor()
    ood_text = "Supply of industrial bananas for food processing facility."
    result = extractor.extract(ood_text)

    assert result["requirements"]["product"] is None
    assert result["product_status"] == "MISSING"


def test_deterministic_input_hash():
    """Identical raw text must produce identical input_hash and identical requirements."""
    extractor = RequirementExtractor()
    text = "Procurement of 11 kV XLPE underground cable."
    res1 = extractor.extract(text)
    res2 = extractor.extract(text)

    assert res1["input_hash"] == res2["input_hash"]
    assert res1["requirements"] == res2["requirements"]
    assert res1["extractor_version"] == res2["extractor_version"]


def test_multilingual_semantic_equivalence():
    """Section 22: '110 mm ka HDPE paani ka pipe' and English equivalent produce matching technical product and material."""
    extractor = RequirementExtractor()
    hinglish_text = "110 mm ka HDPE paani ka pipe"
    english_text = "110 mm HDPE potable water pipe"

    res_hinglish = extractor.extract(hinglish_text)
    res_english = extractor.extract(english_text)

    # Product normalization matches
    assert res_hinglish["requirements"]["product"]["normalization"] == "HDPE Pipes for Water Supply"
    assert res_english["requirements"]["product"]["normalization"] == "HDPE Pipes for Water Supply"

    # Material normalization matches
    assert res_hinglish["requirements"]["material"]["normalization"] == "HDPE"
    assert res_english["requirements"]["material"]["normalization"] == "HDPE"

    # Dimensions preserved
    assert "110" in res_hinglish["requirements"]["dimensions"]["value"]
    assert "110" in res_english["requirements"]["dimensions"]["value"]


def test_longest_first_material_normalization():
    """Section 23: Compound materials must match before single-word substrings (e.g. stainless steel before steel)."""
    from src.extraction.normalizer import normalize_material
    assert normalize_material("stainless steel plate") == "Stainless Steel"
    assert normalize_material("high density polyethylene pipe") == "High Density Polyethylene (HDPE)"
    assert normalize_material("crosslinked polyethylene cable") == "Crosslinked Polyethylene (XLPE)"
    assert normalize_material("rapid hardening portland cement") == "Rapid Hardening Portland Cement"



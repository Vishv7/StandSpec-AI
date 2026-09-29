"""
Unit tests for StandSpec AI V2.1 JSON schemas:
- Layer 4: procurement_ground_truth.schema.json
- Layer 2: standards_lifecycle.schema.json
- Layer 3: regulatory_rules.schema.json

Validates schema compilation, valid instance acceptance, and invalid instance rejection.
"""

import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


@pytest.fixture(scope="module")
def procurement_schema():
    with open(SCHEMAS_DIR / "procurement_ground_truth.schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def lifecycle_schema():
    with open(SCHEMAS_DIR / "standards_lifecycle.schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    return schema


@pytest.fixture(scope="module")
def regulatory_schema():
    with open(SCHEMAS_DIR / "regulatory_rules.schema.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    return schema


def test_procurement_ground_truth_valid_record(procurement_schema):
    """Test that a fully compliant procurement record validates cleanly."""
    valid_record = {
        "query_id": "Q_ETD_104",
        "schema_version": "2.1",
        "dataset_split": "A_discovery",
        "source": {
            "type": "gem_procurement",
            "organization": "NTPC Limited",
            "tender_id": "GEM/2026/B/123456",
            "tender_publication_date": "2026-01-15",
            "evaluation_as_of_date": "2026-09-25",
            "portal_url": "https://gem.gov.in/tenders/123456"
        },
        "query": {
            "raw_text": "Supply of 11 kV Grade Crosslinked Polyethylene (XLPE) Insulated PVC Sheathed Armoured Aluminium Conductor Underground Power Cables.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Electrical Wires & Cables"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Underground Power Cable",
            "scope_keywords": ["XLPE", "cables", "armoured"],
            "material_grade": "Aluminium conductor, XLPE insulation, PVC outer sheath",
            "rating_capacity": "11 kV",
            "application": "Power Distribution",
            "environment": "Underground direct burial",
            "performance_thresholds": "FRLS compliance",
            "installation_method": "Direct burial in ground",
            "testing_requirements": "High voltage and spark testing",
            "packaging_marking": "BIS standard mark on outer sheath"
        },
        "gold_standards": [
            {
                "standard_designation": "IS 7098 (Part 2):2011",
                "applicability": "primary_product",
                "reason": "Covers XLPE insulated cables for working voltages from 3.3 kV up to 33 kV.",
                "evidence_span": "Clause 1.1: This standard covers the requirements of crosslinked polyethylene insulated and PVC sheathed cables for working voltages from 3.3 kV up to and including 33 kV.",
                "evidence_source_tier": 1,
                "relationship_obligation": "MANDATORY",
                "mandatory_by_regulation": True
            }
        ],
        "allied_standards": [
            {
                "standard_designation": "IS 10810 (Part 53):1984",
                "relationship": "test_method",
                "obligation": "MANDATORY",
                "reason": "Prescribes flammability test method required by IS 7098 Part 2.",
                "evidence_span": "Clause 16.2 flammability test shall be conducted in accordance with IS 10810 (Part 53)."
            }
        ],
        "hard_negatives": [
            {
                "standard_designation": "IS 1554 (Part 2):1988",
                "hn_class": "HN3",
                "confusability_reason": "Same voltage rating (up to 33 kV) and power cable application.",
                "rejection_reason": "IS 1554 covers PVC insulation, whereas tender specifies XLPE insulation.",
                "rejection_evidence_span": "Clause 1.1 specifies PVC insulation only.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 7098 (Part 1):1988",
                "hn_class": "HN1",
                "confusability_reason": "XLPE insulated cable standard from the same family.",
                "rejection_reason": "Part 1 covers cables for voltages up to 1.1 kV, but tender requires 11 kV.",
                "rejection_evidence_span": "Clause 1.1 specifies working voltages up to and including 1100 V.",
                "source_tier": 1
            }
        ],
        "version_requirement": {
            "policy": "latest_active_only",
            "acceptable_years": ["2011"]
        },
        "certification_requirement": {
            "regulatory_status": "MANDATORY",
            "certification_scheme": "Scheme I",
            "qco_order_reference": "DPIIT Electrical Wires and Cables (Quality Control) Order, 2023",
            "enforcement_date": "2023-11-10",
            "exemptions": ["Export-only manufacturing"]
        },
        "expected_decision": {
            "query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE"
        },
        "expert_review": {
            "reviewers_count": 2,
            "reviewer_ids": ["EXPERT_ETD_01", "EXPERT_ETD_02"],
            "confidence_score": 1.0,
            "agreement_status": "unanimous"
        }
    }
    validator = Draft202012Validator(procurement_schema)
    errors = list(validator.iter_errors(valid_record))
    assert len(errors) == 0, f"Validation failed with errors: {errors}"


def test_procurement_ground_truth_rejects_missing_required(procurement_schema):
    """Test that records missing required fields are rejected."""
    invalid_record = {
        "query_id": "Q_ETD_105",
        "schema_version": "2.1",
    }
    validator = Draft202012Validator(procurement_schema)
    errors = list(validator.iter_errors(invalid_record))
    assert len(errors) > 0
    err_msgs = [e.message for e in errors]
    assert any("'benchmark_dimensions' is a required property" in msg for msg in err_msgs)


def test_standards_lifecycle_valid_record(lifecycle_schema):
    """Test that a compliant standards lifecycle record validates cleanly."""
    valid_record = {
        "standard_designation": "IS 7098 (Part 2):2011",
        "schema_version": "1.0",
        "lifecycle_status": "ACTIVE",
        "publication_date": "2011-08-15",
        "effective_date": "2011-08-15",
        "reaffirmation_year": 2021,
        "reaffirmation_history": [
            {"year": 2016, "gazette_reference": "G.S.R. 123/2016"},
            {"year": 2021, "gazette_reference": "G.S.R. 456/2021"}
        ],
        "predecessors": [
            {
                "designation": "IS 7098 (Part 2):1985",
                "relationship": "supersedes",
                "effective_date": "2011-08-15"
            }
        ],
        "amendments": [
            {
                "amendment_number": 1,
                "date": "2015-03-01",
                "description": "Modified conductor tensile test requirements in Clause 8"
            }
        ],
        "provenance": {
            "source_tier": 1,
            "source_document": "BIS Manakonline Official Gazette",
            "verification_status": "VERIFIED",
            "extraction_timestamp": "2026-09-25T12:00:00Z"
        }
    }
    validator = Draft202012Validator(lifecycle_schema)
    errors = list(validator.iter_errors(valid_record))
    assert len(errors) == 0, f"Validation failed with errors: {errors}"


def test_standards_lifecycle_rejects_invalid_status(lifecycle_schema):
    """Test that invalid lifecycle status is rejected."""
    invalid_record = {
        "standard_designation": "IS 7098 (Part 2):2011",
        "schema_version": "1.0",
        "lifecycle_status": "INVALID_STATUS",
        "provenance": {
            "source_tier": 1,
            "source_document": "BIS Gazette",
            "verification_status": "VERIFIED"
        }
    }
    validator = Draft202012Validator(lifecycle_schema)
    errors = list(validator.iter_errors(invalid_record))
    assert len(errors) > 0
    assert any("lifecycle_status" in str(e) for e in errors)


def test_regulatory_rules_valid_record(regulatory_schema):
    """Test that a compliant regulatory rules record validates cleanly."""
    valid_record = {
        "rule_id": "QCO_DPIIT_2023_ElectricalWires",
        "schema_version": "1.0",
        "rule_type": "quality_control_order",
        "regulatory_status": "IN_FORCE",
        "issuing_authority": {
            "ministry": "Ministry of Commerce and Industry",
            "department": "Department for Promotion of Industry and Internal Trade (DPIIT)"
        },
        "order_details": {
            "order_title": "Electrical Wires and Cables (Quality Control) Order, 2023",
            "order_number": "S.O. 2023/ETD/01",
            "gazette_date": "2023-05-10",
            "enforcement_date": "2023-11-10",
            "gazette_url": "https://dpiit.gov.in/qco/electrical_cables_2023.pdf"
        },
        "certification_scheme": "Scheme I",
        "applicable_standards": [
            {
                "standard_designation": "IS 7098 (Part 2):2011",
                "product_description": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables"
            }
        ],
        "exemptions": [
            {
                "exemption_type": "export_only",
                "description": "Cables manufactured exclusively for overseas export",
                "clause_reference": "Clause 3(2)"
            }
        ],
        "provenance": {
            "source_tier": 1,
            "source_document": "DPIIT Gazette Notification S.O. 2023/ETD/01",
            "verification_status": "VERIFIED",
            "extraction_timestamp": "2026-09-25T12:00:00Z"
        }
    }
    validator = Draft202012Validator(regulatory_schema)
    errors = list(validator.iter_errors(valid_record))
    assert len(errors) == 0, f"Validation failed with errors: {errors}"


def test_regulatory_rules_rejects_empty_applicable_standards(regulatory_schema):
    """Test that regulatory rule with empty applicable_standards array is rejected."""
    invalid_record = {
        "rule_id": "QCO_DPIIT_2023_Empty",
        "schema_version": "1.0",
        "rule_type": "quality_control_order",
        "regulatory_status": "IN_FORCE",
        "applicable_standards": [],  # minItems: 1 violated
        "provenance": {
            "source_tier": 1,
            "source_document": "DPIIT Gazette",
            "verification_status": "VERIFIED"
        }
    }
    validator = Draft202012Validator(regulatory_schema)
    errors = list(validator.iter_errors(invalid_record))
    assert len(errors) > 0
    assert any("applicable_standards" in str(e) for e in errors)


def test_standard_v1_2_validation():
    """Verify that a canonical V1.2 standard record validates and invalid records are caught."""
    from src.validators import validate_standard_v1_2
    
    valid_record = {
        "record_version": "1.2",
        "input": {
            "source_file": "ETD.xlsx",
            "source_sheet": "Sheet1",
            "source_row": 2,
            "raw_standard_number": "IS 7098 (Part 2):2011",
            "raw_title": "XLPE Insulated Cables"
        },
        "raw_excel": {
            "sheet_name": "Sheet1",
            "row_number": 2,
            "row_sha256": "abc123hash",
            "columns": {"Standard Number": "IS 7098 (Part 2):2011"}
        },
        "identity": {
            "standard_designation": "IS 7098 (Part 2):2011",
            "family": "IS",
            "base_number": "7098",
            "part": "2",
            "section": None,
            "year": "2011"
        },
        "content": {
            "header_text": "IS 7098 (Part 2) : 2011 XLPE Cables",
            "title": "XLPE Insulated Cables",
            "title_source": "preview",
            "ics_raw": "ICS 29.060.20",
            "ics_codes": ["29.060.20"],
            "committee": "ETD 09",
            "scope": {
                "text": "This standard covers requirements for XLPE cables.",
                "status": "present",
                "reason": None,
                "extraction_method": "html_section",
                "scope_source_section": "SCOPE"
            },
            "national_foreword": {
                "text": None,
                "status": "absent",
                "reason": None,
                "extraction_method": None
            },
            "notes": {
                "items": [],
                "status": "absent",
                "reason": None,
                "extraction_method": None
            },
            "evidence_verified": True
        },
        "references": [],
        "source": {
            "verified_source_url": "https://standardsbis.bsbedge.com/BIS_SearchStandard.aspx?id=7098_2_2011",
            "candidate_urls": ["https://standardsbis.bsbedge.com/BIS_SearchStandard.aspx?id=7098_2_2011"],
            "identity_match": "match_version_verified"
        },
        "primary_status": "success",
        "quality": {
            "manual_review_required": False,
            "warnings": [],
            "errors": []
        }
    }
    errors = validate_standard_v1_2(valid_record)
    assert errors == [], f"Expected clean validation, got errors: {errors}"
    
    # Negative test: invalid primary_status and unexpected property
    invalid_record = dict(valid_record)
    invalid_record["primary_status"] = "INVALID_STATUS"
    invalid_record["illegal_field"] = "should_fail"
    errors = validate_standard_v1_2(invalid_record)
    assert len(errors) >= 2


def test_reference_v1_2_validation():
    """Verify that a structured reference record validates against reference_v1_2.schema.json."""
    from src.validators import validate_reference_v1_2
    
    valid_ref = {
        "source_standard": "IS 7098 (Part 2):2011",
        "target": {
            "designation": "IS 10810 (Part 53):1984",
            "family": "IS",
            "base_number": "10810",
            "part": "53",
            "section": None,
            "year": "1984",
            "semantic_type": "BIS_STANDARD"
        },
        "title": "Methods of test for cables: Part 53 Flammability test",
        "reference_type": "formal_reference",
        "relationship": "test_method",
        "relationship_confidence": "structural",
        "section": "REFERENCES",
        "evidence": {
            "text": "IS 10810 (Part 53) : 1984 Methods of test for cables: Part 53 Flammability test",
            "source_section": "REFERENCES",
            "extraction_method": "html_table_row",
            "complete": True,
            "continuation_resolved": False
        }
    }
    errors = validate_reference_v1_2(valid_ref)
    assert errors == [], f"Expected clean validation, got: {errors}"
    
    # Negative test: invalid relationship type
    invalid_ref = dict(valid_ref)
    invalid_ref["relationship"] = "non_canonical_rel"
    errors = validate_reference_v1_2(invalid_ref)
    assert len(errors) > 0

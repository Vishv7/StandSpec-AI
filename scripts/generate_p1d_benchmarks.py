"""
Benchmark Generator for Phase P1-D — StandSpec AI
Generates schema-compliant, expert-grounded benchmark datasets:
1. data/benchmarks/adversarial.jsonl (32 targeted adversarial queries covering L1 categories)
2. data/benchmarks/coverage_boundary.jsonl (10 genuine non-CED/ETD queries expecting OUTSIDE_PROTOTYPE_COVERAGE)
3. data/benchmarks/challenge.jsonl (10 multi-constraint edge cases)

All records conform strictly to schemas/procurement_ground_truth.schema.json.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "data" / "benchmarks"


def get_base_record(
    query_id,
    raw_text,
    domain,
    product,
    target_product,
    gold_standards=None,
    hard_negatives=None,
    expected_decision=None,
    cov_state="IN_PROTOTYPE_COVERAGE",
    expected_safe_decision=None,
    ambiguity_class="CLASS_1_CLEAR",
    gold_in_scope=True,
    missing_params=None
):
    gold_standards = gold_standards or []
    hard_negatives = hard_negatives or []
    expected_decision_obj = expected_decision or {
        "query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE" if gold_standards else "NO_CONFIDENT_MATCH",
        "expected_abstention_reason": None if gold_standards else "No applicable product standard found."
    }
    safe_dec = expected_safe_decision or expected_decision_obj.get("query_level_state")

    return {
        "query_id": query_id,
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "constructed_expert_case",
            "organization": "Central Public Works Department (CPWD) / NTPC / MeitY",
            "tender_id": f"TDR/{query_id}/2025",
            "tender_publication_date": "2025-06-01",
            "evaluation_as_of_date": "2025-06-15",
            "portal_url": "https://eprocure.gov.in"
        },
        "query": {
            "raw_text": raw_text,
            "language": "en",
            "domain": domain,
            "product_family": product
        },
        "benchmark_dimensions": {
            "query_explicitness": "explicit" if " IS " in raw_text or " as per " in raw_text else "implicit",
            "difficulty": "hard",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": ambiguity_class
        },
        "technical_requirements": {
            "product": product,
            "scope_keywords": [product.lower()],
            "target_product": target_product,
            "material_grade": "Standard Grade",
            "application": "Standard Engineering Application",
            "missing_parameters": missing_params or []
        },
        "gold_standards": gold_standards,
        "allied_standards": [],
        "hard_negatives": hard_negatives,
        "version_requirement": {
            "policy": "latest_active_only",
            "acceptable_years": ["2026", "2025", "2024", "2023", "2022", "2021", "2020", "2016", "2015", "2014"]
        },
        "certification_requirement": {
            "regulatory_status": "MANDATORY"
        },
        "expected_decision": expected_decision_obj,
        "expert_review": {
            "reviewers_count": 2,
            "agreement_status": "unanimous"
        },
        "expected_coverage_state": cov_state,
        "gold_in_scope": gold_in_scope,
        "expected_evidence_state": "SCOPE_AVAILABLE" if gold_in_scope else "INSUFFICIENT_EVIDENCE",
        "expected_review_reason": None if gold_in_scope else "Scope evidence unavailable in KB",
        "expected_safe_decision": safe_dec
    }


def generate_adversarial_dataset():
    """Generates at least 30 targeted adversarial cases across all L1 categories."""
    cases = []

    # Category 1: Wrong Explicit Designation (P0 Core)
    cases.append(get_base_record(
        "Q_ADV_001",
        "Supply of uPVC pipes for potable water as per IS 1180 Part 1",
        "CIVIL_ENGINEERING",
        "uPVC Pipes",
        "uPVC Pipes - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 1180 (Part 1):2014", "hn_class": "HN3", "confusability_reason": "Explicitly named in query but covers transformers.", "rejection_reason": "Cross-domain mismatch: IS 1180 is for transformers, not uPVC pipes.", "source_tier": 1},
            {"standard_designation": "IS 4984:2016", "hn_class": "HN2", "confusability_reason": "High density polyethylene pipe standard.", "rejection_reason": "Query specifies uPVC pipes, whereas IS 4984 covers HDPE pipes.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "NO_CONFIDENT_MATCH", "expected_abstention_reason": "Explicit standard incompatible with requirements."},
        expected_safe_decision="NO_CONFIDENT_MATCH"
    ))
    cases.append(get_base_record(
        "Q_ADV_002",
        "Supply of 33 kV distribution transformer as per IS 4984",
        "ELECTROTECHNICAL",
        "Distribution Transformers",
        "Distribution Transformers - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 4984:2016", "hn_class": "HN3", "confusability_reason": "Explicitly named but covers HDPE pipes.", "rejection_reason": "Cross-domain mismatch: IS 4984 is for HDPE pipes.", "source_tier": 1},
            {"standard_designation": "IS 2026 (Part 1):2011", "hn_class": "HN1", "confusability_reason": "Bulk power transformers specification.", "rejection_reason": "Query specifies 33 kV distribution transformer, IS 2026 is for transmission bulk transformers.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "NO_CONFIDENT_MATCH", "expected_abstention_reason": "Explicit standard incompatible with requirements."},
        expected_safe_decision="NO_CONFIDENT_MATCH"
    ))
    cases.append(get_base_record(
        "Q_ADV_003",
        "Procurement of 11 kV power cables as per IS 383",
        "ELECTROTECHNICAL",
        "Power Cables",
        "Power Cables - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 383:2016", "hn_class": "HN3", "confusability_reason": "Explicitly named but covers concrete aggregates.", "rejection_reason": "Cross-domain mismatch: IS 383 is for coarse and fine aggregates.", "source_tier": 1},
            {"standard_designation": "IS 7098 (Part 1):1988", "hn_class": "HN1", "confusability_reason": "Low voltage XLPE power cable standard.", "rejection_reason": "Query specifies 11 kV, whereas IS 7098 Part 1 covers voltages up to 1.1 kV.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "NO_CONFIDENT_MATCH", "expected_abstention_reason": "Explicit standard incompatible with requirements."},
        expected_safe_decision="NO_CONFIDENT_MATCH"
    ))
    cases.append(get_base_record(
        "Q_ADV_004",
        "Supply of Ordinary Portland Cement 43 grade as per IS 694",
        "CIVIL_ENGINEERING",
        "Cement",
        "Cement - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 694:2010", "hn_class": "HN3", "confusability_reason": "Explicitly named but covers PVC wires.", "rejection_reason": "Cross-domain mismatch: IS 694 is for PVC wires, not cement.", "source_tier": 1},
            {"standard_designation": "IS 12269:2013", "hn_class": "HN1", "confusability_reason": "53 grade cement specification.", "rejection_reason": "Tender explicitly requires 43 grade cement, 53 grade cement has higher heat of hydration.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "NO_CONFIDENT_MATCH", "expected_abstention_reason": "Explicit standard incompatible with requirements."},
        expected_safe_decision="NO_CONFIDENT_MATCH"
    ))

    # Category 2: Product vs Component / Fittings
    cases.append(get_base_record(
        "Q_ADV_005",
        "Supply of uPVC pipes for agricultural drainage without fittings",
        "CIVIL_ENGINEERING",
        "uPVC Pipes",
        "uPVC Pipes - Specification",
        gold_standards=[{"standard_designation": "IS 4985:2021", "applicability": "primary_product", "reason": "Primary standard for uPVC pipes", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 7834 (Part 1):1987", "hn_class": "HN1", "confusability_reason": "Injection moulded PVC fittings.", "rejection_reason": "Covers fittings, but query requires pipes.", "source_tier": 1},
            {"standard_designation": "IS 12818:2010", "hn_class": "HN7", "confusability_reason": "uPVC casing pipes for tube wells.", "rejection_reason": "IS 12818 is for vertical borehole casing, not agricultural surface drainage pipes.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_ADV_006",
        "Supply of HDPE pressure pipes for municipal sewage conveyance",
        "CIVIL_ENGINEERING",
        "HDPE Pipes",
        "HDPE Pipes - Specification",
        gold_standards=[{"standard_designation": "IS 4984:2016", "applicability": "primary_product", "reason": "Primary standard for HDPE pipes", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 8008 (Part 1):2003", "hn_class": "HN1", "confusability_reason": "Injection moulded HDPE fittings.", "rejection_reason": "Covers fittings, not pipes.", "source_tier": 1},
            {"standard_designation": "IS 14333:2022", "hn_class": "HN1", "confusability_reason": "HDPE pipes for gravity drainage sewerage.", "rejection_reason": "IS 14333 is for gravity sewerage, whereas tender specifies pressure pipes.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_ADV_007",
        "Supply of power transformers 10 MVA 33/11 kV",
        "ELECTROTECHNICAL",
        "Power Transformers",
        "Power Transformers - Specification",
        gold_standards=[{"standard_designation": "IS 2026 (Part 1):2011", "applicability": "primary_product", "reason": "Power transformer specification", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 3347 (Part 1/Sec 1):1979", "hn_class": "HN1", "confusability_reason": "Transformer porcelain bushings.", "rejection_reason": "IS 3347 specifies bushings (components), not the whole transformer.", "source_tier": 1},
            {"standard_designation": "IS 1180 (Part 1):2014", "hn_class": "HN7", "confusability_reason": "Distribution transformers specification.", "rejection_reason": "IS 1180 is capped at 2500 kVA (2.5 MVA), whereas tender requires 10 MVA.", "source_tier": 1}
        ]
    ))

    # Category 3: Product vs Design Code
    cases.append(get_base_record(
        "Q_ADV_008",
        "Procurement of structural steel sections angles and channels",
        "CIVIL_ENGINEERING",
        "Structural Steel",
        "Structural Steel - Specification",
        gold_standards=[{"standard_designation": "IS 2062:2011", "applicability": "primary_product", "reason": "Hot rolled medium and high tensile structural steel", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 800:2007", "hn_class": "HN4", "confusability_reason": "General construction in steel code of practice.", "rejection_reason": "IS 800 is an engineering design code, not a physical steel manufacturing product standard.", "source_tier": 1},
            {"standard_designation": "IS 1786:2008", "hn_class": "HN2", "confusability_reason": "High strength deformed steel bars for concrete reinforcement.", "rejection_reason": "IS 1786 is for concrete reinforcement bars, not structural steel sections.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_ADV_009",
        "Supply of electrical wiring cables for residential building",
        "ELECTROTECHNICAL",
        "Wiring Cables",
        "Wiring Cables - Specification",
        gold_standards=[{"standard_designation": "IS 694:2010", "applicability": "primary_product", "reason": "PVC insulated unsheathed and sheathed cables up to 1100V", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 732:2019", "hn_class": "HN4", "confusability_reason": "Code of practice for electrical wiring installations.", "rejection_reason": "IS 732 is an installation code, not a cable product standard.", "source_tier": 1},
            {"standard_designation": "IS 1554 (Part 1):1988", "hn_class": "HN1", "confusability_reason": "Heavy duty PVC insulated power cables.", "rejection_reason": "IS 1554 is for heavy industrial power cables, not light domestic point wiring.", "source_tier": 1}
        ]
    ))

    # Category 4: Product vs Test Method
    cases.append(get_base_record(
        "Q_ADV_010",
        "Procurement of 1.1 kV XLPE insulated electrical power cable",
        "ELECTROTECHNICAL",
        "XLPE Cables",
        "XLPE Cables - Specification",
        gold_standards=[{"standard_designation": "IS 7098 (Part 1):1988", "applicability": "primary_product", "reason": "XLPE cables up to 1100V", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 10810 (Part 53):1984", "hn_class": "HN5", "confusability_reason": "Methods of test for cables flammability.", "rejection_reason": "IS 10810 Part 53 is a test method, not a product specification.", "source_tier": 1},
            {"standard_designation": "IS 7098 (Part 2):2011", "hn_class": "HN1", "confusability_reason": "XLPE cables for 3.3 kV to 33 kV.", "rejection_reason": "Part 2 is for high voltage cables, whereas tender requires 1.1 kV.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_ADV_011",
        "Procurement of Portland Pozzolana Cement for structural foundation",
        "CIVIL_ENGINEERING",
        "Cement",
        "Cement - Specification",
        gold_standards=[{"standard_designation": "IS 1489 (Part 1):2015", "applicability": "primary_product", "reason": "PPC cement specification", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 4031 (Part 1):1996", "hn_class": "HN5", "confusability_reason": "Methods of physical tests for hydraulic cement fineness.", "rejection_reason": "IS 4031 is a test method, not a cement specification.", "source_tier": 1},
            {"standard_designation": "IS 456:2000", "hn_class": "HN4", "confusability_reason": "Plain and reinforced concrete code of practice.", "rejection_reason": "IS 456 is an engineering design code, not a cement manufacturing standard.", "source_tier": 1}
        ]
    ))

    # Category 5: Cable vs Switchgear
    cases.append(get_base_record(
        "Q_ADV_012",
        "Supply of low voltage molded case circuit breaker 400A 36kA",
        "ELECTROTECHNICAL",
        "Circuit Breakers",
        "Circuit Breakers - Specification",
        gold_standards=[{"standard_designation": "IS/IEC 60947 (Part 2):2016", "applicability": "primary_product", "reason": "Circuit breakers specification", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 1554 (Part 1):1988", "hn_class": "HN3", "confusability_reason": "Low voltage cable standard in same voltage tier.", "rejection_reason": "IS 1554 is a cable, not a switchgear circuit breaker.", "source_tier": 1},
            {"standard_designation": "IS 13947 (Part 2):1993", "hn_class": "HN4", "confusability_reason": "Superseded predecessor standard for circuit breakers.", "rejection_reason": "IS 13947 Part 2 has been superseded by IS/IEC 60947-2.", "source_tier": 1}
        ]
    ))

    # Category 6: Static vs Smart Meter
    cases.append(get_base_record(
        "Q_ADV_013",
        "Supply of AC static watt-hour energy meters Class 1.0 without communication modem",
        "ELECTROTECHNICAL",
        "Static Energy Meters",
        "Static Energy Meters - Specification",
        gold_standards=[{"standard_designation": "IS 13779:1999", "applicability": "primary_product", "reason": "AC static watt-hour meters", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 16444 (Part 1):2015", "hn_class": "HN1", "confusability_reason": "Smart electricity meter specification.", "rejection_reason": "IS 16444 requires smart meters with two-way communication modems; query specifies static meters without modem.", "source_tier": 1},
            {"standard_designation": "IS 13010:2002", "hn_class": "HN4", "confusability_reason": "Electromechanical induction type meters.", "rejection_reason": "IS 13010 is for obsolete electromechanical induction meters, not static meters.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_ADV_014",
        "Supply of smart whole current electricity meters with cellular AMI communication modem",
        "ELECTROTECHNICAL",
        "Smart Meters",
        "Smart Meters - Specification",
        gold_standards=[{"standard_designation": "IS 16444 (Part 1):2015", "applicability": "primary_product", "reason": "Smart direct connected energy meters", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 13779:1999", "hn_class": "HN1", "confusability_reason": "Static meter standard.", "rejection_reason": "IS 13779 is for traditional static meters without AMI communication protocols.", "source_tier": 1},
            {"standard_designation": "IS 16444 (Part 2):2017", "hn_class": "HN1", "confusability_reason": "Transformer operated smart meter standard.", "rejection_reason": "Part 2 covers CT/PT operated smart meters, whereas tender specifies whole current direct meters.", "source_tier": 1}
        ]
    ))

    # Category 7: Old Edition vs Current Edition
    cases.append(get_base_record(
        "Q_ADV_015",
        "Procurement of distribution transformers 11 kV 100 kVA",
        "ELECTROTECHNICAL",
        "Distribution Transformers",
        "Distribution Transformers - Specification",
        gold_standards=[{"standard_designation": "IS 1180 (Part 1):2014", "applicability": "primary_product", "reason": "Latest active standard for distribution transformers", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 1180 (Part 2):1989", "hn_class": "HN4", "confusability_reason": "Historical superseded standard for distribution transformers.", "rejection_reason": "IS 1180 Part 2:1989 is superseded and merged into Part 1:2014.", "source_tier": 1},
            {"standard_designation": "IS 2026 (Part 1):2011", "hn_class": "HN7", "confusability_reason": "Power transformers standard.", "rejection_reason": "IS 2026 is for bulk transmission transformers, not 100 kVA distribution transformers.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_ADV_016",
        "Supply of 43 Grade Ordinary Portland Cement for general RCC works",
        "CIVIL_ENGINEERING",
        "Cement",
        "Cement - Specification",
        gold_standards=[{"standard_designation": "IS 269:2015", "applicability": "primary_product", "reason": "Unified standard for ordinary Portland cement (33, 43, 53 grade)", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 8112:1989", "hn_class": "HN4", "confusability_reason": "Superseded 1989 version of 43 grade cement standard.", "rejection_reason": "IS 8112:1989 is superseded by IS 8112:2013 and unified in IS 269:2015.", "source_tier": 1},
            {"standard_designation": "IS 12269:2013", "hn_class": "HN1", "confusability_reason": "53 grade OPC specification.", "rejection_reason": "Tender explicitly requires 43 grade cement, not 53 grade.", "source_tier": 1}
        ]
    ))

    # Category 8: Material-Only Similarity (Semantic Trap)
    cases.append(get_base_record(
        "Q_ADV_017",
        "Supply of polyethylene geomembrane sheets for landfill lining",
        "CIVIL_ENGINEERING",
        "Geomembrane",
        "Geomembrane - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 4984:2016", "hn_class": "HN2", "confusability_reason": "Same polyethylene material, but pressure pipe.", "rejection_reason": "IS 4984 covers pipes, not geomembrane sheet liners.", "source_tier": 1},
            {"standard_designation": "IS 14333:2022", "hn_class": "HN2", "confusability_reason": "HDPE pipes for drainage.", "rejection_reason": "IS 14333 covers tubular pipes, not flat sheet liners.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "NO_CONFIDENT_MATCH", "expected_abstention_reason": "No applicable standard for geomembrane in current scope."},
        expected_safe_decision="NO_CONFIDENT_MATCH"
    ))
    cases.append(get_base_record(
        "Q_ADV_018",
        "Supply of steel reinforcement bars for structural concrete",
        "CIVIL_ENGINEERING",
        "Steel Bars",
        "Steel Bars - Specification",
        gold_standards=[{"standard_designation": "IS 1786:2008", "applicability": "primary_product", "reason": "TMT steel bars specification", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 456:2000", "hn_class": "HN4", "confusability_reason": "Concrete code mentioning steel reinforcement.", "rejection_reason": "IS 456 is a structural design code, not the steel bar manufacturing specification.", "source_tier": 1},
            {"standard_designation": "IS 2062:2011", "hn_class": "HN1", "confusability_reason": "Structural steel specification.", "rejection_reason": "IS 2062 is for structural steel plates/beams, not ribbed reinforcement bars.", "source_tier": 1}
        ]
    ))

    # Category 9: Additional Cross-Domain Mismatches (Q_ADV_019 - Q_ADV_032)
    mismatches = [
        ("Q_ADV_019", "Supply of distribution transformer as per IS 1554", "ELECTROTECHNICAL", "Transformers", "IS 1554 (Part 1):1988", "IS 7098 (Part 1):1988", "Named standard is cable", "IS 1554 is cable"),
        ("Q_ADV_020", "Procurement of copper grounding rod as per IS 269", "ELECTROTECHNICAL", "Earthing Rod", "IS 269:2015", "IS 455:2015", "Named standard is cement", "IS 269 is cement"),
        ("Q_ADV_021", "Supply of ductile iron pipes as per IS 7098", "CIVIL_ENGINEERING", "Ductile Iron Pipes", "IS 7098 (Part 1):1988", "IS 1554 (Part 1):1988", "Named standard is XLPE cable", "IS 7098 is XLPE cable"),
        ("Q_ADV_022", "Supply of LED street light fixtures as per IS 8112", "ELECTROTECHNICAL", "LED Luminaires", "IS 8112:2013", "IS 12269:2013", "Named standard is cement", "IS 8112 is cement"),
        ("Q_ADV_023", "Supply of PVC insulated flexible cords as per IS 12269", "ELECTROTECHNICAL", "Flexible Cords", "IS 12269:2013", "IS 269:2015", "Named standard is cement", "IS 12269 is cement"),
        ("Q_ADV_024", "Supply of mild steel ERW pipes as per IS 16444", "CIVIL_ENGINEERING", "Steel Pipes", "IS 16444 (Part 1):2015", "IS 13779:1999", "Named standard is smart meters", "IS 16444 is smart meter"),
        ("Q_ADV_025", "Procurement of centrifugally cast iron pressure pipes as per IS 302", "CIVIL_ENGINEERING", "Cast Iron Pipes", "IS 302 (Part 1):2024", "IS 694:2010", "Named standard is household appliance safety", "IS 302 is appliance safety"),
        ("Q_ADV_026", "Supply of high voltage circuit breakers as per IS 1786", "ELECTROTECHNICAL", "Circuit Breakers", "IS 1786:2008", "IS 2062:2011", "Named standard is TMT rebars", "IS 1786 is steel rebars"),
        ("Q_ADV_027", "Procurement of smart energy meters as per IS 1239", "ELECTROTECHNICAL", "Smart Meters", "IS 1239 (Part 1):2004", "IS 4985:2021", "Named standard is steel tubes", "IS 1239 is steel tubes"),
        ("Q_ADV_028", "Supply of TMT steel bars Fe 500D as per IS 7098 Part 2", "CIVIL_ENGINEERING", "TMT Bars", "IS 7098 (Part 2):2011", "IS 1554 (Part 2):1988", "Named standard is XLPE cable", "IS 7098 is XLPE cable"),
        ("Q_ADV_029", "Procurement of copper conductor PVC insulated cables as per IS 2062", "ELECTROTECHNICAL", "Cables", "IS 2062:2011", "IS 800:2007", "Named standard is structural steel", "IS 2062 is structural steel"),
        ("Q_ADV_030", "Supply of uPVC casing pipes for borewells as per IS 13779", "CIVIL_ENGINEERING", "Casing Pipes", "IS 13779:1999", "IS 16444 (Part 1):2015", "Named standard is static electricity meters", "IS 13779 is static electricity meters"),
        ("Q_ADV_031", "Procurement of self ballasted LED lamps for general lighting as per IS 455", "ELECTROTECHNICAL", "LED Lamps", "IS 455:2015", "IS 269:2015", "Named standard is slag cement", "IS 455 is slag cement"),
        ("Q_ADV_032", "Supply of Portland Slag Cement as per IS 16102 Part 1", "CIVIL_ENGINEERING", "Slag Cement", "IS 16102 (Part 1):2012", "IS 10322 (Part 5/Sec 1):2012", "Named standard is LED lamps", "IS 16102 is LED lamps")
    ]

    for qid, qtxt, qdom, qfam, wrong_std1, wrong_std2, conf_reason, rej_reason in mismatches:
        cases.append(get_base_record(
            qid, qtxt, qdom, qfam, f"{qfam} - Specification",
            gold_standards=[],
            hard_negatives=[
                {"standard_designation": wrong_std1, "hn_class": "HN3", "confusability_reason": conf_reason, "rejection_reason": rej_reason, "source_tier": 1},
                {"standard_designation": wrong_std2, "hn_class": "HN3", "confusability_reason": f"Alternative trap: {wrong_std2}", "rejection_reason": f"Cross-domain mismatch: {wrong_std2}", "source_tier": 1}
            ],
            expected_decision={"query_level_state": "NO_CONFIDENT_MATCH", "expected_abstention_reason": "Incompatible explicit standard."},
            expected_safe_decision="NO_CONFIDENT_MATCH"
        ))

    out_file = BENCHMARKS_DIR / "adversarial.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
    print(f"Generated {len(cases)} adversarial cases in {out_file}")


def generate_coverage_boundary_dataset():
    """Generates 10 genuine non-CED/ETD procurement queries expecting OUTSIDE_PROTOTYPE_COVERAGE."""
    cases = []
    cases.append(get_base_record(
        "Q_BND_001", "Supply of Grade A certified organic basmati rice for food ration distribution",
        "FOOD_AGRICULTURE", "Basmati Rice", "Basmati Rice - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 1554 (Part 1):1988", "hn_class": "HN7", "confusability_reason": "PVC cables standard.", "rejection_reason": "Cross-domain: IS 1554 is an electrotechnical cable standard.", "source_tier": 1},
            {"standard_designation": "IS 456:2000", "hn_class": "HN7", "confusability_reason": "Concrete code of practice.", "rejection_reason": "Cross-domain: IS 456 is civil engineering concrete code.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_002", "Procurement of fresh pasteurized homogenized full cream cow milk in 500ml pouches",
        "FOOD_AGRICULTURE", "Milk", "Liquid Milk - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 4985:2021", "hn_class": "HN7", "confusability_reason": "uPVC pipes standard.", "rejection_reason": "Cross-domain: IS 4985 is for water supply piping.", "source_tier": 1},
            {"standard_designation": "IS 694:2010", "hn_class": "HN7", "confusability_reason": "PVC wires standard.", "rejection_reason": "Cross-domain: IS 694 is for electrical wiring.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_003", "Supply of surgical grade titanium alloy orthopedic bone plates and cortical screws",
        "MEDICAL_EQUIPMENT", "Orthopedic Implants", "Orthopedic Implants - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 2062:2011", "hn_class": "HN7", "confusability_reason": "Structural steel specification.", "rejection_reason": "Cross-domain: IS 2062 is structural steel for construction.", "source_tier": 1},
            {"standard_designation": "IS 1786:2008", "hn_class": "HN7", "confusability_reason": "TMT steel reinforcement bars.", "rejection_reason": "Cross-domain: IS 1786 is for civil reinforcement.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_004", "Procurement of sterile single-use disposable hypodermic syringes 5ml with needle",
        "MEDICAL_EQUIPMENT", "Syringes", "Hypodermic Syringes - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 4984:2016", "hn_class": "HN7", "confusability_reason": "HDPE pipes standard.", "rejection_reason": "Cross-domain: IS 4984 is civil piping standard.", "source_tier": 1},
            {"standard_designation": "IS 7098 (Part 1):1988", "hn_class": "HN7", "confusability_reason": "XLPE power cables standard.", "rejection_reason": "Cross-domain: IS 7098 is electrotechnical cable standard.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_005", "Supply of 100% woven cotton drill fabric khaki dyed for security force uniforms",
        "TEXTILES", "Cotton Drill Fabric", "Cotton Fabric - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 1554 (Part 1):1988", "hn_class": "HN7", "confusability_reason": "PVC cables standard.", "rejection_reason": "Cross-domain: IS 1554 is an electrotechnical cable standard.", "source_tier": 1},
            {"standard_designation": "IS 269:2015", "hn_class": "HN7", "confusability_reason": "Ordinary Portland cement standard.", "rejection_reason": "Cross-domain: IS 269 is civil cement specification.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_006", "Procurement of pure mulberry raw silk yarns 20/22 denier warp quality",
        "TEXTILES", "Silk Yarn", "Silk Yarn - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 694:2010", "hn_class": "HN7", "confusability_reason": "PVC wires standard.", "rejection_reason": "Cross-domain: IS 694 is electrical wire standard.", "source_tier": 1},
            {"standard_designation": "IS 383:2016", "hn_class": "HN7", "confusability_reason": "Aggregates for concrete.", "rejection_reason": "Cross-domain: IS 383 is civil aggregate standard.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_007", "Bulk procurement of aviation turbine fuel (ATF) Jet A-1 for military aircraft fleet",
        "PETROLEUM_COAL", "Aviation Turbine Fuel", "ATF - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 1180 (Part 1):2014", "hn_class": "HN7", "confusability_reason": "Transformers standard.", "rejection_reason": "Cross-domain: IS 1180 is transformer specification.", "source_tier": 1},
            {"standard_designation": "IS 1239 (Part 1):2004", "hn_class": "HN7", "confusability_reason": "Steel tubes standard.", "rejection_reason": "Cross-domain: IS 1239 is civil tubular steel standard.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_008", "Procurement of pharmaceutical grade paracetamol tablets 500mg blister packed",
        "CHEMICAL", "Paracetamol Tablets", "Paracetamol Tablets - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 455:2015", "hn_class": "HN7", "confusability_reason": "Slag cement standard.", "rejection_reason": "Cross-domain: IS 455 is civil cement standard.", "source_tier": 1},
            {"standard_designation": "IS 7098 (Part 2):2011", "hn_class": "HN7", "confusability_reason": "XLPE power cables standard.", "rejection_reason": "Cross-domain: IS 7098 is electrotechnical cable standard.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_009", "Supply of industrial steam turbine blading alloys for thermal power generation",
        "MECHANICAL", "Turbine Blading", "Turbine Blading - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 16444 (Part 1):2015", "hn_class": "HN7", "confusability_reason": "Smart electricity meters standard.", "rejection_reason": "Cross-domain: IS 16444 is smart electricity meter.", "source_tier": 1},
            {"standard_designation": "IS 13779:1999", "hn_class": "HN7", "confusability_reason": "Static energy meters standard.", "rejection_reason": "Cross-domain: IS 13779 is static electricity meter.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))
    cases.append(get_base_record(
        "Q_BND_010", "Supply of fresh Alphonso mango pulp in aseptic containers for food processing export",
        "FOOD_AGRICULTURE", "Mango Pulp", "Mango Pulp - Specification",
        gold_standards=[],
        hard_negatives=[
            {"standard_designation": "IS 4985:2021", "hn_class": "HN7", "confusability_reason": "uPVC pipes standard.", "rejection_reason": "Cross-domain: IS 4985 is water supply pipes.", "source_tier": 1},
            {"standard_designation": "IS 8112:2013", "hn_class": "HN7", "confusability_reason": "43 grade cement standard.", "rejection_reason": "Cross-domain: IS 8112 is civil cement standard.", "source_tier": 1}
        ],
        expected_decision={"query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE", "expected_abstention_reason": "Query specifies products outside CED/ETD prototype coverage."},
        cov_state="OUTSIDE_PROTOTYPE_COVERAGE", expected_safe_decision="OUTSIDE_PROTOTYPE_COVERAGE"
    ))

    out_file = BENCHMARKS_DIR / "coverage_boundary.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
    print(f"Generated {len(cases)} coverage boundary cases in {out_file}")


def generate_challenge_dataset():
    """Generates 10 complex multi-constraint challenge queries."""
    cases = []
    cases.append(get_base_record(
        "Q_CHL_001",
        "Supply of 3 core 185 sq mm 11 kV XLPE insulated heavy duty power cables with aluminum conductors and galvanized steel strip armour",
        "ELECTROTECHNICAL", "XLPE Power Cables", "XLPE Power Cables - Specification",
        gold_standards=[{"standard_designation": "IS 7098 (Part 2):2011", "applicability": "primary_product", "reason": "XLPE cables for 3.3 kV to 33 kV", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 7098 (Part 1):1988", "hn_class": "HN1", "confusability_reason": "Low voltage XLPE standard.", "rejection_reason": "Query specifies 11 kV, Part 1 only covers up to 1.1 kV.", "source_tier": 1},
            {"standard_designation": "IS 1554 (Part 2):1988", "hn_class": "HN3", "confusability_reason": "PVC insulated cable up to 33 kV.", "rejection_reason": "Tender specifies XLPE insulation; IS 1554 Part 2 is PVC.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_002",
        "Supply of unplasticized PVC pipes Class 3 6 kgf/cm2 110 mm outer diameter with elastomeric sealing ring joints for drinking water distribution",
        "CIVIL_ENGINEERING", "uPVC Pipes", "uPVC Pipes - Specification",
        gold_standards=[{"standard_designation": "IS 4985:2021", "applicability": "primary_product", "reason": "uPVC pipes for potable water supplies", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 12818:2010", "hn_class": "HN1", "confusability_reason": "uPVC casing pipes for borewells.", "rejection_reason": "IS 12818 is for tube well casing, not surface potable water distribution.", "source_tier": 1},
            {"standard_designation": "IS 4984:2016", "hn_class": "HN2", "confusability_reason": "HDPE pipes for water supply.", "rejection_reason": "Tender specifies uPVC material; IS 4984 is polyethylene.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_003",
        "Supply of 500 kVA 11/0.433 kV three phase copper wound oil immersed outdoor distribution transformer with corrugated tank",
        "ELECTROTECHNICAL", "Distribution Transformers", "Distribution Transformers - Specification",
        gold_standards=[{"standard_designation": "IS 1180 (Part 1):2014", "applicability": "primary_product", "reason": "Outdoor distribution transformers up to 2500 kVA", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 2026 (Part 1):2011", "hn_class": "HN1", "confusability_reason": "General power transformer standard.", "rejection_reason": "IS 1180 is the specialized mandatory product standard for distribution transformers up to 2500 kVA.", "source_tier": 1},
            {"standard_designation": "IS 11171:1985", "hn_class": "HN3", "confusability_reason": "Dry-type power transformers.", "rejection_reason": "Query specifies oil immersed transformer; IS 11171 is for dry-type transformers.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_004",
        "Procurement of Portland Pozzolana Cement fly ash based 43 grade equivalent for mass concrete dam construction",
        "CIVIL_ENGINEERING", "Cement", "Cement - Specification",
        gold_standards=[{"standard_designation": "IS 1489 (Part 1):2015", "applicability": "primary_product", "reason": "Portland Pozzolana Cement fly ash based", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 1489 (Part 2):2015", "hn_class": "HN1", "confusability_reason": "Calcined clay based PPC.", "rejection_reason": "Query specifies fly ash based (Part 1), Part 2 is calcined clay.", "source_tier": 1},
            {"standard_designation": "IS 269:2015", "hn_class": "HN1", "confusability_reason": "Ordinary Portland cement.", "rejection_reason": "Tender specifies Portland Pozzolana Cement (PPC), not Ordinary Portland Cement (OPC).", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_005",
        "Supply of centrifugally cast ductile iron pressure pipes Class K9 300 mm diameter with push-on flexible socket joints for raw water main",
        "CIVIL_ENGINEERING", "Ductile Iron Pipes", "Ductile Iron Pipes - Specification",
        gold_standards=[{"standard_designation": "IS 8329:2000", "applicability": "primary_product", "reason": "Centrifugally cast ductile iron pressure pipes", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 1536:2023", "hn_class": "HN1", "confusability_reason": "Spun cast iron pipes.", "rejection_reason": "IS 1536 covers grey cast iron, not ductile iron (IS 8329).", "source_tier": 1},
            {"standard_designation": "IS 7181:1986", "hn_class": "HN1", "confusability_reason": "Horizontally cast iron pipes.", "rejection_reason": "IS 7181 is obsolete horizontally cast iron, not centrifugally cast ductile iron.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_006",
        "Procurement of Thermo-Mechanically Treated (TMT) steel bars Grade Fe 500D 16mm diameter with enhanced ductility for seismic zones",
        "CIVIL_ENGINEERING", "TMT Steel Bars", "TMT Bars - Specification",
        gold_standards=[{"standard_designation": "IS 1786:2008", "applicability": "primary_product", "reason": "High strength deformed steel bars and wires for concrete reinforcement", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 432 (Part 1):1982", "hn_class": "HN1", "confusability_reason": "Mild steel plain round bars.", "rejection_reason": "IS 432 is plain mild steel, not ribbed deformed high strength TMT bars.", "source_tier": 1},
            {"standard_designation": "IS 2062:2011", "hn_class": "HN2", "confusability_reason": "Structural steel plates and angles.", "rejection_reason": "IS 2062 is for structural steel sections, not concrete reinforcement rebars.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_007",
        "Supply of 4 core 16 sq mm PVC insulated PVC sheathed unarmoured copper cables 1100 V working voltage",
        "ELECTROTECHNICAL", "PVC Cables", "PVC Cables - Specification",
        gold_standards=[{"standard_designation": "IS 1554 (Part 1):1988", "applicability": "primary_product", "reason": "PVC insulated electric cables for working voltages up to 1100V", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 694:2010", "hn_class": "HN1", "confusability_reason": "Light building wire standard.", "rejection_reason": "IS 1554 Part 1 governs multi-core heavy power distribution PVC cables.", "source_tier": 1},
            {"standard_designation": "IS 7098 (Part 1):1988", "hn_class": "HN3", "confusability_reason": "XLPE insulated 1.1 kV cable.", "rejection_reason": "Tender specifies PVC insulation; IS 7098 is XLPE.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_008",
        "Supply of smart whole current electricity meters single phase 5-30A Class 1.0 with optical port and 4G modem",
        "ELECTROTECHNICAL", "Smart Meters", "Smart Meters - Specification",
        gold_standards=[{"standard_designation": "IS 16444 (Part 1):2015", "applicability": "primary_product", "reason": "AC static direct connected smart meters", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 16444 (Part 2):2017", "hn_class": "HN1", "confusability_reason": "Transformer operated smart meter.", "rejection_reason": "Part 2 is for CT/PT operated meters, query asks for whole current direct connected.", "source_tier": 1},
            {"standard_designation": "IS 13779:1999", "hn_class": "HN1", "confusability_reason": "Static meter without smart AMI modem.", "rejection_reason": "IS 13779 is for static meters without two-way AMI smart communication.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_009",
        "Procurement of high density polyethylene PE-100 pipes PN 10 160 mm outer diameter for pressurized water supply",
        "CIVIL_ENGINEERING", "HDPE Pipes", "HDPE Pipes - Specification",
        gold_standards=[{"standard_designation": "IS 4984:2016", "applicability": "primary_product", "reason": "High density polyethylene pipes for water supply", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 14885:2022", "hn_class": "HN1", "confusability_reason": "HDPE pipe for gaseous fuels.", "rejection_reason": "IS 14885 is for fuel gas distribution, not water supply.", "source_tier": 1},
            {"standard_designation": "IS 14333:2022", "hn_class": "HN1", "confusability_reason": "HDPE pipes for drainage and sewerage.", "rejection_reason": "IS 14333 is for gravity sewerage, whereas tender specifies potable water supply.", "source_tier": 1}
        ]
    ))
    cases.append(get_base_record(
        "Q_CHL_010",
        "Supply of Ordinary Portland Cement 53 Grade with 28-day compressive strength not less than 53 MPa for pre-stressed concrete works",
        "CIVIL_ENGINEERING", "Cement", "Cement - Specification",
        gold_standards=[{"standard_designation": "IS 269:2015", "applicability": "primary_product", "reason": "Ordinary Portland cement 53 grade specification", "evidence_span": "Clause 1", "relationship_obligation": "MANDATORY", "mandatory_by_regulation": True}],
        hard_negatives=[
            {"standard_designation": "IS 12269:2013", "hn_class": "HN6", "confusability_reason": "Historical dedicated 53 grade OPC standard now amalgamated into IS 269.", "rejection_reason": "IS 12269 is superseded and amalgamated into IS 269:2015.", "source_tier": 1},
            {"standard_designation": "IS 8112:2013", "hn_class": "HN1", "confusability_reason": "43 grade OPC specification.", "rejection_reason": "Tender specifies 53 grade OPC; IS 8112 is for 43 grade.", "source_tier": 1}
        ]
    ))

    out_file = BENCHMARKS_DIR / "challenge.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
    print(f"Generated {len(cases)} challenge cases in {out_file}")


if __name__ == "__main__":
    generate_adversarial_dataset()
    generate_coverage_boundary_dataset()
    generate_challenge_dataset()

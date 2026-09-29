"""
Open-World Benchmark Dataset Generator — StandSpec AI
Generates 50 completely new unseen procurement queries across 5 subsets:
1. data/benchmarks/open_world_paraphrase.jsonl (10 queries)
2. data/benchmarks/open_world_compositional.jsonl (10 queries)
3. data/benchmarks/open_world_multilingual.jsonl (10 queries)
4. data/benchmarks/open_world_long_clause.jsonl (10 queries)
5. data/benchmarks/open_world_conflict.jsonl (10 queries)
and merges them into data/benchmarks/open_world.jsonl (50 queries).
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "data" / "benchmarks"
BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)

# Import paraphrase queries from scratch/generate_open_world_benchmarks.py
import sys
sys.path.insert(0, str(PROJECT_ROOT / "scratch"))
from generate_open_world_benchmarks import paraphrase_queries

# 2. COMPOSITIONAL SUBSET (Q_OWC_001 to Q_OWC_010)
compositional_queries = [
    {
        "query_id": "Q_OWC_001",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Maharashtra State Electricity Distribution Co.",
            "tender_id": "MSEDCL/CBL/XLPE/2025/104",
            "tender_publication_date": "2025-07-02",
            "evaluation_as_of_date": "2025-07-20",
            "portal_url": "https://mahadiscom.in"
        },
        "query": {
            "raw_text": "Procurement of 1100 V grade 4-core 240 sq mm crosslinked polyethylene XLPE insulated stranded aluminium conductor armoured cable with galvanized steel strip armour and extruded PVC outer sheath.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Electrical Cables"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "XLPE Insulated Thermoplastic Sheathed Cables",
            "scope_keywords": ["XLPE insulated", "1100 V", "armoured cable", "aluminium conductor", "4-core 240 sq mm"],
            "target_product": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 1 For Working Voltage Up to and Including 1100 V",
            "material_grade": "XLPE insulation, aluminium conductor, GI strip armour",
            "rating_capacity": "1100 V, 4x240 sq mm",
            "application": "Underground power distribution feeder",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 7098 (Part 1):2025",
            "applicability": "primary_product",
            "reason": "Indian Standard for XLPE insulated thermoplastic sheathed cables: Part 1 For working voltage up to and including 1100 V.",
            "evidence_span": "Clause 1: Prescribes the requirements for XLPE insulated cables for working voltages up to and including 1100 V.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 7098 (Part 2):2011",
                "hn_class": "HN1",
                "confusability_reason": "Same XLPE cable series, but Part 2 is for higher voltages 3.3 kV up to 33 kV.",
                "rejection_reason": "Tender asks for 1100 V grade, which is strictly governed by Part 1, not medium/high voltage Part 2.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 1554 (Part 1):1988",
                "hn_class": "HN2",
                "confusability_reason": "PVC insulated armoured cable specification.",
                "rejection_reason": "Tender specifies XLPE insulation, which has higher thermal rating than PVC.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2025", "1988"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_002",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Bangalore Electricity Supply Company (BESCOM)",
            "tender_id": "BESCOM/TRANS/100KVA/2025/18",
            "tender_publication_date": "2025-07-04",
            "evaluation_as_of_date": "2025-07-22",
            "portal_url": "https://bescom.karnataka.gov.in"
        },
        "query": {
            "raw_text": "Supply of 11/0.433 kV, 100 kVA outdoor oil immersed step-down distribution transformer, 3-phase 50 Hz, copper winding with off-circuit tap changer and energy efficiency level 2.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Transformers"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Distribution Transformers Up to 2500 kVA, 33 kV",
            "scope_keywords": ["distribution transformer", "100 kVA", "11 kV", "oil immersed", "energy efficiency"],
            "target_product": "Outdoor/Indoor Type Oil Immersed Distribution Transformers Up to and Including 2500 kVA, 33 kV",
            "material_grade": "CRGO electrical steel core, electrolytic copper winding",
            "rating_capacity": "100 kVA, 11/0.433 kV",
            "application": "Distribution substation power step-down",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 1180 (Part 1):2014",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for outdoor/indoor type oil immersed distribution transformers up to and including 2500 kVA, 33 kV.",
            "evidence_span": "Clause 1.1: Specifies requirements and tests for outdoor/indoor type oil immersed distribution transformers.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 2026 (Part 1):2011",
                "hn_class": "HN7",
                "confusability_reason": "General power transformer standard.",
                "rejection_reason": "Distribution transformers up to 2500 kVA fall strictly under IS 1180 (Part 1) under national QCO.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 11171:1985",
                "hn_class": "HN3",
                "confusability_reason": "Dry-type transformers standard.",
                "rejection_reason": "Tender explicitly requires oil-immersed transformers, not dry-type cast resin.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2014"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_003",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Airports Authority of India (AAI)",
            "tender_id": "AAI/ADH/TILE/2025/09",
            "tender_publication_date": "2025-07-06",
            "evaluation_as_of_date": "2025-07-25",
            "portal_url": "https://aai.aero"
        },
        "query": {
            "raw_text": "Supply of polymer-modified cementitious tile adhesive Type 2 for fixing ceramic, vitrified and mosaic tiles on internal and external walls and floors in new terminal building concourses.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Construction Chemicals"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Adhesives for Tiles",
            "scope_keywords": ["tile adhesive", "ceramic", "vitrified", "Type 2", "mosaic tiles"],
            "target_product": "Adhesives for Use with Ceramic, Mosaic and Stone Tiles - Specification",
            "material_grade": "Polymer-modified cementitious dry mix",
            "rating_capacity": "Type 2 adhesive",
            "application": "Fixing vitrified and ceramic tiles on walls and floors",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 15477:2019",
            "applicability": "primary_product",
            "reason": "Indian Standard for adhesives for use with ceramic, mosaic and stone tiles.",
            "evidence_span": "Clause 1: Prescribes the requirements for adhesives for use with ceramic, mosaic and stone tiles.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 13630 (Part 1):2019",
                "hn_class": "HN5",
                "confusability_reason": "Ceramic tiles testing methods standard.",
                "rejection_reason": "IS 13630 is for ceramic tile sampling and testing, whereas IS 15477 is the adhesive product standard.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 15622:2017",
                "hn_class": "HN2",
                "confusability_reason": "Pressed ceramic tiles standard.",
                "rejection_reason": "IS 15622 is for the tiles themselves, not the adhesive used to fix them.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2019"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_004",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "psu_tender",
            "organization": "Rashtriya Ispat Nigam Limited (RINL)",
            "tender_id": "RINL/CEM/ALUM/2025/31",
            "tender_publication_date": "2025-07-08",
            "evaluation_as_of_date": "2025-07-25",
            "portal_url": "https://vizagsteel.com"
        },
        "query": {
            "raw_text": "Procurement of high alumina cement for structural applications and refractory castable linings in steel melting shop furnaces.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Special Cements"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "High Alumina Cement for Structural Use",
            "scope_keywords": ["high alumina cement", "structural use", "refractory", "calcium aluminate"],
            "target_product": "High Alumina Cement for Structural Use - Specification",
            "material_grade": "Calcium aluminate hydraulic cement",
            "application": "Structural and high temperature refractory concrete",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 6452:2026",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for high alumina cement for structural use.",
            "evidence_span": "Clause 1: Prescribes the requirements for manufacture and chemical and physical requirements of high alumina cement for structural use.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 269:2015",
                "hn_class": "HN1",
                "confusability_reason": "Ordinary Portland cement standard.",
                "rejection_reason": "IS 269 covers ordinary Portland cement with silicate chemistry, completely different from aluminate chemistry under IS 6452.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 6909:2026",
                "hn_class": "HN3",
                "confusability_reason": "Supersulphated cement specification.",
                "rejection_reason": "IS 6909 is supersulphated cement, not calcium aluminate high alumina cement.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2026", "1989"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_005",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Mumbai Port Trust (MbPT)",
            "tender_id": "MBPT/CIVIL/SRC/2025/14",
            "tender_publication_date": "2025-07-10",
            "evaluation_as_of_date": "2025-07-28",
            "portal_url": "https://mumbaiport.gov.in"
        },
        "query": {
            "raw_text": "Supply of sulphate resisting Portland cement for heavy pile cap and maritime wharf jetty substructure exposed to aggressive marine tidal waters.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Special Cements"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Sulphate Resisting Portland Cement",
            "scope_keywords": ["sulphate resisting", "Portland cement", "marine wharf", "pile cap", "sulphate"],
            "target_product": "Specification for Sulphate Resisting Portland Cement",
            "material_grade": "Low C3A (<5%) Portland clinker",
            "application": "Marine concrete substructure and sulphate-rich soil",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 12330:1988",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for sulphate resisting Portland cement.",
            "evidence_span": "Clause 1: Prescribes the requirements for manufacture and chemical and physical requirements of sulphate resisting Portland cement.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 269:2015",
                "hn_class": "HN1",
                "confusability_reason": "Ordinary Portland cement standard.",
                "rejection_reason": "Ordinary Portland cement contains up to 10% C3A and is susceptible to severe ettringite sulphate attack in marine waters.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 12600:1989",
                "hn_class": "HN3",
                "confusability_reason": "Low heat Portland cement specification.",
                "rejection_reason": "IS 12600 is designed for low heat of hydration in dams, not chemical sulphate resistance.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["1988"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_006",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "psu_tender",
            "organization": "Delhi Metro Rail Corporation (DMRC)",
            "tender_id": "DMRC/LIFT/CBL/2025/03",
            "tender_publication_date": "2025-07-12",
            "evaluation_as_of_date": "2025-07-28",
            "portal_url": "https://delhimetrorail.com"
        },
        "query": {
            "raw_text": "Supply of flexible travelling trailing electric cables for passenger elevator shafts, elastomer/rubber insulated flexible multicore rated up to 1100 V for lift cars in underground stations.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Special Cables"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Flexible Cables for Lifts",
            "scope_keywords": ["flexible cables for lifts", "elevator cables", "trailing cables", "lift cars"],
            "target_product": "Flexible Cables for Lifts and Other Flexible Applications Part 1 Elastomer Insulated Cables",
            "material_grade": "Flexible copper conductor, elastomer insulation",
            "rating_capacity": "1100 V flexible",
            "application": "Travelling lift car electrical connections",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 4289 (Part 1):2026",
            "applicability": "primary_product",
            "reason": "Indian Standard for flexible cables for lifts and other flexible applications: Part 1 Elastomer insulated cables.",
            "evidence_span": "Clause 1: Covers the requirements of elastomer insulated flexible cables for lifts and other flexible applications.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 694:2010",
                "hn_class": "HN1",
                "confusability_reason": "General PVC building flexible wires standard.",
                "rejection_reason": "Standard PVC building wires lack high fatigue flex life required for travelling elevator cars.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 9968 (Part 1):2025",
                "hn_class": "HN1",
                "confusability_reason": "General elastomer insulated cables specification.",
                "rejection_reason": "IS 4289 (Part 1) specifically governs lift travelling applications, whereas IS 9968 is general elastomer cables.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2026"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_007",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "industry_rfp",
            "organization": "Ambuja Cements Limited",
            "tender_id": "AMBUJA/RAW/SLAG/2025/90",
            "tender_publication_date": "2025-07-14",
            "evaluation_as_of_date": "2025-07-30",
            "portal_url": "https://ambujacement.com"
        },
        "query": {
            "raw_text": "Procurement of granulated blast furnace slag from iron manufacturing plant for the manufacture of Portland slag cement meeting national chemical and physical specification requirements.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Cement Raw Materials"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Granulated Slag for Manufacture of Portland Slag Cement",
            "scope_keywords": ["granulated slag", "blast furnace slag", "manufacture of Portland slag cement"],
            "target_product": "Specification for Granulated Slag for Manufacture of Portland Slag Cement",
            "material_grade": "Water quenched blast furnace glassy slag",
            "application": "Raw material blending for Portland slag cement (PSC)",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 12089:1987",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for granulated slag for manufacture of Portland slag cement.",
            "evidence_span": "Clause 1: Prescribes the requirements for granulated slag for the manufacture of Portland slag cement.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 455:2015",
                "hn_class": "HN1",
                "confusability_reason": "Finished Portland slag cement specification.",
                "rejection_reason": "IS 455 is for finished blended cement, whereas tender is for the raw granulated slag input material (IS 12089).",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 3812 (Part 1):2013",
                "hn_class": "HN2",
                "confusability_reason": "Pulverized fuel ash (fly ash) for pozzolana cement.",
                "rejection_reason": "Fly ash from thermal plants is different from blast furnace iron slag.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["1987"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_008",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "psu_tender",
            "organization": "Gas Authority of India Limited (GAIL)",
            "tender_id": "GAIL/PIPE/COVER/2025/15",
            "tender_publication_date": "2025-07-15",
            "evaluation_as_of_date": "2025-07-30",
            "portal_url": "https://gailonline.com"
        },
        "query": {
            "raw_text": "Supply of precast concrete cable covers and protection slabs for protecting buried underground electrical power cables along pipeline right-of-way corridor.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Precast Concrete"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Precast Concrete Cable Covers",
            "scope_keywords": ["precast concrete cable covers", "cable protection slabs", "underground cable protection"],
            "target_product": "Precast Concrete Cable Covers - Specification",
            "material_grade": "Reinforced precast concrete slab",
            "application": "Mechanical protection of buried power cables",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 5820:2024",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for precast concrete cable covers.",
            "evidence_span": "Clause 1: Specifies requirements for precast concrete cable covers intended to provide mechanical protection for buried electric cables.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 10418:2024",
                "hn_class": "HN1",
                "confusability_reason": "Drums for electric cables standard.",
                "rejection_reason": "IS 10418 covers transport wooden/steel drums, not trench protection concrete covers.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 2185 (Part 1):2005",
                "hn_class": "HN2",
                "confusability_reason": "Concrete masonry blocks standard.",
                "rejection_reason": "IS 2185 is for structural wall masonry blocks, not cable trench covers.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2024"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_009",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Tamil Nadu Housing Board (TNHB)",
            "tender_id": "TNHB/ELEC/MOT/2025/11",
            "tender_publication_date": "2025-07-16",
            "evaluation_as_of_date": "2025-07-30",
            "portal_url": "https://tnhb.tn.gov.in"
        },
        "query": {
            "raw_text": "Supply of single phase a.c. induction motors 230V 50Hz, output rating 1.5 kW foot mounted for domestic water booster pumps in residential colony.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Electric Motors"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Single Phase a.c. Induction Motors",
            "scope_keywords": ["single phase induction motors", "single phase a.c.", "230V", "1.5 kW"],
            "target_product": "Single Phase a.c. Induction Motors for General Purpose",
            "material_grade": "Capacitor start induction motor",
            "rating_capacity": "1.5 kW, 230V AC",
            "application": "Water booster pump drive",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 996:2025",
            "applicability": "primary_product",
            "reason": "Indian Standard for single phase a.c. induction motors for general purpose.",
            "evidence_span": "Clause 1: Prescribes the requirements for single-phase AC induction motors for general purpose.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 12615:2026",
                "hn_class": "HN1",
                "confusability_reason": "Three-phase induction motors efficiency standard.",
                "rejection_reason": "Tender asks for single-phase motor, while IS 12615 is strictly for line operated 3-phase induction motors.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 7538:1996",
                "hn_class": "HN1",
                "confusability_reason": "Three-phase motors for centrifugal pumps for agricultural applications.",
                "rejection_reason": "IS 7538 is for 3-phase agricultural pumps, not single phase domestic motors.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2025"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWC_010",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "psu_tender",
            "organization": "Bharat Heavy Electricals Limited (BHEL)",
            "tender_id": "BHEL/COND/COP/2025/99",
            "tender_publication_date": "2025-07-18",
            "evaluation_as_of_date": "2025-08-01",
            "portal_url": "https://bhel.com"
        },
        "query": {
            "raw_text": "Procurement of cotton covered copper conductors, round wires and rectangular strips for high-voltage power transformer and stator electrical windings.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Winding Wires"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Cotton Covered Copper Conductors",
            "scope_keywords": ["cotton covered copper conductors", "winding wires", "transformer windings", "copper conductors"],
            "target_product": "Cotton Covered Copper Conductors - Specification Part 1 Round Conductors",
            "material_grade": "High conductivity electrolytic copper with double cotton covering",
            "application": "Electrical machine and transformer stator winding",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 7391 (Part 1):2026",
            "applicability": "primary_product",
            "reason": "Indian Standard for cotton covered copper conductors: Part 1 Round conductors.",
            "evidence_span": "Clause 1: Prescribes the requirements for cotton covered round copper conductors for electrical windings.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 8783 (Part 2):2026",
                "hn_class": "HN1",
                "confusability_reason": "Winding wires for submersible motors standard.",
                "rejection_reason": "IS 8783 is specialized polymer/nylon covered wire for submerged motors, not cotton covered conductors.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 398 (Part 2):2025",
                "hn_class": "HN7",
                "confusability_reason": "Overhead aluminium conductors.",
                "rejection_reason": "IS 398 is bare aluminium conductor for outdoor lines, not insulated copper winding wire.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2026"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    }
]

# 3. MULTILINGUAL SUBSET (Q_OWM_001 to Q_OWM_010)
multilingual_queries = [
    {
        "query_id": "Q_OWM_001",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Uttar Pradesh Public Works Department (UP PWD)",
            "tender_id": "UPPWD/BRIDGE/STEEL/2025/55",
            "tender_publication_date": "2025-07-05",
            "evaluation_as_of_date": "2025-07-20",
            "portal_url": "https://uppwd.gov.in"
        },
        "query": {
            "raw_text": "आरसीसी कंक्रीट निर्माण एवं पुल निर्माण हेतु टीएमटी उच्च शक्ति विकृत स्टील बार Fe 500D ग्रेड की आपूर्ति, बीआईएस मानक विनिर्देश के अनुसार।",
            "language": "hi",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Reinforcing Steel"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "hard",
            "language": "hi",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "High Strength Deformed Steel Bars",
            "scope_keywords": ["विकृत स्टील बार", "Fe 500D", "कंक्रीट निर्माण", "पुल निर्माण"],
            "target_product": "High Strength Deformed Steel Bars and Wires for Concrete Reinforcement",
            "material_grade": "Fe 500D",
            "application": "RCC bridge construction",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 1786:2008",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for high strength deformed steel bars and wires for concrete reinforcement.",
            "evidence_span": "Clause 1.1: Covers the requirements of deformed steel bars and wires for use as reinforcement in concrete.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 432 (Part 1):2026",
                "hn_class": "HN1",
                "confusability_reason": "Mild steel bars for concrete reinforcement.",
                "rejection_reason": "IS 432 covers plain mild steel bars, not high strength Fe 500D deformed bars.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 2062:2011",
                "hn_class": "HN2",
                "confusability_reason": "Hot rolled structural steel plates and sections.",
                "rejection_reason": "IS 2062 is for structural steel plates, not concrete reinforcement.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2008"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_002",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Bihar Urban Infrastructure Development Corp (BUIDCO)",
            "tender_id": "BUIDCO/PIPE/WATER/2025/39",
            "tender_publication_date": "2025-07-06",
            "evaluation_as_of_date": "2025-07-22",
            "portal_url": "https://buidco.in"
        },
        "query": {
            "raw_text": "शहरी पेयजल वितरण नेटवर्क हेतु 110 मिमी नाममात्र व्यास पीएन 10 अनप्लास्टिकाइज्ड पीवीसी पाइप की खरीद।",
            "language": "hi",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Plastic Piping"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "hard",
            "language": "hi",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Unplasticized PVC Pipes for Potable Water Supplies",
            "scope_keywords": ["पेयजल वितरण", "पीवीसी पाइप", "110 मिमी", "पीएन 10", "अनप्लास्टिकाइज्ड"],
            "target_product": "Unplasticized PVC Pipes for Potable Water Supplies - Specification",
            "material_grade": "uPVC",
            "rating_capacity": "PN10, 110 mm",
            "application": "Potable water supply network",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 4985:2021",
            "applicability": "primary_product",
            "reason": "Indian Standard for unplasticized PVC pipes for potable water supplies.",
            "evidence_span": "Clause 1.1: Specifies requirements for unplasticized polyvinyl chloride pipes for potable water supplies.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 12818:2010",
                "hn_class": "HN1",
                "confusability_reason": "uPVC casing pipes for tube wells.",
                "rejection_reason": "IS 12818 covers borewell casing pipes, not distribution mains.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 13592:2013",
                "hn_class": "HN1",
                "confusability_reason": "uPVC soil and waste drainage pipes.",
                "rejection_reason": "IS 13592 is for drainage, not drinking water supply under pressure.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2021"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_003",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Rajasthan Housing Board",
            "tender_id": "RHB/ELEC/SW/2025/12",
            "tender_publication_date": "2025-07-08",
            "evaluation_as_of_date": "2025-07-25",
            "portal_url": "https://urban.rajasthan.gov.in"
        },
        "query": {
            "raw_text": "आवासीय क्वार्टरों में आंतरिक विद्युत स्थापना हेतु 6A एवं 16A 240V फ्लश-माउंटेड पियानो एवं रॉकर स्विच की आपूर्ति।",
            "language": "hi",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Wiring Accessories"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "hard",
            "language": "hi",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Switches for Domestic and Similar Purposes",
            "scope_keywords": ["पियानो स्विच", "रॉकर स्विच", "6A", "16A", "विद्युत स्थापना"],
            "target_product": "Switches for Domestic and Similar Purposes - Specification",
            "material_grade": "Polycarbonate housing",
            "rating_capacity": "6A, 16A, 240V AC",
            "application": "Residential indoor wiring",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 3854:2023",
            "applicability": "primary_product",
            "reason": "Indian Standard for switches for domestic and similar purposes.",
            "evidence_span": "Clause 1: Applies to manually operated general purpose switches for AC only with a rated voltage not exceeding 440 V.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 1293:2019",
                "hn_class": "HN1",
                "confusability_reason": "Plugs and sockets standard.",
                "rejection_reason": "IS 1293 covers socket outlets, not wall switches.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS/IEC 60947 (Part 3):2012",
                "hn_class": "HN7",
                "confusability_reason": "Industrial switches and disconnectors.",
                "rejection_reason": "IS/IEC 60947-3 is for industrial switchgear, not domestic wall switches.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2023"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_004",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Madhya Pradesh Poorv Kshetra Vidyut Vitaran Co. (MPPKVVCL)",
            "tender_id": "MPPKVVCL/TRANS/2025/78",
            "tender_publication_date": "2025-07-10",
            "evaluation_as_of_date": "2025-07-28",
            "portal_url": "https://mpez.co.in"
        },
        "query": {
            "raw_text": "ग्रामीण विद्युत फीडर के लिए 11 kV / 433 V 100 kVA आउटडोर ऑयल-इमर्स्ड वितरण ट्रांसफार्मर, 3-स्टार ऊर्जा दक्षता स्तर, कॉपर वाइंडिंग।",
            "language": "hi",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Transformers"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "hard",
            "language": "hi",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Distribution Transformers",
            "scope_keywords": ["वितरण ट्रांसफार्मर", "100 kVA", "11 kV", "ऑयल-इमर्स्ड", "ऊर्जा दक्षता"],
            "target_product": "Outdoor/Indoor Type Oil Immersed Distribution Transformers Up to and Including 2500 kVA, 33 kV",
            "material_grade": "Copper winding, CRGO core",
            "rating_capacity": "100 kVA, 11/0.433 kV",
            "application": "Rural distribution substation",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 1180 (Part 1):2014",
            "applicability": "primary_product",
            "reason": "Indian Standard for outdoor/indoor type oil immersed distribution transformers up to and including 2500 kVA, 33 kV.",
            "evidence_span": "Clause 1.1: Specifies requirements and tests for outdoor/indoor type oil immersed distribution transformers.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 2026 (Part 1):2011",
                "hn_class": "HN7",
                "confusability_reason": "Power transformers general specification.",
                "rejection_reason": "Distribution transformers are strictly covered under IS 1180 (Part 1).",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 11171:1985",
                "hn_class": "HN3",
                "confusability_reason": "Dry-type transformers standard.",
                "rejection_reason": "Query specifies oil-immersed transformers, not dry-type.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2014"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_005",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Gujarat Housing Board",
            "tender_id": "GHB/CIVIL/TILE/2025/44",
            "tender_publication_date": "2025-07-12",
            "evaluation_as_of_date": "2025-07-28",
            "portal_url": "https://gujarathousingboard.gujarat.gov.in"
        },
        "query": {
            "raw_text": "નવા કોમર્શિયલ બિલ્ડિંગમાં સિરામિક અને મોઝેક ટાઇલ્સ લગાવવા માટે હાઇ પરફોર્મન્સ ટાઇલ એડહેસિવ ટાઇપ 2 ની પ્રાપ્તિ.",
            "language": "gu",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Construction Chemicals"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "hard",
            "language": "gu",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Adhesives for Ceramic and Mosaic Tiles",
            "scope_keywords": ["ટાઇલ એડહેસિવ", "સિરામિક ટાઇલ્સ", "મોઝેક ટાઇલ્સ", "ટાઇપ 2"],
            "target_product": "Adhesives for Use with Ceramic, Mosaic and Stone Tiles - Specification",
            "material_grade": "Type 2 modified cementitious mortar",
            "application": "Wall and floor tile adhesion",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 15477:2019",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for adhesives for use with ceramic, mosaic and stone tiles.",
            "evidence_span": "Clause 1: Prescribes the requirements for adhesives for use with ceramic, mosaic and stone tiles.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 15622:2017",
                "hn_class": "HN2",
                "confusability_reason": "Ceramic tiles standard.",
                "rejection_reason": "Tender is for tile adhesive, not the tiles themselves.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 13630 (Part 1):2019",
                "hn_class": "HN5",
                "confusability_reason": "Test methods for tiles.",
                "rejection_reason": "IS 13630 covers laboratory testing of tiles, not adhesive.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2019"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_006",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Gujarat Energy Transmission Corp (GETCO)",
            "tender_id": "GETCO/ACSR/COND/2025/10",
            "tender_publication_date": "2025-07-14",
            "evaluation_as_of_date": "2025-07-30",
            "portal_url": "https://getcogujarat.com"
        },
        "query": {
            "raw_text": "ઓવરહેડ પાવર ટ્રાન્સમિશન લાઇન માટે એલ્યુમિનિયમ કન્ડક્ટર ગેલ્વેનાઇઝ્ડ સ્ટીલ રિઇનફોર્સ્ડ (ACSR પેન્થર અને ઝેબ્રા) ની સપ્લાય.",
            "language": "gu",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Overhead Conductors"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "hard",
            "language": "gu",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Aluminium Conductor Steel Reinforced (ACSR)",
            "scope_keywords": ["ACSR", "એલ્યુમિનિયમ કન્ડક્ટર", "સ્ટીલ રિઇનફોર્સ્ડ", "ટ્રાન્સમિશન લાઇન"],
            "target_product": "Aluminium Conductor for Overhead Transmission Purposes Part 2 Aluminium Conductors Galvanized Steel Reinforced",
            "material_grade": "ACSR (Aluminium with GI steel core)",
            "application": "High voltage overhead power transmission",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 398 (Part 2):2025",
            "applicability": "primary_product",
            "reason": "Indian Standard for aluminium conductors for overhead transmission purposes: Part 2 Aluminium conductors, galvanized steel-reinforced.",
            "evidence_span": "Clause 1: Prescribes the requirements for aluminium conductors, galvanized steel-reinforced (ACSR) for overhead power transmission.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 398 (Part 1):1996",
                "hn_class": "HN1",
                "confusability_reason": "AAC all aluminium conductors without steel core.",
                "rejection_reason": "Tender asks for ACSR steel reinforced, not AAC.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 398 (Part 4):1994",
                "hn_class": "HN1",
                "confusability_reason": "AAAC aluminium alloy conductors.",
                "rejection_reason": "Tender asks for ACSR, not AAAC alloy.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2025"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_007",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Sardar Sarovar Narmada Nigam Limited (SSNNL)",
            "tender_id": "SSNNL/CEM/RAPID/2025/08",
            "tender_publication_date": "2025-07-15",
            "evaluation_as_of_date": "2025-07-30",
            "portal_url": "https://sardarsarovardam.org"
        },
        "query": {
            "raw_text": "કેનાલ રિપેરિંગ અને તાત્કાલિક પ્રિકાસ્ટ કોંક્રીટ કામો માટે રેપિડ હાર્ડનિંગ પોર્ટલેન્ડ સિમેન્ટ ની ખરીદી.",
            "language": "gu",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Cement and Binders"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "hard",
            "language": "gu",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Rapid Hardening Portland Cement",
            "scope_keywords": ["રેપિડ હાર્ડનિંગ", "પોર્ટલેન્ડ સિમેન્ટ", "કેનાલ રિપેરિંગ", "પ્રિકાસ્ટ કોંક્રીટ"],
            "target_product": "Rapid Hardening Portland Cement - Specification",
            "material_grade": "Rapid hardening cement clinker",
            "application": "Emergency canal repair and rapid turnaround precast",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 8041:2026",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for rapid hardening Portland cement.",
            "evidence_span": "Clause 1: Prescribes the requirements for manufacture and chemical and physical requirements of rapid hardening Portland cement.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 269:2015",
                "hn_class": "HN1",
                "confusability_reason": "Ordinary Portland cement standard.",
                "rejection_reason": "Ordinary Portland cement does not meet high early strength requirements.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 455:2015",
                "hn_class": "HN3",
                "confusability_reason": "Portland slag cement.",
                "rejection_reason": "Slag cement has slow early strength gain.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2026"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_008",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Delhi State Industrial and Infrastructure Dev. Corp (DSIIDC)",
            "tender_id": "DSIIDC/ELEC/CBL/2025/11",
            "tender_publication_date": "2025-07-16",
            "evaluation_as_of_date": "2025-07-30",
            "portal_url": "https://dsiidc.org"
        },
        "query": {
            "raw_text": "Residential building internal wiring ke liye 1100V copper conductor PVC insulated flexible wire chahiye, BIS certification mandatory.",
            "language": "hinglish",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Electrical Cables"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "hinglish",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "PVC Insulated Cables for Working Voltages Up to 1100 V",
            "scope_keywords": ["internal wiring", "1100V", "copper conductor", "PVC insulated", "flexible wire"],
            "target_product": "PVC Insulated Cables for Working Voltages Up to and Including 1100 V",
            "material_grade": "Copper, PVC",
            "rating_capacity": "1100 V",
            "application": "Internal building wiring",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 694:2010",
            "applicability": "primary_product",
            "reason": "Indian Standard for PVC insulated cables for working voltages up to and including 1100 V.",
            "evidence_span": "Clause 1.1: Covers the requirements for PVC insulated cables for working voltages up to and including 1100 V.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 1554 (Part 1):1988",
                "hn_class": "HN1",
                "confusability_reason": "Heavy duty armoured cables.",
                "rejection_reason": "Tender is for domestic flexible building wire, not heavy duty armoured mains cable.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 7098 (Part 1):1988",
                "hn_class": "HN2",
                "confusability_reason": "XLPE cables standard.",
                "rejection_reason": "Tender specifies PVC insulation, not XLPE.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2010"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_009",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Noida Power Company Limited (NPCL)",
            "tender_id": "NPCL/XLPE/CBL/2025/19",
            "tender_publication_date": "2025-07-18",
            "evaluation_as_of_date": "2025-08-01",
            "portal_url": "https://noidapower.com"
        },
        "query": {
            "raw_text": "Substation underground power cabling ke liye 4 core 185 sq mm aluminium conductor XLPE insulated armoured cable 1.1 kV grade supply karna hai.",
            "language": "hinglish",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Electrical Cables"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "hinglish",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "XLPE Insulated Thermoplastic Sheathed Cables",
            "scope_keywords": ["underground cabling", "4 core 185 sq mm", "aluminium", "XLPE insulated", "armoured cable", "1.1 kV"],
            "target_product": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 1 For Working Voltage Up to and Including 1100 V",
            "material_grade": "XLPE, aluminium, GI strip",
            "rating_capacity": "1.1 kV, 4x185 sq mm",
            "application": "Underground power feeder cabling",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 7098 (Part 1):2025",
            "applicability": "primary_product",
            "reason": "Indian Standard for XLPE insulated thermoplastic sheathed cables: Part 1 For working voltage up to and including 1100 V.",
            "evidence_span": "Clause 1: Prescribes the requirements for XLPE insulated cables for working voltages up to and including 1100 V.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 7098 (Part 2):2011",
                "hn_class": "HN1",
                "confusability_reason": "Part 2 of same series for 3.3 kV to 33 kV.",
                "rejection_reason": "Tender asks for 1.1 kV, which falls strictly under Part 1.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 1554 (Part 1):1988",
                "hn_class": "HN2",
                "confusability_reason": "PVC armoured cables.",
                "rejection_reason": "Tender specifies XLPE insulation, not PVC.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2025", "1988"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWM_010",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Central Public Works Department (CPWD)",
            "tender_id": "CPWD/CIVIL/GYP/2025/99",
            "tender_publication_date": "2025-07-20",
            "evaluation_as_of_date": "2025-08-05",
            "portal_url": "https://cpwd.gov.in"
        },
        "query": {
            "raw_text": "Commercial office false ceiling aur partition drywall ke liye plain gypsum plaster board 12.5 mm thickness procurement karni hai.",
            "language": "hinglish",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Wall and Ceiling Boards"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "hinglish",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Gypsum Plaster Boards",
            "scope_keywords": ["false ceiling", "partition drywall", "plain gypsum plaster board", "12.5 mm"],
            "target_product": "Gypsum Plaster Boards - Specification Part 1 Plain Gypsum Plaster Boards",
            "material_grade": "Gypsum board paper faced",
            "rating_capacity": "12.5 mm thickness",
            "application": "Ceiling and drywall installation",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 2095 (Part 1):2023",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for gypsum plaster boards: Part 1 Plain gypsum plaster boards.",
            "evidence_span": "Clause 1: Prescribes the requirements for plain gypsum plaster boards used in building construction.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 2095 (Part 2):2022",
                "hn_class": "HN1",
                "confusability_reason": "Coated gypsum plaster boards.",
                "rejection_reason": "Tender asks for plain gypsum plaster board, not coated/pre-decorated boards.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 14862:2000",
                "hn_class": "HN2",
                "confusability_reason": "Fibre cement flat sheets.",
                "rejection_reason": "Cement sheets are not gypsum boards.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2023"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    }
]

print(f"Generated {len(multilingual_queries)} multilingual queries.")

# 4. LONG CLAUSE SUBSET (Q_OWL_001 to Q_OWL_010)
long_clause_queries = [
    {
        "query_id": "Q_OWL_001",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "National Highways & Infrastructure Development Corp (NHIDCL)",
            "tender_id": "NHIDCL/TUNNEL/STEEL/2025/01",
            "tender_publication_date": "2025-07-01",
            "evaluation_as_of_date": "2025-07-20",
            "portal_url": "https://nhidcl.com"
        },
        "query": {
            "raw_text": "Section 4.2.1 Technical Specifications for Structural Reinforcement: The contractor shall supply and deliver to site high strength thermo-mechanically treated (TMT) deformed steel rebar conforming to Fe 500D grade for all reinforced cement concrete tunnel lining works. Steel rebars must possess minimum 0.2 percent proof stress of 500 MPa, tensile strength to yield stress ratio TS/YS >= 1.12, and minimum percentage elongation at fracture of 16 percent. Chemical composition must strictly limit Carbon to maximum 0.25%, Sulphur to 0.040%, Phosphorus to 0.040%, and combined S+P to 0.075%. Manufacturer test certificates from primary steel producers along with third party NABL accredited laboratory test reports verifying bend and rebend test properties must accompany every consignment. The entire supply must strictly satisfy the Indian Standard specification for deformed steel bars and wires for concrete reinforcement.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Reinforcing Steel"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "High Strength Deformed Steel Bars",
            "scope_keywords": ["TMT deformed steel rebar", "Fe 500D", "proof stress 500 MPa", "tunnel lining", "concrete reinforcement"],
            "target_product": "High Strength Deformed Steel Bars and Wires for Concrete Reinforcement",
            "material_grade": "Fe 500D",
            "application": "RCC tunnel lining concrete reinforcement",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 1786:2008",
            "applicability": "primary_product",
            "reason": "Primary standard governing high strength deformed steel bars and wires for concrete reinforcement.",
            "evidence_span": "Clause 1.1: Covers the requirements of deformed steel bars and wires for use as reinforcement in concrete.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 432 (Part 1):2026",
                "hn_class": "HN1",
                "confusability_reason": "Mild steel bar specification.",
                "rejection_reason": "Plain mild steel bars cannot achieve 500 MPa yield strength with Fe 500D ductility.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 2062:2011",
                "hn_class": "HN2",
                "confusability_reason": "Structural steel specification.",
                "rejection_reason": "IS 2062 is for structural steel plates and sections, not concrete reinforcing rebars.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2008"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_002",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Uttarakhand Peyjal Nigam",
            "tender_id": "UPN/WTR/UPVC/2025/61",
            "tender_publication_date": "2025-07-03",
            "evaluation_as_of_date": "2025-07-22",
            "portal_url": "https://peyjal.uk.gov.in"
        },
        "query": {
            "raw_text": "Clause 8.1 Scope of Supply and Technical Standards for Potable Water Piping: Manufacture, supply, inspection, testing, and delivery at departmental store of rigid unplasticized polyvinyl chloride (uPVC) pressure pipes for rural piped water supply schemes. All pipes shall be nominal diameter 90 mm and 110 mm rated for working pressure of 0.6 MPa (PN6) and 1.0 MPa (PN10) service. The pipes shall have socket and spigot ends suitable for elastomeric sealing ring joints conforming to toxicological and hygienic requirements for drinking water conveyance. Raw material shall be virgin unplasticized PVC without lead stabilizer additives. Hydrostatic pressure proof testing, opacity test, and short-term hydraulic test must be certified under BIS product certification license scheme. The product must strictly comply with the national specification for uPVC pipes for potable water supplies.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Plastic Piping"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Unplasticized PVC Pipes for Potable Water Supplies",
            "scope_keywords": ["unplasticized polyvinyl chloride", "uPVC pressure pipes", "potable water supply", "PN6", "PN10", "110 mm"],
            "target_product": "Unplasticized PVC Pipes for Potable Water Supplies - Specification",
            "material_grade": "Lead-free virgin uPVC compound",
            "rating_capacity": "PN6, PN10, 90mm, 110mm",
            "application": "Rural drinking water supply network",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 4985:2021",
            "applicability": "primary_product",
            "reason": "Indian Standard for unplasticized PVC pipes for potable water supplies.",
            "evidence_span": "Clause 1.1: Specifies requirements for unplasticized polyvinyl chloride pipes for potable water supplies.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 12818:2010",
                "hn_class": "HN1",
                "confusability_reason": "uPVC casing and screen pipes for tube wells.",
                "rejection_reason": "IS 12818 covers deep borewell casing, not distribution piping networks.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 13592:2013",
                "hn_class": "HN1",
                "confusability_reason": "uPVC soil and waste pipes.",
                "rejection_reason": "IS 13592 is for non-pressure drainage, not potable water supply.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2021"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_003",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Hubli Electricity Supply Company (HESCOM)",
            "tender_id": "HESCOM/DIST/TRANS/2025/11",
            "tender_publication_date": "2025-07-05",
            "evaluation_as_of_date": "2025-07-24",
            "portal_url": "https://hescom.karnataka.gov.in"
        },
        "query": {
            "raw_text": "Specification No. HESCOM/E-66/2025 Technical Clause 3.1: Manufacture, testing, supply, and delivery of 11/0.433 kV, 250 kVA, 3-phase, 50 Hz, outdoor type, oil-immersed, naturally cooled (ONAN) distribution transformers. The transformers shall have high quality prime grade cold rolled grain oriented (CRGO) silicon steel core laminations and pure electrolytic copper double paper covered winding wires. Total maximum losses at 50% and 100% loading shall not exceed the statutory limits corresponding to Energy Efficiency Level 2. The oil shall be uninhibited new mineral insulating oil conforming to national insulation requirements. Each transformer shall be provided with standard fittings including off-circuit tap changing switch with +/- 5% range in steps of 2.5%, oil level gauge, silica gel breather, and pressure relief valve. The units must strictly comply with the Indian Standard specification for outdoor/indoor type oil immersed distribution transformers up to and including 2500 kVA, 33 kV.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Transformers"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Distribution Transformers Up to 2500 kVA, 33 kV",
            "scope_keywords": ["distribution transformers", "250 kVA", "11/0.433 kV", "oil-immersed", "copper winding", "ONAN"],
            "target_product": "Outdoor/Indoor Type Oil Immersed Distribution Transformers Up to and Including 2500 kVA, 33 kV",
            "material_grade": "CRGO core, copper conductor, mineral insulating oil",
            "rating_capacity": "250 kVA, 11/0.433 kV",
            "application": "Outdoor distribution substation step-down",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 1180 (Part 1):2014",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for outdoor/indoor type oil immersed distribution transformers up to and including 2500 kVA, 33 kV.",
            "evidence_span": "Clause 1.1: Specifies requirements and tests for outdoor/indoor type oil immersed distribution transformers.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 2026 (Part 1):2011",
                "hn_class": "HN7",
                "confusability_reason": "Power transformers general specification.",
                "rejection_reason": "IS 1180 (Part 1) is the mandated standard for distribution transformers up to 2500 kVA.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 11171:1985",
                "hn_class": "HN3",
                "confusability_reason": "Dry-type transformers standard.",
                "rejection_reason": "Tender explicitly requires oil-immersed ONAN transformers, not dry-type.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2014"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_004",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Military Engineer Services (MES), Western Command",
            "tender_id": "MES/WC/ELEC/WIRE/2025/81",
            "tender_publication_date": "2025-07-06",
            "evaluation_as_of_date": "2025-07-25",
            "portal_url": "https://mes.gov.in"
        },
        "query": {
            "raw_text": "Tender Specification Schedule 'A' Item No. 14: Providing and drawing single-core multi-stranded annealed high conductivity electrolytic bare copper conductor flexible electrical cables, flame retardant low smoke (FRLS) PVC insulated and unsheathed, rated for working voltage up to and including 1100 V. Cable sizes comprise 1.5 sq mm, 2.5 sq mm, 4.0 sq mm, and 6.0 sq mm in recessed steel/PVC conduits for sub-main wiring and light/fan point circuits in multi-storey military accommodation barracks. Insulation resistance, spark test at 6 kV, high voltage dielectric test, and oxygen index minimum 29% shall conform to test standards. The wires shall bear standard BIS certification mark and conform to the Indian Standard for PVC insulated cables for working voltages up to and including 1100 V.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Electrical Cables"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "PVC Insulated Cables for Working Voltages Up to and Including 1100 V",
            "scope_keywords": ["PVC insulated", "flexible electrical cables", "copper conductor", "1100 V", "FRLS"],
            "target_product": "PVC Insulated Cables for Working Voltages Up to and Including 1100 V",
            "material_grade": "Electrolytic copper, FRLS PVC",
            "rating_capacity": "1100 V, 1.5 to 6.0 sq mm",
            "application": "Internal electrical wiring in conduits",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 694:2010",
            "applicability": "primary_product",
            "reason": "Indian Standard for PVC insulated cables for working voltages up to and including 1100 V.",
            "evidence_span": "Clause 1.1: Covers the requirements for PVC insulated cables for working voltages up to and including 1100 V.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 1554 (Part 1):1988",
                "hn_class": "HN1",
                "confusability_reason": "Heavy duty PVC armoured cables.",
                "rejection_reason": "IS 1554 is for heavy duty power/mains cables, not conduit wiring flexible wire.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 7098 (Part 1):1988",
                "hn_class": "HN2",
                "confusability_reason": "XLPE cables standard.",
                "rejection_reason": "Tender explicitly specifies PVC insulation, not XLPE.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2010"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_005",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Chennai Metro Rail Limited (CMRL)",
            "tender_id": "CMRL/PHASE2/CBL/2025/07",
            "tender_publication_date": "2025-07-08",
            "evaluation_as_of_date": "2025-07-28",
            "portal_url": "https://chennaimetrorail.org"
        },
        "query": {
            "raw_text": "Section 9 Electrical Power Supply Distribution System: Design, manufacture, testing at works, packing, and supply of 1.1 kV rated 3.5-core and 4-core crosslinked polyethylene (XLPE) insulated, stranded aluminium compact conductor, galvanized flat steel strip armoured heavy-duty power cables. The insulation shall be extruded crosslinked polyethylene complying with electrical and physical properties for 90 deg C continuous conductor operating temperature. The outer jacket shall be ultraviolet and water resistant extruded thermoplastic sheath. Cables will be installed in concrete cable trenches and ventilated ladder trays in elevated and underground metro station substations. The product shall strictly conform to the national specification for XLPE insulated thermoplastic sheathed cables for working voltage up to and including 1100 V.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Electrical Cables"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "XLPE Insulated Thermoplastic Sheathed Cables",
            "scope_keywords": ["XLPE insulated", "1.1 kV", "armoured", "aluminium conductor", "cables"],
            "target_product": "Crosslinked Polyethylene Insulated Thermoplastic Sheathed Cables: Part 1 For Working Voltage Up to and Including 1100 V",
            "material_grade": "XLPE, aluminium, steel strip",
            "rating_capacity": "1.1 kV, 3.5-core & 4-core",
            "application": "Metro rail station low voltage power distribution",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 7098 (Part 1):2025",
            "applicability": "primary_product",
            "reason": "Indian Standard for XLPE insulated thermoplastic sheathed cables: Part 1 For working voltage up to and including 1100 V.",
            "evidence_span": "Clause 1: Prescribes the requirements for XLPE insulated cables for working voltages up to and including 1100 V.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 7098 (Part 2):2011",
                "hn_class": "HN1",
                "confusability_reason": "Part 2 of same series for 3.3 kV to 33 kV.",
                "rejection_reason": "Tender asks for 1.1 kV grade, strictly under Part 1.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 1554 (Part 1):1988",
                "hn_class": "HN2",
                "confusability_reason": "PVC insulated cables standard.",
                "rejection_reason": "Tender specifies XLPE insulation with 90°C rating, not PVC with 70°C rating.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2025", "1988"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_006",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "National Highways Authority of India (NHAI)",
            "tender_id": "NHAI/EXP/AGG/2025/44",
            "tender_publication_date": "2025-07-10",
            "evaluation_as_of_date": "2025-07-30",
            "portal_url": "https://nhai.gov.in"
        },
        "query": {
            "raw_text": "Section 1000 Materials for Concrete Structures: The coarse aggregate for structural concrete grades M35, M40, and pavement quality concrete (PQC) shall consist of clean, hard, dense, durable crushed stone free from decomposed rock, clay, lumps, shale, organic impurities, and other deleterious materials. Grading shall be 20 mm and 10 mm graded aggregate. The fine aggregate shall be natural river sand or manufactured stone sand conforming to grading Zone II. Combined aggregate grading must achieve maximum packing density in accordance with mix design requirements. Deleterious materials limits, flakiness index, elongation index, Los Angeles abrasion loss, aggregate impact value, and soundness tests must fully conform to the Indian Standard specification for coarse and fine aggregates for concrete.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Concrete Aggregates"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Coarse and Fine Aggregate for Concrete",
            "scope_keywords": ["coarse aggregate", "fine aggregate", "crushed stone", "structural concrete", "PQC"],
            "target_product": "Coarse and Fine Aggregate for Concrete - Specification",
            "material_grade": "Crushed stone aggregate and Zone II sand",
            "application": "Structural and pavement concrete",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 383:2016",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for coarse and fine aggregate for concrete.",
            "evidence_span": "Clause 1: Prescribes the requirements for aggregates, natural and manufactured, for use in concrete.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 2386 (Part 1):1963",
                "hn_class": "HN5",
                "confusability_reason": "Aggregate testing methods.",
                "rejection_reason": "IS 2386 series covers testing methods, while IS 383 is the overarching material product specification.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 650:1991",
                "hn_class": "HN1",
                "confusability_reason": "Standard sand for testing cement.",
                "rejection_reason": "IS 650 is laboratory calibration sand, not bulk concrete construction aggregate.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2016"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_007",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Airports Authority of India (AAI)",
            "tender_id": "AAI/TERM/SW/2025/29",
            "tender_publication_date": "2025-07-12",
            "evaluation_as_of_date": "2025-08-01",
            "portal_url": "https://aai.aero"
        },
        "query": {
            "raw_text": "Terminal Building Electrical Works Clause 6.3: Supply, installation, testing and commissioning of 10AX and 16A, 240V AC 50Hz modular flush-type piano and rocker wall switches with fire retardant polycarbonate front plates for passenger terminal concourse and administrative offices. All switches must have silver alloy contacts, positive snap action mechanism, and be tested for 40,000 operations electrical endurance at full rated current. The switches must be certified under the compulsory BIS certification scheme conforming to the national specification for switches for domestic and similar purposes.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Wiring Accessories"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Switches for Domestic and Similar Purposes",
            "scope_keywords": ["modular wall switches", "10AX", "16A", "piano switches", "rocker switches", "240V"],
            "target_product": "Switches for Domestic and Similar Purposes - Specification",
            "material_grade": "Polycarbonate housing, silver alloy contacts",
            "rating_capacity": "10AX, 16A, 240V AC",
            "application": "Airport terminal lighting and power switching",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 3854:2023",
            "applicability": "primary_product",
            "reason": "Indian Standard for switches for domestic and similar purposes.",
            "evidence_span": "Clause 1: Applies to manually operated general purpose switches for AC only with a rated voltage not exceeding 440 V.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 1293:2019",
                "hn_class": "HN1",
                "confusability_reason": "Plugs and sockets standard.",
                "rejection_reason": "IS 1293 covers socket outlets, not wall control switches.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS/IEC 60947 (Part 3):2012",
                "hn_class": "HN7",
                "confusability_reason": "Industrial switches and disconnectors.",
                "rejection_reason": "IS/IEC 60947-3 is for industrial power disconnectors, not domestic modular wall switches.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2023"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_008",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Deendayal Port Authority (Kandla)",
            "tender_id": "DPA/CIVIL/SRC/2025/19",
            "tender_publication_date": "2025-07-14",
            "evaluation_as_of_date": "2025-08-02",
            "portal_url": "https://deendayalport.gov.in"
        },
        "query": {
            "raw_text": "Section 3.1.2 Hydraulic Binders for Marine Exposure: The cement used in the construction of marine jetty pile foundations, diaphragm walls, and seawater intake chambers shall be sulphate resisting Portland cement. The tricalcium aluminate (C3A) content shall not exceed 5.0 percent and 2C3A + C4AF shall not exceed 25 percent. The fineness (specific surface by Blaine air permeability method) shall not be less than 225 m2/kg. Compressive strength shall be not less than 33 MPa at 28 days. Every tanker consignment must be sampled and tested for sulphate expansion in accordance with national cement testing codes. The product must strictly conform to the Indian Standard specification for sulphate resisting Portland cement.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Special Cements"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Sulphate Resisting Portland Cement",
            "scope_keywords": ["sulphate resisting", "Portland cement", "marine jetty", "C3A content", "marine exposure"],
            "target_product": "Specification for Sulphate Resisting Portland Cement",
            "material_grade": "Low C3A (<5%) Portland clinker",
            "application": "Marine jetty piles and seawater intake",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 12330:1988",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for sulphate resisting Portland cement.",
            "evidence_span": "Clause 1: Prescribes the requirements for manufacture and chemical and physical requirements of sulphate resisting Portland cement.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 269:2015",
                "hn_class": "HN1",
                "confusability_reason": "Ordinary Portland cement standard.",
                "rejection_reason": "OPC contains excessive C3A which reacts with seawater sulphates to form expansive ettringite, causing spalling.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 12600:1989",
                "hn_class": "HN3",
                "confusability_reason": "Low heat Portland cement.",
                "rejection_reason": "IS 12600 is designed for low thermal cracking in massive dam concrete, not sulphate resistance.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["1988"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_009",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Jaipur Smart City Limited (JSCL)",
            "tender_id": "JSCL/LED/LIGHT/2025/33",
            "tender_publication_date": "2025-07-16",
            "evaluation_as_of_date": "2025-08-04",
            "portal_url": "https://jaipursmartcity.rajasthan.gov.in"
        },
        "query": {
            "raw_text": "Tender Document Volume II Section 5 Lighting Luminaires: Supply of self-ballasted LED lamps 9W and 12W for general lighting services in heritage buildings and municipal premises. The LED lamps shall have bayonet cap B22d, nominal operating voltage 230V AC 50 Hz, power factor greater than 0.90, luminous efficacy >= 100 lm/W, and correlated colour temperature 4000K/6500K. The lamps must satisfy all mandatory safety provisions including insulation resistance, electric strength, mechanical strength, resistance to heat and fire, and photobiological safety under the compulsory registration scheme of the Bureau of Indian Standards. The lamps must strictly comply with the Indian Standard for self-ballasted LED lamps for general lighting services Part 1 Safety requirements.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Lighting"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Self-Ballasted LED Lamps",
            "scope_keywords": ["self-ballasted LED lamps", "LED lamps", "general lighting services", "B22d", "safety requirements"],
            "target_product": "Self-Ballasted LED Lamps for General Lighting Services Part 1 Safety Requirements",
            "material_grade": "Solid state lighting LED",
            "rating_capacity": "9W, 12W, 230V AC",
            "application": "General interior domestic and municipal lighting",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 16102 (Part 1):2026",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for self-ballasted LED lamps for general lighting services: Part 1 Safety requirements.",
            "evidence_span": "Clause 1: Specifies the safety and interchangeability requirements for self-ballasted LED lamps.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 16102 (Part 2):2026",
                "hn_class": "HN1",
                "confusability_reason": "Performance requirements part of same LED lamp series.",
                "rejection_reason": "Part 1 covers mandatory electrical safety certification under CRS.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 2418 (Part 1):1977",
                "hn_class": "HN4",
                "confusability_reason": "Tubular fluorescent lamps specification.",
                "rejection_reason": "IS 2418 is for obsolete fluorescent discharge tubes, not modern LED lamps.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2026"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    },
    {
        "query_id": "Q_OWL_010",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "National Buildings Construction Corporation (NBCC)",
            "tender_id": "NBCC/INTERIOR/GYP/2025/51",
            "tender_publication_date": "2025-07-18",
            "evaluation_as_of_date": "2025-08-05",
            "portal_url": "https://nbccindia.com"
        },
        "query": {
            "raw_text": "Section 09250 Gypsum Board Assemblies: Furnish and install paper-faced gypsum plaster boards for interior partition walls and suspended ceiling assemblies in the high-court annex complex. Plaster boards shall have thickness 12.5 mm and 15 mm with tapered edges suitable for seamless joint tape and joint compound finishing. The gypsum core shall be non-combustible gypsum encased in firmly bonded recycled paper liners meeting flexural breaking load, surface water absorption, and nail pull resistance. Partition assemblies must achieve minimum 1-hour fire resistance rating and sound transmission class STC 48 when installed with light gauge galvanized steel stud framing. The gypsum plaster boards must strictly comply with the Indian Standard specification for plain gypsum plaster boards Part 1.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Wall and Ceiling Boards"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Gypsum Plaster Boards",
            "scope_keywords": ["gypsum plaster boards", "paper-faced", "partition walls", "ceiling assemblies", "12.5 mm"],
            "target_product": "Gypsum Plaster Boards - Specification Part 1 Plain Gypsum Plaster Boards",
            "material_grade": "Gypsum core paper faced",
            "rating_capacity": "12.5 mm, 15 mm thickness",
            "application": "Internal partition walls and false ceiling",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 2095 (Part 1):2023",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for gypsum plaster boards: Part 1 Plain gypsum plaster boards.",
            "evidence_span": "Clause 1: Prescribes the requirements for plain gypsum plaster boards used in building construction.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 2095 (Part 2):2022",
                "hn_class": "HN1",
                "confusability_reason": "Coated gypsum plaster boards specification.",
                "rejection_reason": "Part 2 covers factory pre-decorated boards, while tender asks for plain plaster boards finished with tape.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 14862:2000",
                "hn_class": "HN2",
                "confusability_reason": "Fibre cement flat sheets.",
                "rejection_reason": "Fibre cement sheets are cement-based, not gypsum boards.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2023"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": True,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "COMPLETE",
        "gold_recommendation_ready": True,
        "expected_evidence_state": "SCOPE_AVAILABLE",
        "expected_safe_decision": "PRIMARY_RECOMMENDATION_AVAILABLE"
    }
]

print(f"Generated {len(long_clause_queries)} long clause queries.")

# 5. CONFLICT / BOUNDARY SUBSET (Q_OWX_001 to Q_OWX_010)
conflict_queries = [
    {
        "query_id": "Q_OWX_001",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "constructed_expert_case",
            "organization": "Adversarial Robustness Testing Team",
            "tender_id": "ADV/CONFLICT/PIPE/01",
            "tender_publication_date": "2025-07-01",
            "evaluation_as_of_date": "2025-07-15",
            "portal_url": None
        },
        "query": {
            "raw_text": "Procurement of unplasticized PVC pipes nominal diameter 110 mm rated for 33 kV high voltage electrical power transmission.",
            "language": "en",
            "domain": "CROSS_SECTOR",
            "product_family": "Contradictory Specification"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "adversarial",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_3_INSUFFICIENT_INFORMATION"
        },
        "technical_requirements": {
            "product": "Contradictory uPVC Pipe / High Voltage Cable",
            "scope_keywords": ["unplasticized PVC pipes", "33 kV", "high voltage power transmission"],
            "target_product": None,
            "material_grade": "Contradictory plastic pipe vs electrical cable",
            "rating_capacity": "33 kV conflicting",
            "application": "Impossible combined application",
            "missing_parameters": ["electrical conductor material", "cable insulation type", "actual product type"]
        },
        "gold_standards": [],
        "hard_negatives": [
            {
                "standard_designation": "IS 4985:2021",
                "hn_class": "HN1",
                "confusability_reason": "Matches uPVC pipe keywords.",
                "rejection_reason": "IS 4985 is for cold potable water pipes; it cannot transmit 33 kV electrical power.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 7098 (Part 2):2011",
                "hn_class": "HN1",
                "confusability_reason": "Matches 33 kV power transmission rating.",
                "rejection_reason": "IS 7098 (Part 2) is an electrical cable, not a PVC pipe.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": []},
        "certification_requirement": {"regulatory_status": "UNKNOWN"},
        "expected_decision": {
            "query_level_state": "INSUFFICIENT_INFORMATION",
            "expected_abstention_reason": "Conflicting technical requirements: PVC water pipe combined with 33 kV power transmission."
        },
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": False,
        "gold_primary_candidate_eligible": False,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_safe_decision": "INSUFFICIENT_INFORMATION"
    },
    {
        "query_id": "Q_OWX_002",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "constructed_expert_case",
            "organization": "Adversarial Robustness Testing Team",
            "tender_id": "ADV/CONFLICT/TRANS/02",
            "tender_publication_date": "2025-07-02",
            "evaluation_as_of_date": "2025-07-15",
            "portal_url": None
        },
        "query": {
            "raw_text": "Supply of 400 kV extra high voltage pole mounted distribution transformer with 5 kVA capacity for rural consumer connection.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Contradictory Specification"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "adversarial",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_3_INSUFFICIENT_INFORMATION"
        },
        "technical_requirements": {
            "product": "Contradictory 400 kV / 5 kVA Distribution Transformer",
            "scope_keywords": ["400 kV", "5 kVA", "pole mounted", "distribution transformer"],
            "target_product": None,
            "material_grade": "Contradictory EHV transmission vs low capacity pole mount",
            "rating_capacity": "400 kV with 5 kVA impossible combination",
            "application": "Impossible power rating combination",
            "missing_parameters": ["verified voltage class", "verified kVA capacity"]
        },
        "gold_standards": [],
        "hard_negatives": [
            {
                "standard_designation": "IS 1180 (Part 1):2014",
                "hn_class": "HN1",
                "confusability_reason": "Matches distribution transformer.",
                "rejection_reason": "IS 1180 is limited to voltages up to 33 kV; 400 kV is completely outside its scope.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 2026 (Part 1):2011",
                "hn_class": "HN1",
                "confusability_reason": "Matches 400 kV power transformer.",
                "rejection_reason": "400 kV transformers are massive multi-MVA grid autotransformers, not 5 kVA pole-mounted units.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": []},
        "certification_requirement": {"regulatory_status": "UNKNOWN"},
        "expected_decision": {
            "query_level_state": "INSUFFICIENT_INFORMATION",
            "expected_abstention_reason": "Contradictory rating: 400 kV voltage is incompatible with 5 kVA pole-mounted distribution transformer."
        },
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": False,
        "gold_primary_candidate_eligible": False,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_safe_decision": "INSUFFICIENT_INFORMATION"
    },
    {
        "query_id": "Q_OWX_003",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Food Corporation of India (FCI)",
            "tender_id": "FCI/PROC/RICE/2025/99",
            "tender_publication_date": "2025-07-04",
            "evaluation_as_of_date": "2025-07-20",
            "portal_url": "https://fci.gov.in"
        },
        "query": {
            "raw_text": "Procurement of 500 Metric Tonnes of export quality 1121 Basmati Rice with maximum 2% broken grains and 12% moisture content.",
            "language": "en",
            "domain": "FOOD_AGRICULTURE",
            "product_family": "Agricultural Grains"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_4_NO_MATCH_UNKNOWN"
        },
        "technical_requirements": {
            "product": "Basmati Rice",
            "scope_keywords": ["Basmati Rice", "broken grains", "moisture content", "1121"],
            "target_product": "Basmati Rice Specification (FAD 16)",
            "material_grade": "Oryza sativa indica",
            "application": "Human food consumption",
            "missing_parameters": []
        },
        "gold_standards": [],
        "hard_negatives": [
            {
                "standard_designation": "IS 383:2016",
                "hn_class": "HN7",
                "confusability_reason": "Aggregates and grains confusion.",
                "rejection_reason": "IS 383 is for concrete rock aggregates, not edible cereal grain.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": []},
        "certification_requirement": {"regulatory_status": "UNKNOWN"},
        "expected_decision": {
            "query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE",
            "expected_abstention_reason": "Product family 'Agricultural Grains / Basmati Rice' falls under Food and Agriculture Department (FAD), outside the CED/ETD prototype coverage boundary."
        },
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": False,
        "gold_primary_candidate_eligible": False,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_safe_decision": "OUTSIDE_PROTOTYPE_COVERAGE"
    },
    {
        "query_id": "Q_OWX_004",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "All India Institute of Medical Sciences (AIIMS)",
            "tender_id": "AIIMS/MED/COTTON/2025/11",
            "tender_publication_date": "2025-07-06",
            "evaluation_as_of_date": "2025-07-22",
            "portal_url": "https://aiims.edu"
        },
        "query": {
            "raw_text": "Supply of sterile absorbent surgical cotton wool rolls 500g and sterile open weave cotton gauze bandages for operation theatre wound dressing.",
            "language": "en",
            "domain": "MEDICAL_EQUIPMENT",
            "product_family": "Medical Textiles"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_4_NO_MATCH_UNKNOWN"
        },
        "technical_requirements": {
            "product": "Absorbent Surgical Cotton",
            "scope_keywords": ["surgical cotton", "gauze bandages", "wound dressing", "sterile absorbent"],
            "target_product": "Absorbent Cotton Wool (TXD)",
            "material_grade": "Bleached absorbent cotton fibres",
            "application": "Medical surgical wound dressing",
            "missing_parameters": []
        },
        "gold_standards": [],
        "hard_negatives": [
            {
                "standard_designation": "IS 7391 (Part 1):2026",
                "hn_class": "HN7",
                "confusability_reason": "Cotton covered copper conductors keyword match on cotton.",
                "rejection_reason": "IS 7391 is an electrical winding wire, completely unrelated to medical surgical cotton.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": []},
        "certification_requirement": {"regulatory_status": "UNKNOWN"},
        "expected_decision": {
            "query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE",
            "expected_abstention_reason": "Medical textiles fall under TXD/MHD, outside the prototype CED/ETD coverage boundary."
        },
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": False,
        "gold_primary_candidate_eligible": False,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_safe_decision": "OUTSIDE_PROTOTYPE_COVERAGE"
    },
    {
        "query_id": "Q_OWX_005",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Delhi Transport Corporation (DTC)",
            "tender_id": "DTC/AUTO/TYRE/2025/89",
            "tender_publication_date": "2025-07-08",
            "evaluation_as_of_date": "2025-07-24",
            "portal_url": "https://dtc.delhi.gov.in"
        },
        "query": {
            "raw_text": "Supply of steel belted radial ply pneumatic tyres size 295/80 R22.5 with all-steel casing for low floor passenger city buses.",
            "language": "en",
            "domain": "MECHANICAL",
            "product_family": "Automotive Components"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_4_NO_MATCH_UNKNOWN"
        },
        "technical_requirements": {
            "product": "Automotive Pneumatic Tyres",
            "scope_keywords": ["radial ply", "pneumatic tyres", "passenger buses", "steel belted"],
            "target_product": "Automotive Tyres Specification (TED 7)",
            "material_grade": "Vulcanized rubber with steel cord reinforcement",
            "rating_capacity": "295/80 R22.5",
            "application": "City bus road transit",
            "missing_parameters": []
        },
        "gold_standards": [],
        "hard_negatives": [
            {
                "standard_designation": "IS 1786:2008",
                "hn_class": "HN7",
                "confusability_reason": "Matches steel reinforcement keywords.",
                "rejection_reason": "IS 1786 is for concrete rebars, not automotive tire cords.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": []},
        "certification_requirement": {"regulatory_status": "UNKNOWN"},
        "expected_decision": {
            "query_level_state": "OUTSIDE_PROTOTYPE_COVERAGE",
            "expected_abstention_reason": "Automotive pneumatic tyres fall under Transport Engineering Department (TED), outside the prototype CED/ETD coverage boundary."
        },
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "OUTSIDE_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": False,
        "gold_primary_candidate_eligible": False,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_safe_decision": "OUTSIDE_PROTOTYPE_COVERAGE"
    },
    {
        "query_id": "Q_OWX_006",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "constructed_expert_case",
            "organization": "Adversarial Robustness Testing Team",
            "tender_id": "ADV/CONFLICT/REBAR/06",
            "tender_publication_date": "2025-07-10",
            "evaluation_as_of_date": "2025-07-26",
            "portal_url": None
        },
        "query": {
            "raw_text": "Supply of high-strength deformed rebar made entirely of copper alloy with 500 MPa yield strength for reinforced concrete bridge pillars.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Contradictory Specification"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "adversarial",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_3_INSUFFICIENT_INFORMATION"
        },
        "technical_requirements": {
            "product": "Contradictory Copper Rebar for Concrete",
            "scope_keywords": ["deformed rebar", "copper alloy", "500 MPa", "concrete bridge pillars"],
            "target_product": None,
            "material_grade": "Contradictory copper alloy concrete rebar",
            "rating_capacity": "500 MPa",
            "application": "Concrete rebar reinforcement",
            "missing_parameters": ["verified material specification"]
        },
        "gold_standards": [],
        "hard_negatives": [
            {
                "standard_designation": "IS 1786:2008",
                "hn_class": "HN1",
                "confusability_reason": "High strength deformed rebar specification.",
                "rejection_reason": "IS 1786 governs steel bars and wires, not copper alloy rebar.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 7391 (Part 1):2026",
                "hn_class": "HN7",
                "confusability_reason": "Matches copper conductor keyword.",
                "rejection_reason": "IS 7391 is an electrical winding conductor, not concrete reinforcement.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": []},
        "certification_requirement": {"regulatory_status": "UNKNOWN"},
        "expected_decision": {
            "query_level_state": "INSUFFICIENT_INFORMATION",
            "expected_abstention_reason": "National building codes and concrete standards do not recognize copper alloy deformed rebars for structural concrete reinforcement."
        },
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": False,
        "gold_primary_candidate_eligible": False,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_safe_decision": "INSUFFICIENT_INFORMATION"
    },
    {
        "query_id": "Q_OWX_007",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Delhi Development Authority (DDA)",
            "tender_id": "DDA/GLASS/TOUGH/2025/11",
            "tender_publication_date": "2025-07-12",
            "evaluation_as_of_date": "2025-07-28",
            "portal_url": "https://dda.gov.in"
        },
        "query": {
            "raw_text": "Procurement of thermally toughened architectural safety glass panes 10 mm thickness for external structural glazing and building facade openings.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Glass and Glazing"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Architectural Safety Glass",
            "scope_keywords": ["toughened safety glass", "safety glass", "10 mm", "facade openings"],
            "target_product": "Safety Glass - Specification: Part 1 Architectural, Building and General Uses",
            "material_grade": "Thermally toughened soda lime glass",
            "rating_capacity": "10 mm",
            "application": "External structural glazing",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 2553 (Part 1):2018",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for safety glass: Part 1 Architectural, building and general uses.",
            "evidence_span": "Clause 1: Prescribes requirements and tests for safety glass intended for architectural and building applications.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 14900:2018",
                "hn_class": "HN3",
                "confusability_reason": "Transparent float glass standard.",
                "rejection_reason": "Ordinary annealed float glass does not qualify as toughened safety glass under IS 2553.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 2553 (Part 2):2019",
                "hn_class": "HN7",
                "confusability_reason": "Part 2 covers automotive road transport glazing.",
                "rejection_reason": "Automotive safety glass is governed by Part 2, whereas architectural building glass is strictly under Part 1.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2018"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "UNHYDRATED_STUB",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "UNHYDRATED_STUB",
        "expected_review_reason": "Gold standard lacks verified scope evidence in knowledge base.",
        "expected_safe_decision": "EXPERT_REVIEW_REQUIRED"
    },
    {
        "query_id": "Q_OWX_008",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "government_tender",
            "organization": "Haryana Shehri Vikas Pradhikaran (HSVP)",
            "tender_id": "HSVP/CIVIL/FLOAT/2025/08",
            "tender_publication_date": "2025-07-14",
            "evaluation_as_of_date": "2025-07-30",
            "portal_url": "https://hsvp.org.in"
        },
        "query": {
            "raw_text": "Supply of clear transparent flat float glass panes 6 mm nominal thickness for residential window assemblies.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Glass and Glazing"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Transparent Float Glass",
            "scope_keywords": ["transparent float glass", "clear float glass", "6 mm", "flat glass"],
            "target_product": "Transparent Float Glass - Specification",
            "material_grade": "Clear soda-lime float glass",
            "rating_capacity": "6 mm",
            "application": "Residential window glazing",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 14900:2018",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for transparent float glass.",
            "evidence_span": "Clause 1: Prescribes requirements for transparent flat float glass used for glazing and mirrors.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 2553 (Part 1):2018",
                "hn_class": "HN3",
                "confusability_reason": "Safety glass standard.",
                "rejection_reason": "Tender asks for ordinary clear annealed float glass, not safety glass.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 2835:1987",
                "hn_class": "HN6",
                "confusability_reason": "Historical flat sheet glass specification.",
                "rejection_reason": "IS 2835 covers obsolete drawn sheet glass, replaced by float glass IS 14900.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2018"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_review_reason": "Gold standard lacks verified scope evidence in knowledge base.",
        "expected_safe_decision": "EXPERT_REVIEW_REQUIRED"
    },
    {
        "query_id": "Q_OWX_009",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "state_procurement",
            "organization": "Kerala Water Authority (KWA)",
            "tender_id": "KWA/HDPE/2025/71",
            "tender_publication_date": "2025-07-16",
            "evaluation_as_of_date": "2025-08-01",
            "portal_url": "https://kwa.kerala.gov.in"
        },
        "query": {
            "raw_text": "Procurement of high density polyethylene HDPE pressure pipes nominal diameter 110 mm PE100 PN10 for potable water conveyance.",
            "language": "en",
            "domain": "CIVIL_ENGINEERING",
            "product_family": "Plastic Piping"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "medium",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_1_CLEAR"
        },
        "technical_requirements": {
            "product": "Polyethylene Pipes for Water Supply",
            "scope_keywords": ["high density polyethylene", "HDPE pipes", "PE100", "PN10", "110 mm"],
            "target_product": "Polyethylene Pipes for Water Supply - Specification",
            "material_grade": "PE100",
            "rating_capacity": "PN10, 110 mm",
            "application": "Potable water supply conveyance",
            "missing_parameters": []
        },
        "gold_standards": [{
            "standard_designation": "IS 4984:2016",
            "applicability": "primary_product",
            "reason": "Indian Standard specification for polyethylene pipes for water supply.",
            "evidence_span": "Clause 1: Prescribes requirements for polyethylene pipes intended for the conveyance of water for human consumption.",
            "relationship_obligation": "MANDATORY",
            "mandatory_by_regulation": True
        }],
        "hard_negatives": [
            {
                "standard_designation": "IS 4985:2021",
                "hn_class": "HN2",
                "confusability_reason": "uPVC water pipes.",
                "rejection_reason": "Tender specifies HDPE (polyethylene), not uPVC.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 14885:2001",
                "hn_class": "HN1",
                "confusability_reason": "Polyethylene pipes for gas supply.",
                "rejection_reason": "IS 14885 is for natural gas distribution, not potable water.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": ["2016"]},
        "certification_requirement": {"regulatory_status": "MANDATORY"},
        "expected_decision": {"query_level_state": "PRIMARY_RECOMMENDATION_AVAILABLE", "expected_abstention_reason": None},
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": True,
        "gold_primary_candidate_eligible": True,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_review_reason": "Gold standard lacks verified scope evidence in knowledge base.",
        "expected_safe_decision": "EXPERT_REVIEW_REQUIRED"
    },
    {
        "query_id": "Q_OWX_010",
        "schema_version": "2.1",
        "dataset_split": "D_blind_test",
        "source": {
            "type": "constructed_expert_case",
            "organization": "Under-specified Query Evaluation Team",
            "tender_id": "ADV/VAGUE/POWER/10",
            "tender_publication_date": "2025-07-18",
            "evaluation_as_of_date": "2025-08-01",
            "portal_url": None
        },
        "query": {
            "raw_text": "Supply and delivery of electrical power equipment for departmental works.",
            "language": "en",
            "domain": "ELECTROTECHNICAL",
            "product_family": "Under-specified General Query"
        },
        "benchmark_dimensions": {
            "query_explicitness": "implicit",
            "difficulty": "hard",
            "language": "en",
            "temporal_context": "current",
            "ambiguity_class": "CLASS_3_INSUFFICIENT_INFORMATION"
        },
        "technical_requirements": {
            "product": None,
            "scope_keywords": ["electrical power equipment"],
            "target_product": None,
            "material_grade": None,
            "rating_capacity": None,
            "application": "Departmental electrical works",
            "missing_parameters": ["specific product name", "voltage rating", "power rating", "operating function"]
        },
        "gold_standards": [],
        "hard_negatives": [
            {
                "standard_designation": "IS 1180 (Part 1):2014",
                "hn_class": "HN1",
                "confusability_reason": "Common electrical equipment.",
                "rejection_reason": "Query lacks specific equipment type; cannot assume transformer over switchgear, cable, or motor.",
                "source_tier": 1
            },
            {
                "standard_designation": "IS 694:2010",
                "hn_class": "HN1",
                "confusability_reason": "Common electrical equipment.",
                "rejection_reason": "Query does not specify cable or wire.",
                "source_tier": 1
            }
        ],
        "version_requirement": {"policy": "latest_active_only", "acceptable_years": []},
        "certification_requirement": {"regulatory_status": "UNKNOWN"},
        "expected_decision": {
            "query_level_state": "INSUFFICIENT_INFORMATION",
            "expected_abstention_reason": "Query is severely under-specified; lacking product entity, voltage, power rating, and operating domain."
        },
        "expert_review": {"reviewers_count": 2, "agreement_status": "unanimous"},
        "expected_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "prototype_coverage_state": "IN_PROTOTYPE_COVERAGE",
        "gold_in_scope": False,
        "gold_in_graph": False,
        "gold_primary_candidate_eligible": False,
        "gold_evidence_state": "SCOPE_UNAVAILABLE",
        "gold_recommendation_ready": False,
        "expected_evidence_state": "SCOPE_UNAVAILABLE",
        "expected_safe_decision": "INSUFFICIENT_INFORMATION"
    }
]

print(f"Generated {len(conflict_queries)} conflict queries.")

# Combine all 5 subsets
all_open_world_queries = (
    paraphrase_queries +
    compositional_queries +
    multilingual_queries +
    long_clause_queries +
    conflict_queries
)

print(f"Total open world queries: {len(all_open_world_queries)}")

# Export files
files_to_write = [
    (BENCHMARKS_DIR / "open_world_paraphrase.jsonl", paraphrase_queries),
    (BENCHMARKS_DIR / "open_world_compositional.jsonl", compositional_queries),
    (BENCHMARKS_DIR / "open_world_multilingual.jsonl", multilingual_queries),
    (BENCHMARKS_DIR / "open_world_long_clause.jsonl", long_clause_queries),
    (BENCHMARKS_DIR / "open_world_conflict.jsonl", conflict_queries),
    (BENCHMARKS_DIR / "open_world.jsonl", all_open_world_queries),
]

for file_path, q_list in files_to_write:
    with open(file_path, "w", encoding="utf-8") as f:
        for q in q_list:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"Wrote {len(q_list)} records to {file_path}")


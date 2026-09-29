"""
Ingest Verified Standards Audit Data — StandSpec AI (Part 2 Domain Ingestion)
Applies verified domain facts, scope summaries, lifecycle supersessions,
and role corrections into data/processed/standards_graph.json.
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.role_classifier import RoleClassifier
from scripts.build_knowledge_graph import compute_node_evidence_and_readiness, _content_hash

GRAPH_PATH = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"


def run_ingestion():
    print(f"Loading knowledge graph from {GRAPH_PATH}...")
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    nodes = [n for n in graph.get("nodes", []) if n.get("id") != "IS 1180 (Part 2):1989"]
    node_map = {n.get("id"): n for n in nodes}
    print(f"Loaded {len(nodes)} nodes.")

    # 1. Option 1: Lifecycle & Supersession Resolutions
    # 1.1 IS 1139:1966 -> Superseded by IS 1786:2008
    if "IS 1139:1966" in node_map:
        n = node_map["IS 1139:1966"]
        n["status"] = "SUPERSEDED"
        n["lifecycle_status"] = "SUPERSEDED"
        n["superseded_by"] = "IS 1786:2008"
        n["recommend_as_current"] = False
        n["candidate_status"] = "EXCLUDED"
        n["candidate_reason"] = "SUPERSEDED_BY_IS_1786"
        n["is_recommendation_eligible"] = False
        n["standard_role"] = "SUPPORTING_OTHER"
        n["role_reason"] = "Superseded historical specification; superseded by IS 1786:2008"
        n["evidence_source"] = "Official BIS IS 1786:2008 standard-details page"
        print("[UPDATED] IS 1139:1966 marked as SUPERSEDED by IS 1786:2008.")

    # 1.2 IS 12615:2026 -> Published Current Edition
    if "IS 12615:2026" in node_map:
        n = node_map["IS 12615:2026"]
        n["status"] = "PUBLISHED_CURRENT"
        n["lifecycle_status"] = "PUBLISHED_CURRENT"
        n["title"] = "Line Operated Three Phase AC Motors — IE Code — Efficiency Classes and Performance Specification"
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["certification_status"] = "MANDATORY"
        n["recommend_as_current"] = True
        n["supersedes"] = "IS 12615:2018"
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["regulatory_review_required"] = True
        n["scope"] = "1.1 This standard specifies performance requirements and energy efficiency classes (IE code) for line-operated three-phase a.c. motors."
        n["scope_text"] = n["scope"]
        n["is_hydrated"] = True
        print("[UPDATED] IS 12615:2026 marked as PUBLISHED_CURRENT (Mandatory).")

    # 1.3 IS 1180 (Part 1):2014 -> Replacement scope and Part 2 merger
    # (Part 2:1989 was withdrawn and merged into Part 1:2014 per official BIS Know Your Standards)
    if "IS 1180 (Part 1):2014" in node_map:
        n = node_map["IS 1180 (Part 1):2014"]
        n["scope"] = (
            "1.1 This standard (Part 1) covers the requirements of outdoor type oil-immersed "
            "distribution transformers up to and including 2500 kVA and 33 kV, including both sealed "
            "and non-sealed types (incorporating scopes of erstwhile Part 1:1989 and Part 2:1989)."
        )
        n["scope_text"] = n["scope"]
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["is_hydrated"] = True
        n["supersedes"] = ["IS 1180 (Part 1):1989", "IS 1180 (Part 2):1989"]
        n["merged_standards"] = ["IS 1180 (Part 2):1989"]
        n["technical_attributes"] = {
            "type": "oil_immersed",
            "enclosure": ["sealed", "non_sealed"],
            "max_capacity_kva": 2500,
            "max_voltage_kv": 33.0
        }
        print("[UPDATED] IS 1180 (Part 1):2014 scope, technical parameters, and Part 2 merger hydrated.")

    # 2. Option 2: Verified Clause Scopes and Attribute Guardrails
    # 2.1 IS 432 (Part 1):1982
    if "IS 432 (Part 1):1982" in node_map:
        n = node_map["IS 432 (Part 1):1982"]
        n["scope"] = "1.1 This standard covers the requirements for mild-steel and medium-tensile-steel bars for use as reinforcement in concrete in nominal sizes from 5 mm to 50 mm."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_summary"
        n["verbatim_clause_status"] = "not_verified"
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "material": "mild_steel",
            "grades": ["Grade I", "Grade II"],
            "nominal_sizes_mm": [5, 6, 8, 10, 12, 16, 20, 22, 25, 28, 32, 36, 40, 45, 50],
            "diameter_evidence_status": "verified_official_product_manual",
            "verbatim_clause_status": "not_verified"
        }
        print("[UPDATED] IS 432 (Part 1):1982 scope and verified product-manual sizes hydrated.")

    # 2.2 IS 456:2000
    if "IS 456:2000" in node_map:
        n = node_map["IS 456:2000"]
        n["standard_role"] = "DESIGN_CODE"
        n["scope"] = (
            "1.1 This standard deals with the general structural use of plain and reinforced concrete. "
            "Special structures require their respective specialised standards and may also use IS 456 "
            "where referenced or applicable (bridges, chimneys, liquid-retaining structures, etc.)."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_summary"
        n["special_structure_rule"] = "Use relevant specialised standards for special structures (bridges, chimneys, liquid-retaining structures)"
        n["future_revision_warning"] = True
        n["amendments_count"] = 6
        n["is_hydrated"] = True
        print("[UPDATED] IS 456:2000 verified as DESIGN_CODE with specialised structure rules.")

    # 2.3 IS 16415:2015
    if "IS 16415:2015" in node_map:
        n = node_map["IS 16415:2015"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers the manufacture and chemical and physical requirements of composite cement using fly ash and granulated slag."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_summary"
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["reviewed_in"] = 2025
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "fly_ash_percentage_by_mass": {"min": 10, "max": 25, "reference": "IS 3812 (Part 1)"},
            "granulated_slag_percentage_by_mass": {"min": 25, "max": 40, "reference": "IS 12089"},
            "blend_status": "verified_official_compendium",
            "verbatim_clause_status": "not_verified"
        }
        print("[UPDATED] IS 16415:2015 composite cement scope and blend ratios hydrated.")

    # 2.4 IS 12818:2010
    if "IS 12818:2010" in node_map:
        n = node_map["IS 12818:2010"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers PVC-U screen and casing pipes intended for boreholes/tubewells."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_title_verified"
        n["reviewed_in"] = 2026
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "diameter_range": None,
            "screen_slot_range": None,
            "technical_limits_status": "not_verified",
            "manual_review_required": True
        }
        print("[UPDATED] IS 12818:2010 casing pipes scope hydrated with null unverified boundaries.")

    # 2.5 IS 16651:2017
    if "IS 16651:2017" in node_map:
        n = node_map["IS 16651:2017"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers the requirements of high-strength deformed stainless-steel bars and wires for concrete reinforcement."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_title_verified"
        n["reviewed_in"] = 2022
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "steel_grades": None,
            "grade_status": "not_verified",
            "technical_attribute_review_required": True
        }
        print("[UPDATED] IS 16651:2017 stainless rebars scope hydrated with null unverified grades.")

    # ── Batch 2: Priority 1 — Cables and Electrical Conductors ──
    # 2.6 IS 1554 (Part 2):1988
    if "IS 1554 (Part 2):1988" in node_map:
        n = node_map["IS 1554 (Part 2):1988"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard (Part 2) covers the requirements for PVC-insulated, heavy-duty, armoured "
            "electric cables for working voltages from 3.3 kV up to and including 11 kV with aluminium "
            "or copper conductors for fixed installations."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_official_compendium"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "voltage_minimum_kv": {"value": 3.3, "source": "BIS compendium", "evidence_status": "verified_official"},
            "voltage_maximum_kv": {"value": 11.0, "source": "BIS compendium", "evidence_status": "verified_official"},
            "voltage_wording": "from 3.3 kV up to and including 11 kV",
            "voltage_basis": "phase-to-phase",
            "armoured": {"value": True, "source": "BIS compendium", "evidence_status": "verified_official"},
            "unarmoured": {"value": None, "evidence_status": "not_verified", "manual_review_required": True},
            "conductor_material": ["aluminium", "copper"],
            "installation": "fixed installations"
        }
        print("[UPDATED] IS 1554 (Part 2):1988 heavy duty cable scope and voltage limits hydrated.")

    # 2.7 IS 398 (Part 4):1994
    if "IS 398 (Part 4):1994" in node_map:
        n = node_map["IS 398 (Part 4):1994"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard (Part 4) covers aluminium-alloy stranded conductors of the "
            "aluminium-magnesium-silicon type (AAAC) for overhead power transmission purposes."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_official_product_manual"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "aluminium alloy stranded conductor",
            "abbreviation": "AAAC",
            "alloy_type": "aluminium-magnesium-silicon",
            "application": "overhead power transmission",
            "maximum_actual_stranded_area_mm2": {"value": 767, "source": "BIS product manual", "evidence_status": "verified_official"},
            "conductor_construction": "stranded"
        }
        print("[UPDATED] IS 398 (Part 4):1994 AAAC overhead conductor scope hydrated.")

    # 2.8 IS 398 (Part 5):1992
    if "IS 398 (Part 5):1992" in node_map:
        n = node_map["IS 398 (Part 5):1992"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard (Part 5) covers aluminium conductors, galvanized-steel-reinforced (ACSR), "
            "for extra-high-voltage overhead power lines of 400 kV and above."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_official_product_manual"
        n["is_hydrated"] = True
        n["lifecycle_warning"] = "Amalgamated into IS 398 Part 2:2025 per BIS circular; check active enforceability."
        n["technical_attributes"] = {
            "product": "aluminium conductor galvanized-steel-reinforced",
            "abbreviation": "ACSR",
            "application": "extra-high-voltage overhead power lines",
            "minimum_voltage_kv": {"value": 400.0, "source": "BIS product manual", "evidence_status": "verified_official"},
            "core_material": "galvanized steel wire",
            "nominal_aluminium_areas_mm2": [520, 560, 690]
        }
        print("[UPDATED] IS 398 (Part 5):1992 EHV ACSR conductor scope hydrated with amalgamation warning.")

    # 2.9 IS 731:1971
    if "IS 731:1971" in node_map:
        n = node_map["IS 731:1971"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers porcelain insulators for overhead power lines with a nominal voltage greater than 1 000 V."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_title_and_lifecycle_verified"
        n["reviewed_in"] = 2021
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "porcelain insulators",
            "application": "overhead power lines",
            "nominal_voltage_condition": "> 1000 V",
            "pin_disc_classification": {"value": None, "evidence_status": "not_verified", "manual_review_required": True},
            "failing_load_limits": {"value": None, "evidence_status": "not_verified", "manual_review_required": True}
        }
        print("[UPDATED] IS 731:1971 porcelain insulators scope hydrated with guarded null limits.")

    # ── Batch 2: Priority 2 — Water Supply and Drainage Piping ──
    # 2.10 IS 13592:2013
    if "IS 13592:2013" in node_map:
        n = node_map["IS 13592:2013"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard covers unplasticized polyvinyl chloride (PVC-U) pipes intended for soil and waste "
            "discharge systems (Type B) and for rainwater and ventilation systems (Type A) inside and outside buildings."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_official_product_manual"
        n["reviewed_in"] = 2023
        n["potable_water"] = False
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "type_A": {"application": ["rainwater", "ventilation"], "nominal_outside_diameter_mm": "40–160"},
            "type_B": {"application": ["soil discharge", "waste discharge"], "nominal_outside_diameter_mm": "40–315"},
            "joint_options": ["plain ended", "solvent cement socket", "grooved socket"],
            "potable_water": {"value": False, "source": "BIS product manual", "evidence_status": "verified_negative_rule"}
        }
        print("[UPDATED] IS 13592:2013 PVC-U soil/waste pipes scope hydrated with Type A/B boundaries.")

    # 2.11 IS 651:2007
    if "IS 651:2007" in node_map:
        n = node_map["IS 651:2007"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard covers glazed stoneware pipes and fittings for sewage conveyance, drainage, "
            "and industrial waste conveyance. Not intended for potable water applications."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_official_product_manual"
        n["reviewed_in"] = 2022
        n["potable_water"] = False
        n["certification_status"] = "VOLUNTARY"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "glazed stoneware pipes and fittings",
            "potable_water": {"value": False, "source": "BIS product manual", "evidence_status": "verified_negative_rule"},
            "pipe_classes": ["SP1", "SP2", "SP3"],
            "internal_diameter_mm": [100, 150, 200, 230, 250, 300, 350, 400, 450, 500, 600, 700, 800],
            "standard_lengths_mm": [600, 750, 900, 1000]
        }
        print("[UPDATED] IS 651:2007 glazed stoneware pipes scope hydrated with negative potable rule.")

    # 2.12 IS 1592:2003
    if "IS 1592:2003" in node_map:
        n = node_map["IS 1592:2003"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers asbestos-cement pressure pipes and joints for pressure pipelines."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_product_manual_verified"
        n["reviewed_in"] = 2023
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["certification_status"] = "MANDATORY"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "pressure_classes_verified": [10, 15, 20, 25],
            "other_classes": [12, 18, 24, 30],
            "potable_water_status": {"value": None, "evidence_status": "requires_verification", "manual_review_required": True}
        }
        print("[UPDATED] IS 1592:2003 asbestos-cement pipes scope hydrated with verified pressure classes.")

    # ── Batch 2: Priority 3 — Masonry and Building Assemblies ──
    # 2.13 IS 2185 (Part 1):2005
    if "IS 2185 (Part 1):2005" in node_map:
        n = node_map["IS 2185 (Part 1):2005"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard (Part 1) covers hollow and solid concrete masonry blocks manufactured with dense or lightweight aggregates."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_official_product_manual"
        n["reviewed_in"] = 2025
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "hollow_block_grades": {"A_MPa": [3.5, 4.5, 5.5, 7.0, 8.5, 10.0, 12.5, 15.0], "B_MPa": [3.5, 5.0]},
            "solid_block_grades": {"C_MPa": [4.0, 5.0]},
            "strength_basis": "minimum average compressive strength at 28 days"
        }
        print("[UPDATED] IS 2185 (Part 1):2005 concrete blocks scope hydrated with Grade A/B/C strengths.")

    # 2.14 IS 14862:2000
    if "IS 14862:2000" in node_map:
        n = node_map["IS 14862:2000"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers the requirements for fibre-cement flat sheets for building and civil engineering use."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "verified_official_product_manual"
        n["reviewed_in"] = 2025
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["certification_status"] = "MANDATORY"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "length_max_mm": 3000,
            "width_max_mm": 1220,
            "thickness_range_mm": {"min": 3, "max": 30, "source": "BIS product manual"},
            "internal_external_exposure": {"value": None, "evidence_status": "not_verified", "manual_review_required": True}
        }
        print("[UPDATED] IS 14862:2000 fibre-cement flat sheets scope hydrated with 3-30 mm range.")

    # 2.15 IS 12894:2002
    if "IS 12894:2002" in node_map:
        n = node_map["IS 12894:2002"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers pulverized fuel ash-lime bricks for masonry construction."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_title_and_product_manual_available"
        n["reviewed_in"] = 2022
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "fly_ash_reference": "IS 3812",
            "fly_ash_percentage": {"value": None, "evidence_status": "not_verified", "manual_review_required": True},
            "compressive_strength_classes": {"value": None, "evidence_status": "not_verified", "manual_review_required": True}
        }
        print("[UPDATED] IS 12894:2002 fly ash-lime bricks scope hydrated with guarded null tables.")

    # 2.16 IS 16720:2018
    if "IS 16720:2018" in node_map:
        n = node_map["IS 16720:2018"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers pulverized fuel ash-cement bricks manufactured using fly ash and cement for masonry construction."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_product_manual_and_BIS_publication_verified"
        n["reviewed_in"] = 2023
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "fly_ash_minimum_percent_by_mass": {"value": 35, "source": "BIS publication", "evidence_status": "verified_official"},
            "size_max_mm": {"length": 300, "width": 150, "height": 100},
            "types": ["modular", "non-modular"],
            "wet_compressive_strength_classes_MPa": [5, 7.5, 10, 12.5, 15],
            "strength_basis": "average 28-day wet compressive strength",
            "fly_ash_reference": ["IS 3812 (Part 1)", "IS 3812 (Part 2)"],
            "related_testing_standards": ["IS 3495 (Part 1)", "IS 4139"]
        }
        print("[UPDATED] IS 16720:2018 fly ash-cement bricks scope hydrated with 35% min and classes.")

    # 2.17 IS 16526:2017
    if "IS 16526:2017" in node_map:
        n = node_map["IS 16526:2017"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = "1.1 This standard covers atactic polypropylene (APP) modified bituminous waterproofing and damp-proofing membrane with glass-fibre reinforcement."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_title_and_sector_publication_verified"
        n["reviewed_in"] = 2022
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "modifier": "atactic polypropylene (APP)",
            "material": "bituminous membrane",
            "reinforcement": {"value": "glass fibre", "source": "BIS standard title", "evidence_status": "verified_official"},
            "related_alternative": "IS 16532:2017 uses polyester reinforcement",
            "thickness_range": {"value": None, "evidence_status": "not_verified", "manual_review_required": True},
            "cold_flexibility": {"value": None, "evidence_status": "not_verified", "manual_review_required": True}
        }
        print("[UPDATED] IS 16526:2017 APP membrane scope hydrated with glass-fibre verification.")

    # ── Batch 3: Priority 1 — Structural Steel and Fasteners ──
    # 2.18 IS 2062:2011
    if "IS 2062:2011" in node_map:
        n = node_map["IS 2062:2011"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard covers the requirements of hot-rolled medium and high tensile structural "
            "steel, including plates, strips, sections, flats and bars used in structural work."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_product_manual_and_LIMS_verified"
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["certification_status"] = "MANDATORY"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "hot-rolled medium- and high-tensile structural steel",
            "grades": ["E250", "E275", "E300", "E350", "E410", "E450", "E550", "E600", "E650"],
            "qualities": {
                "E250": ["A", "BR", "B0", "C"],
                "E275": ["A", "BR", "B0", "C"],
                "E300": ["A", "BR", "B0", "C"],
                "E350": ["A", "BR"],
                "E410": ["A", "BR"],
                "E450": ["A", "BR"],
                "E550": ["A", "BR"],
                "E600": ["A", "BR"],
                "E650": ["A", "BR"]
            },
            "application": "structural work",
            "lifecycle_warning": "newer grade additions (E235, E500) reported by BIS; current edition/manual must be checked"
        }
        print("[UPDATED] IS 2062:2011 structural steel scope, grades E250-E650 and qualities hydrated.")

    # ── Batch 3: Priority 2 — Sanitary Appliances ──
    # 2.19 IS 2556 (Part 2):2024
    if "IS 2556 (Part 2):2024" in node_map:
        n = node_map["IS 2556 (Part 2):2024"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard (Part 2) covers specific requirements of vitreous china washdown water closets, "
            "including Pattern 1, Pattern 2, Pattern 3, Pattern 4 and other declared patterns (superseding 2004 edition)."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_product_manual_verified"
        n["is_hydrated"] = True
        n["supersedes"] = ["IS 2556 (Part 2):2004"]
        n["technical_attributes"] = {
            "product": "vitreous china washdown water closets",
            "material": "vitreous china",
            "patterns": ["Pattern 1", "Pattern 2", "Pattern 3", "Pattern 4", "other declared pattern"]
        }
        print("[UPDATED] IS 2556 (Part 2):2024 vitreous china water closets scope hydrated.")

    # 2.20 IS 2556 (Part 3):2024
    if "IS 2556 (Part 3):2024" in node_map:
        n = node_map["IS 2556 (Part 3):2024"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard (Part 3) covers specific requirements of vitreous china squatting pans, "
            "including Long, Orissa, Rural and other patterns (superseding 2004 edition)."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_product_manual_verified"
        n["is_hydrated"] = True
        n["supersedes"] = ["IS 2556 (Part 3):2004"]
        n["technical_attributes"] = {
            "product": "vitreous china squatting pans",
            "material": "vitreous china",
            "patterns": {
                "Long": ["580 mm", "630 mm"],
                "Orissa": ["580 × 440 mm", "630 × 450 mm"],
                "Rural": ["480 mm"]
            }
        }
        print("[UPDATED] IS 2556 (Part 3):2024 vitreous china squatting pans scope hydrated.")

    # ── Batch 3: Priority 3 — Electrical Switchgear and Earthing ──
    # 2.21 IS/IEC 60898-1:2015
    if "IS/IEC 60898-1:2015" in node_map:
        n = node_map["IS/IEC 60898-1:2015"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard applies to a.c. circuit-breakers for overcurrent protection for household and "
            "similar installations for operation at 50 Hz, having a rated voltage not exceeding 440 V (between phases), "
            "a rated current not exceeding 125 A and a rated short-circuit capacity not exceeding 25 000 A."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_publication_and_product_manual_verified"
        n["reviewed_in"] = 2024
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "MCB / AC circuit-breaker for overcurrent protection",
            "application": ["household installations", "similar installations"],
            "frequency_hz": 50,
            "rated_voltage_max_v": 440,
            "rated_current_max_a": 125,
            "rated_short_circuit_capacity_max_a": 25000,
            "user_type": "uninstructed persons",
            "pollution_degree": 2,
            "suitable_for_isolation": True
        }
        print("[UPDATED] IS/IEC 60898-1:2015 MCB scope and limits (440V, 125A, 25kA, 50Hz) hydrated.")

    # 2.22 IS 3043:2018
    if "IS 3043:2018" in node_map:
        n = node_map["IS 3043:2018"]
        n["standard_role"] = "DESIGN_CODE"
        n["scope"] = "1.1 This code of practice covers the design and installation of earthing systems for electrical installations."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_standard_details_verified"
        n["role_reason"] = "Code of practice for earthing systems design and installation; not a product standard for standalone electrodes/plates"
        n["product_standard"] = False
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product_standard": False,
            "subject": "earthing practice",
            "certification_status": "N/A",
            "department": "ETD",
            "committee": "ETD 20",
            "revision": "second revision"
        }
        print("[UPDATED] IS 3043:2018 earthing code verified as DESIGN_CODE.")

    # ── Batch 4: Additional Critical Standards & Multi-Standard Infrastructure ──
    # 2.23 IS/IEC 60947-2:2016 & IS/IEC 60947 (Part 2):2016
    for mcb_id in ["IS/IEC 60947-2:2016", "IS/IEC 60947 (Part 2):2016"]:
        if mcb_id in node_map:
            n = node_map[mcb_id]
            n["standard_role"] = "PRIMARY_PRODUCT"
            n["scope"] = (
                "1.1 This standard applies to circuit-breakers, the main contacts of which are intended to be "
                "connected to circuits, the rated voltage of which does not exceed 1 000 V a.c. or 1 500 V d.c.; "
                "it covers industrial circuit-breakers including MCCBs and ACBs."
            )
            n["scope_text"] = n["scope"]
            n["scope_status"] = "official_BIS_product_manual_verified"
            n["is_hydrated"] = True
            n["technical_attributes"] = {
                "product_family": ["MCCB", "ACB", "industrial circuit-breaker"],
                "application": "industrial and commercial low-voltage switchgear",
                "voltage_max_ac_v": 1000,
                "voltage_max_dc_v": 1500,
                "certification_scheme": "Scheme X",
                "complementary_to": "IS/IEC 60898-1:2015"
            }
            print(f"[UPDATED] {mcb_id} industrial circuit-breaker scope hydrated under Scheme X.")

    # 2.24 IS 4985:2021
    if "IS 4985:2021" in node_map:
        n = node_map["IS 4985:2021"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["scope"] = (
            "1.1 This standard covers requirements for plain as well as socket-ended unplasticized polyvinyl "
            "chloride (PVC-U) pipes for potable water supplies."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_product_manual_and_LIMS_verified"
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["certification_status"] = "MANDATORY"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "unplasticized PVC pipes for water supplies",
            "application": "potable-water supply",
            "revision": "fourth revision",
            "certification_scheme": "Scheme I",
            "complementary_to": ["IS 13592:2013", "IS 651:2007", "IS 12818:2010"]
        }
        print("[UPDATED] IS 4985:2021 potable water uPVC pipe scope and Scheme I certification hydrated.")

    # 2.25 IS 383:2016
    if "IS 383:2016" in node_map:
        n = node_map["IS 383:2016"]
        n["standard_role"] = "COMPONENT"
        n["scope"] = (
            "1.1 This standard covers the requirements for coarse and fine aggregates from natural and other "
            "than natural sources for use in concrete."
        )
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_product_manual_verified"
        n["role_reason"] = "Material specification for coarse and fine aggregates; supporting material for concrete"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "coarse and fine aggregates for concrete",
            "material_specification": True,
            "fine_aggregate_grading_zones": ["Zone I", "Zone II", "Zone III", "Zone IV"],
            "coarse_aggregate_single_sizes_mm": [10, 12.5, 16, 20, 40, 63],
            "coarse_aggregate_graded_sizes_mm": [12.5, 16, 20, 40],
            "fine_aggregate_sources": ["natural sand", "crushed stone sand", "crushed gravel sand", "manufactured aggregate"]
        }
        print("[UPDATED] IS 383:2016 concrete aggregates scope, grading zones I-IV and sizes hydrated.")

    # 2.26 IS 12615:2018 & IS 12615:2026
    if "IS 12615:2018" in node_map:
        n = node_map["IS 12615:2018"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["status"] = "SUPERSEDED"
        n["lifecycle_status"] = "SUPERSEDED"
        n["superseded_by"] = "IS 12615:2026"
        n["scope"] = "1.1 This standard covers line-operated three-phase AC induction motors with efficiency classes IE2, IE3, and IE4."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_product_manual_verified"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "line-operated three-phase AC motors",
            "efficiency_classes": ["IE2", "IE3", "IE4"],
            "certification_status": "MANDATORY"
        }
        print("[UPDATED] IS 12615:2018 motors marked as SUPERSEDED by IS 12615:2026.")

    if "IS 12615:2026" in node_map:
        n = node_map["IS 12615:2026"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["status"] = "PUBLISHED_CURRENT"
        n["lifecycle_status"] = "PUBLISHED_CURRENT"
        n["supersedes"] = "IS 12615:2018"
        n["scope"] = "1.1 This standard covers line-operated three-phase AC induction motors, establishing requirements for energy-efficient motors."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_standard_details_verified"
        n["qco_mandatory"] = True
        n["mandatory_certification"] = True
        n["certification_status"] = "MANDATORY"
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "line-operated three-phase AC motors",
            "efficiency_classes": ["IE2", "IE3", "IE4"],
            "certification_status": "MANDATORY"
        }
        print("[UPDATED] IS 12615:2026 motors scope hydrated as PUBLISHED_CURRENT.")

    # 2.27 IS 4926:2003
    if "IS 4926:2003" in node_map:
        n = node_map["IS 4926:2003"]
        n["standard_role"] = "PRIMARY_PRODUCT"
        n["status"] = "ACTIVE_VALID"
        n["lifecycle_status"] = "ACTIVE_VALID"
        n["scope"] = "1.1 This standard applies to the manufacture and supply of ready-mixed concrete."
        n["scope_text"] = n["scope"]
        n["scope_status"] = "official_BIS_code_of_practice_verified"
        n["reviewed_in"] = 2022
        n["is_hydrated"] = True
        n["technical_attributes"] = {
            "product": "ready-mixed concrete",
            "service_code": "production and supply of ready-mixed concrete",
            "supporting_material_standards": ["IS 269", "IS 383", "IS 456", "IS 10262"]
        }
        print("[UPDATED] IS 4926:2003 ready-mixed concrete scope hydrated.")

    # 3. Role Reclassifications & Regulatory Flags for Allied Standards
    allied_roles = {
        "IS 650:1991": ("TEST_METHOD", "Standard sand for testing cement; reference/testing standard, not primary product"),
        "IS 5831:1984": ("COMPONENT", "PVC insulation and sheath of electric cables; raw material/component"),
        "IS 1778:1980": ("COMPONENT", "Reels and drums for bare conductors; packaging component"),
        "IS 1709:1984": ("COMPONENT", "Capacitors for electric fan motors; motor sub-component"),
        "IS 2026 (Part 2):2010": ("TEST_METHOD", "Power transformers temperature rise test code"),
        "IS 2026 (Part 3):2018": ("TEST_METHOD", "Power transformers insulation levels and dielectric test code"),
        "IS 8783 (Part 1):1995": ("COMPONENT", "Winding wires for submersible motors; motor conductor component"),
        "IS 1363": ("COMPONENT", "Hexagon head bolts, screws and nuts of product grade C; fastener component"),
        "IS 1367": ("COMPONENT", "Technical supply conditions, tolerances and mechanical properties for fasteners"),
        "IS 1363:1984": ("COMPONENT", "Hexagon head bolts, screws and nuts of product grade C"),
        "IS 1367:1967": ("COMPONENT", "Fastener supply conditions and mechanical properties")
    }
    for desig, (role, reason) in allied_roles.items():
        if desig in node_map:
            n = node_map[desig]
            n["standard_role"] = role
            n["role_reason"] = reason
            n["role_confidence"] = 0.98
            n["role_source"] = "user_audit_verified"
            print(f"[RECLASSIFIED] {desig} -> {role}")

    # Normalize any non-conforming references_status
    for n in nodes:
        if n.get("references_status") == "curated":
            n["references_status"] = "parsed"

    # Mark mandatory certification where confirmed
    mandatory_standards = ["IS 1566:1982", "IS 1592:2003", "IS 14862:2000"]
    for desig in mandatory_standards:
        if desig in node_map:
            n = node_map[desig]
            n["qco_mandatory"] = True
            n["mandatory_certification"] = True
            n["certification_status"] = "MANDATORY"
            n["regulatory_evidence_available"] = True
            print(f"[REGULATORY] {desig} marked as MANDATORY certification.")

    # 4. Recompute Evidence & Readiness Invariants
    for n in nodes:
        if n.get("scope") or n.get("scope_text"):
            if not n.get("status"):
                n["status"] = "ACTIVE_VALID"
            if not n.get("lifecycle_status"):
                n["lifecycle_status"] = n.get("status")

        meta_avail = bool(n.get("metadata_available", True))
        ident_ver = bool(n.get("identity_verified", True))
        doc_avail = bool(n.get("document_available", True))
        has_scope = bool(n.get("scope") or n.get("scope_text"))
        has_refs = bool(n.get("references") or n.get("references_status") == "parsed")
        has_life = bool(n.get("year") or n.get("lifecycle_status") or n.get("status"))
        has_reg = bool(n.get("qco_mandatory") or n.get("mandatory_certification"))

        readiness = compute_node_evidence_and_readiness(
            node=n,
            metadata_available=meta_avail,
            identity_verified=ident_ver,
            document_available=doc_avail,
            has_scope=has_scope,
            has_refs=has_refs,
            has_lifecycle=has_life,
            has_regulatory=has_reg
        )
        n.update(readiness)

    # 5. Recompute Content Hash and Save Graph
    print("Recalculating graph content hash...")
    graph["nodes"] = nodes
    graph["nodes_count"] = len(nodes)
    graph["hydrated_nodes_count"] = sum(1 for n in nodes if n.get("is_hydrated"))
    graph["unhydrated_nodes_count"] = len(nodes) - graph["hydrated_nodes_count"]
    graph["updated_at"] = datetime.now(timezone.utc).isoformat()
    new_hash = _content_hash(graph)
    graph["content_hash"] = new_hash

    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Ingested audit data into {GRAPH_PATH} (Hash: {new_hash[:16]}...)")


if __name__ == "__main__":
    run_ingestion()

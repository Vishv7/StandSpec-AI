"""
Standard Role Classifier — StandSpec AI (Layer 5 Recommendation / Phase D Trust Core)
Classifies Indian Standards and allied standards into canonical architectural roles:
  - PRIMARY_PRODUCT: Finished product, equipment, apparatus, or assembly specification.
  - COMPONENT: Feedstock, profile, intermediate part, fitting, or accessory.
  - DIMENSIONAL_MOUNTING: Mechanical envelope, rail mounting, dimensional standardization.
  - TEST_METHOD: Procedure for testing, sampling, chemical/physical analysis.
  - INSTALLATION_CODE: Code of practice for laying, installation, erection, or maintenance.
  - DESIGN_CODE: Engineering design code, structural load calculation, building code.
  - SAFETY_STANDARD: General or functional safety standard.
  - TERMINOLOGY: Vocabulary, glossary, symbols, rounding rules.
  - SUPPORTING_OTHER: General handbook or auxiliary guideline.
  - UNKNOWN_ROLE: Role unverified / lacking explicit architectural evidence (SAFE DEFAULT).
"""

import re
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


class StandardRole(str, Enum):
    PRIMARY_PRODUCT = "PRIMARY_PRODUCT"
    COMPONENT = "COMPONENT"
    DIMENSIONAL_MOUNTING = "DIMENSIONAL_MOUNTING"
    TEST_METHOD = "TEST_METHOD"
    INSTALLATION_CODE = "INSTALLATION_CODE"
    DESIGN_CODE = "DESIGN_CODE"
    SAFETY_STANDARD = "SAFETY_STANDARD"
    TERMINOLOGY = "TERMINOLOGY"
    SUPPORTING_OTHER = "SUPPORTING_OTHER"
    UNKNOWN_ROLE = "UNKNOWN_ROLE"


class RoleClassifier:
    """
    Evidence-grounded role classifier for Indian Standards based on title,
    base number, scope, and committee taxonomy.
    Fails closed to UNKNOWN_ROLE rather than assuming PRIMARY_PRODUCT.
    """

    KNOWN_TEST_METHOD_BASES = {
        10810,  # Methods of test for cables
        2065,   # Method for determination of ...
        3400,   # Methods of test for vulcanized rubber
        4905,   # Random sampling inspection
        2720,   # Methods of test for soils
        516,    # Method of test for strength of concrete
        17910,  # Thermal performance of windows and doors - test method
        1528,   # Methods of sampling and physical tests for refractory materials
        650,    # Standard sand for testing cement (test material / testing standard)
    }

    KNOWN_TERMINOLOGY_BASES = {
        1885,   # Electrotechnical vocabulary
        2,      # Rules for rounding off
        282,    # Glossary of terms relating to ...
    }

    KNOWN_MOUNTING_BASES = {
        60715,  # Standardized mounting on rails (IS/IEC 60715)
        6392,   # Steel pipe flanges
        1231,   # Dimensions and output series of foot mounted induction motors
        2223,   # Dimensions of flange mounted induction motors
    }

    KNOWN_COMPONENT_BASES = {
        8130,   # Conductors for insulated electric cables
        17953,  # Profiles for manufacture of windows and doors
        5831,   # PVC insulation and sheath of electric cables
        1778,   # Reels and drums for bare conductors
        1709,   # Capacitors for electric fan motors
        8783,   # Winding wires for submersible motors
        1363,   # Hexagon head bolts, screws and nuts
        1367,   # Technical supply conditions and mechanical properties for fasteners
        383,    # Coarse and fine aggregates for concrete (material feedstock / component)
    }

    KNOWN_DESIGN_CODE_BASES = {
        456,    # Plain and reinforced concrete - code of practice
        800,    # General construction in steel - code of practice
        875,    # Code of practice for design loads (other than earthquake)
        1893,   # Criteria for earthquake resistant design of structures
        13920,  # Ductile design and detailing of reinforced concrete structures
        16231,  # Use of glass in buildings - Code of practice
        8009,   # Code of practice for calculation of settlement of foundations
        1904,   # Code of practice for design and construction of foundations in soils
        3043,   # Code of practice for earthing
    }

    @classmethod
    def classify_with_evidence(cls, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify candidate standard with explicit evidence, reason, confidence, and source.
        """
        doc = candidate.get("document", candidate) if isinstance(candidate.get("document"), dict) else candidate
        title = (doc.get("title") or candidate.get("title") or "").strip().lower()
        desig = (candidate.get("designation") or doc.get("designation") or doc.get("id") or "").strip().lower()
        scope = (doc.get("scope") or candidate.get("scope") or "").strip().lower()
        base_num = doc.get("base_number") or candidate.get("base_number")

        base_int = None
        if base_num is not None:
            try:
                base_int = int(base_num)
            except (ValueError, TypeError):
                pass
        if base_int is None and desig:
            m = re.search(r'\b(?:is\s*(?:/iec\s*)?)?(\d+)\b', desig)
            base_int = int(m.group(1)) if m else None

        evidence: List[str] = []

        # 1. Check known dedicated base numbers
        if base_int in cls.KNOWN_TEST_METHOD_BASES:
            return {
                "standard_role": StandardRole.TEST_METHOD.value,
                "role_confidence": 0.98,
                "role_reason": f"Base number {base_int} is a dedicated testing procedure series.",
                "role_evidence": [f"base_number={base_int} in KNOWN_TEST_METHOD_BASES"],
                "role_source": "base_taxonomy",
            }
        if base_int in cls.KNOWN_TERMINOLOGY_BASES:
            return {
                "standard_role": StandardRole.TERMINOLOGY.value,
                "role_confidence": 0.98,
                "role_reason": f"Base number {base_int} is a dedicated vocabulary/terminology standard.",
                "role_evidence": [f"base_number={base_int} in KNOWN_TERMINOLOGY_BASES"],
                "role_source": "base_taxonomy",
            }
        if base_int in cls.KNOWN_MOUNTING_BASES:
            return {
                "standard_role": StandardRole.DIMENSIONAL_MOUNTING.value,
                "role_confidence": 0.98,
                "role_reason": f"Base number {base_int} specifies mechanical mounting/dimensional envelope.",
                "role_evidence": [f"base_number={base_int} in KNOWN_MOUNTING_BASES"],
                "role_source": "base_taxonomy",
            }
        if base_int in cls.KNOWN_COMPONENT_BASES:
            return {
                "standard_role": StandardRole.COMPONENT.value,
                "role_confidence": 0.96,
                "role_reason": f"Base number {base_int} is an intermediate component/feedstock specification.",
                "role_evidence": [f"base_number={base_int} in KNOWN_COMPONENT_BASES"],
                "role_source": "base_taxonomy",
            }
        if base_int in cls.KNOWN_DESIGN_CODE_BASES:
            return {
                "standard_role": StandardRole.DESIGN_CODE.value,
                "role_confidence": 0.96,
                "role_reason": f"Base number {base_int} is an engineering design code / structural standard.",
                "role_evidence": [f"base_number={base_int} in KNOWN_DESIGN_CODE_BASES"],
                "role_source": "base_taxonomy",
            }

        # 1b. Specific Part-Level Test Codes (e.g. IS 2026 Part 2 / Part 3)
        if "2026 (part 2" in desig or "2026 (part 3" in desig:
            return {
                "standard_role": StandardRole.TEST_METHOD.value,
                "role_confidence": 0.98,
                "role_reason": "IS 2026 Part 2/Part 3 specifies transformer temperature-rise / dielectric test procedures.",
                "role_evidence": [f"designation={desig} is transformer test code"],
                "role_source": "part_taxonomy",
            }

        # 2. Test Methods
        test_indicators = [
            "method of test", "methods of test", "method for test", "methods for test",
            "testing of", "determination of", "test method", "measurement of",
            "sampling inspection", "sampling and test", "chemical analysis of",
            "physical test", "hot-box method", "laboratory test"
        ]
        matched_test = [t for t in test_indicators if t in title]
        if matched_test:
            return {
                "standard_role": StandardRole.TEST_METHOD.value,
                "role_confidence": 0.95,
                "role_reason": f"Title explicitly indicates testing/analytical procedure ('{matched_test[0]}').",
                "role_evidence": [f"title contains '{m}'" for m in matched_test],
                "role_source": "title_taxonomy",
            }

        # 3. Dimensional / Mounting Standards
        mounting_indicators = [
            "standardized mounting on rails", "mounting on rails",
            "mechanical support of switchgear", "mounting dimensions",
            "standardized dimensions for", "envelopes and dimensions",
            "dimensions and output series", "dimensions of flange mounted",
            "dimensions of foot mounted",
        ]
        matched_mounting = [m for m in mounting_indicators if m in title]
        if matched_mounting or ("dimensions of" in title and "switchgear" in title and "mounting" in title):
            ev = [f"title contains '{m}'" for m in matched_mounting] or ["title contains switchgear mounting dimensions"]
            return {
                "standard_role": StandardRole.DIMENSIONAL_MOUNTING.value,
                "role_confidence": 0.95,
                "role_reason": "Title indicates standardized mechanical mounting / dimensioning.",
                "role_evidence": ev,
                "role_source": "title_taxonomy",
            }

        # 4. Design Codes (Engineering Design / Structural / Load codes)
        design_indicators = [
            "code of practice for design", "code of practice for structural",
            "criteria for earthquake resistant", "earthquake resistant design",
            "ductile design and detailing", "limit state design",
            "design loads", "wind loads", "calculation of settlement",
            "use of glass in buildings - code of practice", "use of glass in buildings"
        ]
        matched_design = [d for d in design_indicators if d in title]
        if matched_design:
            return {
                "standard_role": StandardRole.DESIGN_CODE.value,
                "role_confidence": 0.94,
                "role_reason": f"Title indicates engineering design/structural calculation code ('{matched_design[0]}').",
                "role_evidence": [f"title contains '{m}'" for m in matched_design],
                "role_source": "title_taxonomy",
            }

        # 5. Installation Codes / Codes of Practice for Laying, Erection, Maintenance
        install_indicators = [
            "code of practice for laying", "code of practice for installation",
            "code of practice for maintenance", "code of practice for erection",
            "code of practice for fabrication", "code of practice for jointing",
            "code of practice for use of", "code of practice for construction"
        ]
        matched_install = [i for i in install_indicators if i in title]
        if matched_install:
            return {
                "standard_role": StandardRole.INSTALLATION_CODE.value,
                "role_confidence": 0.92,
                "role_reason": f"Title indicates code of practice for field installation/laying ('{matched_install[0]}').",
                "role_evidence": [f"title contains '{m}'" for m in matched_install],
                "role_source": "title_taxonomy",
            }

        # Generic code of practice fallback to DESIGN_CODE / SUPPORTING_OTHER if not supply
        if "code of practice" in title:
            return {
                "standard_role": StandardRole.DESIGN_CODE.value,
                "role_confidence": 0.88,
                "role_reason": "Title is a general code of practice.",
                "role_evidence": ["title contains 'code of practice'"],
                "role_source": "title_taxonomy",
            }

        # 6. Component / Profile Specifications
        component_indicators = [
            "profiles for", "profiles for the manufacture", "upvc profiles",
            "pipe fittings", "fittings for", "cable accessories",
            "joints and terminations", "rubber sealing rings for",
            "gaskets for", "insulating tape", "enamelled winding wires",
            "conductors for overhead", "conductors for insulated", "conductors for"
        ]
        matched_comp = [c for c in component_indicators if c in title]
        if matched_comp:
            # Check if title explicitly specifies finished framed assembly
            if any(a in title for a in [
                "framed doors", "profile framed doors", "doors, windows and sliders - specification",
                "doors and windows - specification"
            ]) and not ("profiles for the manufacture" in title or "profiles for windows" in title):
                return {
                    "standard_role": StandardRole.PRIMARY_PRODUCT.value,
                    "role_confidence": 0.92,
                    "role_reason": "Title explicitly indicates complete framed door/window assembly.",
                    "role_evidence": ["title contains framed assembly specification"],
                    "role_source": "title_taxonomy",
                }
            return {
                "standard_role": StandardRole.COMPONENT.value,
                "role_confidence": 0.92,
                "role_reason": f"Title indicates component/profile/fitting ('{matched_comp[0]}').",
                "role_evidence": [f"title contains '{m}'" for m in matched_comp],
                "role_source": "title_taxonomy",
            }

        # 7. Terminology & Vocabulary
        term_indicators = [
            "glossary of terms", "vocabulary", "rules for rounding",
            "graphical symbols", "letter symbols"
        ]
        matched_term = [t for t in term_indicators if t in title]
        if matched_term:
            return {
                "standard_role": StandardRole.TERMINOLOGY.value,
                "role_confidence": 0.95,
                "role_reason": "Title indicates vocabulary, symbols, or rounding rules.",
                "role_evidence": [f"title contains '{m}'" for m in matched_term],
                "role_source": "title_taxonomy",
            }

        # 8. Safety Standards
        safety_indicators = [
            "general safety requirements", "safety requirements for electrical",
            "safety of household", "insulation coordination"
        ]
        matched_safety = [s for s in safety_indicators if s in title]
        if matched_safety:
            return {
                "standard_role": StandardRole.SAFETY_STANDARD.value,
                "role_confidence": 0.90,
                "role_reason": "Title indicates safety / protective requirements standard.",
                "role_evidence": [f"title contains '{m}'" for m in matched_safety],
                "role_source": "title_taxonomy",
            }

        # 8b. Guidelines / Guides / Handbooks
        guide_indicators = [
            "guide on", "guide for", "guide to",
            "handbook on", "manual on", "recommended practice"
        ]
        matched_guide = [g for g in guide_indicators if g in title]
        if matched_guide:
            return {
                "standard_role": StandardRole.SUPPORTING_OTHER.value,
                "role_confidence": 0.95,
                "role_reason": f"Title indicates auxiliary guide/handbook/guideline ('{matched_guide[0]}').",
                "role_evidence": [f"title contains '{m}'" for m in matched_guide],
                "role_source": "title_taxonomy",
            }

        # 9. Primary Products: Positive Specification Indicator Required!
        # Must explicitly contain "specification", "requirements", or well-known finished apparatus
        is_explicit_spec = (
            "specification" in title or "specifications" in title
            or any(p in title for p in [
                "electric cables", "power cables", "sheathed cables", "insulated cables", "cables",
                "distribution transformers", "power transformers",
                "circuit-breakers", "circuit breakers", "circuitbreakers", "switchgear and controlgear", "induction motors", "energy meters",
                "electricity meters", "polyethylene pipes", "upvc pipes", "cast iron pipes",
                "portland cement", "led lamps", "pressure gauges"
            ])
            or "60947-2" in desig or "60947 (part 2" in desig
        )
        if is_explicit_spec:
            return {
                "standard_role": StandardRole.PRIMARY_PRODUCT.value,
                "role_confidence": 0.88,
                "role_reason": "Title explicitly indicates product specification / equipment standard.",
                "role_evidence": ["title indicates product specification"],
                "role_source": "title_taxonomy",
            }

        # 10. SAFE DEFAULT: UNKNOWN_ROLE (Trust Mandate: Never guess PRIMARY_PRODUCT!)
        return {
            "standard_role": StandardRole.UNKNOWN_ROLE.value,
            "role_confidence": 0.50,
            "role_reason": "Standard lacks conclusive product specification or architectural role indicators.",
            "role_evidence": ["no recognized role indicators matched"],
            "role_source": "fallback_default",
        }

    @classmethod
    def classify(cls, candidate: Dict[str, Any]) -> StandardRole:
        """Convenience method returning canonical StandardRole enum."""
        meta = cls.classify_with_evidence(candidate)
        return StandardRole(meta["standard_role"])

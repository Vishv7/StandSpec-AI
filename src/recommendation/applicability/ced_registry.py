"""
CED Domain Rule Registry — StandSpec AI (Phase P1-B)
Civil Engineering domain rules: Cement, Pipes, Concrete, Structural Steel,
Rebar, Safety Glass, Doors and Windows.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from src.recommendation.applicability.base_registry import DomainRuleRegistry
from src.recommendation.applicability.state import AttributeStatus


class CEDRuleRegistry(DomainRuleRegistry):
    """
    Rule registry for Civil Engineering Department (CED) standards.
    """

    @property
    def department_code(self) -> str:
        return "CED"

    def get_product_stem_mappings(self) -> Dict[str, List[str]]:
        return {
            "HDPE Pipes for Water Supply": ["polyethylene pipe", "hdpe pipe", "high density polyethylene pipe", "pe pipe", "pipe"],
            "uPVC Pipes for Potable Water Supplies": ["unplasticized polyvinyl chloride pipe", "upvc pipe", "pvc-u pipe", "pvc pipe", "pipe"],
            "Centrifugally Cast Iron Pressure Pipes": ["cast iron pressure pipe", "spun iron pipe", "centrifugally cast pipe", "pressure pipe", "cast iron pipe", "spun pipe", "pipe"],
            "Steel Tubes and Tubulars": ["steel tube", "tubular", "steel pipe", "mild steel tube", "erw tube", "tube"],
            "Pipes and Fittings": ["pipe", "tube", "tubular", "fitting"],
            "High Alumina Cement": ["high alumina cement", "alumina cement", "cement"],
            "Ordinary Portland Cement": ["ordinary portland cement", "opc", "portland cement", "cement"],
            "Portland Pozzolana Cement": ["portland pozzolana cement", "ppc", "cement"],
            "Portland Slag Cement": ["portland slag cement", "psc", "cement"],
            "Ready Mixed Concrete": ["ready mixed concrete", "concrete", "rmc"],
            "Cement": ["cement", "concrete"],
            "General Construction in Steel Code": ["construction in steel", "structural steel", "steel structure", "limit state design", "code of practice"],
            "Steel Reinforcement Bars": ["reinforcement bar", "tmt bar", "steel bar", "deformed bar", "rebar"],
            "uPVC Doors and Windows": ["door", "window", "upvc door", "upvc window"],
            "Safety Glass Architectural Building and General Uses": ["safety glass", "glass in building", "glazing", "architectural glass"],
            "Use of Glass in Buildings Energy and Light": ["glass in building", "energy and light", "architectural glass", "solar"],
            "Safety Glass and Glazing in Buildings": ["safety glass", "glass in building", "glazing"],
            "Doors and Windows": ["door", "window"],
            "Transparent Float Glass": ["float glass", "transparent float", "glass"],
            "Coarse and Fine Aggregate for Concrete": ["coarse aggregate", "fine aggregate", "crushed stone aggregate", "river sand", "aggregate for concrete", "aggregate"],
        }

    def get_scope_boundaries(self) -> List[Dict[str, Any]]:
        return [
            # Mild steel plain bars vs Deformed TMT rebar
            {
                "standard_family": "IS 432",
                "attribute": "GRADE",
                "exclusion_rule": lambda req: any(
                    grade in (str(req.get("grade") or "")).upper()
                    for grade in ["FE 415", "FE 500", "FE 550", "FE 600", "TMT"]
                ),
                "reason": "IS 432 is strictly for mild steel and medium tensile plain steel bars. High-strength deformed / TMT bars are governed by IS 1786.",
            },
            # Deformed TMT rebar vs Mild steel plain bars
            {
                "standard_family": "IS 1786",
                "attribute": "GRADE",
                "exclusion_rule": lambda req: "MILD STEEL" in (str(req.get("material") or "")).upper() and "TMT" not in (str(req.get("material") or "")).upper(),
                "reason": "IS 1786 applies to high strength deformed steel bars. Mild steel plain bars are governed by IS 432.",
            },
            # Ordinary Portland Cement 43 vs 53 grade
            {
                "standard_family": "IS 8112",
                "attribute": "GRADE",
                "exclusion_rule": lambda req: "53" in str(req.get("grade") or "") and "43" not in str(req.get("grade") or ""),
                "reason": "IS 8112 is strictly 43 Grade Ordinary Portland Cement. 53 Grade OPC is governed by IS 12269 (or consolidated IS 269:2015).",
            },
            {
                "standard_family": "IS 12269",
                "attribute": "GRADE",
                "exclusion_rule": lambda req: "43" in str(req.get("grade") or "") and "53" not in str(req.get("grade") or ""),
                "reason": "IS 12269 is strictly 53 Grade Ordinary Portland Cement. 43 Grade OPC is governed by IS 8112 (or consolidated IS 269:2015).",
            },
            # High Alumina Cement vs Portland Cement
            {
                "standard_family": "IS 6452",
                "attribute": "MATERIAL",
                "exclusion_rule": lambda req: any(
                    p in (str(req.get("material") or "") + " " + str(req.get("product") or "")).upper()
                    for p in ["PORTLAND", "OPC", "PPC", "SLAG"]
                ),
                "reason": "IS 6452 is for High Alumina Cement (refractory). Portland cements are governed by IS 269, IS 1489, or IS 455.",
            },
            # Cast iron pressure pipes vs ductile iron or fittings
            {
                "standard_family": "IS 1536",
                "attribute": "PRODUCT",
                "exclusion_rule": lambda req: any(
                    f in (str(req.get("product") or "")).upper()
                    for f in ["FITTING", "BEND", "TEE", "VALVE"]
                ),
                "reason": "IS 1536 is strictly for centrifugally cast iron pressure pipes. Fittings are governed by IS 1538.",
            },
            # Steel tubes for water vs structural hollow sections
            {
                "standard_family": "IS 1239 (Part 1)",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: "HOLLOW SECTION" in (str(req.get("product") or "")).upper() and "WATER" not in (str(req.get("application") or "")).upper(),
                "reason": "IS 1239 Part 1 is for steel tubes for water and non-hazardous gas. Structural hollow sections are governed by IS 4923.",
            },
            # Polyethylene pipes for water vs gaseous fuels
            {
                "standard_family": "IS 14885",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("application") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["POTABLE", "DRINKING WATER", "WATER SUPPLY", "WATER DISTRIBUTION"]
                ),
                "reason": "IS 14885 is strictly for polyethylene pipes for the supply of gaseous fuels. Potable water supply pipes are governed by IS 4984.",
            },
            # Polyethylene pipes for water vs sewerage / drainage
            {
                "standard_family": "IS 14333",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("application") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["POTABLE", "DRINKING WATER", "WATER SUPPLY", "WATER DISTRIBUTION"]
                ),
                "reason": "IS 14333 is strictly for HDPE pipes for sewerage and industrial waste disposal. Drinking water pipes are governed by IS 4984.",
            },
            # Glazed stoneware pipes: strictly sewage/drainage, not potable water
            {
                "standard_family": "IS 651",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("application") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["POTABLE", "DRINKING WATER", "WATER SUPPLY", "POTABLE WATER"]
                ),
                "reason": "IS 651 is strictly for glazed stoneware pipes and fittings for sewage and industrial waste drainage; not applicable to potable water systems.",
            },
            # PVC-U soil and waste discharge pipes vs potable water supply
            {
                "standard_family": "IS 13592",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("application") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["POTABLE", "DRINKING WATER", "PRESSURE PIPE", "POTABLE WATER"]
                ),
                "reason": "IS 13592 applies to PVC-U pipes for soil, waste, ventilation, and rainwater inside/outside buildings; potable water supply pipes are governed by IS 4985.",
            },
            # APP-modified bituminous membrane with glass-fibre reinforcement vs polyester reinforcement
            {
                "standard_family": "IS 16526",
                "attribute": "MATERIAL",
                "exclusion_rule": lambda req: "POLYESTER" in (str(req.get("material") or "") + " " + str(req.get("raw_text") or "")).upper(),
                "reason": "IS 16526 is strictly for APP-modified bituminous waterproofing membrane with glass-fibre reinforcement. Polyester-reinforced membranes are governed by IS 16532.",
            },
            # Structural steel vs Concrete reinforcement (rebar)
            {
                "standard_family": "IS 2062",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("product") or "") + " " + str(req.get("application") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["CONCRETE REINFORCEMENT", "REBAR", "TMT BAR", "REINFORCING BAR", "MILD STEEL BAR FOR CONCRETE"]
                ) and "STRUCTURAL" not in (str(req.get("product") or "") + " " + str(req.get("raw_text") or "")).upper(),
                "reason": "IS 2062 covers hot-rolled medium and high tensile structural steel (plates, sections, flats) for structural work; concrete reinforcement bars are governed by IS 1786 or IS 432.",
            },
            # Glazed fireclay sanitary appliances vs Vitreous china
            {
                "standard_family": "IS 771",
                "attribute": "MATERIAL",
                "exclusion_rule": lambda req: "VITREOUS" in (str(req.get("material") or "") + " " + str(req.get("raw_text") or "")).upper(),
                "reason": "IS 771 is strictly for glazed fireclay sanitary appliances (withdrawn 2022); vitreous china appliances are governed by IS 2556.",
            },
            # uPVC Potable Water Pipes (IS 4985) vs Soil/Waste/Rainwater (IS 13592) vs Stoneware (IS 651)
            {
                "standard_family": "IS 4985",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("application") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["SOIL DISCHARGE", "WASTE DISCHARGE", "SEWAGE CONVEYANCE", "RAINWATER PIPE", "VENTILATION PIPE"]
                ),
                "reason": "IS 4985 is strictly for unplasticized PVC pipes for potable water supplies. Soil/waste pipes are governed by IS 13592, and sewage pipes by IS 651.",
            },
            # Ready-mixed concrete (IS 4926) vs Raw aggregate (IS 383)
            {
                "standard_family": "IS 383",
                "attribute": "PRODUCT",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("product") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["READY MIXED CONCRETE", "RMC", "CONCRETE SUPPLY", "READY-MIX CONCRETE"]
                ) and not any(
                    w in (str(req.get("raw_text") or "")).upper()
                    for w in ["AGGREGATE", "SAND", "GRAVEL", "CRUSHED STONE"]
                ),
                "reason": "IS 383 is strictly for coarse and fine aggregates for concrete (material feedstock). Ready-mixed concrete production and supply is governed by IS 4926.",
            },
            # Broken brick aggregate in lime concrete vs Concrete aggregate
            {
                "standard_family": "IS 3068",
                "attribute": "MATERIAL",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("product") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["CRUSHED STONE", "RIVER SAND", "PAVEMENT", "PQC", "M35", "M40", "STRUCTURAL CONCRETE"]
                ) and "LIME CONCRETE" not in (str(req.get("raw_text") or "")).upper(),
                "reason": "IS 3068 is strictly for broken brick (burnt clay) coarse aggregate for use in lime concrete. Natural / crushed stone aggregates for concrete are governed by IS 383.",
            },
            # Raw granulated slag vs Finished Portland cement
            {
                "standard_family": "IS 12089",
                "attribute": "PRODUCT",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("product") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["RAPID HARDENING", "SULPHATE RESISTING", "HIGH ALUMINA", "LOW HEAT", "PORTLAND CEMENT"]
                ) and not any(
                    w in (str(req.get("raw_text") or "")).upper()
                    for w in ["SLAG FOR", "MANUFACTURE OF", "RAW SLAG", "GRANULATED SLAG"]
                ),
                "reason": "IS 12089 is strictly raw granulated blast furnace slag for the manufacture of Portland slag cement, not finished hydraulic cement.",
            },
            # Masonry cement vs Structural / Concrete Portland cements
            {
                "standard_family": "IS 3466",
                "attribute": "PRODUCT",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("product") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["RAPID HARDENING", "SULPHATE RESISTING", "PRECAST", "MARINE", "STRUCTURAL CONCRETE", "OPC", "PPC"]
                ),
                "reason": "IS 3466 covers masonry cement for mortar and rendering only; it is not permitted for structural concrete, rapid hardening, or sulphate resisting applications.",
            },
        ]

    def evaluate_custom_attribute(
        self,
        attribute_name: str,
        standard_desig: str,
        req_val: Any,
        cand_doc: Dict[str, Any],
        req_obj: Dict[str, Any],
    ) -> Optional[AttributeStatus]:
        reqs = req_obj.get("requirements", {})
        raw_text = (req_obj.get("raw_text") or "").lower()
        title = (cand_doc.get("title") or "").lower()
        scope = (cand_doc.get("scope") or "").lower()
        candidate_text = f"{title} {scope} {standard_desig}".lower()

        if attribute_name == "MATERIAL":
            mat_val = (req_val.get("value") or "").lower() if isinstance(req_val, dict) else str(req_val or "").lower()
            if not mat_val:
                for m in ["hdpe", "upvc", "cast iron", "spun iron", "mild steel", "alumina", "pe-100", "pe-80"]:
                    if m in raw_text:
                        mat_val = m
                        break
            if mat_val:
                if any(h in mat_val or h in raw_text for h in ["hdpe", "pe-100", "pe 100", "high density polyethylene"]):
                    if ("composite" in candidate_text or "aluminium" in candidate_text or "pe-al-pe" in candidate_text) and not ("composite" in raw_text):
                        return AttributeStatus.MISMATCH
                    elif "polyvinyl chloride" in candidate_text or "upvc" in candidate_text or "cast iron" in candidate_text or "polypropylene" in candidate_text or re.search(r'\b(pvc|pp|pp-r)\b', candidate_text):
                        return AttributeStatus.MISMATCH
                    elif "polyethylene" in candidate_text or "hdpe" in candidate_text:
                        return AttributeStatus.MATCH
                elif "upvc" in mat_val or "unplasticized" in mat_val:
                    if "polyethylene" in candidate_text or "cast iron" in candidate_text:
                        return AttributeStatus.MISMATCH
                    elif "unplasticized" in candidate_text or "pvc" in candidate_text:
                        return AttributeStatus.MATCH
                elif "cast iron" in mat_val or "spun iron" in mat_val:
                    if "steel tube" in candidate_text or "polyethylene" in candidate_text or "concrete" in candidate_text:
                        return AttributeStatus.MISMATCH
                    elif "cast iron" in candidate_text or "spun iron" in candidate_text:
                        return AttributeStatus.MATCH
                elif "alumina" in mat_val:
                    if "pozzolana" in candidate_text or "portland slag" in candidate_text:
                        return AttributeStatus.MISMATCH
                    elif "high alumina" in candidate_text or "alumina" in candidate_text:
                        return AttributeStatus.MATCH

        elif attribute_name == "GRADE":
            grade_val = (req_val.get("value") or "").lower() if isinstance(req_val, dict) else str(req_val or "").lower()
            if not grade_val:
                for g in ["43 grade", "53 grade", "33 grade", "fe 500", "fe 550", "heavy class", "class 3"]:
                    if g in raw_text:
                        grade_val = g
                        break
            if grade_val:
                if "43 grade" in grade_val and "12269" in standard_desig:
                    return AttributeStatus.MISMATCH
                elif "53 grade" in grade_val and "8112" in standard_desig:
                    return AttributeStatus.MISMATCH
                elif "class 3" in grade_val and "4985" in standard_desig:
                    return AttributeStatus.MATCH
                elif "heavy class" in grade_val and "1239" in standard_desig:
                    return AttributeStatus.MATCH
                elif grade_val in candidate_text:
                    return AttributeStatus.MATCH

        elif attribute_name == "APPLICATION":
            app_val = (req_val.get("value") or "").lower() if isinstance(req_val, dict) else str(req_val or "").lower()
            if not app_val:
                if "drinking water" in raw_text or "potable water" in raw_text:
                    app_val = "potable water"
                elif "sewerage" in raw_text or "drainage" in raw_text:
                    app_val = "sewerage"
                elif "building facade" in raw_text or "architectural" in raw_text:
                    app_val = "architectural"
                elif "automotive" in raw_text or "road transport" in raw_text:
                    app_val = "automotive"

            if app_val:
                # Potable water vs sewerage / gaseous fuels
                if any(p in app_val for p in ["potable", "drinking"]) and any(s in candidate_text for s in ["sewerage", "drainage", "sewer", "gaseous fuel", "gas supply", "fuel gas"]):
                    return AttributeStatus.MISMATCH
                if any(s in app_val for s in ["sewerage", "drainage", "sewer"]) and any(p in candidate_text for p in ["potable", "drinking water"]):
                    return AttributeStatus.MISMATCH
                # Architectural building glass vs automotive road transport
                if any(a in app_val for a in ["architectural", "building", "glazing", "facade"]) and ("road transport" in candidate_text or "part 2" in standard_desig.lower() and "2553" in standard_desig):
                    return AttributeStatus.MISMATCH
                if any(a in app_val for a in ["automotive", "road transport", "vehicle"]) and ("architectural" in candidate_text or "part 1" in standard_desig.lower() and "2553" in standard_desig):
                    return AttributeStatus.MISMATCH

        return None

    def check_custom_contradiction(
        self,
        standard_desig: str,
        cand_doc: Dict[str, Any],
        req_obj: Dict[str, Any],
    ) -> Optional[Tuple[bool, str]]:
        req_text = (req_obj.get("raw_text") or "").lower()
        title = (cand_doc.get("title") or "").lower()

        # Check cement type contradiction
        if "high alumina" in req_text and ("portland" in title or "pozzolana" in title or "slag" in title):
            return True, "Procurement specifies High Alumina Cement; candidate is a Portland cement variant."
        if "pozzolana" in req_text and "high alumina" in title:
            return True, "Procurement specifies Pozzolana Cement; candidate is High Alumina Cement."

        # Check pipe material contradiction
        if "hdpe" in req_text and ("upvc" in title or "cast iron" in title or "steel" in title):
            return True, "Procurement specifies HDPE pipe; candidate standard covers different material."
        if "upvc" in req_text and ("polyethylene" in title or "cast iron" in title):
            return True, "Procurement specifies uPVC pipe; candidate standard covers different material."

        # Check pipe application contradiction
        if ("potable" in req_text or "drinking water" in req_text) and ("gaseous fuel" in title or "gas supply" in title):
            return True, "Procurement specifies potable water pipes; candidate standard is for gaseous fuel conveyance."

        return None

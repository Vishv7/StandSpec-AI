"""
ETD Domain Rule Registry — StandSpec AI (Phase P1-B)
Electrotechnical domain rules: Power Cables, Transformers, Switchgear,
Electricity Meters, Surge Arresters, Induction Motors, Appliances, LED Lamps.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from src.recommendation.applicability.base_registry import DomainRuleRegistry
from src.recommendation.applicability.state import AttributeStatus


class ETDRuleRegistry(DomainRuleRegistry):
    """
    Rule registry for Electrotechnical Department (ETD) standards.
    """

    @property
    def department_code(self) -> str:
        return "ETD"

    def get_product_stem_mappings(self) -> Dict[str, List[str]]:
        return {
            "Power Cable": ["power cable", "cable", "conductor", "wire"],
            "Aerial Bunched Cable": ["aerial bunched", "ab cable", "cable"],
            "Power Transformers": ["power transformer", "distribution transformer", "autotransformer", "transformer"],
            "Distribution Transformers": ["distribution transformer", "transformer"],
            "Low-Voltage Switchgear and Controlgear": ["switchgear", "circuit-breaker", "circuit breaker", "controlgear", "switchboard"],
            "Surge Arresters": ["surge arrester", "lightning arrester", "arrester"],
            "Three Phase Induction Motors": ["induction motor", "electric motor", "motor"],
            "Smart Static Electricity Meters": ["smart static electricity meter", "smart meter", "ac static smart", "electricity meter", "smart static meter"],
            "Static Energy Meters": ["static energy meter", "static watthour", "electricity meter", "energy meter", "watthour meter"],
            "AC Electricity Meters Induction Type": ["induction type meter", "electromechanical meter", "ac electricity meter", "induction meter", "meter"],
            "Electricity Meter": ["electricity meter", "energy meter", "watthour meter", "meter"],
            "Direct Reading pH Meters": ["ph meter", "direct reading ph", "ph meter"],
            "Thermocouple Pyrometers": ["pyrometer", "thermocouple pyrometer", "pyrometers"],
            "Pressure and Vacuum Gauges": ["pressure gauge", "vacuum gauge", "bourdon tube gauge", "pressure and vacuum gauge"],
            "Food Waste Disposers Safety": ["food waste disposer", "waste disposer", "disposer"],
            "Self-Ballasted LED Lamps": ["led lamp", "self-ballasted lamp", "self-ballasted led"],
            "Household Electrical Appliances": ["household appliance", "electrical appliance", "water heater", "geyser"],
        }

    def _extract_voltage_volts(self, req: Dict[str, Any]) -> Optional[float]:
        v_str = str(req.get("voltage") or "").strip().lower()
        if not v_str:
            v_str = str(req.get("raw_text") or "").strip().lower()
        if not v_str:
            return None
        m_kv = re.search(r'(\d+(?:\.\d+)?)\s*kv', v_str)
        if m_kv:
            return float(m_kv.group(1)) * 1000.0
        m_v = re.search(r'(\d+(?:\.\d+)?)\s*v\b', v_str)
        if m_v:
            return float(m_v.group(1))
        return None

    def _extract_kva(self, req: Dict[str, Any]) -> Optional[float]:
        cap_str = str(req.get("capacity") or "").strip().lower()
        if not cap_str:
            cap_str = str(req.get("raw_text") or "").strip().lower()
        if not cap_str:
            return None
        m_mva = re.search(r'(\d+(?:\.\d+)?)\s*mva', cap_str)
        if m_mva:
            return float(m_mva.group(1)) * 1000.0
        m_kva = re.search(r'(\d+(?:\.\d+)?)\s*kva', cap_str)
        if m_kva:
            return float(m_kva.group(1))
        return None

    def get_scope_boundaries(self) -> List[Dict[str, Any]]:
        return [
            # Distribution transformers vs Bulk transmission power autotransformers
            {
                "standard_family": "IS 1180",
                "attribute": "CAPACITY",
                "max_rating_kva": 2500,
                "exclusion_rule": lambda req: self._extract_kva(req) is not None and self._extract_kva(req) > 2500,
                "reason": "IS 1180 is strictly limited to distribution transformers up to 2500 kVA. Bulk transmission power transformers are governed by IS 2026.",
            },
            # Small power supply transformers vs bulk grid autotransformers
            {
                "standard_family": "IS/IEC 61558",
                "attribute": "CAPACITY",
                "exclusion_rule": lambda req: (
                    (self._extract_kva(req) is not None and self._extract_kva(req) > 25)
                    or (self._extract_voltage_volts(req) is not None and self._extract_voltage_volts(req) > 1000)
                    or any(w in str(req.get("raw_text") or "").lower() for w in ["mva", "substation", "grid", "autotransformer", "transmission"])
                ),
                "reason": "IS/IEC 61558 is limited to small power transformers and power supply units (< 25 kVA). Large power autotransformers and grid substation equipment are governed by IS 2026.",
            },
            # Low voltage cables: IS 694 vs IS 7098 Part 2 (MV/HV)
            {
                "standard_family": "IS 694",
                "attribute": "VOLTAGE",
                "exclusion_rule": lambda req: self._extract_voltage_volts(req) is not None and self._extract_voltage_volts(req) > 1100,
                "reason": "IS 694 is strictly for PVC insulated cables up to and including 1100 V. Medium/High voltage cables (> 1.1 kV) are governed by IS 7098 Part 2.",
            },
            # Low voltage PVC cables (IS 1554 Part 1 <= 1.1 kV)
            {
                "standard_family": "IS 1554 (Part 1)",
                "attribute": "VOLTAGE",
                "exclusion_rule": lambda req: self._extract_voltage_volts(req) is not None and self._extract_voltage_volts(req) > 1100,
                "reason": "IS 1554 Part 1 is strictly for PVC insulated cables for working voltages up to and including 1100 V.",
            },
            # Medium voltage PVC cables (IS 1554 Part 2: 3.3 kV to 11 kV)
            {
                "standard_family": "IS 1554 (Part 2)",
                "attribute": "VOLTAGE",
                "exclusion_rule": lambda req: self._extract_voltage_volts(req) is not None and (
                    self._extract_voltage_volts(req) < 3300 or self._extract_voltage_volts(req) > 11000
                ),
                "reason": "IS 1554 Part 2 is strictly for PVC insulated heavy-duty cables from 3.3 kV up to and including 11 kV.",
            },
            # Overhead AAAC conductors (IS 398 Part 4) vs Underground cables
            {
                "standard_family": "IS 398 (Part 4)",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("application") or "") + " " + str(req.get("installation") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["UNDERGROUND", "BURIED", "TRENCH", "INSULATED CABLE"]
                ),
                "reason": "IS 398 Part 4 is strictly for aluminium alloy stranded conductors (AAAC, Al-Mg-Si) for overhead power transmission.",
            },
            # Overhead ACSR conductors for EHV (IS 398 Part 5: 400 kV and above)
            {
                "standard_family": "IS 398 (Part 5)",
                "attribute": "VOLTAGE",
                "exclusion_rule": lambda req: self._extract_voltage_volts(req) is not None and self._extract_voltage_volts(req) < 400000,
                "reason": "IS 398 Part 5 covers aluminium conductors galvanized-steel-reinforced (ACSR) for extra-high-voltage overhead lines of 400 kV and above.",
            },
            # Porcelain insulators for overhead lines > 1000 V (IS 731)
            {
                "standard_family": "IS 731",
                "attribute": "VOLTAGE",
                "exclusion_rule": lambda req: self._extract_voltage_volts(req) is not None and self._extract_voltage_volts(req) <= 1000,
                "reason": "IS 731 covers porcelain insulators for overhead power lines with a nominal voltage greater than 1000 V (<= 1000 V is covered by IS 1445).",
            },
            # Miniature Circuit Breakers (IS/IEC 60898-1): <= 440 V, <= 125 A, <= 25 kA, AC 50 Hz only
            {
                "standard_family": "IS/IEC 60898-1",
                "attribute": "VOLTAGE",
                "exclusion_rule": lambda req: (
                    (self._extract_voltage_volts(req) is not None and self._extract_voltage_volts(req) > 440)
                    or "DC" in (str(req.get("technology") or "") + " " + str(req.get("raw_text") or "")).upper().split()
                ),
                "reason": "IS/IEC 60898-1 covers AC circuit-breakers for household and similar installations for rated voltages up to 440 V; DC circuit breakers are governed by IS/IEC 60898-2 and industrial circuit breakers by IS/IEC 60947-2.",
            },
            # Earthing Code of Practice (IS 3043) vs Electrode / Plate Hardware Product Standards
            {
                "standard_family": "IS 3043",
                "attribute": "ROLE",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("product") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["SUPPLY OF COPPER EARTH PLATE", "SUPPLY OF GI PIPE ELECTRODE", "EARTHING CHEMICAL COMPOUND", "EARTH ELECTRODE PRODUCT"]
                ) and "INSTALLATION" not in (str(req.get("raw_text") or "")).upper(),
                "reason": "IS 3043:2018 is a Code of Practice / Installation and Design standard for earthing systems, not a primary product specification for standalone earth electrodes/plates.",
            },
            # Industrial Circuit Breakers MCCB/ACB (IS/IEC 60947-2) vs Household MCB (IS/IEC 60898-1)
            {
                "standard_family": "IS/IEC 60947-2",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: (
                    any(w in (str(req.get("product") or "") + " " + str(req.get("raw_text") or "")).upper() for w in ["HOUSEHOLD", "DOMESTIC", "RESIDENTIAL"])
                    and self._extract_voltage_volts(req) is not None and self._extract_voltage_volts(req) <= 440
                    and "MCCB" not in (str(req.get("raw_text") or "")).upper()
                    and "ACB" not in (str(req.get("raw_text") or "")).upper()
                ),
                "reason": "IS/IEC 60947-2 covers low-voltage switchgear circuit-breakers (MCCBs and ACBs) for industrial and commercial installations. Household and similar MCBs are governed by IS/IEC 60898-1.",
            },
            # Three-Phase Induction Motors (IS 12615) - Line operated AC motors
            {
                "standard_family": "IS 12615",
                "attribute": "PRODUCT",
                "exclusion_rule": lambda req: any(
                    w in (str(req.get("product") or "") + " " + str(req.get("raw_text") or "")).upper()
                    for w in ["SINGLE PHASE", "FRACTIONAL HORSEPOWER", "DC MOTOR"]
                ),
                "reason": "IS 12615 is strictly for line-operated three-phase AC induction motors (energy efficiency classes IE2, IE3, IE4).",
            },
            # XLPE cables Part 1 (LV <= 1.1 kV) vs Part 2 (MV 3.3 to 33 kV)
            {
                "standard_family": "IS 7098 (Part 1)",
                "attribute": "VOLTAGE",
                "exclusion_rule": lambda req: self._extract_voltage_volts(req) is not None and self._extract_voltage_volts(req) > 1100,
                "reason": "IS 7098 Part 1 covers working voltages up to and including 1100 V. Working voltages from 3.3 kV to 33 kV are governed by IS 7098 Part 2.",
            },
            {
                "standard_family": "IS 7098 (Part 2)",
                "attribute": "VOLTAGE",
                "exclusion_rule": lambda req: self._extract_voltage_volts(req) is not None and (
                    self._extract_voltage_volts(req) < 3300 or self._extract_voltage_volts(req) > 33000
                ),
                "reason": "IS 7098 Part 2 is strictly for working voltages from 3.3 kV up to and including 33 kV. Low voltage (<= 1.1 kV) is Part 1; EHV (> 33 kV) is Part 3.",
            },
            # Aerial Bunched Cables vs Underground / Standard Power Cables
            {
                "standard_family": "IS 14255",
                "attribute": "APPLICATION",
                "exclusion_rule": lambda req: any(
                    ug in (str(req.get("application") or "") + " " + str(req.get("installation") or "")).upper()
                    for ug in ["UNDERGROUND", "BURIED", "TRENCH", "DUCT"]
                ),
                "reason": "IS 14255 is strictly for Aerial Bunched Cables (overhead distribution). Underground power cables are governed by IS 7098 or IS 1554.",
            },
            # Smart Prepaid Meters vs Conventional Static Meters
            {
                "standard_family": "IS 13779",
                "attribute": "PRODUCT",
                "exclusion_rule": lambda req: any(
                    sm in (str(req.get("product") or "") + " " + str(req.get("application") or "")).upper()
                    for sm in ["SMART METER", "PREPAID", "SMART PREPAID", "TWO-WAY COMMUNICATION", "AMI"]
                ),
                "reason": "IS 13779 is for conventional AC static watthour meters (Class 1 & 2). Smart meters with two-way communication / prepayment features are governed by IS 16444.",
            },
            {
                "standard_family": "IS 13010",
                "attribute": "PRODUCT",
                "exclusion_rule": lambda req: any(
                    st in (str(req.get("product") or "") + " " + str(req.get("material") or "")).upper()
                    for st in ["STATIC", "SMART", "ELECTRONIC", "MICROPROCESSOR"]
                ),
                "reason": "IS 13010 is strictly for induction type (electromechanical) electricity meters. Static energy meters are governed by IS 13779 or IS 16444.",
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
                for m in ["xlpe", "pvc", "crosslinked"]:
                    if m in raw_text:
                        mat_val = m
                        break
            if mat_val:
                if "xlpe" in mat_val or "crosslinked polyethylene" in mat_val:
                    if "pvc insulated" in candidate_text and "xlpe" not in candidate_text and "crosslinked" not in candidate_text:
                        return AttributeStatus.MISMATCH
                    elif "xlpe" in candidate_text or "crosslinked" in candidate_text:
                        return AttributeStatus.MATCH
                elif "pvc" in mat_val:
                    if "xlpe insulated" in candidate_text:
                        return AttributeStatus.MISMATCH
                    elif "pvc" in candidate_text:
                        return AttributeStatus.MATCH

        elif attribute_name == "VOLTAGE":
            volt_v = self._extract_voltage_volts(req_obj.get("requirements", {}))
            if volt_v is not None:
                if "up to 1100" in candidate_text and volt_v > 1100:
                    return AttributeStatus.MISMATCH
                elif ("3.3 kv" in candidate_text or "part 2" in standard_desig.lower()) and "7098" in standard_desig and volt_v < 3300:
                    return AttributeStatus.MISMATCH
                elif ("33 kv" in candidate_text or "part 2" in standard_desig.lower()) and "7098" in standard_desig and volt_v > 33000:
                    return AttributeStatus.MISMATCH
                elif (volt_v > 1100 and "7098 (part 2)" in standard_desig.lower()) or (volt_v <= 1100 and "7098 (part 1)" in standard_desig.lower()):
                    return AttributeStatus.MATCH

        elif attribute_name == "ENVIRONMENT":
            env_val = (req_val.get("value") or "").lower() if isinstance(req_val, dict) else str(req_val or "").lower()
            if not env_val:
                if "underground" in raw_text:
                    env_val = "underground"
                elif "overhead" in raw_text or "aerial" in raw_text:
                    env_val = "aerial"

            if env_val:
                if "underground" in env_val and ("aerial bunched" in candidate_text or "14255" in standard_desig):
                    return AttributeStatus.MISMATCH
                if ("aerial" in env_val or "overhead" in env_val) and "underground" in candidate_text:
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

        # Check smart meter vs conventional static meter contradiction
        if ("smart meter" in req_text or "prepaid" in req_text) and "13779" in standard_desig:
            return True, "Procurement specifies smart/prepaid meter; IS 13779 is for non-smart conventional static meters."

        # Check aerial vs underground cable contradiction
        if "aerial bunched" in req_text and "7098" in standard_desig:
            return True, "Procurement specifies aerial bunched cable; IS 7098 is for standard insulated power cables."
        if "underground" in req_text and "14255" in standard_desig:
            return True, "Procurement specifies underground cable; IS 14255 is for aerial bunched overhead cables."

        return None

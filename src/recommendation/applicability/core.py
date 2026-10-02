"""
Generic Technical Applicability Engine — StandSpec AI (Phase P1-B)
Modular core engine for technical attribute evaluation, scope boundary verification,
and contradiction detection. Department-agnostic core logic with domain rule registries.

Core Principles:
1. "Never let 'no rejection rule fired' become equivalent to 'this standard is applicable'."
2. Evaluates 10 distinct technical dimensions:
   PRODUCT, MATERIAL, GRADE, VOLTAGE, CAPACITY, DIMENSIONS,
   APPLICATION, ENVIRONMENT, PERFORMANCE, SAFETY, INSTALLATION
3. Each attribute strictly evaluates to MATCH / MISMATCH / UNKNOWN.
4. Positive PRODUCT == MATCH evidence is mandatory for APPLICABLE.
5. Any attribute evaluating to MISMATCH strictly disqualifies the candidate (NOT_APPLICABLE).
6. Preserves UNKNOWN when attributes are under-specified rather than guessing.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from src.recommendation.role_classifier import RoleClassifier, StandardRole
from src.recommendation.applicability.state import ApplicabilityState, AttributeStatus
from src.recommendation.applicability.base_registry import DomainRuleRegistry
from src.recommendation.applicability.material_concepts import (
    resolve_material,
    resolve_material_compatibility,
    extract_material_from_text,
    MaterialMatchResult,
)
from src.recommendation.applicability.product_concepts import (
    resolve_base_product,
    build_product_signature,
    compare_products,
    detect_product_from_title,
)


class GenericApplicabilityEngine:
    """
    Department-independent Applicability Engine driven by domain rule registries.
    """

    def __init__(self, registries: Optional[List[DomainRuleRegistry]] = None):
        self.registries: List[DomainRuleRegistry] = registries or []
        self._rebuild_registry_caches()

    def register(self, registry: DomainRuleRegistry):
        """Register a new domain rule plugin."""
        self.registries.append(registry)
        self._rebuild_registry_caches()

    def _rebuild_registry_caches(self):
        self.product_stem_mappings: Dict[str, List[str]] = {}
        self.scope_boundaries: List[Dict[str, Any]] = []

        for reg in self.registries:
            self.product_stem_mappings.update(reg.get_product_stem_mappings())
            self.scope_boundaries.extend(reg.get_scope_boundaries())

    def evaluate_applicability(
        self,
        candidate: Dict[str, Any],
        normalized_requirements: Dict[str, Any],
        hydration_document: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate candidate standard against tender requirements.
        Produces full per-attribute breakdown with evidence reasoning.
        """
        doc = hydration_document or candidate.get("document", candidate)
        if not isinstance(doc, dict):
            doc = candidate

        reqs = normalized_requirements.get("requirements", {})
        intent = normalized_requirements.get("procurement_intent", {})
        raw_text = normalized_requirements.get("raw_text", "")
        desig = candidate.get("designation") or doc.get("designation") or doc.get("id") or "UNKNOWN"
        title = doc.get("title") or candidate.get("title") or ""
        scope = doc.get("scope") or candidate.get("scope") or ""

        # Step 0: Check Standard Architectural Role (P0-1 & P1-B)
        # Check persisted standard_role on node first, fallback to classifier
        persisted_role = doc.get("standard_role") or candidate.get("standard_role")
        if persisted_role:
            role_type = persisted_role
            role_confidence = doc.get("role_confidence", 0.95)
            role_reason = doc.get("role_reason", f"Persisted graph role: {persisted_role}")
        else:
            role_result = RoleClassifier.classify_with_evidence(candidate)
            role_type = role_result["standard_role"]
            role_confidence = role_result["role_confidence"]
            role_reason = role_result["role_reason"]

        proc_obj = intent.get("procurement_object", {})
        proc_obj_val = proc_obj.get("value") if isinstance(proc_obj, dict) else proc_obj
        obj_type = intent.get("object_type", "FINISHED_PRODUCT")

        # 0.1: Test Methods and Auxiliary Mountings are classified as RELATED
        if role_type in (StandardRole.TEST_METHOD.value, StandardRole.DIMENSIONAL_MOUNTING.value):
            return {
                "is_applicable": False,
                "state": ApplicabilityState.RELATED.value,
                "confidence": 0.85,
                "matched_attributes": [],
                "mismatched_attributes": [],
                "unknown_attributes": ["ALL"],
                "rejection_reason": f"{desig} is a {role_type} standard ({role_reason}). Classified as allied/related reference, not primary product recommendation.",
                "evidence_summary": role_reason,
                "standard_role": role_type,
            }

        # 0.2: Components vs Finished Assembly / Product Gating
        if role_type == StandardRole.COMPONENT.value and obj_type in ("FINISHED_ASSEMBLY", "FINISHED_PRODUCT"):
            return {
                "is_applicable": False,
                "state": ApplicabilityState.RELATED.value,
                "confidence": 0.85,
                "matched_attributes": [],
                "mismatched_attributes": ["PRODUCT", "ROLE_MISMATCH"],
                "unknown_attributes": [],
                "rejection_reason": f"{desig} is an intermediate component/profile standard (COMPONENT). It cannot serve as a primary product specification for procurement of {obj_type.lower().replace('_', ' ')}.",
                "evidence_summary": role_reason,
                "standard_role": role_type,
            }

        # 0.3: Design Codes are NOT primary products
        if role_type == StandardRole.DESIGN_CODE.value and obj_type in ("FINISHED_PRODUCT", "FINISHED_ASSEMBLY") and not (
            proc_obj_val and any(term in str(proc_obj_val).lower() for term in ["code", "design", "structural", "construction"])
        ):
            return {
                "is_applicable": False,
                "state": ApplicabilityState.RELATED.value,
                "confidence": 0.90,
                "matched_attributes": [],
                "mismatched_attributes": ["PRODUCT", "ROLE_MISMATCH"],
                "unknown_attributes": [],
                "rejection_reason": f"{desig} is an Engineering Design Code (DESIGN_CODE). It cannot serve as a primary product specification for a procurement tender.",
                "evidence_summary": role_reason,
                "standard_role": role_type,
            }

        # 0.4: Scope Text Availability Check
        has_scope_evidence = bool(
            candidate.get("scope_evidence_available", False)
            or doc.get("scope_evidence_available", False)
            or (scope and str(scope).strip())
        )
        rec_ready = candidate.get("recommendation_ready", doc.get("recommendation_ready", None))
        if rec_ready is False:
            scope_missing = True
        elif not has_scope_evidence:
            scope_missing = True
        else:
            scope_missing = False

        attribute_evaluations: Dict[str, AttributeStatus] = {}
        mismatched: List[str] = []
        matched: List[str] = []
        unknown: List[str] = []

        # 1. PRODUCT EVALUATION (Mandatory Grounding)
        prod_status, prod_reason = self._evaluate_product(reqs, title, scope, raw_text)
        attribute_evaluations["PRODUCT"] = prod_status
        if prod_status == AttributeStatus.MATCH:
            matched.append("PRODUCT")
        elif prod_status == AttributeStatus.MISMATCH:
            mismatched.append("PRODUCT")
        else:
            unknown.append("PRODUCT")

        # 2. Scope Boundaries Check (Domain Registry Rule Check)
        combined_reqs = {**reqs, "raw_text": raw_text, "product": reqs.get("product") or raw_text}
        for boundary in self.scope_boundaries:
            fam = boundary["standard_family"]
            if fam.upper() in desig.upper() or (fam + " ") in desig or (fam + ":") in desig:
                rule_fn = boundary["exclusion_rule"]
                if rule_fn(combined_reqs):
                    attr = boundary["attribute"]
                    attribute_evaluations[attr] = AttributeStatus.MISMATCH
                    if attr not in mismatched:
                        mismatched.append(attr)
                    eval_trace = {
                        k.lower(): {
                            "attribute": k,
                            "status": v.value,
                            "value": str(reqs.get(k.lower()) or ""),
                            "evidence": f"Exclusion rule boundary: {boundary['reason']}",
                        }
                        for k, v in attribute_evaluations.items()
                    }
                    return {
                        "is_applicable": False,
                        "state": ApplicabilityState.NOT_APPLICABLE.value,
                        "confidence": 0.95,
                        "matched_attributes": matched,
                        "mismatched_attributes": mismatched,
                        "unknown_attributes": unknown,
                        "rejection_reason": boundary["reason"],
                        "evidence_summary": f"Exclusion triggered: {boundary['reason']}",
                        "standard_role": role_type,
                        "evaluation_trace": eval_trace,
                    }

        # 3. Standard 10-Attribute Evaluations
        eval_attrs = [
            ("MATERIAL", self._evaluate_material),
            ("GRADE", self._evaluate_grade),
            ("VOLTAGE", self._evaluate_voltage),
            ("CAPACITY", self._evaluate_capacity),
            ("DIMENSIONS", self._evaluate_dimensions),
            ("APPLICATION", self._evaluate_application),
            ("ENVIRONMENT", self._evaluate_environment),
            ("PERFORMANCE", self._evaluate_performance),
            ("SAFETY", self._evaluate_safety),
            ("INSTALLATION", self._evaluate_installation),
        ]

        for attr_name, eval_fn in eval_attrs:
            # Check domain registry override first
            override_status = None
            for reg in self.registries:
                override_status = reg.evaluate_custom_attribute(
                    attr_name, desig, reqs.get(attr_name.lower()), doc, normalized_requirements
                )
                if override_status is not None:
                    break

            if override_status is not None:
                status = override_status
            else:
                status = eval_fn(reqs.get(attr_name.lower()), title, scope, desig)

            attribute_evaluations[attr_name] = status
            if status == AttributeStatus.MATCH:
                matched.append(attr_name)
            elif status == AttributeStatus.MISMATCH:
                mismatched.append(attr_name)
            else:
                unknown.append(attr_name)

        # Build structured evaluation trace for UI and audit logging
        eval_trace = {
            k.lower(): {
                "attribute": k,
                "status": v.value,
                "value": str(reqs.get(k.lower()) or ""),
                "evidence": f"Evaluation for {k}: {v.value}",
            }
            for k, v in attribute_evaluations.items()
        }

        # 5. Final State Derivation
        if mismatched:
            return {
                "is_applicable": False,
                "state": ApplicabilityState.NOT_APPLICABLE.value,
                "confidence": 0.90,
                "matched_attributes": matched,
                "mismatched_attributes": mismatched,
                "unknown_attributes": unknown,
                "rejection_reason": f"Candidate failed attribute verification on: {', '.join(mismatched)}.",
                "evidence_summary": f"Mismatches detected: {mismatched}",
                "standard_role": role_type,
                "evaluation_trace": eval_trace,
            }

        # Trust Mandate P0-1: Scope Missing Gate
        if scope_missing:
            return {
                "is_applicable": False,
                "state": ApplicabilityState.EXPERT_REVIEW_REQUIRED.value,
                "confidence": 0.50,
                "matched_attributes": matched,
                "mismatched_attributes": ["evidence_readiness"],
                "unknown_attributes": unknown,
                "rejection_reason": f"{desig} lacks verified scope evidence in the knowledge base (recommendation_ready={rec_ready}). Detailed technical boundaries cannot be confirmed without expert review.",
                "evidence_summary": "Unready scope evidence in knowledge base.",
                "standard_role": role_type,
                "evaluation_trace": eval_trace,
            }

        # If product did not positively match
        if prod_status != AttributeStatus.MATCH:
            return {
                "is_applicable": False,
                "state": ApplicabilityState.UNKNOWN.value,
                "confidence": 0.30,
                "matched_attributes": matched,
                "mismatched_attributes": [],
                "unknown_attributes": unknown,
                "rejection_reason": "No positive product grounding evidence found in candidate title or scope.",
                "evidence_summary": "Product unverified.",
                "standard_role": role_type,
                "evaluation_trace": eval_trace,
            }

        # Grounding depth evaluation
        high_signal_attrs = {"MATERIAL", "VOLTAGE", "CAPACITY", "GRADE", "DIMENSIONS"}
        grounded_high_signal = [a for a in matched if a in high_signal_attrs]

        if not grounded_high_signal and len(unknown) >= 8:
            return {
                "is_applicable": True,
                "state": ApplicabilityState.CONDITIONALLY_APPLICABLE.value,
                "confidence": 0.65,
                "matched_attributes": matched,
                "mismatched_attributes": [],
                "unknown_attributes": unknown,
                "rejection_reason": None,
                "conditional_reason": f"Product matches '{matched[0]}', but critical technical parameters are UNKNOWN in tender specification.",
                "evidence_summary": f"Product matches '{matched[0]}', but critical technical parameters are UNKNOWN in tender specification.",
                "standard_role": role_type,
                "evaluation_trace": eval_trace,
            }

        return {
            "is_applicable": True,
            "state": ApplicabilityState.APPLICABLE.value,
            "confidence": 0.90,
            "matched_attributes": matched,
            "mismatched_attributes": [],
            "unknown_attributes": unknown,
            "rejection_reason": None,
            "evidence_summary": f"Grounded match on {len(matched)} technical attributes: {', '.join(matched)}.",
            "standard_role": role_type,
            "evaluation_trace": eval_trace,
        }

    def _evaluate_product(
        self, reqs: Dict[str, Any], title: str, scope: str, raw_text: str
    ) -> Tuple[AttributeStatus, str]:
        prod = reqs.get("product")
        content = f"{title} {scope}".lower()

        if not prod:
            if raw_text:
                for p_norm, stems in self.product_stem_mappings.items():
                    for s in stems:
                        if s.lower() in raw_text.lower():
                            if s.lower() in content or re.search(r'\b' + re.escape(s.lower()) + r'(?:s|es)?\b', content):
                                return AttributeStatus.MATCH, f"Matched canonical stem '{s}' from raw query"
            return AttributeStatus.UNKNOWN, "No product specified in query requirements"

        if isinstance(prod, dict):
            prod_norm = prod.get("normalization") or prod.get("value") or ""
            prod_val = prod.get("value") or ""
        else:
            prod_norm = str(prod or "")
            prod_val = str(prod or "")

        # Check product stem mappings from registries
        stems = self.product_stem_mappings.get(prod_norm) or self.product_stem_mappings.get(prod_val)
        if stems:
            for s in stems:
                s_low = s.lower()
                if s_low in content or re.search(r'\b' + re.escape(s_low) + r'(?:s|es)?\b', content):
                    return AttributeStatus.MATCH, f"Matched canonical stem '{s}'"

        # Explicit cross-category product-family conflict checks
        title_lower = title.lower()
        prod_val_lower = prod_val.lower()

        # 1. Pipe/Tube vs Valve/Fitting/Manhole conflict
        if ("pipe" in prod_val_lower or "tube" in prod_val_lower):
            if any(w in title_lower for w in ["valve", "valves", "fitting", "fittings", "jointing", "accessory", "accessories"]):
                if not any(w in title_lower for w in ["pipes", "tubes"]) and not re.search(r'\bpipe\b|\btube\b', title_lower):
                    return AttributeStatus.MISMATCH, "Candidate covers pipe fittings/valves/accessories, but query requires pipes/tubes."
            if any(w in title_lower for w in ["tank", "tanks", "vessel", "reservoir", "septic"]):
                if not any(w in title_lower for w in ["pipes", "tubes"]) and not re.search(r'\bpipe\b|\btube\b', title_lower):
                    return AttributeStatus.MISMATCH, "Candidate covers tanks/vessels, but query requires pipes/tubes."
        if any(w in prod_val_lower for w in ["fitting", "fittings", "valve", "valves"]):
            if "pipe" in title_lower or "tube" in title_lower:
                if not any(w in title_lower for w in ["fitting", "fittings", "valve", "valves"]):
                    return AttributeStatus.MISMATCH, "Candidate covers pipes/tubes, but query requires fittings/valves."

        # 2. Meter vs Transformer/Switchgear/Cable conflict
        if ("meter" in prod_val_lower or "gauge" in prod_val_lower) and (
            "transformer" in title_lower or "switchgear" in title_lower or "cable" in title_lower
        ):
            if "meter" not in title_lower and "gauge" not in title_lower:
                return AttributeStatus.MISMATCH, "Candidate covers heavy electrical apparatus, but query requires meters/gauges."

        # 3. Cable/Conductor vs Transformer/Switchgear conflict
        if ("cable" in prod_val_lower or "conductor" in prod_val_lower) and (
            "transformer" in title_lower or "switchgear" in title_lower or "switchboard" in title_lower
        ):
            if "cable" not in title_lower and "conductor" not in title_lower:
                return AttributeStatus.MISMATCH, "Candidate covers switchgear/transformers, but query requires cables/conductors."

        # 4. Lamp/Luminaire vs Controlgear/Ballast conflict
        if ("lamp" in prod_val_lower or "luminaire" in prod_val_lower) and (
            "controlgear" in title_lower or "ballast" in title_lower or "driver" in title_lower
        ):
            if "lamp" not in title_lower and "luminaire" not in title_lower:
                return AttributeStatus.MISMATCH, "Candidate covers auxiliary controlgear/ballast, but query requires lamps/luminaires."

        # 4b. Glass / Glazing vs Panels / Boards / Gypsum conflict
        if ("glass" in prod_val_lower or "glazing" in prod_val_lower):
            if any(w in title_lower for w in ["panel", "panels", "gypsum", "board", "boards", "insulating material"]):
                if not any(w in title_lower for w in ["safety glass", "float glass", "sheet glass", "flat glass"]):
                    return AttributeStatus.MISMATCH, "Candidate covers composite panels/boards/insulation, but query requires architectural/safety glass."

        # 5. Cable vs Overhead Bare Conductor conflict
        if any(w in prod_val_lower or w in raw_text.lower() for w in ["cable", "insulated wire", "armoured cable", "xlpe"]):
            if "overhead" in title_lower and "conductor" in title_lower and "insulated" not in title_lower:
                return AttributeStatus.MISMATCH, "Candidate covers bare overhead conductors, but query requires insulated power cables."
        if any(w in prod_val_lower or w in raw_text.lower() for w in ["acsr", "overhead transmission conductor", "overhead conductor"]):
            if "insulated cable" in title_lower or "sheathed cable" in title_lower:
                return AttributeStatus.MISMATCH, "Candidate covers insulated cables, but query requires bare overhead conductors."

        # 6. Rebar / Reinforcing Steel vs Powder / Brush / Piping conflict
        if any(w in prod_val_lower or w in raw_text.lower() for w in ["rebar", "reinforcing steel", "reinforcement bar", "deformed bar", "tmt"]):
            if any(w in title_lower for w in ["powder", "brush", "tamping", "pipe", "tube", "fitting", "conductor", "cable"]):
                return AttributeStatus.MISMATCH, "Candidate does not cover concrete reinforcement steel rebar."

        # 7. Civil/Piping vs Electrical/Power Equipment conflict
        civil_keywords = [
            "pipe", "tube", "cement", "concrete", "aggregate", "sand", "bitumen",
            "brick", "door", "window", "glazing", "tank", "rebar", "reinforcement",
            "plaster", "gypsum", "tile", "adhesive"
        ]
        electrical_keywords = [
            "transformer", "switchgear", "mccb", "acb", "cable", "conductor",
            "motor", "meter", "arrester", "luminaire", "lamp", "switch", "socket",
            "wire", "powder", "brush", "insulator", "switchboard"
        ]

        query_tokens = f"{prod_val_lower} {raw_text.lower()}"
        is_civil_query = any(k in query_tokens for k in civil_keywords)
        is_elec_query = any(k in query_tokens for k in electrical_keywords)
        is_civil_standard = any(k in title_lower for k in civil_keywords)
        is_elec_standard = any(k in title_lower for k in electrical_keywords)

        if is_civil_query and not is_elec_query and is_elec_standard and not is_civil_standard:
            return AttributeStatus.MISMATCH, f"Cross-domain mismatch: query requires civil product ('{prod_val}'), but candidate standard covers electrical equipment."
        if is_elec_query and not is_civil_query and is_civil_standard and not is_elec_standard:
            return AttributeStatus.MISMATCH, f"Cross-domain mismatch: query requires electrical product ('{prod_val}'), but candidate standard covers civil materials/structures."

        MODIFIER_WORDS = {
            "centrifugally", "cast", "spun", "iron", "steel", "mild", "high", "density", "polyethylene",
            "unplasticized", "polyvinyl", "chloride", "plastic", "copper", "aluminum", "heavy", "medium",
            "light", "hot", "rolled", "cold", "formed", "seamless", "welded", "erw", "rigid", "flexible",
            "direct", "reading", "self", "ballasted", "three", "phase", "single", "ac", "dc", "smart",
            "static", "electric", "electrical", "electronic", "thermal", "domestic", "industrial",
            "general", "service", "services", "specification", "requirements", "safety", "code", "practice",
            "supply", "procurement", "national", "standard", "type", "class", "grade",
            "pressure", "casing", "nominal", "diameter", "distribution", "drainage", "sewage", "sewerage",
            "agricultural", "potable", "drinking", "water"
        }
        prod_tokens = [t for t in re.split(r'[\s\-_/,()]+', prod_val_lower) if len(t) > 2 and t not in MODIFIER_WORDS]
        matched_tokens = [t for t in prod_tokens if t in content or re.search(r'\b' + re.escape(t) + r'(?:s|es)?\b', content)]
        if matched_tokens:
            return AttributeStatus.MATCH, f"Matched core product tokens: {matched_tokens}"

        return AttributeStatus.UNKNOWN, f"Could not positively confirm product '{prod_val}'"

    def _evaluate_material(self, mat_req: Optional[Any], title: str, scope: str, desig: str) -> AttributeStatus:
        """Evaluate material compatibility using canonical material taxonomy (Phase 4)."""
        if not mat_req:
            return AttributeStatus.UNKNOWN
        mat_val = (mat_req.get("value") or "").lower() if isinstance(mat_req, dict) else str(mat_req or "").lower()
        if not mat_val:
            return AttributeStatus.UNKNOWN

        content = f"{title} {scope}".lower()

        # Phase 4: Use canonical material taxonomy for concept-level compatibility
        query_canonical = resolve_material(mat_val)
        candidate_canonical = extract_material_from_text(f"{title} {scope}")

        if query_canonical and candidate_canonical:
            result, reason = resolve_material_compatibility(mat_val, f"{title} {scope}")
            if result == MaterialMatchResult.MATCH:
                return AttributeStatus.MATCH
            elif result == MaterialMatchResult.MISMATCH:
                return AttributeStatus.MISMATCH
            elif result == MaterialMatchResult.SAME_FAMILY:
                # Same family but different specific materials → context-dependent
                # For now treat as UNKNOWN (needs domain-specific rules)
                return AttributeStatus.UNKNOWN
            elif result == MaterialMatchResult.RELATED:
                return AttributeStatus.UNKNOWN

        # Legacy fallback: direct string matching for unresolved materials
        if mat_val and (mat_val in content or (mat_val == "upvc" and ("pvc" in content or "polyvinyl chloride" in content))):
            return AttributeStatus.MATCH

        # Legacy mutual exclusion for cable/winding insulation materials
        if any(p in mat_val for p in ["pvc", "polyvinyl chloride", "xlpe", "crosslinked polyethylene", "cross-linked"]):
            if any(c in content for c in ["cotton covered", "paper covered", "enamelled", "tamping powder"]):
                return AttributeStatus.MISMATCH
        if "cotton covered" in mat_val:
            if any(c in content for c in ["pvc insulated", "xlpe insulated", "polyvinyl chloride", "crosslinked"]):
                return AttributeStatus.MISMATCH

        return AttributeStatus.UNKNOWN

    def _evaluate_grade(self, grade_req: Optional[Any], title: str, scope: str, desig: str) -> AttributeStatus:
        if not grade_req:
            return AttributeStatus.UNKNOWN
        val = (grade_req.get("value") or "").lower() if isinstance(grade_req, dict) else str(grade_req or "").lower()
        content = f"{title} {scope}".lower()
        if val in content:
            return AttributeStatus.MATCH
        return AttributeStatus.UNKNOWN

    def _evaluate_voltage(self, volt_req: Optional[Any], title: str, scope: str, desig: str) -> AttributeStatus:
        if not volt_req:
            return AttributeStatus.UNKNOWN
        v_str = (volt_req.get("value") or "").lower() if isinstance(volt_req, dict) else str(volt_req or "").lower()
        content = f"{title} {scope}".lower()
        m_kv = re.search(r'(\d+(?:\.\d+)?)\s*kv', v_str)
        if m_kv:
            kv_val = m_kv.group(1)
            if f"{kv_val} kv" in content or f"{kv_val}kv" in content:
                return AttributeStatus.MATCH
        return AttributeStatus.UNKNOWN

    def _evaluate_capacity(self, cap_req: Optional[Any], title: str, scope: str, desig: str) -> AttributeStatus:
        if not cap_req:
            return AttributeStatus.UNKNOWN
        val = (cap_req.get("value") or "").lower() if isinstance(cap_req, dict) else str(cap_req or "").lower()
        content = f"{title} {scope}".lower()
        if val in content:
            return AttributeStatus.MATCH
        return AttributeStatus.UNKNOWN

    def _evaluate_dimensions(self, dim_req: Optional[Any], title: str, scope: str, desig: str) -> AttributeStatus:
        if not dim_req:
            return AttributeStatus.UNKNOWN
        val = (dim_req.get("value") or "").lower() if isinstance(dim_req, dict) else str(dim_req or "").lower()
        content = f"{title} {scope}".lower()
        if val in content:
            return AttributeStatus.MATCH
        return AttributeStatus.UNKNOWN

    def _evaluate_application(self, app_req: Optional[Any], title: str, scope: str, desig: str) -> AttributeStatus:
        if not app_req:
            return AttributeStatus.UNKNOWN
        val = (app_req.get("value") or "").lower() if isinstance(app_req, dict) else str(app_req or "").lower()
        content = f"{title} {scope}".lower()
        if val in content:
            return AttributeStatus.MATCH
        return AttributeStatus.UNKNOWN

    def _evaluate_environment(self, env_req: Optional[Dict[str, Any]], title: str, scope: str, desig: str) -> AttributeStatus:
        return AttributeStatus.UNKNOWN

    def _evaluate_performance(self, perf_req: Optional[Dict[str, Any]], title: str, scope: str, desig: str) -> AttributeStatus:
        return AttributeStatus.UNKNOWN

    def _evaluate_safety(self, safe_req: Optional[Dict[str, Any]], title: str, scope: str, desig: str) -> AttributeStatus:
        return AttributeStatus.UNKNOWN

    def _evaluate_installation(self, inst_req: Optional[Dict[str, Any]], title: str, scope: str, desig: str) -> AttributeStatus:
        return AttributeStatus.UNKNOWN

"""
Feature Extractors and Scoring Policy for StandSpec AI Candidate Reranker.
Provides decoupled, modular generic feature extractors and scoring policy (Phase P1-D):

12 Generic Features:
1. DesignationAlignment
2. PartSectionAlignment
3. RoleAlignment
4. ProductCategoryAlignment
5. MaterialAlignment
6. ApplicationAlignment
7. TechnologyModifierAlignment
8. ScopeBoundary
9. Specificity
10. CandidateEvidenceAvailability
11. ProcurementIntentAlignment
12. ContradictionPenalty

Each feature returns structured FeatureResult with states:
MATCH, MISMATCH, UNKNOWN, NOT_APPLICABLE
plus evidence and explainable score deltas.
"""

import re
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple


class FeatureState(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class FeatureResult:
    feature_name: str
    state: FeatureState
    evidence: str
    score_delta: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class BaseFeatureExtractor:
    """Base interface for candidate reranking feature extractors."""

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        """
        Evaluate feature and return structured FeatureResult with state, evidence, and score_delta.
        """
        raise NotImplementedError

    def extract(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Backward-compatible signal delta dictionary extractor.
        """
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        return {self.name: res.score_delta}


# ---------------------------------------------------------------------------
# Feature 1: DesignationAlignment
# ---------------------------------------------------------------------------
class DesignationAlignment(BaseFeatureExtractor):
    """
    Evaluates exact designation match, base standard alignment,
    and penalties for unrequested explicit citations.
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        desig = (candidate.get("designation") or doc.get("designation") or doc.get("id") or "").lower()
        q_lower = query_text.lower()

        base_match = re.search(r'\b(?:is\s*)?(\d+)\b', desig)
        cand_base = base_match.group(1) if base_match else None

        q_base_matches = re.findall(r'\bis\s*(\d{2,5})\b', q_lower)

        if not q_base_matches:
            return FeatureResult(
                feature_name=self.name,
                state=FeatureState.NOT_APPLICABLE,
                evidence="No explicit IS standard designation cited in query.",
                score_delta=0.0,
            )

        if cand_base and cand_base in q_base_matches:
            return FeatureResult(
                feature_name=self.name,
                state=FeatureState.MATCH,
                evidence=f"Base designation IS {cand_base} matches cited standard.",
                score_delta=10.0,
                details={"matched_base": cand_base},
            )
        else:
            return FeatureResult(
                feature_name=self.name,
                state=FeatureState.MISMATCH,
                evidence=f"Candidate IS {cand_base} differs from query cited standard(s): {q_base_matches}.",
                score_delta=-3.0,
                details={"candidate_base": cand_base, "query_bases": q_base_matches},
            )

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        deltas = {"exact_desig_match": 0.0, "scope_penalty": 0.0}
        if res.state == FeatureState.MATCH:
            deltas["exact_desig_match"] = res.score_delta
        elif res.state == FeatureState.MISMATCH:
            deltas["scope_penalty"] = res.score_delta
        return deltas


# ---------------------------------------------------------------------------
# Feature 2: PartSectionAlignment
# ---------------------------------------------------------------------------
class PartSectionAlignment(BaseFeatureExtractor):
    """
    Evaluates alignment of Part and Section numbers between query and candidate.
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        cand_text = f"{candidate.get('designation', '')} {doc.get('title', '')}".lower()
        q_lower = query_text.lower()

        q_part = re.search(r'\bpart\s*(\d+)\b', q_lower)
        cand_part = re.search(r'\bpart\s*(\d+)\b', cand_text)

        if not q_part:
            return FeatureResult(
                feature_name=self.name,
                state=FeatureState.NOT_APPLICABLE,
                evidence="Query does not specify a part number.",
                score_delta=0.0,
            )

        q_part_num = q_part.group(1)
        if cand_part:
            cand_part_num = cand_part.group(1)
            if q_part_num == cand_part_num:
                return FeatureResult(
                    feature_name=self.name,
                    state=FeatureState.MATCH,
                    evidence=f"Part {q_part_num} matches between query and candidate.",
                    score_delta=4.0,
                    details={"part": q_part_num},
                )
            else:
                return FeatureResult(
                    feature_name=self.name,
                    state=FeatureState.MISMATCH,
                    evidence=f"Part conflict: query requested Part {q_part_num} but candidate is Part {cand_part_num}.",
                    score_delta=-8.0,
                    details={"requested_part": q_part_num, "candidate_part": cand_part_num},
                )

        return FeatureResult(
            feature_name=self.name,
            state=FeatureState.UNKNOWN,
            evidence=f"Query specifies Part {q_part_num} but candidate does not declare a part.",
            score_delta=-3.0,
        )

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        if res.state == FeatureState.MATCH:
            return {"exact_desig_match": res.score_delta}
        elif res.state in (FeatureState.MISMATCH, FeatureState.UNKNOWN):
            return {"scope_penalty": res.score_delta}
        return {}


# ---------------------------------------------------------------------------
# Feature 3: RoleAlignment
# ---------------------------------------------------------------------------
class RoleAlignment(BaseFeatureExtractor):
    """
    Evaluates candidate architectural role (PRIMARY_PRODUCT, COMPONENT, TEST_METHOD,
    DESIGN_CODE, INSTALLATION_CODE, UNKNOWN_ROLE) against procurement intent.
    Prevents UNKNOWN_ROLE or auxiliary standards from being promoted to primary product.
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        from src.recommendation.role_classifier import RoleClassifier, StandardRole

        cand_role = RoleClassifier.classify(candidate)
        q_lower = query_text.lower()
        proc_intent = (req_obj or {}).get("procurement_intent") or {}
        tech_intent = proc_intent.get("technical_intent", "")
        obj_type = proc_intent.get("object_type", "")

        is_test_intent = tech_intent == "TESTING" or any(w in q_lower for w in ["test method", "methods of test", "testing", "sampling", "determination of"])
        is_code_intent = tech_intent in ("INSTALLATION", "DESIGN", "INSTALLATION_SERVICE", "DESIGN_ACTIVITY") or any(w in q_lower for w in ["code of practice", "design code", "installation code", "general construction"])

        if is_test_intent:
            if cand_role == StandardRole.TEST_METHOD:
                return FeatureResult(self.name, FeatureState.MATCH, "Test method role aligns with testing intent.", 4.0)
            elif cand_role == StandardRole.PRIMARY_PRODUCT:
                return FeatureResult(self.name, FeatureState.MISMATCH, "Product specification given for testing intent.", -2.0)
        elif is_code_intent:
            if cand_role in (StandardRole.DESIGN_CODE, StandardRole.INSTALLATION_CODE):
                return FeatureResult(self.name, FeatureState.MATCH, "Code role aligns with code of practice intent.", 3.5)
            elif cand_role == StandardRole.PRIMARY_PRODUCT:
                return FeatureResult(self.name, FeatureState.MISMATCH, "Product specification given for engineering code intent.", -1.5)
        else:
            # Default intent: Primary Product Procurement
            if cand_role == StandardRole.PRIMARY_PRODUCT:
                return FeatureResult(self.name, FeatureState.MATCH, "Primary product role aligns with supply procurement.", 3.0)
            elif cand_role == StandardRole.COMPONENT:
                return FeatureResult(self.name, FeatureState.MISMATCH, "Component standard offered for primary product requirement.", -3.5)
            elif cand_role in (StandardRole.TEST_METHOD, StandardRole.DIMENSIONAL_MOUNTING):
                return FeatureResult(self.name, FeatureState.MISMATCH, f"{cand_role.value} cannot serve as primary product specification.", -5.0)
            elif cand_role in (StandardRole.DESIGN_CODE, StandardRole.INSTALLATION_CODE):
                return FeatureResult(self.name, FeatureState.MISMATCH, "Code of practice cannot serve as physical product specification.", -3.5)
            elif cand_role == StandardRole.UNKNOWN_ROLE:
                return FeatureResult(self.name, FeatureState.UNKNOWN, "Role is unverified; cannot be promoted to primary.", -4.0)

        return FeatureResult(self.name, FeatureState.NOT_APPLICABLE, "Neutral role alignment.", 0.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        return {"role_alignment": res.score_delta}


# ---------------------------------------------------------------------------
# Feature 4: ProductCategoryAlignment
# ---------------------------------------------------------------------------
class ProductCategoryAlignment(BaseFeatureExtractor):
    """
    Evaluates product category title alignment and morphological keyword match.
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        title = (doc.get("title") or candidate.get("title") or "").lower()
        scope = (doc.get("scope") or "").lower()
        cand_all = f"{title} {scope}".lower()
        q_lower = query_text.lower()

        reqs = (req_obj or {}).get("requirements") or {}
        prod_field = reqs.get("product") or {}
        if isinstance(prod_field, str):
            prod = prod_field.lower()
        elif isinstance(prod_field, dict):
            prod = (prod_field.get("normalization") or prod_field.get("value") or "").lower()
        else:
            prod = ""

        keywords = []
        if prod:
            keywords.extend([w for w in re.findall(r'\w+', prod) if len(w) > 3])

        if not keywords:
            for w in ["transformer", "cable", "pipe", "cement", "switchgear", "circuit-breaker", "meter", "conductor", "glass", "door", "window", "aggregate", "steel"]:
                if w in q_lower:
                    keywords.append(w)

        matched = [k for k in keywords if k in cand_all]
        if matched:
            delta = 1.0 + 1.0 * len(matched)
            return FeatureResult(self.name, FeatureState.MATCH, f"Keywords matched in candidate: {matched}", delta)
        elif keywords:
            return FeatureResult(self.name, FeatureState.MISMATCH, f"None of target product keywords {keywords} found in candidate.", -2.5)

        return FeatureResult(self.name, FeatureState.UNKNOWN, "No distinct category keywords detected.", 0.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        deltas = {"title_match": 0.0, "scope_penalty": 0.0}
        if res.state == FeatureState.MATCH:
            deltas["title_match"] = res.score_delta
        elif res.state == FeatureState.MISMATCH:
            deltas["scope_penalty"] = res.score_delta
        return deltas


# ---------------------------------------------------------------------------
# Feature 5: MaterialAlignment
# ---------------------------------------------------------------------------
class MaterialAlignment(BaseFeatureExtractor):
    """
    Evaluates material grade compatibility (PVC, XLPE, HDPE, Ductile Iron, Cast Iron, Structural Steel, Timber, Rubber, Copper, Aluminium).
    """

    MATERIALS = {
        "xlpe": ["xlpe", "crosslinked polyethylene"],
        "pvc": ["pvc", "polyvinyl chloride", "upvc"],
        "hdpe": ["hdpe", "high density polyethylene", "polyethylene"],
        "ductile iron": ["ductile iron", "ductile"],
        "cast iron": ["cast iron", "spun iron"],
        "steel": ["steel", "tmt", "rebar", "reinforcement bar", "fe 500", "fe 415", "fe 550", "deformed bar", "carbon steel", "structural steel"],
        "polymer": ["polymer", "gfrp", "frp", "glass fibre reinforced polymer"],
        "copper": ["copper"],
        "aluminium": ["aluminium", "aluminum"],
        "ppc": ["pozzolana", "ppc", "fly ash"],
        "opc": ["ordinary portland", "opc"],
        "psc": ["slag cement", "psc", "slag"],
        "gypsum": ["gypsum", "plaster board"],
        "glass": ["glass", "glazing", "float glass"],
    }

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        cand_all = f"{doc.get('title', '')} {doc.get('scope', '')}".lower()
        q_lower = query_text.lower()

        # Integrate req_obj material
        reqs = (req_obj or {}).get("requirements") or {}
        mat_field = reqs.get("material") or {}
        mat_val = (mat_field.get("normalization") or mat_field.get("value") or "").lower() if isinstance(mat_field, dict) else str(mat_field or "").lower()

        detected_q_mats = []
        for mat_key, patterns in self.MATERIALS.items():
            if any(p in mat_val for p in patterns) or any(p in q_lower for p in patterns):
                detected_q_mats.append(mat_key)

        if not detected_q_mats:
            return FeatureResult(self.name, FeatureState.NOT_APPLICABLE, "No explicit material specified in query.", 0.0)

        for mat in detected_q_mats:
            patterns = self.MATERIALS[mat]
            if any(p in cand_all for p in patterns):
                return FeatureResult(self.name, FeatureState.MATCH, f"Material '{mat}' matched in candidate scope/title.", 2.5)

        # Mismatch check
        return FeatureResult(self.name, FeatureState.MISMATCH, f"Query specified material(s) {detected_q_mats} but candidate specifies different material.", -4.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        if res.state == FeatureState.MATCH:
            return {"attribute_match": res.score_delta}
        elif res.state == FeatureState.MISMATCH:
            return {"scope_penalty": res.score_delta}
        return {}


# ---------------------------------------------------------------------------
# Feature 6: ApplicationAlignment
# ---------------------------------------------------------------------------
class ApplicationAlignment(BaseFeatureExtractor):
    """
    Evaluates application domain alignment (potable water vs sewage, EHV bulk transmission vs distribution).
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        cand_all = f"{doc.get('title', '')} {doc.get('scope', '')}".lower()
        q_lower = query_text.lower()

        # Integrate req_obj application
        reqs = (req_obj or {}).get("requirements") or {}
        app_field = reqs.get("application") or {}
        app_val = (app_field.get("normalization") or app_field.get("value") or "").lower() if isinstance(app_field, dict) else str(app_field or "").lower()
        search_app = f"{app_val} {q_lower}".strip()

        # Potable water vs sewage
        if "potable" in search_app or "drinking water" in search_app:
            if any(w in cand_all for w in ["sewerage", "drainage", "industrial waste"]):
                return FeatureResult(self.name, FeatureState.MISMATCH, "Candidate covers sewage/drainage, but query requires potable water.", -5.0)
            elif "water supply" in cand_all or "potable" in cand_all:
                return FeatureResult(self.name, FeatureState.MATCH, "Candidate specifically covers water supply/potable water.", 2.0)

        # Bulk power vs distribution
        if "distribution" in search_app and "transformer" in search_app:
            if "2026" in candidate.get("designation", "") and "part 1" in candidate.get("designation", "").lower():
                return FeatureResult(self.name, FeatureState.MISMATCH, "IS 2026 is for bulk transmission power transformers, not distribution transformers.", -3.0)

        return FeatureResult(self.name, FeatureState.NOT_APPLICABLE, "Neutral application alignment.", 0.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        if res.state == FeatureState.MATCH:
            return {"attribute_match": res.score_delta}
        elif res.state == FeatureState.MISMATCH:
            return {"scope_penalty": res.score_delta}
        return {}


# ---------------------------------------------------------------------------
# Feature 7: TechnologyModifierAlignment
# ---------------------------------------------------------------------------
class TechnologyModifierAlignment(BaseFeatureExtractor):
    """
    Evaluates technology discriminators (smart vs static meters, oil-immersed vs dry type).
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        cand_all = f"{doc.get('title', '')} {doc.get('scope', '')} {candidate.get('designation', '')}".lower()
        q_lower = query_text.lower()

        # Smart meter vs static meter
        if any(w in q_lower for w in ["smart meter", "ami", "prepayment", "two-way"]):
            if "smart" in cand_all or "16444" in cand_all:
                return FeatureResult(self.name, FeatureState.MATCH, "Smart meter technology modifier matched.", 3.5)
            elif "13779" in cand_all or "static" in cand_all:
                return FeatureResult(self.name, FeatureState.MISMATCH, "Candidate is standard static meter, but smart meter was specified.", -4.0)

        # Static meter without modem
        if "static" in q_lower and not any(w in q_lower for w in ["smart", "ami"]):
            if "13779" in cand_all or "static" in cand_all:
                return FeatureResult(self.name, FeatureState.MATCH, "Static meter technology matched.", 2.5)
            elif "16444" in cand_all or "smart" in cand_all:
                return FeatureResult(self.name, FeatureState.MISMATCH, "Candidate is smart meter, but static meter was specified.", -3.0)

        return FeatureResult(self.name, FeatureState.NOT_APPLICABLE, "No technology modifier conflict.", 0.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        if res.state == FeatureState.MATCH:
            return {"attribute_match": res.score_delta}
        elif res.state == FeatureState.MISMATCH:
            return {"scope_penalty": res.score_delta}
        return {}


# ---------------------------------------------------------------------------
# Feature 8: ScopeBoundary
# ---------------------------------------------------------------------------
class ScopeBoundary(BaseFeatureExtractor):
    """
    Evaluates scope inclusion and exclusion boundaries.
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        scope = (doc.get("scope") or "").lower()
        q_lower = query_text.lower()

        if not scope:
            return FeatureResult(self.name, FeatureState.UNKNOWN, "No scope clause available.", 0.0)

        reqs = (req_obj or {}).get("requirements") or {}
        prod_field = reqs.get("product") or {}
        if isinstance(prod_field, str):
            prod = prod_field.lower()
        elif isinstance(prod_field, dict):
            prod = (prod_field.get("normalization") or prod_field.get("value") or "").lower()
        else:
            prod = ""
        target_words = [w for w in re.findall(r'\w+', prod)] if prod else [w for w in q_lower.split() if len(w) > 2]

        # Check explicit exclusions
        exclusion_patterns = [r"excludes\s+([^\.]+)", r"does\s+not\s+cover\s+([^\.]+)", r"excluding\s+([^\.]+)"]
        for p in exclusion_patterns:
            matches = re.findall(p, scope)
            for m in matches:
                for word in target_words:
                    if len(word) > 2 and word in m:
                        return FeatureResult(self.name, FeatureState.MISMATCH, f"Scope explicitly excludes '{word}': {m}", -8.0)

        # Check positive coverage
        if any(w in scope for w in ["prescribes requirements", "covers the requirements", "specifies the requirements"]):
            return FeatureResult(self.name, FeatureState.MATCH, "Candidate scope prescribes formal requirements.", 1.5)

        return FeatureResult(self.name, FeatureState.UNKNOWN, "Scope boundary indeterminate.", 0.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        deltas = {"scope_match": 0.0, "scope_penalty": 0.0}
        if res.state == FeatureState.MATCH:
            deltas["scope_match"] = res.score_delta
        elif res.state == FeatureState.MISMATCH:
            deltas["scope_penalty"] = res.score_delta
        return deltas


# ---------------------------------------------------------------------------
# Feature 9: Specificity
# ---------------------------------------------------------------------------
class Specificity(BaseFeatureExtractor):
    """
    Evaluates specification specificity (product vs general framework, pipe vs fittings).
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        desig = (candidate.get("designation") or doc.get("designation") or doc.get("id") or "").lower()
        cand_all = f"{doc.get('title', '')} {doc.get('scope', '')} {desig}".lower()
        q_lower = query_text.lower()

        # Pipe vs Fitting
        if ("pipe" in q_lower or "tube" in q_lower) and not any(k in q_lower for k in ["fitting", "fittings", "flange", "joint"]):
            if any(k in cand_all for k in ["fittings for", "pipe fittings", "flanges and", "jointing"]):
                return FeatureResult(self.name, FeatureState.MISMATCH, "Candidate specifies pipe fittings, but query requires pipes.", -4.0)

        # Smart / Prepaid vs Static Induction Meters
        if any(k in q_lower for k in ["smart", "prepaid", "ami", "two-way"]):
            if "smart" in cand_all or "16444" in desig:
                return FeatureResult(self.name, FeatureState.MATCH, "Smart meter technology matched", 3.5)
            elif "static" in cand_all or "13779" in desig:
                return FeatureResult(self.name, FeatureState.MISMATCH, "Static meter offered for smart meter query", -4.0)

        return FeatureResult(self.name, FeatureState.MATCH, "Specificity check passed.", 1.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        deltas = {"attribute_match": 0.0, "scope_penalty": 0.0}
        if res.state == FeatureState.MATCH:
            deltas["attribute_match"] = res.score_delta
        elif res.state == FeatureState.MISMATCH:
            deltas["scope_penalty"] = res.score_delta
        return deltas


# ---------------------------------------------------------------------------
# Feature 10: CandidateEvidenceAvailability
# ---------------------------------------------------------------------------
class CandidateEvidenceAvailability(BaseFeatureExtractor):
    """
    Evaluates evidence readiness (hydrated vs stub, verified scope text, active lifecycle).
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        scope = doc.get("scope") or ""
        is_hydrated = candidate.get("is_hydrated", True)

        if not is_hydrated or not scope.strip():
            return FeatureResult(self.name, FeatureState.UNKNOWN, "Candidate is an unhydrated stub without verified scope clause.", -1.5)

        return FeatureResult(self.name, FeatureState.MATCH, "Candidate is fully hydrated with verified scope clause.", 1.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        return {"scope_match": res.score_delta}


# ---------------------------------------------------------------------------
# Feature 11: ProcurementIntentAlignment
# ---------------------------------------------------------------------------
class ProcurementIntentAlignment(BaseFeatureExtractor):
    """
    Evaluates procurement tender intent alignment (product vs service vs test).
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        q_lower = query_text.lower()
        if any(w in q_lower for w in ["supply", "procurement", "purchase", "delivery"]):
            return FeatureResult(self.name, FeatureState.MATCH, "Standard procurement supply intent aligned.", 1.0)
        return FeatureResult(self.name, FeatureState.NOT_APPLICABLE, "General procurement intent.", 0.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        return {"role_alignment": res.score_delta}


# ---------------------------------------------------------------------------
# Feature 12: ContradictionPenalty
# ---------------------------------------------------------------------------
class ContradictionPenalty(BaseFeatureExtractor):
    """
    Detects cross-domain contradictions (pipe vs transformer, wire vs cement, steel vs meter).
    """

    CONTRADICTIONS = [
        (("pipe", "tubing", "conduit"), ("transformer", "substation", "switchgear", "bushing")),
        (("wire", "cable", "conductor"), ("cement", "concrete", "aggregate")),
        (("meter", "relay"), ("pipe", "rebar", "reinforcement", "structural steel")),
    ]

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        cand_all = f"{doc.get('title', '')} {doc.get('scope', '')} {candidate.get('designation', '')}".lower()
        q_lower = query_text.lower()

        for group_a, group_b in self.CONTRADICTIONS:
            q_has_a = any(w in q_lower for w in group_a)
            cand_has_b = any(w in cand_all for w in group_b)
            if q_has_a and cand_has_b:
                return FeatureResult(self.name, FeatureState.MISMATCH, f"Cross-domain conflict: query has {group_a} but candidate has {group_b}.", -10.0)

            q_has_b = any(w in q_lower for w in group_b)
            cand_has_a = any(w in cand_all for w in group_a)
            if q_has_b and cand_has_a:
                return FeatureResult(self.name, FeatureState.MISMATCH, f"Cross-domain conflict: query has {group_b} but candidate has {group_a}.", -10.0)

        return FeatureResult(self.name, FeatureState.MATCH, "No cross-domain contradiction detected.", 0.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        if res.state == FeatureState.MISMATCH:
            return {"scope_penalty": res.score_delta}
        return {}


# ---------------------------------------------------------------------------
# Feature 13: TechnicalParametersAlignment
# ---------------------------------------------------------------------------
class TechnicalParametersAlignment(BaseFeatureExtractor):
    """
    Evaluates fine-grained technical parameters (voltage, capacity, dimensions, grade)
    extracted in req_obj against candidate title, scope, and technical metadata.
    Prevents cross-voltage, cross-capacity, or cross-grade misrecommendations.
    """

    def evaluate(
        self,
        query_text: str,
        candidate: Dict[str, Any],
        req_obj: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FeatureResult:
        doc = candidate.get("document", candidate)
        cand_text = f"{doc.get('title', '')} {doc.get('scope', '')} {candidate.get('designation', '')}".lower()
        q_lower = query_text.lower()
        reqs = (req_obj or {}).get("requirements") or {}

        # 1. Voltage Evaluation
        volt_field = reqs.get("voltage") or {}
        volt_val = (volt_field.get("normalization") or volt_field.get("value") or "").lower() if isinstance(volt_field, dict) else str(volt_field or "").lower()

        # 2. Grade Evaluation
        grade_field = reqs.get("grade") or {}
        grade_val = (grade_field.get("normalization") or grade_field.get("value") or "").lower() if isinstance(grade_field, dict) else str(grade_field or "").lower()

        # 3. Capacity Evaluation
        cap_field = reqs.get("capacity") or {}
        cap_val = (cap_field.get("normalization") or cap_field.get("value") or "").lower() if isinstance(cap_field, dict) else str(cap_field or "").lower()

        matches = []
        mismatches = []

        # Voltage checks
        if volt_val or any(v in q_lower for v in ["1100 v", "1100v", "1.1 kv", "3.3 kv", "11 kv", "33 kv", "66 kv"]):
            is_lv = any(v in volt_val or v in q_lower for v in ["1100 v", "1100v", "1.1 kv", "up to and including 1100"])
            is_mv_hv = any(v in volt_val or v in q_lower for v in ["3.3 kv", "11 kv", "22 kv", "33 kv", "66 kv"])

            if is_lv:
                if any(w in cand_text for w in ["up to and including 1100 v", "up to 1100 v", "1100 v", "part 1"]):
                    matches.append("LV voltage rating (<= 1100 V)")
                elif any(w in cand_text for w in ["3.3 kv to 33 kv", "3.3 kv up to 33 kv", "part 2"]):
                    if "7098" in cand_text or "1554" in cand_text:
                        mismatches.append("Query requests LV <=1100V, but candidate is MV/HV (Part 2: 3.3 kV to 33 kV)")
            elif is_mv_hv:
                if any(w in cand_text for w in ["3.3 kv to 33 kv", "3.3 kv up to 33 kv", "part 2", "11 kv", "33 kv"]):
                    matches.append("MV/HV voltage rating (3.3 kV - 33 kV)")
                elif any(w in cand_text for w in ["up to and including 1100 v", "up to 1100 v", "1100 v", "part 1"]):
                    if "7098" in cand_text or "1554" in cand_text:
                        mismatches.append("Query requests MV/HV cable, but candidate is LV (Part 1: up to 1100 V)")

        # Grade checks (e.g. Fe 500, Fe 415, 53 grade cement)
        if grade_val or any(g in q_lower for g in ["53 grade", "43 grade", "33 grade", "fe 500", "fe 415", "fe 550"]):
            if "53 grade" in grade_val or "53 grade" in q_lower:
                if "53 grade" in cand_text or "12269" in cand_text or "269" in cand_text:
                    matches.append("53 grade cement")
                elif "43 grade" in cand_text or "8112" in cand_text or "33 grade" in cand_text:
                    mismatches.append("Query specified 53 grade, candidate is 43 or 33 grade")
            if "fe 500" in grade_val or "fe 500" in q_lower:
                if "1786" in cand_text or "fe 500" in cand_text or "high strength deformed" in cand_text:
                    matches.append("Fe 500 / High strength deformed steel rebar")

        # Capacity checks (e.g. 100 kVA, distribution vs power transformer)
        if cap_val or any(c in q_lower for c in ["100 kva", "250 kva", "500 kva", "1000 kva", "2500 kva"]):
            is_dist_cap = any(c in cap_val or c in q_lower for c in ["16 kva", "25 kva", "63 kva", "100 kva", "250 kva", "500 kva", "1000 kva", "2500 kva"])
            if is_dist_cap:
                if "1180" in cand_text or "distribution transformer" in cand_text:
                    matches.append("Distribution transformer capacity (<= 2500 kVA)")
                elif "2026" in cand_text and "part 1" in cand_text:
                    mismatches.append("Query requires distribution transformer, candidate is IS 2026 bulk power transformer")

        if mismatches:
            return FeatureResult(
                self.name,
                FeatureState.MISMATCH,
                f"Technical parameter conflict: {'; '.join(mismatches)}",
                -4.0,
                {"matches": matches, "mismatches": mismatches},
            )
        elif matches:
            delta = 2.0 + 1.0 * len(matches)
            return FeatureResult(
                self.name,
                FeatureState.MATCH,
                f"Technical parameters matched: {'; '.join(matches)}",
                delta,
                {"matches": matches, "mismatches": mismatches},
            )

        return FeatureResult(self.name, FeatureState.NOT_APPLICABLE, "No specific technical parameter discriminator evaluated.", 0.0)

    def extract(self, query_text, candidate, req_obj=None, context=None) -> Dict[str, float]:
        res = self.evaluate(query_text, candidate, req_obj=req_obj, context=context)
        if res.state == FeatureState.MATCH:
            return {"attribute_match": res.score_delta}
        elif res.state == FeatureState.MISMATCH:
            return {"scope_penalty": res.score_delta}
        return {}


# ---------------------------------------------------------------------------
# Scoring Policy
# ---------------------------------------------------------------------------
class ScoringPolicy:
    """
    Consumes structured feature results to produce an explainable
    composite logit, final calibrated probability score, and diagnostic trace.
    """

    def __init__(self, baseline_bias: float = -1.5):
        self.baseline_bias = baseline_bias

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x < -20.0:
            return 0.0
        if x > 20.0:
            return 1.0
        return 1.0 / (1.0 + math.exp(-x))

    def score(
        self,
        feature_results: List[FeatureResult],
        candidate: Dict[str, Any],
    ) -> Tuple[float, Dict[str, float], Dict[str, Any]]:
        raw_logit = self.baseline_bias
        signals = {
            "exact_desig_match": 0.0,
            "title_match": 0.0,
            "scope_match": 0.0,
            "attribute_match": 0.0,
            "role_alignment": 0.0,
            "scope_penalty": 0.0,
        }
        diagnostics = {}

        for fr in feature_results:
            diagnostics[fr.feature_name] = {
                "state": fr.state.value,
                "evidence": fr.evidence,
                "score_delta": fr.score_delta,
            }
            raw_logit += fr.score_delta

            # Map to legacy signals for backward compatibility
            fn = fr.feature_name
            if fn in ("DesignationAlignment", "PartSectionAlignment"):
                if fr.score_delta > 0:
                    signals["exact_desig_match"] += fr.score_delta
                else:
                    signals["scope_penalty"] += fr.score_delta
            elif fn == "ProductCategoryAlignment":
                if fr.score_delta > 0:
                    signals["title_match"] += fr.score_delta
                else:
                    signals["scope_penalty"] += fr.score_delta
            elif fn in ("RoleAlignment", "ProcurementIntentAlignment"):
                signals["role_alignment"] += fr.score_delta
            elif fn in ("MaterialAlignment", "ApplicationAlignment", "TechnologyModifierAlignment", "Specificity", "TechnicalParametersAlignment"):
                if fr.score_delta > 0:
                    signals["attribute_match"] += fr.score_delta
                else:
                    signals["scope_penalty"] += fr.score_delta
            elif fn in ("ScopeBoundary", "CandidateEvidenceAvailability"):
                if fr.score_delta > 0:
                    signals["scope_match"] += fr.score_delta
                else:
                    signals["scope_penalty"] += fr.score_delta
            elif fn == "ContradictionPenalty":
                signals["scope_penalty"] += fr.score_delta

        prob_score = round(self._sigmoid(raw_logit), 4)
        return prob_score, signals, diagnostics

    def explain_ranking(self, candidate: Dict[str, Any]) -> str:
        diag = candidate.get("rerank_diagnostics", {})
        lines = [f"Candidate: {candidate.get('designation')} (Score: {candidate.get('rerank_score')})"]
        for fn, info in diag.items():
            if info["score_delta"] != 0.0:
                sign = "+" if info["score_delta"] > 0 else ""
                lines.append(f"  - {fn}: [{info['state']}] {sign}{info['score_delta']} ({info['evidence']})")
        return "\n".join(lines)

    def why_ranked_above(self, cand_a: Dict[str, Any], cand_b: Dict[str, Any]) -> str:
        score_a = cand_a.get("rerank_score", 0.0)
        score_b = cand_b.get("rerank_score", 0.0)
        desig_a = cand_a.get("designation", "Candidate A")
        desig_b = cand_b.get("designation", "Candidate B")

        diag_a = cand_a.get("rerank_diagnostics", {})
        diag_b = cand_b.get("rerank_diagnostics", {})

        lines = [f"{desig_a} (Score: {score_a:.4f}) ranked above {desig_b} (Score: {score_b:.4f}) because:"]
        all_features = set(diag_a.keys()).union(diag_b.keys())
        for fn in sorted(all_features):
            delta_a = diag_a.get(fn, {}).get("score_delta", 0.0)
            delta_b = diag_b.get(fn, {}).get("score_delta", 0.0)
            diff = delta_a - delta_b
            if abs(diff) > 0.1:
                ev_a = diag_a.get(fn, {}).get("evidence", "None")
                ev_b = diag_b.get(fn, {}).get("evidence", "None")
                lines.append(f"  * {fn}: Δ {diff:+.2f} ({desig_a}: {ev_a} vs {desig_b}: {ev_b})")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backward Compatibility Aliases
# ---------------------------------------------------------------------------
DesignationAlignmentFeature = DesignationAlignment
PartSectionAlignmentFeature = PartSectionAlignment
RoleAlignmentFeature = RoleAlignment
ProductCategoryFeature = ProductCategoryAlignment
MaterialAlignmentFeature = MaterialAlignment
ApplicationAlignmentFeature = ApplicationAlignment
TechnologyModifierFeature = TechnologyModifierAlignment
ScopeCoverageFeature = ScopeBoundary
SpecificityFeature = Specificity
CandidateEvidenceFeature = CandidateEvidenceAvailability
ProcurementIntentFeature = ProcurementIntentAlignment
ContradictionPenaltyFeature = ContradictionPenalty
TechnicalParametersFeature = TechnicalParametersAlignment

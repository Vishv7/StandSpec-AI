"""
Requirement Consistency Gate — StandSpec AI (Phase 2 / Mentor Review Part 3)
Reusable contradiction detection gate evaluated early in the recommendation lifecycle.
Detects physical, electrical, material, or cross-domain specification contradictions.

Invariants:
- When a contradiction is detected, primary recommendation MUST NOT be made (primary_recommendation is None).
- decision_state is INSUFFICIENT_INFORMATION.
- Returns explicit contradiction diagnostics, reasons, and clarification guidance for procurement officers.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re


@dataclass
class ContradictionItem:
    conflict_type: str
    parameters: List[str]
    description: str
    clarification_prompt: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_type": self.conflict_type,
            "parameters": self.parameters,
            "description": self.description,
            "clarification_prompt": self.clarification_prompt,
        }


@dataclass
class ConsistencyCheckResult:
    is_consistent: bool
    contradictions: List[ContradictionItem] = field(default_factory=list)
    decision_state: Optional[str] = None
    abstention_reason: Optional[str] = None
    clarification_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_consistent": self.is_consistent,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "decision_state": self.decision_state,
            "abstention_reason": self.abstention_reason,
            "clarification_message": self.clarification_message,
        }


class RequirementConsistencyGate:
    """
    Reusable contradiction detector for procurement requirements.
    Detects within-domain parameter conflicts and cross-domain product collisions.
    """

    # ── Cross-Domain Collision Rules ──
    # Pairs of (domain_a_terms, domain_b_terms, conflict_type, description, clarification)
    CROSS_DOMAIN_RULES: List[Tuple[Tuple[str, ...], Tuple[str, ...], str, str, str]] = [
        # Pipe/Plumbing vs Electrical Equipment (Transformers, Switchgear, High-Voltage)
        (
            ("hdpe pipe", "upvc pipe", "cast iron pipe", "ductile iron pipe", "pvc pipe", "water pipe", "sewer pipe", "drainage pipe"),
            ("transformer", "distribution transformer", "switchgear", "substation", "33 kv", "33kv", "11 kv", "11kv", "xlpe insulation"),
            "CROSS_DOMAIN_PIPE_ELECTRICAL",
            "Conflicting product categories: specification combines civil/plumbing pipes with high-voltage electrical equipment or cable insulation.",
            "Please split the procurement request into separate civil piping and electrical equipment line items.",
        ),
        # Cable/Conductor vs Cement/Concrete
        (
            ("xlpe cable", "power cable", "insulated cable", "aluminium conductor", "copper conductor", "electric cable"),
            ("portland cement", "opc 43", "opc 53", "pozzolana cement", "concrete mix", "coarse aggregate"),
            "CROSS_DOMAIN_CABLE_CEMENT",
            "Conflicting product categories: specification combines insulated electric power cables with civil structural cement/aggregates.",
            "Please procure electrical cables and civil cement materials as distinct procurement packages.",
        ),
        # Energy Meter vs Structural Steel / Rebar
        (
            ("energy meter", "smart meter", "static meter", "watt-hour meter", "electricity meter"),
            ("tmt bar", "tmt rebar", "fe 500d", "fe 550d", "reinforcement steel", "structural steel"),
            "CROSS_DOMAIN_METER_STEEL",
            "Conflicting product categories: specification combines electrical energy meters with civil reinforcement steel/TMT bars.",
            "Please separate electrical metering instruments from civil structural steel requirements.",
        ),
        # Structural Steel vs Lighting / Luminaires
        (
            ("tmt bar", "tmt rebar", "fe 500", "fe 550", "structural steel beams"),
            ("led luminaire", "led lamp", "lighting fixture", "ceiling fan"),
            "CROSS_DOMAIN_STEEL_LIGHTING",
            "Conflicting product categories: specification combines civil structural steel reinforcement with electrical lighting/appliances.",
            "Please create separate line items for structural steel and lighting fixtures.",
        ),
        # Transformers vs Plumbing / Sanitary
        (
            ("distribution transformer", "power transformer", "substation transformer"),
            ("cast iron pipe", "sanitary ware", "vitrified tile", "plumbing pipe"),
            "CROSS_DOMAIN_TRANSFORMER_PLUMBING",
            "Conflicting product categories: specification combines power transformers with civil plumbing or sanitary products.",
            "Please separate transformer procurement from plumbing and building material schedules.",
        ),
    ]

    @classmethod
    def check(cls, raw_text: str, requirements: Optional[Dict[str, Any]] = None) -> ConsistencyCheckResult:
        """
        Evaluates a raw procurement requirement string and optional extracted requirements dictionary
        for technical, physical, material, or cross-domain contradictions.
        """
        contradictions: List[ContradictionItem] = []
        q_lower = raw_text.lower()

        # ── 1. Within-Domain Technical Contradictions ──

        # 1a. Cement Grade Contradictions
        has_33 = bool(re.search(r'\b(?:grade\s*33|33\s*grade)\b', q_lower))
        has_43 = bool(re.search(r'\b(?:grade\s*43|43\s*grade)\b', q_lower))
        has_53 = bool(re.search(r'\b(?:grade\s*53|53\s*grade)\b', q_lower))
        cement_grades = [g for g, present in [("33 Grade", has_33), ("43 Grade", has_43), ("53 Grade", has_53)] if present]
        if len(cement_grades) > 1:
            contradictions.append(ContradictionItem(
                conflict_type="CEMENT_GRADE_CONFLICT",
                parameters=cement_grades,
                description=f"Conflicting cement grades specified simultaneously: {', '.join(cement_grades)}.",
                clarification_prompt="Specify exactly one OPC cement grade (33, 43, or 53 Grade) per tender line item.",
            ))

        # 1b. Steel Reinforcement Grade Contradictions
        has_fe415 = bool(re.search(r'\b(?:fe\s*415[a-z]*|fe415[a-z]*)\b', q_lower))
        has_fe500 = bool(re.search(r'\b(?:fe\s*500[a-z]*|fe500[a-z]*)\b', q_lower))
        has_fe550 = bool(re.search(r'\b(?:fe\s*550[a-z]*|fe550[a-z]*)\b', q_lower))
        has_fe600 = bool(re.search(r'\b(?:fe\s*600[a-z]*|fe600[a-z]*)\b', q_lower))
        steel_grades = [g for g, present in [("Fe 415", has_fe415), ("Fe 500", has_fe500), ("Fe 550", has_fe550), ("Fe 600", has_fe600)] if present]
        if len(steel_grades) > 1:
            contradictions.append(ContradictionItem(
                conflict_type="STEEL_GRADE_CONFLICT",
                parameters=steel_grades,
                description=f"Conflicting steel reinforcement grades specified simultaneously: {', '.join(steel_grades)}.",
                clarification_prompt="Specify exactly one reinforcement steel grade (e.g., Fe 500D) per schedule item.",
            ))

        # 1c. Cement Material Incompatibility
        if "high alumina" in q_lower and any(w in q_lower for w in ["portland", "pozzolana", "slag cement", "supersulphated"]):
            contradictions.append(ContradictionItem(
                conflict_type="CEMENT_TYPE_CONFLICT",
                parameters=["High Alumina Cement", "Portland/Pozzolana/Slag Cement"],
                description="Conflicting cement types: High Alumina Cement cannot be combined with Portland or Pozzolana cement specifications.",
                clarification_prompt="Clarify whether High Alumina refractory cement or Portland/Pozzolana hydraulic cement is required.",
            ))

        # 1d. Pipe Material Incompatibility (single pipe line item)
        pipe_mats = []
        if re.search(r'\b(?:hdpe|polyethylene)\s*pipe', q_lower):
            pipe_mats.append("HDPE")
        if re.search(r'\b(?:upvc|pvc-u|pvc)\s*pipe', q_lower):
            pipe_mats.append("uPVC")
        if re.search(r'\b(?:cast iron|ductile iron|di)\s*pipe', q_lower):
            pipe_mats.append("Cast/Ductile Iron")
        if re.search(r'\b(?:concrete|rcc)\s*pipe', q_lower):
            pipe_mats.append("Concrete/RCC")
        if len(pipe_mats) > 1:
            contradictions.append(ContradictionItem(
                conflict_type="PIPE_MATERIAL_CONFLICT",
                parameters=pipe_mats,
                description=f"Conflicting pipe materials specified for single pipe line item: {', '.join(pipe_mats)}.",
                clarification_prompt="Specify a single pipe material (e.g. HDPE conforming to IS 4984 or uPVC to IS 4985).",
            ))

        # 1e. Pipe Application Incompatibility
        has_potable = bool(re.search(r'\b(?:potable|drinking water)\b', q_lower))
        has_sewage = bool(re.search(r'\b(?:sewage|sewerage|drainage|soil and waste)\b', q_lower))
        has_gas = bool(re.search(r'\b(?:gaseous fuel|gas supply|natural gas)\b', q_lower))
        if has_potable and has_sewage:
            contradictions.append(ContradictionItem(
                conflict_type="APPLICATION_CONFLICT",
                parameters=["potable water supply", "sewage/drainage"],
                description="Conflicting applications: potable water supply vs sewage/drainage specified in single piping requirement.",
                clarification_prompt="Indicate whether the pipe is designated for potable drinking water or sewage/drainage conveyance.",
            ))
        if has_potable and has_gas:
            contradictions.append(ContradictionItem(
                conflict_type="APPLICATION_CONFLICT",
                parameters=["potable water supply", "gaseous fuel"],
                description="Conflicting applications: potable water supply vs gaseous fuel conveyance specified simultaneously.",
                clarification_prompt="Clarify whether the pipes are intended for water distribution or gas supply.",
            ))

        # 1f. Meter Technology Incompatibility
        has_static = "static" in q_lower or "electronic" in q_lower
        has_induction = "induction" in q_lower or "electromechanical" in q_lower
        has_smart = "smart meter" in q_lower or "prepaid" in q_lower or "pre-payment" in q_lower
        if has_static and has_induction:
            contradictions.append(ContradictionItem(
                conflict_type="METER_TECHNOLOGY_CONFLICT",
                parameters=["static (electronic)", "induction (electromechanical)"],
                description="Conflicting meter technologies: static electronic meter vs electromechanical induction meter specified.",
                clarification_prompt="Select either static electronic meters (IS 13779 / IS 16444) or induction meters.",
            ))
        if has_smart and has_induction:
            contradictions.append(ContradictionItem(
                conflict_type="METER_TECHNOLOGY_CONFLICT",
                parameters=["smart meter", "induction meter"],
                description="Conflicting meter technologies: advanced smart meter vs obsolete induction meter specified.",
                clarification_prompt="Specify modern smart meters (IS 16444) or verify requirement.",
            ))

        # 1g. Cable Installation / Construction Incompatibility
        has_abc = bool(re.search(r'\b(?:aerial bunched|overhead cable|abc cable)\b', q_lower))
        has_ug = bool(re.search(r'\b(?:underground cable|direct buried|trench)\b', q_lower))
        if has_abc and has_ug:
            contradictions.append(ContradictionItem(
                conflict_type="INSTALLATION_CONFLICT",
                parameters=["aerial bunched (overhead)", "underground cable"],
                description="Conflicting cable installations: aerial bunched overhead cable vs underground buried cable in same clause.",
                clarification_prompt="Indicate whether overhead aerial bunched cable (IS 14255) or underground cable (IS 7098) is required.",
            ))

        # 1h. Voltage Class Incompatibility
        has_lv = bool(re.search(r'\b(?:low voltage|lt cable|up to 1100\s*v|1100v|1\.1\s*kv)\b', q_lower))
        has_ht = bool(re.search(r'\b(?:33\s*kv|33kv|66\s*kv|66kv|high tension|ht cable)\b', q_lower))
        if has_lv and has_ht:
            contradictions.append(ContradictionItem(
                conflict_type="VOLTAGE_CLASS_CONFLICT",
                parameters=["low voltage (<= 1.1 kV)", "high voltage (33 kV / 66 kV)"],
                description="Conflicting voltage classes: Low Voltage (<= 1.1 kV) specified alongside High Voltage (33 kV / 66 kV).",
                clarification_prompt="Clarify operating voltage rating (e.g. 1.1 kV for LT distribution or 33 kV for HT transmission).",
            ))

        # 1i. Glass Safety Performance Incompatibility
        has_toughened = bool(re.search(r'\b(?:toughened safety|tempered safety|laminated safety)\b', q_lower))
        has_annealed = bool(re.search(r'\b(?:annealed glass|non-safety glass|ordinary float glass)\b', q_lower))
        if has_toughened and has_annealed:
            contradictions.append(ContradictionItem(
                conflict_type="SAFETY_PERFORMANCE_CONFLICT",
                parameters=["toughened safety glass", "ordinary annealed float glass"],
                description="Conflicting safety requirements: architectural safety glass specified alongside non-safety annealed glass.",
                clarification_prompt="Confirm whether certified safety glass (IS 2553 Part 1) or ordinary float glass (IS 14900) is required.",
            ))

        # ── 2. Cross-Domain Impossible Product Combinations ──
        for terms_a, terms_b, conflict_type, desc, prompt in cls.CROSS_DOMAIN_RULES:
            match_a = [t for t in terms_a if t in q_lower]
            match_b = [t for t in terms_b if t in q_lower]
            if match_a and match_b:
                contradictions.append(ContradictionItem(
                    conflict_type=conflict_type,
                    parameters=[match_a[0], match_b[0]],
                    description=f"{desc} (Detected '{match_a[0]}' and '{match_b[0]}').",
                    clarification_prompt=prompt,
                ))

        if not contradictions:
            return ConsistencyCheckResult(
                is_consistent=True,
                contradictions=[],
                decision_state=None,
                abstention_reason=None,
                clarification_message=None,
            )

        abstention_reason = (
            "Contradictory technical specifications detected: "
            + "; ".join(c.description for c in contradictions)
        )
        clarification_msg = (
            "Please resolve the following conflicting requirements: "
            + "; ".join(c.clarification_prompt for c in contradictions)
        )

        return ConsistencyCheckResult(
            is_consistent=False,
            contradictions=contradictions,
            decision_state="INSUFFICIENT_INFORMATION",
            abstention_reason=abstention_reason,
            clarification_message=clarification_msg,
        )

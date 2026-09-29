"""
Explicit Open-World Query Contract — StandSpec AI (Phase P1-E Section 3).

The production engine must accept ANY procurement query string without
assuming a predefined template or relying on benchmark metadata.

CORE CONTRACT INVARIANTS:
1. Zero benchmark leakage: OpenWorldQuery NEVER stores or accepts benchmark IDs,
   gold standards, expected decisions, or labels.
2. Clean separation of SEARCHABLE vs RECOMMENDABLE:
   - An under-specified query (e.g. 'Supply of cable') is SEARCHABLE (retrieves candidates),
     even if not yet RECOMMENDABLE (decision layer must abstain/request review).
   - An empty query is neither searchable nor recommendable.
3. Universal input: Can be instantiated from raw text in any supported language
   (English, Hindi, Gujarati, Hinglish).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import re

FORBIDDEN_BENCHMARK_KEYS = {
    "benchmark_id",
    "gold_standards",
    "expected_decision",
    "expected_safe_decision",
    "expected_coverage_state",
    "hard_negatives",
    "benchmark_split",
    "is_gold",
    "gold_in_scope",
}


@dataclass
class OpenWorldQuery:
    """
    Authoritative runtime query object for unseen procurement queries.
    Completely isolated from evaluation benchmarks.
    """
    raw_text: str
    language: str = "en"
    procurement_object: Optional[str] = None
    object_type: str = "PRODUCT"  # PRODUCT, COMPONENT, MATERIAL, SERVICE, UNKNOWN
    technical_intent: str = "SUPPLY"  # SUPPLY, INSTALLATION, DESIGN, TESTING, PROCUREMENT
    requirements: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    requested_designations: List[str] = field(default_factory=list)
    application_context: Optional[str] = None
    query_sufficiency: str = "SUFFICIENT"  # SUFFICIENT, PARTIALLY_SPECIFIED, UNDER_SPECIFIED, AMBIGUOUS
    contradictions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.raw_text = (self.raw_text or "").strip()
        if not self.raw_text:
            raise ValueError("OpenWorldQuery raw_text cannot be empty.")
        self.validate_benchmark_isolation()

    def validate_benchmark_isolation(self) -> None:
        """Ensures no evaluation/benchmark keys leak into production query state."""
        leaked = []
        for k in FORBIDDEN_BENCHMARK_KEYS:
            if k in self.requirements or k in self.metadata:
                leaked.append(k)
        if leaked:
            raise ValueError(
                f"Benchmark isolation violation: OpenWorldQuery contains forbidden benchmark fields: {leaked}"
            )

    @property
    def is_searchable(self) -> bool:
        """
        Determines whether the query contains sufficient semantic content for candidate retrieval.
        Section 5.5: Query-sufficiency must NOT block valid product search early.
        """
        if len(self.raw_text.split()) < 2 and not self.requested_designations:
            return False
        if self.procurement_object or self.requested_designations:
            return True
        if self.requirements.get("product") or self.requirements.get("material"):
            return True
        # Even partially specified queries with meaningful technical tokens are searchable
        meaningful_tokens = [w for w in re.findall(r"\w+", self.raw_text.lower()) if len(w) > 2]
        return len(meaningful_tokens) >= 2

    @property
    def is_recommendable(self) -> bool:
        """
        Determines whether the query provides enough critical discriminators
        for the decision layer to promote a primary recommendation (vs review/abstain).
        """
        if self.query_sufficiency in ("UNDER_SPECIFIED", "AMBIGUOUS") or bool(self.contradictions):
            return False
        if not self.procurement_object and not (self.requirements.get("product") or {}).get("value"):
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the query contract to a clean dictionary."""
        return {
            "raw_text": self.raw_text,
            "language": self.language,
            "procurement_object": self.procurement_object,
            "object_type": self.object_type,
            "technical_intent": self.technical_intent,
            "requirements": self.requirements,
            "constraints": self.constraints,
            "requested_designations": self.requested_designations,
            "application_context": self.application_context,
            "query_sufficiency": self.query_sufficiency,
            "contradictions": self.contradictions,
            "metadata": self.metadata,
            "is_searchable": self.is_searchable,
            "is_recommendable": self.is_recommendable,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenWorldQuery":
        """Instantiates OpenWorldQuery from a dictionary, enforcing strict isolation."""
        leaked = [k for k in FORBIDDEN_BENCHMARK_KEYS if k in data]
        if leaked:
            raise ValueError(f"Cannot create OpenWorldQuery from benchmark data: contains {leaked}")

        return cls(
            raw_text=data["raw_text"],
            language=data.get("language", "en"),
            procurement_object=data.get("procurement_object"),
            object_type=data.get("object_type", "PRODUCT"),
            technical_intent=data.get("technical_intent", "SUPPLY"),
            requirements=data.get("requirements", {}),
            constraints=data.get("constraints", []),
            requested_designations=data.get("requested_designations", []),
            application_context=data.get("application_context"),
            query_sufficiency=data.get("query_sufficiency", "SUFFICIENT"),
            contradictions=data.get("contradictions", []),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_raw_text(cls, raw_text: str, language: str = "en") -> "OpenWorldQuery":
        """Factory method for initial raw tender clauses."""
        return cls(raw_text=raw_text, language=language)

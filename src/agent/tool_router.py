"""
StandSpec AI — Tool Router & BIS Tool Implementations (Phase P1-F Section 6)
Implements the 7 core BIS tools exposing the deterministic knowledge and evidence layer
to the LLM agent:
  1. search_standards
  2. get_standard_evidence
  3. check_applicability
  4. check_lifecycle
  5. check_regulatory
  6. check_prototype_coverage
  7. get_standard_relationships
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.agent.tool_registry import Tool, ToolRegistry
from src.recommendation.role_classifier import RoleClassifier, StandardRole
from src.recommendation.evidence_bundle import EvidencePolicy, EvidenceBundle
from src.recommendation.corpus_policy import CandidateEligibilityPolicy


class ToolRouter:
    """
    Constructs and registers the 7 official BIS tools backed by the
    StandSpecRecommendationEngine's underlying deterministic services.
    """

    def __init__(self, engine: Any, default_evaluation_date: Optional[str] = None):
        self.engine = engine
        self.default_evaluation_date = default_evaluation_date or getattr(engine, "default_evaluation_date", None)
        self.graph = engine.standards_graph or {}
        self.nodes = self.graph.get("nodes", [])
        self.edges = self.graph.get("edges", [])
        
        # Build quick node lookup index by base and full designation
        self._node_by_desig = {}
        self._node_by_base = {}
        for n in self.nodes:
            desig = n.get("designation", "").strip()
            if desig:
                self._node_by_desig[desig] = n
                base = desig.split(":")[0].strip()
                if base not in self._node_by_base:
                    self._node_by_base[base] = n

    def _resolve_node(self, designation: str) -> Optional[Dict[str, Any]]:
        """Resolves a designation to a graph node."""
        if not designation:
            return None
        d = designation.strip()
        if d in self._node_by_desig:
            return self._node_by_desig[d]
        base = d.split(":")[0].strip()
        if base in self._node_by_base:
            return self._node_by_base[base]
        # Case-insensitive / whitespace / parentheses normalized lookup
        norm_target = re.sub(r"[\(\)]", "", re.sub(r"\s+", " ", d.lower())).strip()
        for k, v in self._node_by_desig.items():
            norm_k = re.sub(r"[\(\)]", "", re.sub(r"\s+", " ", k.lower())).strip()
            norm_k_base = norm_k.split(":")[0].strip()
            if norm_k == norm_target or norm_k_base == norm_target:
                return v
        return None

    # ── 1. search_standards ──
    def tool_search_standards(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search BIS primary candidate standards via BM25 + Dense + RRF + Cross-Encoder."""
        query_text = args.get("query", "").strip()
        top_k = int(args.get("top_k", 10))
        requirements = args.get("requirements")

        if not query_text:
            return {"status": "ERROR", "error_message": "Query cannot be empty.", "candidates": []}

        # Perform candidate generation using engine's hybrid pipeline
        try:
            from src.retrieval.fusion import reciprocal_rank_fusion
            # BM25 Retrieval
            bm25_cands = self.engine.bm25_retriever.retrieve(query_text, top_k=top_k * 3)
            # Dense Retrieval
            dense_cands = self.engine.dense_retriever.retrieve(query_text, top_k=top_k * 3)
            
            # Reciprocal Rank Fusion
            fused = reciprocal_rank_fusion({"bm25": bm25_cands, "dense": dense_cands}, top_k=top_k * 3)
            
            # Graph Expansion
            expanded = self.engine.graph_expander.expand(fused, top_k=top_k * 4)

            # Rerank via Cross-Encoder
            reranked = self.engine.reranker.rerank(
                query_text,
                expanded,
                req_obj={"requirements": requirements} if requirements else None,
                top_k=top_k,
            )
        except Exception:
            # Fallback to direct scoring over primary candidates if components differ
            reranked = self.engine.primary_candidates[:top_k]

        candidates_out = []
        for rank, cand in enumerate(reranked[:top_k], start=1):
            role_enum = RoleClassifier.classify(cand)
            desig = cand.get("designation")
            title = cand.get("title")
            dept = cand.get("primary_department") or (cand.get("source_departments") or ["UNKNOWN"])[0]
            
            candidates_out.append({
                "rank": rank,
                "designation": desig,
                "title": title,
                "role": role_enum.value,
                "department": dept,
                "retrieval_score": round(float(cand.get("rrf_score", cand.get("score", 1.0 / rank))), 4),
                "is_primary_eligible": CandidateEligibilityPolicy.is_primary_candidate(cand),
                "candidate_status": cand.get("candidate_status", "ELIGIBLE"),
            })

        return {
            "status": "SUCCESS",
            "query": query_text,
            "count": len(candidates_out),
            "candidates": candidates_out,
        }

    # ── 2. get_standard_evidence ──
    def tool_get_standard_evidence(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch structured EvidenceBundle for a specific Indian Standard."""
        desig = args.get("designation", "").strip()
        node = self._resolve_node(desig)
        if not node:
            return {
                "status": "NOT_FOUND",
                "designation": desig,
                "error_message": f"Standard '{desig}' not found in indexed BIS knowledge graph.",
                "evidence": None,
            }

        bundle = EvidenceBundle.from_node(node)
        return {
            "status": "SUCCESS",
            "designation": node.get("designation"),
            "evidence": bundle.to_dict(),
        }

    # ── 3. check_applicability ──
    def tool_check_applicability(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate technical applicability of a standard against query requirements."""
        desig = args.get("designation", "").strip()
        node = self._resolve_node(desig)
        if not node:
            return {
                "status": "NOT_FOUND",
                "designation": desig,
                "applicability_state": "UNKNOWN",
                "error_message": f"Standard '{desig}' not found in knowledge graph.",
            }

        requirements = args.get("requirements")
        query_text = args.get("query", "")
        if not requirements and query_text:
            ext_res = self.engine.extractor.extract(query_text)
            requirements = ext_res.get("requirements", {})
        elif not requirements:
            requirements = {}

        norm_reqs = {
            "requirements": requirements,
            "raw_text": query_text or " ".join(str(v.get("value", "")) for v in requirements.values() if isinstance(v, dict)),
        }
        app_res = self.engine.applicability_engine.evaluate_applicability(
            candidate=node,
            normalized_requirements=norm_reqs,
        )
        app_state = app_res.get("state") or app_res.get("applicability_state", "UNKNOWN")
        
        return {
            "status": "SUCCESS",
            "designation": node.get("designation"),
            "applicability_state": app_state,
            "matched_attributes": app_res.get("matched_attributes", []),
            "mismatched_attributes": app_res.get("mismatched_attributes", []),
            "unknown_attributes": app_res.get("unknown_attributes", []),
            "rejection_reason": app_res.get("rejection_reason"),
            "evidence_summary": app_res.get("evidence_summary"),
        }

    # ── 4. check_lifecycle ──
    def tool_check_lifecycle(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check active/superseded/withdrawn lifecycle status as of evaluation date."""
        desig = args.get("designation", "").strip()
        eval_date = args.get("evaluation_date") or self.default_evaluation_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lifecycle_res = self.engine.lifecycle_gate.resolve_edition(candidate_designation=desig, evaluation_date=eval_date)
        return {
            "status": "SUCCESS",
            "designation": desig,
            "lifecycle_state": lifecycle_res.get("lifecycle_state", "UNKNOWN"),
            "recommended_edition": lifecycle_res.get("recommended_edition"),
            "superseded_by": lifecycle_res.get("superseding_edition"),
            "is_superseded": lifecycle_res.get("is_superseded", False),
            "amendment_notes": lifecycle_res.get("amendment_notes"),
            "temporal_validity": lifecycle_res.get("temporal_validity", {}),
        }

    # ── 5. check_regulatory ──
    def tool_check_regulatory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check statutory mandate status (QCO / CRS) without false non-mandatory claims."""
        desig = args.get("designation", "").strip()
        eval_date = args.get("evaluation_date") or self.default_evaluation_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        query_context = args.get("query_context") or {}
        
        reg_res = self.engine.regulatory_gate.evaluate_regulatory_status(
            standard_designation=desig,
            evaluation_date=eval_date,
            evaluation_context=str(query_context.get("product") or ""),
        )
        reg_state = reg_res.get("regulatory_state", "NOT_VERIFIED_IN_CURRENT_CORPUS")
        
        # Strict legal statement construction (cannot say 'not mandatory' if unverified)
        if reg_state == "MANDATORY_CONFIRMED":
            qco = reg_res.get("order_number") or reg_res.get("qco_order") or "QCO"
            statement = f"Statutory Mandate: MANDATORY under Gazette Order {qco}."
        elif reg_state in ("NOT_VERIFIED_IN_CURRENT_CORPUS", "MANDATE_NOT_FOUND_IN_SEARCHED_SOURCES", "UNVERIFIED", "UNKNOWN"):
            statement = "Statutory Mandate: Regulatory mandatory status was not verified in the current regulatory corpus."
        elif reg_state == "CONFLICTING_EVIDENCE":
            statement = "Statutory Mandate: Conflicting regulatory evidence prevents a verified mandate conclusion."
        else:
            statement = f"Statutory Mandate: {reg_state}."

        return {
            "status": "SUCCESS",
            "designation": desig,
            "regulatory_state": reg_state,
            "is_mandatory": reg_res.get("is_mandatory", False),
            "order_number": reg_res.get("order_number"),
            "authority": reg_res.get("authority"),
            "gazette_reference": reg_res.get("gazette_reference"),
            "effective_date": reg_res.get("effective_date"),
            "statement": statement,
        }

    # ── 6. check_prototype_coverage ──
    def tool_check_prototype_coverage(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Verify whether standard or department is within current CED + ETD prototype scope."""
        dept = args.get("department")
        desig = args.get("designation")
        
        from src.recommendation.corpus_policy import PrototypeCoveragePolicy
        if not dept and desig:
            node = self._resolve_node(desig)
            if node:
                dept = PrototypeCoveragePolicy.resolve_department(node)

        is_in_scope = bool(dept and dept.upper() in PrototypeCoveragePolicy.SUPPORTED_PRIMARY_DEPARTMENTS)
        coverage_state = "IN_PROTOTYPE_COVERAGE" if is_in_scope else "OUTSIDE_PROTOTYPE_COVERAGE"
        
        return {
            "status": "SUCCESS",
            "coverage_state": coverage_state,
            "department": dept,
            "prototype_departments": list(PrototypeCoveragePolicy.SUPPORTED_PRIMARY_DEPARTMENTS),
            "explanation": "Current prototype strictly indexes Civil Engineering (CED) and Electrotechnical (ETD) standards.",
        }

    # ── 7. get_standard_relationships ──
    def tool_get_standard_relationships(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch parts, test methods, components, and superseding standards for a designation."""
        desig = args.get("designation", "").strip()
        if not desig:
            return {"status": "ERROR", "error_message": "Designation required."}

        base_target = desig.split(":")[0].strip()
        
        supersedes = []
        superseded_by = []
        parts = []
        test_methods = []
        supporting_standards = []
        components = []
        related = []

        for e in self.edges:
            src = e.get("source", "")
            tgt = e.get("target", "")
            rel = e.get("relation") or e.get("type") or ""

            if src.startswith(base_target) or tgt.startswith(base_target):
                other = tgt if src.startswith(base_target) else src
                if rel in ("SUPERSEDES", "REPLACES"):
                    if src.startswith(base_target):
                        supersedes.append(other)
                    else:
                        superseded_by.append(other)
                elif "PART" in rel or "SECTION" in rel:
                    parts.append(other)
                elif "TEST" in rel or "METHOD" in rel:
                    test_methods.append(other)
                elif "MOUNTING" in rel or "DIMENSION" in rel or "GUIDE" in rel:
                    supporting_standards.append(other)
                elif "COMPONENT" in rel or "FITTING" in rel:
                    components.append(other)
                else:
                    related.append(other)

        return {
            "status": "SUCCESS",
            "designation": desig,
            "relationships": {
                "supersedes": list(set(supersedes)),
                "superseded_by": list(set(superseded_by)),
                "parts": list(set(parts)),
                "test_methods": list(set(test_methods)),
                "supporting_standards": list(set(supporting_standards)),
                "components": list(set(components)),
                "related": list(set(related)),
            },
        }

    def build_registry(self) -> ToolRegistry:
        """Constructs and populates ToolRegistry with all 7 official tools."""
        registry = ToolRegistry()

        registry.register(Tool(
            name="search_standards",
            description="Search BIS standards catalog for candidates matching procurement requirements using BM25, dense retrieval, RRF, and cross-encoder reranking.",
            input_schema={
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Procurement requirement search clause"},
                    "top_k": {"type": "integer", "default": 10, "description": "Maximum number of candidate standards to return"},
                    "requirements": {"type": "object", "description": "Optional structured requirements dictionary"},
                },
            },
            output_schema={"type": "object"},
            handler=self.tool_search_standards,
        ))

        registry.register(Tool(
            name="get_standard_evidence",
            description="Fetch comprehensive EvidenceBundle for an Indian Standard (identity, scope text, inclusions, exclusions, role, lifecycle, provenance).",
            input_schema={
                "type": "object",
                "required": ["designation"],
                "properties": {
                    "designation": {"type": "string", "description": "Indian Standard designation (e.g. 'IS 4984:2016')"},
                },
            },
            output_schema={"type": "object"},
            handler=self.tool_get_standard_evidence,
        ))

        registry.register(Tool(
            name="check_applicability",
            description="Evaluate technical applicability of a candidate standard against procurement requirements (per-attribute match/mismatch/unknown).",
            input_schema={
                "type": "object",
                "required": ["designation"],
                "properties": {
                    "designation": {"type": "string", "description": "Target standard designation"},
                    "query": {"type": "string", "description": "Raw procurement query string"},
                    "requirements": {"type": "object", "description": "Normalized requirements dictionary"},
                },
            },
            output_schema={"type": "object"},
            handler=self.tool_check_applicability,
        ))

        registry.register(Tool(
            name="check_lifecycle",
            description="Check lifecycle status of a standard (ACTIVE_VALID, SUPERSEDED, WITHDRAWN, FUTURE_NOT_VALID) as of contemporary procurement date.",
            input_schema={
                "type": "object",
                "required": ["designation"],
                "properties": {
                    "designation": {"type": "string", "description": "Target standard designation"},
                    "evaluation_date": {"type": "string", "description": "ISO date YYYY-MM-DD for lifecycle check (default 2026-07-15)"},
                },
            },
            output_schema={"type": "object"},
            handler=self.tool_check_lifecycle,
        ))

        registry.register(Tool(
            name="check_regulatory",
            description="Check statutory mandate status under official gazette Quality Control Orders (QCO) or Compulsory Registration Scheme (CRS).",
            input_schema={
                "type": "object",
                "required": ["designation"],
                "properties": {
                    "designation": {"type": "string", "description": "Target standard designation"},
                    "query_context": {"type": "object", "description": "Optional procurement context"},
                },
            },
            output_schema={"type": "object"},
            handler=self.tool_check_regulatory,
        ))

        registry.register(Tool(
            name="check_prototype_coverage",
            description="Check if a procurement object or standard belongs to current prototype scope (Civil Engineering CED + Electrotechnical ETD only).",
            input_schema={
                "type": "object",
                "properties": {
                    "designation": {"type": "string", "description": "Standard designation"},
                    "department": {"type": "string", "description": "Department code (e.g. CED, ETD, MED, TXD)"},
                },
            },
            output_schema={"type": "object"},
            handler=self.tool_check_prototype_coverage,
        ))

        registry.register(Tool(
            name="get_standard_relationships",
            description="Fetch graph relationships (parts, test methods, mountings, components, superseding standards) for a candidate.",
            input_schema={
                "type": "object",
                "required": ["designation"],
                "properties": {
                    "designation": {"type": "string", "description": "Standard designation"},
                },
            },
            output_schema={"type": "object"},
            handler=self.tool_get_standard_relationships,
        ))

        return registry

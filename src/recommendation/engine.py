"""
End-to-End Procurement Recommendation Engine — StandSpec AI (Layer 5 Recommender Pipeline)
Implements the defensive recommendation workflow:
Raw Tender Text
  ↓
Requirement Extraction (Phase 6 / V1.3 with offsets & provenance)
  ↓
Primary Candidate Corpus Retrieval & RRF Fusion (Phases 8-10)
  ↓
Cycle-Safe Graph Expansion into Context Pack (Phase 11)
  ↓
Cross-Encoder Candidate Reranking (Phase 12)
  ↓
Technical Applicability Gating: Per-Attribute MATCH/MISMATCH (Phase 13)
  ↓
Lifecycle Edition Chain Resolution (Phase 14)
  ↓
Regulatory Gate with Gazette Provenance (Phase 15)
  ↓
Calibrated Selective Abstention Policy (Phase 16)
"""

import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from src.version import ENGINE_VERSION, RELEASE_ID
from src.extraction.requirement_extractor import RequirementExtractor
from src.llm.structured_extractor import BoundedStructuredExtractor
from src.llm.explanation import EvidenceGroundedExplainer
from src.llm.provider import get_llm_provider
from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import DenseRetriever, DeterministicSemanticProjection
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.graph_expansion import GraphCandidateExpander
from src.retrieval.cross_encoder import CrossEncoderReranker, RuleBasedReranker
from src.retrieval.designation_resolver import DesignationResolver
from src.recommendation.applicability_engine import TechnicalApplicabilityEngine, ApplicabilityState
from src.recommendation.lifecycle_gate import LifecycleGate
from src.recommendation.regulatory_gate import RegulatoryGate
from src.recommendation.role_classifier import RoleClassifier, StandardRole
from src.recommendation.evidence_bundle import (
    EvidenceBundle,
    EvidenceItem,
    EvidencePolicy,
    ClaimType,
    EvidenceGapCode,
)
from src.calibration.policy import SelectiveAbstentionPolicy
from src.recommendation.consistency_gate import RequirementConsistencyGate


class StandSpecRecommendationEngine:
    """
    End-to-End Procurement Recommendation Engine for Indian Standards (BIS).
    Enforces corpus segregation, per-attribute applicability grounding, and calibrated abstention.
    """

    ENGINE_VERSION = ENGINE_VERSION

    @classmethod
    def from_release(
        cls,
        release_manifest_path: Optional[str] = None,
        graph_path: Optional[str] = None,
        retriever_mode: str = "hybrid_deterministic",
        reranker_mode: str = "rule_based",
        tau_recommend: Optional[float] = None,
        tau_min: Optional[float] = None,
        delta_margin: Optional[float] = None,
        default_evaluation_date: Optional[str] = None,
    ) -> "StandSpecRecommendationEngine":
        """
        Production Factory: Instantiates the engine directly from the authoritative
        release manifest and knowledge graph artifacts (P1-A).
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        manifest_p = (
            Path(release_manifest_path)
            if release_manifest_path
            else (project_root / "data" / "manifests" / "standspec_prototype_release.json")
        )

        if not graph_path and manifest_p.exists():
            with open(manifest_p, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            rel_graph = manifest_data.get("artifacts", {}).get("knowledge_graph", {}).get("path")
            if rel_graph:
                graph_path = str(project_root / rel_graph)

        if not graph_path:
            graph_path = str(project_root / "data" / "processed" / "standards_graph.json")

        graph_p = Path(graph_path)
        if not graph_p.exists():
            raise FileNotFoundError(f"Knowledge graph not found at {graph_path}. Cannot initialize production engine.")

        with open(graph_p, "r", encoding="utf-8") as f:
            graph_data = json.load(f)

        return cls(
            standards_graph=graph_data,
            retriever_mode=retriever_mode,
            reranker_mode=reranker_mode,
            tau_recommend=tau_recommend,
            tau_min=tau_min,
            delta_margin=delta_margin,
            default_evaluation_date=default_evaluation_date,
        )

    def __init__(
        self,
        standards_graph: Optional[dict] = None,
        retriever_mode: str = "hybrid_deterministic",
        reranker_mode: str = "rule_based",
        auto_load_default: bool = False,
        strict_init: bool = False,
        tau_recommend: Optional[float] = None,
        tau_min: Optional[float] = None,
        delta_margin: Optional[float] = None,
        default_evaluation_date: Optional[str] = None,
    ):
        self.retriever_mode = retriever_mode
        self.reranker_mode = reranker_mode
        self.default_evaluation_date = default_evaluation_date
        self._lifecycle_cache: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}
        self._regulatory_cache: Dict[Tuple[str, Optional[str], Optional[str]], Dict[str, Any]] = {}
        self._nodes_by_desig: Dict[str, Dict[str, Any]] = {}

        if standards_graph is None and auto_load_default:
            project_root = Path(__file__).resolve().parent.parent.parent
            def_graph = project_root / "data" / "processed" / "standards_graph.json"
            if def_graph.exists():
                with open(def_graph, "r", encoding="utf-8") as f:
                    standards_graph = json.load(f)

        if standards_graph is None:
            if strict_init:
                raise ValueError("Engine initialized with empty standards_graph in strict mode.")
            logging.getLogger("StandSpecRecommendationEngine").warning(
                "StandSpecRecommendationEngine initialized without a standards_graph. "
                "Corpus is empty; use StandSpecRecommendationEngine.from_release() for production."
            )

        self.llm_provider = get_llm_provider()
        self.extractor = BoundedStructuredExtractor(llm_provider=self.llm_provider)
        self.explainer = EvidenceGroundedExplainer(llm_provider=self.llm_provider)
        self.bm25_retriever = BM25Retriever()
        if retriever_mode in ("dense_neural", "hybrid_neural"):
            self.dense_retriever = DenseRetriever(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        else:
            self.dense_retriever = DenseRetriever()
        self.graph_expander = GraphCandidateExpander(standards_graph) if standards_graph else GraphCandidateExpander()
        self.reranker = CrossEncoderReranker()
        self.applicability_engine = TechnicalApplicabilityEngine()
        self.lifecycle_gate = LifecycleGate(standards_graph) if standards_graph else LifecycleGate()
        self.regulatory_gate = RegulatoryGate()
        self.abstention_policy = SelectiveAbstentionPolicy(
            tau_recommend=tau_recommend if tau_recommend is not None else 0.40,
            tau_min=tau_min if tau_min is not None else 0.35,
            delta_margin=delta_margin if delta_margin is not None else 0.04,
        )
        self.designation_resolver = DesignationResolver(standards_graph) if standards_graph else DesignationResolver()
        self.consistency_gate = RequirementConsistencyGate()

        self.standards_graph = standards_graph
        self.primary_candidates: List[Dict[str, Any]] = []
        self.supporting_context: List[Dict[str, Any]] = []
        self.external_references: List[Dict[str, Any]] = []
        self.graph_release_id: str = "STANDSPEC_CED_ETD_GRAPH_V2_0"

        if standards_graph:
            self.index_graph(standards_graph)

    def index_graph(self, standards_graph: dict):
        """
        Segregates graph nodes into distinct corpora and indexes primary candidates.
        Corpus segregation law:
          - PRIMARY_CANDIDATE_CORPUS: Product specifications & design codes (ELIGIBLE).
          - SUPPORTING_CONTEXT_CORPUS: Test methods, material references, codes of practice (SUPPORTING_ONLY).
          - EXTERNAL_REFERENCE_CORPUS: Foreign/international standards (ISO, IEC, ASTM).
        """
        self.standards_graph = standards_graph
        self.graph_release_id = standards_graph.get("release_id", "graph-v1.2.1")
        nodes = standards_graph.get("nodes", [])

        # Segregate corpora via semantic CandidateEligibilityPolicy (Phase P1-E Section 6)
        from src.recommendation.corpus_policy import CandidateEligibilityPolicy

        self.primary_candidates = [n for n in nodes if CandidateEligibilityPolicy.is_primary_candidate(n)]

        # Fallback if primary_candidates empty (e.g. synthetic test graph)
        if not self.primary_candidates:
            self.primary_candidates = [
                n for n in nodes
                if n.get("node_type") != "EXTERNAL_STANDARD"
                and n.get("candidate_status") != "CONTEXT_ONLY"
            ]
        if not self.primary_candidates:
            self.primary_candidates = nodes

        self.supporting_context = [n for n in nodes if CandidateEligibilityPolicy.is_supporting_context(n)]
        self.external_references = [n for n in nodes if CandidateEligibilityPolicy.is_external_reference(n)]

        # Index PRIMARY candidates for direct retrieval
        self.bm25_retriever.index_documents(self.primary_candidates)
        self.dense_retriever.index_documents(self.primary_candidates)

        # Graph expander, lifecycle gate, and designation resolver have full graph view
        self.graph_expander.load_graph(standards_graph)
        self.lifecycle_gate.load_graph(standards_graph)
        self.designation_resolver.index_graph(standards_graph)

        # Index nodes by designation and base designation for O(1) lookups
        self._nodes_by_desig = {}
        for n in nodes:
            d = n.get("designation") or n.get("id")
            if d:
                self._nodes_by_desig[d] = n
                base = re.sub(r':\d{4}$', '', d).strip()
                if base not in self._nodes_by_desig:
                    self._nodes_by_desig[base] = n

    def _find_graph_node(self, desig: str) -> Optional[Dict[str, Any]]:
        """Look up graph node by full designation or base designation in O(1)."""
        if not desig or not self.standards_graph:
            return None
        if desig in self._nodes_by_desig:
            return self._nodes_by_desig[desig]
        base = re.sub(r':\d{4}$', '', desig).strip()
        if base in self._nodes_by_desig:
            return self._nodes_by_desig[base]
        # Fallback linear search if index missed
        for n in self.standards_graph.get("nodes", []):
            d = n.get("designation") or n.get("id") or ""
            if d == desig or re.sub(r':\d{4}$', '', d).strip() == base:
                return n
        return None

    def recommend(
        self,
        raw_text: str,
        query_id: str = None,
        evaluation_date: str = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Execute full recommendation pipeline on procurement text.
        Conforms strictly to schemas/recommendation_result.schema.json.
        """
        eval_date = evaluation_date or self.default_evaluation_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Step 1: Procurement Requirement Extraction
        req_obj = self.extractor.extract(raw_text, query_id=query_id or "Q_AUTO")
        requirements = req_obj.get("requirements", {})
        missing_discriminators = req_obj.get("missing_discriminators", [])
        product_status = req_obj.get("product_status", "EXTRACTED")

        # Formulate search query using normalized target product & scope terms
        target_prod = (
            (requirements.get("product") or {}).get("normalization")
            or (requirements.get("product") or {}).get("value")
            or ""
        )
        mat = (
            (requirements.get("material") or {}).get("normalization")
            or (requirements.get("material") or {}).get("value")
            or ""
        )
        volt = (
            (requirements.get("voltage") or {}).get("normalization")
            or (requirements.get("voltage") or {}).get("value")
            or ""
        )
        cap = (
            (requirements.get("capacity") or {}).get("normalization")
            or (requirements.get("capacity") or {}).get("value")
            or ""
        )
        app = (
            (requirements.get("application") or {}).get("value")
            or ""
        )
        grade = (
            (requirements.get("grade") or {}).get("normalization")
            or (requirements.get("grade") or {}).get("value")
            or ""
        )
        dims = (
            (requirements.get("dimensions") or {}).get("normalization")
            or (requirements.get("dimensions") or {}).get("value")
            or ""
        )
        inst = (
            (requirements.get("installation") or {}).get("value")
            or ""
        )
        tech = (
            (requirements.get("technology") or {}).get("value")
            or ""
        )

        acronyms = []
        full_lower = f"{mat} {raw_text}".lower()
        if "polyvinyl chloride" in full_lower or "pvc" in full_lower:
            acronyms.extend(["pvc", "upvc", "unplasticized"])
        if "polyethylene" in full_lower or "hdpe" in full_lower:
            acronyms.extend(["hdpe", "pe"])
        if "mild steel" in full_lower or "steel tubes" in target_prod.lower():
            acronyms.extend(["erw", "tubulars"])
        if "cast iron" in full_lower or "spun iron" in full_lower:
            acronyms.extend(["spun iron", "centrifugally cast"])
        if "ductile iron" in full_lower or "di pipe" in full_lower:
            acronyms.extend(["ductile iron", "spun ductile", "centrifugally cast"])
        if any(w in full_lower for w in ["steel", "rebar", "fe 500", "fe 415", "tmt", "reinforcement"]):
            acronyms.extend(["high strength deformed steel bars wires reinforcement concrete"])
        if "piano switch" in full_lower or "flush-mounted" in full_lower:
            acronyms.extend(["switches domestic similar purposes"])
        if "gypsum" in full_lower or "plaster board" in full_lower:
            acronyms.extend(["gypsum plaster boards"])
        if "rapid hardening" in full_lower:
            acronyms.extend(["rapid hardening portland cement"])
        if "coarse aggregate" in full_lower or "crushed stone" in full_lower:
            acronyms.extend(["coarse fine aggregate concrete"])
        acronym_str = " ".join(acronyms)

        # Retain all technical discriminators in focused_query so BM25 and dense retrieval never drop them
        focused_parts = [p for p in [target_prod, mat, grade, volt, cap, dims, inst, tech, app, acronym_str] if p]
        focused_query = " ".join(focused_parts).strip()
        enriched_query = f"{focused_query} {raw_text}".strip()

        # Step 1.5: Exact Designation Intent Detection
        detected_desigs = self.designation_resolver.detect_designations(raw_text)
        explicit_candidates = []
        if detected_desigs:
            for det in detected_desigs:
                cand_node = self.designation_resolver.resolve_candidate(det)
                if cand_node:
                    c_dict = dict(cand_node)
                    c_dict["retrieval_source"] = "exact_designation"
                    c_dict["rerank_score"] = 1.0
                    c_dict["rerank_signals"] = {"exact_designation_matched": 5.0}
                    explicit_candidates.append(c_dict)

        # Step 1.6: Boundary, Consistency & Query-Sufficiency Checks (Mentor Review Part 3)
        consistency_gate = getattr(self, "consistency_gate", None)
        if consistency_gate is None:
            from src.recommendation.consistency_gate import RequirementConsistencyGate
            consistency_gate = RequirementConsistencyGate()
            self.consistency_gate = consistency_gate

        consistency_result = consistency_gate.check(raw_text, requirements=req_obj.get("requirements"))
        has_contradictions = (not consistency_result.is_consistent) or bool(req_obj.get("contradictions"))

        outside_keywords = [
            "banana", "bananas", "fruit", "fruits", "vegetable", "mango", "grain", "wheat", "rice",
            "spice", "spices", "milk", "dairy", "meat", "tea", "coffee", "food processing",
            "cotton", "silk", "wool", "textile", "garment", "apparel", "yarn",
            "crude oil", "aviation turbine fuel", "petroleum refining",
            "pharmaceutical", "tablet", "injections", "vaccine", "medical implant", "surgical",
            "mri", "magnetic resonance", "superconducting magnet",
            "satellite", "ku-band", "ground station",
        ]
        raw_lower = raw_text.lower()
        is_outside_domain = (
            any(w in raw_lower for w in outside_keywords)
            and not detected_desigs
            and not any(w in raw_lower for w in ["cable", "transformer", "pipe", "switchgear", "cement", "concrete", "structural steel", "glass", "door", "window", "meter", "conductor", "fuse", "relay", "breaker", "tube", "tubular", "mortar", "brick", "aggregate", "sand"])
        )

        query_sufficiency = req_obj.get("query_sufficiency", {})
        is_query_underspecified = (
            query_sufficiency.get("state") == "INSUFFICIENT"
            and not detected_desigs
            and not is_outside_domain
        )

        # Step 2: Retrieval over PRIMARY CANDIDATE CORPUS (Phase P1-E Section 5.5)
        # Search whenever query is not outside domain and contains meaningful search tokens.
        # Query under-specification must NOT block candidate retrieval early;
        # the decision layer will decide whether evidence is sufficient to recommend or abstain.
        bm25_candidates = []
        dense_candidates = []

        is_searchable = not is_outside_domain and (len(raw_text.split()) >= 2 or bool(detected_desigs))
        if is_searchable:
            if self.retriever_mode in ("bm25_only", "hybrid_deterministic", "hybrid_neural"):
                # Use enriched query to prevent dropping critical discriminators and units from raw_text (R1.3)
                bm25_query = enriched_query if enriched_query else (focused_query or raw_text)
                bm25_candidates = self.bm25_retriever.retrieve(
                    bm25_query, top_k=25
                )

            if self.retriever_mode in ("dense_only", "dense_deterministic", "dense_neural", "hybrid_deterministic", "hybrid_neural"):
                dense_candidates = self.dense_retriever.retrieve(enriched_query, top_k=25)

        # Step 3: Selection / Fusion
        if self.retriever_mode == "bm25_only":
            fused_candidates = bm25_candidates[:20]
        elif self.retriever_mode in ("dense_only", "dense_deterministic", "dense_neural"):
            fused_candidates = dense_candidates[:20]
        else:
            fused_candidates = reciprocal_rank_fusion(
                {"bm25": bm25_candidates, "dense": dense_candidates},
                k=60,
                weights={"bm25": 1.2, "dense": 0.8},
                top_k=20,
            )

        # Build Channel Diagnostics Index (P1-B Step 3)
        channel_diagnostics: Dict[str, Dict[str, Any]] = {}
        for item in bm25_candidates:
            des = item.get("designation") or (item.get("document") or {}).get("designation")
            if des:
                channel_diagnostics.setdefault(des, {})["bm25_rank"] = item.get("rank")
                channel_diagnostics[des]["bm25_score"] = item.get("score")

        for item in dense_candidates:
            des = item.get("designation") or (item.get("document") or {}).get("designation")
            if des:
                channel_diagnostics.setdefault(des, {})["dense_rank"] = item.get("rank")
                channel_diagnostics[des]["dense_score"] = item.get("score", item.get("dense_score"))

        for item in fused_candidates:
            des = item.get("designation") or (item.get("document") or {}).get("designation")
            if des:
                channel_diagnostics.setdefault(des, {})["rrf_rank"] = item.get("rank")
                channel_diagnostics[des]["rrf_score"] = item.get("rrf_score")

        # Step 4: Graph Expansion (expands primary candidates with family parts)
        expanded_candidates = self.graph_expander.expand(fused_candidates, top_k=25)

        # Prepend explicit designation candidates at rank 1
        if explicit_candidates:
            explicit_desigs = {ec.get("designation") for ec in explicit_candidates}
            expanded_candidates = explicit_candidates + [
                c for c in expanded_candidates
                if (c.get("designation") or (c.get("document") or {}).get("designation")) not in explicit_desigs
            ]

        # Attach retrieval channel diagnostics to all candidates
        for c in expanded_candidates:
            des = c.get("designation") or (c.get("document") or {}).get("designation")
            diag = channel_diagnostics.get(des, {})
            c["retrieval_diagnostics"] = {
                "bm25_rank": diag.get("bm25_rank"),
                "bm25_score": diag.get("bm25_score"),
                "dense_rank": diag.get("dense_rank"),
                "dense_score": diag.get("dense_score"),
                "rrf_rank": diag.get("rrf_rank"),
                "rrf_score": diag.get("rrf_score"),
                "retrieval_source": c.get("retrieval_source", "exact_designation" if c in explicit_candidates else "hybrid"),
            }

        # Step 5: Candidate Reranking
        if self.reranker_mode == "none":
            reranked_candidates = []
            for c in expanded_candidates:
                c_copy = dict(c)
                if "rerank_score" not in c_copy:
                    c_copy["rerank_score"] = float(c_copy.get("score", 0.5))
                if "rerank_signals" not in c_copy:
                    c_copy["rerank_signals"] = {}
                reranked_candidates.append(c_copy)
        else:
            reranked_candidates = self.reranker.rerank(
                enriched_query,
                expanded_candidates,
                req_obj=req_obj,
                top_k=15,
            )
            # P0-6: If explicit designations were requested, keep matching explicit candidates at the top
            # and do not allow conflicting parts or bare bases to replace them
            if explicit_candidates:
                explicit_desig_set = {
                    ec.get("designation") for ec in explicit_candidates if ec.get("designation")
                }
                exp_matched = [c for c in reranked_candidates if c.get("designation") in explicit_desig_set]
                for ec in explicit_candidates:
                    if ec.get("designation") not in {c.get("designation") for c in exp_matched}:
                        exp_matched.append(ec)
                others = [
                    c for c in reranked_candidates
                    if c.get("designation") not in explicit_desig_set
                    and not any(
                        ec.get("base_number") and str(ec.get("base_number")) == str(c.get("base_number"))
                        and ec.get("part") != c.get("part")
                        for ec in explicit_candidates
                    )
                ]
                reranked_candidates = exp_matched + others

        # Step 6: Technical Applicability Gating (Evidence-based per-attribute verification)
        applicable_candidates = []
        allied_candidates = []
        rejected_candidates = []

        for c in reranked_candidates:
            app_result = self.applicability_engine.evaluate_applicability(c, req_obj)
            c_annotated = dict(c)
            c_annotated["applicability"] = app_result

            # Trust Mandate P1-D: Explicit designation is an identity anchor,
            # NEVER an automatic override of technical applicability.
            # Never convert UNKNOWN, MISMATCH, or ungrounded states into APPLICABLE.
            is_explicit = c.get("retrieval_source") == "exact_designation" or any(
                det.get("canonical_base", "").upper() in (c.get("designation") or "").upper()
                for det in detected_desigs
            ) if detected_desigs else False
            c_annotated["is_explicit_designation"] = is_explicit

            state = app_result["state"]
            if state == ApplicabilityState.APPLICABLE.value:
                applicable_candidates.append(c_annotated)
            elif state == ApplicabilityState.CONDITIONALLY_APPLICABLE.value:
                # Trust Mandate: CONDITIONALLY_APPLICABLE candidates are eligible
                # but have thin grounding evidence — placed after fully APPLICABLE.
                applicable_candidates.append(c_annotated)
            elif state == ApplicabilityState.RELATED.value:
                allied_candidates.append(c_annotated)
            else:
                rejected_candidates.append(c_annotated)

        # Step 7 & 8: Lifecycle and Regulatory Resolution for Applicable Standards (with caching)
        resolved_recommendations = []
        for cand in applicable_candidates[:top_k]:
            desig = cand.get("designation") or (cand.get("document") or {}).get("designation") or ""
            
            # Cached Lifecycle check
            life_key = (desig, eval_date)
            if life_key in self._lifecycle_cache:
                lifecycle_info = self._lifecycle_cache[life_key]
            else:
                lifecycle_info = self.lifecycle_gate.resolve_edition(desig, evaluation_date=eval_date)
                self._lifecycle_cache[life_key] = lifecycle_info

            resolved_desig = lifecycle_info["recommended_edition"]
            
            # Cached Regulatory check
            reg_key = (resolved_desig, eval_date, raw_text)
            if reg_key in self._regulatory_cache:
                reg_info = self._regulatory_cache[reg_key]
            else:
                reg_info = self.regulatory_gate.evaluate_regulatory_status(
                    resolved_desig,
                    evaluation_date=eval_date,
                    evaluation_context=raw_text,
                )
                self._regulatory_cache[reg_key] = reg_info

            # Hydrate EvidenceBundle with O(1) base-normalized node lookup (Phase P1-D / P0)
            node = self._find_graph_node(desig)
            bundle = EvidenceBundle.from_node(
                node or cand,
                lifecycle_info=lifecycle_info,
                reg_info=reg_info,
                applicability_info=cand.get("applicability"),
            )

            # Trust Mandate P1-D: EvidencePolicy is the sole authority for recommendation readiness.
            # Independent of pre-baked graph booleans; evaluates bundle state directly with technical context.
            app_ctx = {
                "target_product": target_prod,
                "matched_attributes": cand.get("applicability", {}).get("matched_attributes", []),
                "mismatched_attributes": cand.get("applicability", {}).get("mismatched_attributes", []),
                "unmatched_attributes": cand.get("applicability", {}).get("unmatched_attributes", []),
                "applicability_state": cand.get("applicability", {}).get("state"),
            }
            rec_ready, primary_gaps = EvidencePolicy.evaluate_claim(
                ClaimType.PRIMARY_RECOMMENDATION_CLAIM,
                bundle,
                context=app_ctx,
            )

            resolved_recommendations.append({
                "standard_designation": resolved_desig,
                "original_candidate": desig,
                "title": cand.get("title") or (cand.get("document") or {}).get("title"),
                "confidence_score": cand.get("rerank_score", 0.0),
                "recommendation_ready": rec_ready,
                "evidence_gaps": primary_gaps,
                "evidence_exception": None,
                "applicability": cand.get("applicability", {}),
                "lifecycle": lifecycle_info,
                "regulatory": reg_info,
                "relevance_signals": cand.get("rerank_signals", {}),
                "evidence_bundle": bundle.to_dict(),
                "retrieval_diagnostics": cand.get("retrieval_diagnostics", {}),
            })

        # Deduplicate resolved candidates (prevent multiple superseded editions from duplicating top candidate)
        seen_resolved = set()
        deduped_resolved = []
        for r in resolved_recommendations:
            r_desig = r["standard_designation"]
            if r_desig not in seen_resolved:
                seen_resolved.add(r_desig)
                deduped_resolved.append(r)
        resolved_recommendations = deduped_resolved

        # Step 9: Calibrated Selective Abstention Policy
        if has_contradictions:
            decision_state = "INSUFFICIENT_INFORMATION"
            abstention_reason = consistency_result.abstention_reason or f"Contradictory technical specifications detected: {'; '.join(req_obj.get('contradictions', []))}"
            primary_rec = None
            viable_recs = []
        elif is_outside_domain:
            decision_state = "OUTSIDE_PROTOTYPE_COVERAGE"
            abstention_reason = "Query specifies products outside the CED (Civil) and ETD (Electrotechnical) prototype coverage boundary."
            primary_rec = None
            viable_recs = []
        elif is_query_underspecified:
            decision_state = "INSUFFICIENT_INFORMATION"
            abstention_reason = query_sufficiency.get("reason", "Procurement query is under-specified. Key discriminators missing.")
            primary_rec = None
            viable_recs = []
        else:
            decision_state, abstention_reason, primary_rec, viable_recs = self.abstention_policy.decide(
                resolved_recommendations,
                missing_discriminators=missing_discriminators,
            )

        # Step 9.5: Enforce Evidence Readiness, Review Candidate, & Claim Gate (P0-1, P0-2, P0-3)
        review_candidate = None

        if primary_rec:
            rec_ready = primary_rec.get("recommendation_ready", False)
            orig_desig = primary_rec.get("original_candidate") or primary_rec.get("standard_designation") or ""

            is_explicit_request = any(
                det.get("canonical_base", "").upper() in orig_desig.upper()
                for det in detected_desigs
            ) if detected_desigs else False

            # P1-D / P0 Integrity Mandate:
            # If the tender explicitly cited standard designation(s), do NOT silently substitute
            # an unrequested retrieved standard as primary recommendation if explicit candidate failed.
            if detected_desigs and not is_explicit_request:
                viable_recs = [primary_rec] + [r for r in viable_recs if r != primary_rec]
                abstention_reason = (
                    f"Explicit standard {[d.get('canonical') or d.get('canonical_base') for d in detected_desigs]} cited in query "
                    f"does not match technical requirements or is incompatible. Candidate {primary_rec.get('standard_designation')} "
                    f"identified as alternative, but primary recommendation is withheld due to explicit specification mismatch."
                )
                primary_rec = None
                decision_state = "NO_CONFIDENT_MATCH"
                claim_level = "ABSTAINED"

        if primary_rec:
            rec_ready = primary_rec.get("recommendation_ready", False)
            orig_desig = primary_rec.get("original_candidate") or primary_rec.get("standard_designation") or ""
            is_explicit_request = any(
                det.get("canonical_base", "").upper() in orig_desig.upper()
                for det in detected_desigs
            ) if detected_desigs else False
            cand_app = primary_rec.get("applicability", {})
            cand_app_state = cand_app.get("state")

            if not rec_ready:
                # Trust Mandate P0-1, P0-3 & P1-C: EvidencePolicy gate
                # Must NOT erase candidate — surface as review_candidate
                review_cand_desig = primary_rec.get("standard_designation") or orig_desig
                cand_gaps = primary_rec.get("evidence_gaps") or (
                    bundle.get_evidence_gaps(ClaimType.PRIMARY_RECOMMENDATION_CLAIM) if bundle else ["SCOPE_MISSING"]
                )
                review_candidate = {
                    "designation": review_cand_desig,
                    "standard_designation": review_cand_desig,
                    "title": primary_rec.get("title"),
                    "role": primary_rec.get("evidence_bundle", {}).get("standard_role", "PRODUCT_STANDARD"),
                    "candidate_relevance": "HIGH" if (is_explicit_request or primary_rec.get("confidence_score", 0) >= 0.75) else "PLAUSIBLE",
                    "applicability_state": cand_app_state or "UNKNOWN",
                    "claim_level": "REVIEW_REQUIRED",
                    "evidence_state": "SCOPE_UNAVAILABLE" if "SCOPE_MISSING" in cand_gaps else "EVIDENCE_INSUFFICIENT",
                    "missing_evidence": cand_gaps,
                    "evidence_gaps": cand_gaps,
                    "lifecycle_state": (primary_rec.get("lifecycle") or {}).get("lifecycle_state") or "UNKNOWN",
                    "regulatory_state": (primary_rec.get("regulatory") or {}).get("regulatory_state") or "UNVERIFIED",
                    "review_reason": f"Standard {review_cand_desig} lacks verified scope evidence in the knowledge base; the available BIS evidence is insufficient to verify applicability ({', '.join(cand_gaps)}).",
                    "evidence_bundle": primary_rec.get("evidence_bundle"),
                    "retrieval_diagnostics": primary_rec.get("retrieval_diagnostics", {}),
                    "provenance": {
                        "engine_version": self.ENGINE_VERSION,
                        "graph_release_id": self.graph_release_id,
                        "retrieval_source": primary_rec.get("relevance_signals", {}).get("retrieval_source", "hybrid"),
                    }
                }
                primary_rec = None
                decision_state = "EXPERT_REVIEW_REQUIRED"
                abstention_reason = f"Standard {review_cand_desig} lacks verified scope evidence in the knowledge base; the available BIS evidence is insufficient to verify applicability ({', '.join(cand_gaps)})."
                claim_level = "REVIEW_REQUIRED"
            elif cand_app_state == ApplicabilityState.CONDITIONALLY_APPLICABLE.value:
                # Trust Mandate P0-2: Conditional applicability stays conditional
                primary_rec["evidence_exception"] = (
                    "CONDITIONAL_APPLICABILITY: Product matched but grounding attributes are largely unknown. "
                    "Verification required against detailed procurement specifications."
                )
                if decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE":
                    decision_state = "CONDITIONAL_RECOMMENDATION"
                    if not abstention_reason:
                        abstention_reason = (
                            f"Standard {orig_desig} is conditionally applicable; key technical parameters require verification."
                        )
                primary_rec["candidate_relevance"] = "HIGH"
                primary_rec["applicability_state"] = cand_app_state
                primary_rec["evidence_state"] = "CONDITIONAL"
                primary_rec["recommendability"] = "CONDITIONALLY_RECOMMENDABLE"
                primary_rec["claim_level"] = "CONDITIONALLY_SUPPORTED"
                claim_level = "CONDITIONALLY_SUPPORTED"
            else:
                primary_rec["evidence_exception"] = None
                primary_rec["candidate_relevance"] = "HIGH"
                primary_rec["applicability_state"] = cand_app_state or "APPLICABLE"
                primary_rec["evidence_state"] = "SUFFICIENT"
                primary_rec["recommendability"] = "RECOMMENDABLE"
                primary_rec["claim_level"] = (
                    "VERIFIED_FOR_RECOMMENDATION" if decision_state == "PRIMARY_RECOMMENDATION_AVAILABLE"
                    else "CONDITIONALLY_SUPPORTED"
                )
                claim_level = primary_rec["claim_level"]
                if is_explicit_request and decision_state not in (
                    "INSUFFICIENT_INFORMATION",
                    "NO_CONFIDENT_MATCH",
                    "EXPERT_REVIEW_REQUIRED",
                ):
                    decision_state = "PRIMARY_RECOMMENDATION_AVAILABLE"

            if decision_state in (
                "INSUFFICIENT_INFORMATION",
                "MULTIPLE_POSSIBLE_STANDARDS",
                "NO_CONFIDENT_MATCH",
                "OUTSIDE_PROTOTYPE_COVERAGE",
                "EXPERT_REVIEW_REQUIRED",
            ):
                if is_explicit_request and primary_rec and not review_candidate:
                    review_candidate = {
                        "designation": primary_rec.get("standard_designation") or orig_desig,
                        "standard_designation": primary_rec.get("standard_designation") or orig_desig,
                        "title": primary_rec.get("title"),
                        "role": (primary_rec.get("evidence_bundle") or {}).get("standard_role", "PRODUCT_STANDARD"),
                        "candidate_relevance": "HIGH",
                        "applicability_state": cand_app_state or "APPLICABLE",
                        "claim_level": "REVIEW_REQUIRED",
                        "evidence_state": "SUFFICIENT",
                        "missing_evidence": [],
                        "evidence_gaps": [],
                        "lifecycle_state": (primary_rec.get("lifecycle") or {}).get("lifecycle_state") or "UNKNOWN",
                        "regulatory_state": (primary_rec.get("regulatory") or {}).get("regulatory_state") or "UNVERIFIED",
                        "review_reason": abstention_reason or "Verification required against missing procurement specifications.",
                        "evidence_bundle": primary_rec.get("evidence_bundle"),
                        "retrieval_diagnostics": primary_rec.get("retrieval_diagnostics", {}),
                        "provenance": {
                            "engine_version": self.ENGINE_VERSION,
                            "graph_release_id": self.graph_release_id,
                            "retrieval_source": (primary_rec.get("relevance_signals") or {}).get("retrieval_source", "exact_designation"),
                        }
                    }
                primary_rec = None
                claim_level = "ABSTAINED" if decision_state in ("INSUFFICIENT_INFORMATION", "NO_CONFIDENT_MATCH", "OUTSIDE_PROTOTYPE_COVERAGE") else ("REVIEW_REQUIRED" if decision_state == "EXPERT_REVIEW_REQUIRED" else "PLAUSIBLE")

        elif not has_contradictions and not is_outside_domain and not is_query_underspecified:
            # No primary recommendation reached threshold or survived applicability.
            # Check if an explicit candidate or an unready candidate blocked by evidence exists
            cand_to_review = None
            if explicit_candidates:
                # Only review explicit candidate if it's NOT a hard mismatch!
                # If explicit standard is technically incompatible (MISMATCH), it is rejected, NOT review_candidate!
                for ec in explicit_candidates:
                    ec_app = ec.get("applicability") or self.applicability_engine.evaluate_applicability(ec, req_obj)
                    if ec_app.get("state") != ApplicabilityState.NOT_APPLICABLE.value:
                        cand_to_review = ec
                        cand_to_review["applicability"] = ec_app
                        break
            elif rejected_candidates:
                cand_to_review = next(
                    (c for c in rejected_candidates
                     if "evidence_readiness" in c.get("applicability", {}).get("mismatched_attributes", [])
                     and "PRODUCT" not in c.get("applicability", {}).get("mismatched_attributes", [])),
                    None
                )
                if not cand_to_review:
                    cand_to_review = next(
                        (c for c in rejected_candidates
                         if c.get("applicability", {}).get("state") == ApplicabilityState.EXPERT_REVIEW_REQUIRED.value
                         and "PRODUCT" not in c.get("applicability", {}).get("mismatched_attributes", [])),
                        None
                    )

            if cand_to_review:
                rev_desig = cand_to_review.get("designation") or (cand_to_review.get("document") or {}).get("designation")
                rev_title = cand_to_review.get("title") or (cand_to_review.get("document") or {}).get("title")
                rev_app = cand_to_review.get("applicability", {})
                rev_is_explicit = cand_to_review.get("retrieval_source") == "exact_designation" or any(
                    det.get("canonical_base", "").upper() in (rev_desig or "").upper()
                    for det in detected_desigs
                ) if detected_desigs else False

                rev_node = next((n for n in self.standards_graph.get("nodes", []) if n.get("designation") == rev_desig), None) if self.standards_graph else None
                rev_scope = bool((rev_node.get("scope") or "").strip()) if rev_node else False

                rev_lifecycle = self.lifecycle_gate.resolve_edition(rev_desig, evaluation_date=evaluation_date)
                rev_reg = self.regulatory_gate.evaluate_regulatory_status(
                    rev_lifecycle["recommended_edition"],
                    evaluation_date=evaluation_date,
                    evaluation_context=raw_text,
                )
                rev_bundle = EvidenceBundle.from_node(
                    rev_node or cand_to_review,
                    lifecycle_info=rev_lifecycle,
                    reg_info=rev_reg,
                    applicability_info=rev_app,
                )
                rev_gaps = rev_bundle.get_evidence_gaps(
                    ClaimType.PRIMARY_RECOMMENDATION_CLAIM,
                    context={
                        "target_product": target_prod,
                        "matched_attributes": rev_app.get("matched_attributes", []),
                        "mismatched_attributes": rev_app.get("mismatched_attributes", []),
                    },
                )

                decision_state = "EXPERT_REVIEW_REQUIRED"
                abstention_reason = (
                    f"Candidate standard {rev_desig} lacks verified scope evidence. "
                    "The available BIS evidence is insufficient to verify applicability."
                )
                primary_rec = None
                viable_recs = []
                claim_level = "REVIEW_REQUIRED"
                review_candidate = {
                    "designation": rev_desig,
                    "standard_designation": rev_desig,
                    "title": rev_title,
                    "role": rev_bundle.standard_role,
                    "candidate_relevance": "HIGH" if (rev_is_explicit or cand_to_review.get("rerank_score", 0) >= 0.75) else "PLAUSIBLE",
                    "applicability_state": rev_app.get("state") or "UNKNOWN",
                    "claim_level": "REVIEW_REQUIRED",
                    "evidence_state": "SCOPE_UNAVAILABLE" if not rev_scope else "INSUFFICIENT_EVIDENCE",
                    "missing_evidence": rev_gaps or ["SCOPE_TEXT_UNAVAILABLE_IN_KB", "RECOMMENDATION_NOT_READY"],
                    "evidence_gaps": rev_gaps or ["SCOPE_TEXT_UNAVAILABLE_IN_KB", "RECOMMENDATION_NOT_READY"],
                    "lifecycle_state": rev_lifecycle.get("lifecycle_state", "UNKNOWN"),
                    "regulatory_state": rev_reg.get("regulatory_state", "UNVERIFIED"),
                    "review_reason": "The available BIS evidence is insufficient to verify applicability.",
                    "evidence_bundle": rev_bundle.to_dict(),
                    "retrieval_diagnostics": cand_to_review.get("retrieval_diagnostics", {}),
                    "provenance": {
                        "engine_version": self.ENGINE_VERSION,
                        "graph_release_id": self.graph_release_id,
                        "retrieval_source": cand_to_review.get("retrieval_source", "hybrid"),
                    }
                }
            elif decision_state not in ("MULTIPLE_POSSIBLE_STANDARDS", "INSUFFICIENT_INFORMATION", "EXPERT_REVIEW_REQUIRED"):
                decision_state = "NO_CONFIDENT_MATCH"
                abstention_reason = "No candidate standard achieved technical applicability and grounding."
                primary_rec = None
                viable_recs = []
                review_candidate = None
                claim_level = "ABSTAINED"

        # Alternative standards
        alternative_standards = [r for r in viable_recs if r != primary_rec]

        # Supporting context pack grounded in knowledge graph edges
        supporting_context_pack = self._build_supporting_context_pack(
            primary_rec=primary_rec,
            allied_candidates=allied_candidates,
            rejected_candidates=rejected_candidates,
        )

        cal_prob = primary_rec.get("calibrated_confidence") if primary_rec else None
        if primary_rec:
            primary_rec["calibrated_probability"] = cal_prob
        for alt in alternative_standards:
            if "calibrated_probability" not in alt:
                alt["calibrated_probability"] = alt.get("calibrated_confidence")

        # Trust Mandate P0-5: Data Coverage & Evidence Coverage Accounting
        if primary_rec:
            primary_desig = primary_rec.get("standard_designation")
            target_node = (
                next((n for n in self.standards_graph.get("nodes", []) if n.get("designation") == primary_desig), None)
                if (self.standards_graph and primary_desig) else None
            )
            node_hydrated = bool(target_node.get("is_hydrated", False)) if target_node else False
            node_scope = bool((target_node.get("scope") or "").strip()) if target_node else False
            node_ready = bool(primary_rec.get("recommendation_ready", False))

            if node_ready and node_scope and node_hydrated:
                coverage_level = "COMPLETE"
            elif node_hydrated or node_scope:
                coverage_level = "PARTIAL"
            elif target_node:
                coverage_level = "MINIMAL"
            else:
                coverage_level = "UNAVAILABLE"

            cand_app_state = (primary_rec.get("applicability") or {}).get("state")
            if node_ready and cand_app_state == ApplicabilityState.APPLICABLE.value:
                ev_status = "SUFFICIENT"
                ev_details = "Verified scope evidence and attribute grounding available in knowledge base."
                claim_level = "VERIFIED_FOR_RECOMMENDATION"
            elif cand_app_state == ApplicabilityState.CONDITIONALLY_APPLICABLE.value:
                ev_status = "CONDITIONAL"
                ev_details = "Product match identified but detailed attribute evidence is partial/unknown."
                claim_level = "CONDITIONALLY_SUPPORTED"
            else:
                ev_status = "INSUFFICIENT"
                ev_details = "Evidence insufficiency detected during applicability evaluation."
                claim_level = "REVIEW_REQUIRED"
            primary_rec["claim_level"] = claim_level

        elif review_candidate:
            rev_desig = review_candidate["standard_designation"]
            rev_node = (
                next((n for n in self.standards_graph.get("nodes", []) if n.get("designation") == rev_desig), None)
                if (self.standards_graph and rev_desig) else None
            )
            node_hydrated = bool(rev_node.get("is_hydrated", False)) if rev_node else False
            node_scope = bool((rev_node.get("scope") or "").strip()) if rev_node else False
            node_ready = False
            coverage_level = "PARTIAL" if node_hydrated else "UNAVAILABLE"
            ev_status = "INSUFFICIENT"
            ev_details = "The available BIS evidence is insufficient to verify applicability."
            claim_level = "REVIEW_REQUIRED"
        else:
            node_hydrated = False
            node_scope = False
            node_ready = False
            coverage_level = "UNAVAILABLE"
            ev_status = "DATA_UNAVAILABLE"
            ev_details = "No candidate standard met evidentiary threshold."
            claim_level = "ABSTAINED"

        data_coverage = {
            "is_hydrated": node_hydrated,
            "has_scope": node_scope,
            "recommendation_ready": node_ready,
            "coverage_level": coverage_level,
        }

        evidence_coverage = {
            "status": ev_status,
            "details": ev_details,
        }

        # Structured Decision Trace (14 Stages) with explicit blocking and status
        stages_data = [
            ("extraction",
             "PASS" if req_obj.get("requirements") or req_obj.get("intent") else "FAIL",
             "Normalized requirements extracted successfully" if (req_obj.get("requirements") or req_obj.get("intent")) else "Failed to extract requirements from query text",
             {"intent": req_obj.get("intent"), "requirements_count": len(req_obj.get("requirements", []))},
             bool(not (req_obj.get("requirements") or req_obj.get("intent")))),

            ("exact_designation",
             "PASS" if detected_desigs else "SKIPPED",
             f"Detected exact designations: {[d.get('canonical') or d.get('canonical_base') for d in detected_desigs]}" if detected_desigs else "No exact standard designation cited in query",
             [d.get("canonical") or d.get("canonical_base") for d in detected_desigs] if detected_desigs else None,
             False),

            ("query_sufficiency",
             "CONFLICT" if has_contradictions else ("BLOCKED" if (req_obj.get("query_sufficiency") or {}).get("state") == "INSUFFICIENT" else "PASS"),
             abstention_reason if has_contradictions else ((req_obj.get("query_sufficiency") or {}).get("reason") or "Query context sufficient for retrieval"),
             {"query_sufficiency": req_obj.get("query_sufficiency"), "contradictions": [c.to_dict() for c in consistency_result.contradictions] if not consistency_result.is_consistent else req_obj.get("contradictions", [])},
             bool(has_contradictions or (req_obj.get("query_sufficiency") or {}).get("state") == "INSUFFICIENT")),

            ("retrieval",
             "PASS" if (bm25_candidates or dense_candidates) else "FAIL",
             f"BM25 ({len(bm25_candidates)}) / Dense ({len(dense_candidates)}) candidates found" if (bm25_candidates or dense_candidates) else "Zero candidates retrieved across channels",
             {"bm25_count": len(bm25_candidates), "dense_count": len(dense_candidates)},
             bool(not (bm25_candidates or dense_candidates))),

            ("fusion",
             "PASS" if fused_candidates else "FAIL",
             f"Fused {len(fused_candidates)} candidates via reciprocal rank fusion" if fused_candidates else "RRF fusion yielded no candidates",
             {"fused_count": len(fused_candidates)},
             bool(not fused_candidates)),

            ("graph_expansion",
             "PASS" if len(expanded_candidates) > len(fused_candidates) else "SKIPPED",
             f"Expanded graph neighbors to {len(expanded_candidates)} total candidates" if len(expanded_candidates) > len(fused_candidates) else "No graph expansions added",
             {"expanded_count": len(expanded_candidates)},
             False),

            ("rerank",
             "PASS" if reranked_candidates else "FAIL",
             f"Reranked {len(reranked_candidates)} candidates" if reranked_candidates else "No candidates scored by reranker",
             {"reranked_count": len(reranked_candidates)},
             bool(not reranked_candidates)),

            ("candidate_role",
             "PASS" if (primary_rec or review_candidate or not any(r.get("applicability", {}).get("mismatched_attributes") == ["ROLE_MISMATCH"] for r in rejected_candidates)) else "BLOCKED",
             "Candidate role aligned with procurement object" if (primary_rec or review_candidate) else "Candidates failed role classification check",
             {"primary_role": primary_rec.get("standard_role") if primary_rec else None},
             bool(not primary_rec and not review_candidate and any(r.get("applicability", {}).get("mismatched_attributes") == ["ROLE_MISMATCH"] for r in rejected_candidates))),

            ("applicability",
             "PASS" if applicable_candidates else (
                 "UNKNOWN" if review_candidate else "FAIL"
             ),
             "Technical applicability satisfied" if applicable_candidates else (
                 "Applicability unverified due to incomplete KB scope" if review_candidate else "No candidates satisfied technical applicability criteria"
             ),
             (primary_rec.get("applicability") if primary_rec else (review_candidate.get("applicability_state") if review_candidate else None)),
             bool(not applicable_candidates and not review_candidate)),

            ("evidence_gate",
             "PASS" if (primary_rec and primary_rec.get("recommendation_ready")) else (
                 "BLOCKED" if (review_candidate or (rejected_candidates and any("evidence_readiness" in r.get("applicability", {}).get("mismatched_attributes", []) for r in rejected_candidates))) else "SKIPPED"
             ),
             "Verified scope and lifecycle evidence present" if (primary_rec and primary_rec.get("recommendation_ready")) else (
                 "Blocked by evidence readiness gate: unverified scope/lifecycle" if review_candidate else "No candidates evaluated at evidence gate"
             ),
             (primary_rec.get("evidence_bundle") if primary_rec else (review_candidate.get("missing_evidence") if review_candidate else None)),
             bool(review_candidate is not None)),

            ("lifecycle",
             "BLOCKED" if (primary_rec and (primary_rec.get("lifecycle") or {}).get("is_superseded")) else (
                 "PASS" if (primary_rec or review_candidate) else "SKIPPED"
             ),
             f"Candidate standard is superseded by {(primary_rec.get('lifecycle') or {}).get('superseded_by')}" if (primary_rec and (primary_rec.get("lifecycle") or {}).get("is_superseded")) else "Lifecycle verified active or unblocked",
             (primary_rec.get("lifecycle") if primary_rec else None),
             bool(primary_rec and (primary_rec.get("lifecycle") or {}).get("is_superseded"))),

            ("regulatory",
             "CONFLICT" if ((primary_rec and (primary_rec.get("regulatory") or {}).get("regulatory_state") == "CONFLICTING_EVIDENCE") or (review_candidate and (review_candidate.get("regulatory") or {}).get("regulatory_state") == "CONFLICTING_EVIDENCE")) else (
                 "PASS" if (primary_rec or review_candidate) else "SKIPPED"
             ),
             "Conflicting regulatory mandates detected across sources" if ((primary_rec and (primary_rec.get("regulatory") or {}).get("regulatory_state") == "CONFLICTING_EVIDENCE") or (review_candidate and (review_candidate.get("regulatory") or {}).get("regulatory_state") == "CONFLICTING_EVIDENCE")) else "Regulatory status verified or unconflicted",
             (primary_rec.get("regulatory") if primary_rec else None),
             bool((primary_rec and (primary_rec.get("regulatory") or {}).get("regulatory_state") == "CONFLICTING_EVIDENCE") or (review_candidate and (review_candidate.get("regulatory") or {}).get("regulatory_state") == "CONFLICTING_EVIDENCE"))),

            ("calibration",
             "PASS" if (primary_rec and (primary_rec.get("calibrated_confidence", 0.0) >= self.abstention_policy.tau_min)) else (
                 "BLOCKED" if primary_rec else "SKIPPED"
             ),
             f"Calibrated probability {cal_prob:.3f} >= threshold {self.abstention_policy.tau_min}" if (primary_rec and cal_prob is not None and cal_prob >= self.abstention_policy.tau_min) else "Calibration threshold not met or skipped",
             {"calibrated_probability": cal_prob, "threshold": self.abstention_policy.tau_min},
             bool(primary_rec and (primary_rec.get("calibrated_confidence", 0.0) < self.abstention_policy.tau_min))),

            ("final_decision",
             "PASS" if primary_rec else ("BLOCKED" if review_candidate else "FAIL"),
             f"Decision state: {decision_state}" + (f" ({abstention_reason})" if abstention_reason else ""),
             {"decision_state": decision_state, "claim_level": claim_level},
             bool(primary_rec is None)),
        ]

        decision_trace = []
        failure_trace = {}
        first_failure = None

        for stage_name, status, reason, ev_data, blocking in stages_data:
            decision_trace.append({
                "stage": stage_name,
                "status": status,
                "state": status,  # Explicit contract state
                "reason": reason,
                "evidence": ev_data,
                "blocking": blocking,
                "outputs": ev_data if isinstance(ev_data, dict) else {"output": ev_data},
            })
            failure_trace[stage_name] = status
            if blocking and status in ("FAIL", "BLOCKED", "CONFLICT") and first_failure is None:
                first_failure = stage_name

        failure_trace["first_failure_stage"] = first_failure

        # Enforce Monotonic Claim Level:
        # A candidate cannot have claim level VERIFIED_FOR_RECOMMENDATION if any prior blocking stage is not PASS
        if primary_rec and primary_rec.get("claim_level") == "VERIFIED_FOR_RECOMMENDATION":
            prior_blocking_failed = any(
                s["blocking"] and s["status"] not in ("PASS", "SKIPPED")
                for s in decision_trace
                if s["stage"] != "final_decision"
            )
            if prior_blocking_failed or not primary_rec.get("recommendation_ready"):
                primary_rec["claim_level"] = "REVIEW_REQUIRED"
                claim_level = "REVIEW_REQUIRED"

        # If evidence gate blocks, claim_level cannot remain PLAUSIBLE or higher
        ev_gate = next((s for s in decision_trace if s["stage"] == "evidence_gate"), None)
        if ev_gate and ev_gate["status"] in ("BLOCKED", "FAIL"):
            if claim_level in ("VERIFIED_FOR_RECOMMENDATION", "CONDITIONALLY_SUPPORTED", "PLAUSIBLE"):
                claim_level = "REVIEW_REQUIRED"
            if primary_rec and primary_rec.get("claim_level") in ("VERIFIED_FOR_RECOMMENDATION", "CONDITIONALLY_SUPPORTED", "PLAUSIBLE"):
                primary_rec["claim_level"] = "REVIEW_REQUIRED"

        # Calibration status
        cal_status = (
            "CALIBRATED"
            if (
                getattr(self.abstention_policy, "is_empirical_calibrator", False)
                and getattr(self.abstention_policy.calibrator, "is_fitted", False)
                and (getattr(self.abstention_policy.calibrator, "metadata", {}) or {}).get("n_samples", 0) >= 100
            )
            else "CALIBRATION_INSUFFICIENT_DATA"
        )

        result: Dict[str, Any] = {
            # Canonical RecommendationResult schema properties
            "query": {
                "raw_text": raw_text,
                "query_id": query_id,
                "language": req_obj.get("language", "en"),
                "domain": req_obj.get("domain"),
            },
            "normalized_requirements": req_obj,
            "decision_state": decision_state,
            "abstention_reason": abstention_reason,
            "contradictions": [c.to_dict() for c in consistency_result.contradictions] if not consistency_result.is_consistent else req_obj.get("contradictions", []),
            "clarification_prompt": consistency_result.clarification_message if not consistency_result.is_consistent else None,
            "claim_level": claim_level,
            "data_coverage": data_coverage,
            "evidence_coverage": evidence_coverage,
            "failure_trace": failure_trace,
            "decision_trace": decision_trace,
            "primary_recommendation": primary_rec,
            "review_candidate": review_candidate,
            "alternative_standards": alternative_standards,
            "candidate_recommendations": resolved_recommendations,
            "allied_standards": allied_candidates[:5],
            "rejected_candidates": rejected_candidates[:5],
            "supporting_context_pack": supporting_context_pack,
            "calibration": {
                "method": "PlattScaling",
                "calibration_status": cal_status,
                "calibrated_probability": cal_prob,
                "abstention_threshold": self.abstention_policy.tau_recommend,
                "margin_delta": self.abstention_policy.delta_margin,
                "is_abstained": bool(primary_rec is None),
            },
            "evaluation_as_of_date": evaluation_date,
            "provenance": {
                "engine_version": self.ENGINE_VERSION,
                "graph_release_id": self.graph_release_id,
                "retriever_mode": self.retriever_mode,
                "reranker_mode": self.reranker_mode,
                "dense_retriever": self.dense_retriever.get_metadata() if getattr(self, "dense_retriever", None) else None,
                "dense_effective_mode": getattr(self.dense_retriever, "effective_mode", "UNKNOWN") if getattr(self, "dense_retriever", None) else None,
            },
            "natural_language_explanation": self.explainer.explain({
                "decision_state": decision_state,
                "abstention_reason": abstention_reason,
                "primary_recommendation": primary_rec,
                "review_candidate": review_candidate,
            }),
        }

        return result

    def _build_supporting_context_pack(
        self,
        primary_rec: Optional[Dict[str, Any]],
        allied_candidates: List[Dict[str, Any]],
        rejected_candidates: List[Dict[str, Any]],
    ) -> Dict[str, List[Any]]:
        normative_refs = []
        test_methods = []
        materials = []
        installation_codes = []

        if primary_rec and self.standards_graph:
            primary_desig = primary_rec.get("standard_designation") or ""
            orig_desig = primary_rec.get("original_candidate") or primary_desig
            desig_keys = {
                primary_desig,
                orig_desig,
                primary_desig.split(":")[0].strip(),
                orig_desig.split(":")[0].strip(),
            }

            edges = self.standards_graph.get("edges", [])
            for e in edges:
                src = e.get("source", "")
                tgt = e.get("target", "")
                rel = (e.get("relationship") or "").lower()

                # Outgoing edges from primary candidate
                if src in desig_keys:
                    if "test" in rel or "10810" in tgt or "test" in tgt.lower():
                        if tgt not in test_methods:
                            test_methods.append(tgt)
                    elif "material" in rel or "8130" in tgt or "1786" in tgt or "2062" in tgt:
                        if tgt not in materials:
                            materials.append(tgt)
                    elif "install" in rel or "practice" in rel or "laying" in rel:
                        if tgt not in installation_codes:
                            installation_codes.append(tgt)
                    else:
                        if tgt not in normative_refs:
                            normative_refs.append(tgt)

                # Incoming edges citing primary candidate
                elif tgt in desig_keys:
                    if "used_in_conjunction_with" in rel or "normative_reference" in rel:
                        if src not in normative_refs:
                            normative_refs.append(src)

        # Fallback / supplement from allied candidates
        for a in allied_candidates[:5]:
            desig = a.get("designation") or (a.get("document") or {}).get("designation") or ""
            title = (a.get("title") or (a.get("document") or {}).get("title") or "").lower()
            if not desig:
                continue
            role = RoleClassifier.classify(a)
            if role == StandardRole.TEST_METHOD or "test method" in title or "methods of test" in title:
                if desig not in test_methods:
                    test_methods.append(desig)
            elif role == StandardRole.COMPONENT or "material" in title or "conductor" in title or "profile" in title:
                if desig not in materials:
                    materials.append(desig)
            elif role in (StandardRole.INSTALLATION_CODE, StandardRole.DIMENSIONAL_MOUNTING) or "code of practice" in title or "laying" in title or "mounting" in title:
                if desig not in installation_codes:
                    installation_codes.append(desig)
            else:
                if desig not in normative_refs:
                    normative_refs.append(desig)

        for r in rejected_candidates[:5]:
            desig = r.get("designation") or (r.get("document") or {}).get("designation") or ""
            title = (r.get("title") or (r.get("document") or {}).get("title") or "").lower()
            if desig and ("test method" in title or "methods of test" in title) and desig not in test_methods:
                test_methods.append(desig)

        # Structured standards bundle reasoning (Option B - multi-standard decomposition)
        hierarchy_explanation = []
        if primary_rec:
            p_desig = (primary_rec.get("standard_designation") or "").upper()
            if "4926" in p_desig:
                hierarchy_explanation = [
                    "IS 4926 governs ready-mixed concrete production and supply (service/production code).",
                    "IS 269 / IS 1489 governs specified cementitious material (material specification).",
                    "IS 383 governs aggregate quality and grading (material specification).",
                    "IS 456 governs structural concrete design and performance context (design code).",
                    "IS 10262 governs concrete mix proportioning where specified (design/mix code)."
                ]
            elif "60947-2" in p_desig or "60947 (PART 2" in p_desig:
                hierarchy_explanation = [
                    "IS/IEC 60947-2 governs low-voltage industrial circuit-breakers (MCCBs/ACBs).",
                    "IS/IEC 60898-1 is for domestic/household circuit-breakers (MCBs up to 125 A, 25 kA).",
                    "IS 3043 provides earthing and installation system design rules."
                ]
            elif "1786" in p_desig:
                hierarchy_explanation = [
                    "IS 1786 governs high strength deformed steel bars for concrete reinforcement (primary product).",
                    "IS 456 governs structural concrete design and detailing requirements (design code).",
                    "IS 2062 is for structural steel plates/sections and is distinct from reinforcement rebars."
                ]
            elif "4985" in p_desig:
                hierarchy_explanation = [
                    "IS 4985 governs unplasticized PVC pipes for potable water supplies (primary product).",
                    "IS 13592 governs PVC-U pipes for soil and waste discharge inside and outside buildings.",
                    "IS 651 governs glazed stoneware pipes for underground drainage and sewage."
                ]

        return {
            "normative_references": normative_refs[:8],
            "test_methods": test_methods[:5],
            "materials": materials[:5],
            "installation_codes": installation_codes[:5],
            "hierarchy_explanation": hierarchy_explanation,
        }



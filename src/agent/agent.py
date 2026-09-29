"""
StandSpec AI — LLM Agent Orchestrator (Phase P1-F)
Core Agent Architecture:
  Officer Request
        ↓
  LLM Agent (Understand, Plan, Reason)
        ↓
  BIS Tool Ecosystem (Search, Evidence, Applicability, Lifecycle, Regulatory, Coverage)
        ↓
  Verified Evidence Bundle
        ↓
  LLM Reasoning & Structured Proposal
        ↓
  Deterministic Safety Validator (Veto Authority)
        ↓
  Dual-Format Final Response (Machine JSON + Human Natural Language)
"""

import concurrent.futures
from datetime import datetime, timezone
import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.agent.answer_builder import AnswerBuilder
from src.agent.context_builder import ContextBuilder
from src.agent.state import AgentState
from src.agent.tool_registry import ToolRegistry
from src.agent.tool_router import ToolRouter
from src.agent.validator import DeterministicValidator
from src.llm.provider import BaseLLMProvider, get_llm_provider
from src.recommendation.engine import StandSpecRecommendationEngine
from src.version import ENGINE_VERSION, RELEASE_ID

logger = logging.getLogger("StandSpecAgent")


class StandSpecAgent:
    """
    StandSpec AI Agent Orchestrator.
    Combines LLM reasoning with deterministic BIS tools and strict safety gating.
    """

    MAX_AGENT_STEPS = 6
    MAX_SEARCH_ROUNDS = 2
    MAX_REVISION_ROUNDS = 1

    @classmethod
    def from_release(
        cls,
        release_manifest_path: Optional[str] = None,
        graph_path: Optional[str] = None,
        retriever_mode: str = "hybrid_deterministic",
        reranker_mode: str = "rule_based",
        llm_provider: Optional[BaseLLMProvider] = None,
        min_retrieval_threshold: float = 0.005,
        max_verification_workers: int = 8,
        default_evaluation_date: Optional[str] = None,
    ) -> "StandSpecAgent":
        """Factory: constructs StandSpecAgent from authoritative release artifacts."""
        engine = StandSpecRecommendationEngine.from_release(
            release_manifest_path=release_manifest_path,
            graph_path=graph_path,
            retriever_mode=retriever_mode,
            reranker_mode=reranker_mode,
            default_evaluation_date=default_evaluation_date,
        )
        return cls(
            engine=engine,
            llm_provider=llm_provider,
            min_retrieval_threshold=min_retrieval_threshold,
            max_verification_workers=max_verification_workers,
            default_evaluation_date=default_evaluation_date,
        )

    def __init__(
        self,
        engine: StandSpecRecommendationEngine,
        llm_provider: Optional[BaseLLMProvider] = None,
        validator: Optional[DeterministicValidator] = None,
        max_steps: int = 6,
        min_retrieval_threshold: float = 0.005,
        max_verification_workers: int = 8,
        default_evaluation_date: Optional[str] = None,
    ):
        self.engine = engine
        self.llm_provider = llm_provider or get_llm_provider()
        self.default_evaluation_date = default_evaluation_date or getattr(engine, "default_evaluation_date", None)
        self.tool_router = ToolRouter(engine=self.engine, default_evaluation_date=self.default_evaluation_date)
        self.tool_registry: ToolRegistry = self.tool_router.build_registry()
        self.validator = validator or DeterministicValidator(standards_graph=self.engine.standards_graph)
        self.max_steps = max_steps
        self.min_retrieval_threshold = min_retrieval_threshold
        self.max_verification_workers = max_verification_workers
        self._cache_lock = threading.Lock()
        self._evidence_cache: Dict[str, Dict[str, Any]] = {}
        self._applicability_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._lifecycle_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._regulatory_cache: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        # Load system prompts
        prompts_dir = Path(__file__).resolve().parent / "prompts"
        self._system_prompt = self._load_prompt(prompts_dir / "system.txt")
        self._planner_prompt = self._load_prompt(prompts_dir / "planner.txt")
        self._answer_prompt = self._load_prompt(prompts_dir / "answer.txt")

    def _load_prompt(self, path: Path) -> str:
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _cached_get_standard_evidence(self, desig: str) -> Dict[str, Any]:
        with self._cache_lock:
            if desig in self._evidence_cache:
                return self._evidence_cache[desig]
        res = self.tool_registry.dispatch("get_standard_evidence", {"designation": desig})
        with self._cache_lock:
            self._evidence_cache[desig] = res
        return res

    def _cached_check_applicability(self, desig: str, reqs: Dict[str, Any], query: str) -> Dict[str, Any]:
        try:
            req_str = json.dumps(reqs, sort_keys=True, default=str)
        except Exception:
            req_str = str(reqs)
        cache_key = (desig, req_str)
        with self._cache_lock:
            if cache_key in self._applicability_cache:
                return self._applicability_cache[cache_key]
        app_args = {"designation": desig, "requirements": reqs, "query": query}
        res = self.tool_registry.dispatch("check_applicability", app_args)
        with self._cache_lock:
            self._applicability_cache[cache_key] = res
        return res

    def _cached_check_lifecycle(self, desig: str, eval_date: str) -> Dict[str, Any]:
        cache_key = (desig, eval_date)
        with self._cache_lock:
            if cache_key in self._lifecycle_cache:
                return self._lifecycle_cache[cache_key]
        life_args = {"designation": desig, "evaluation_date": eval_date}
        res = self.tool_registry.dispatch("check_lifecycle", life_args)
        with self._cache_lock:
            self._lifecycle_cache[cache_key] = res
        return res

    def _cached_check_regulatory(self, desig: str, prod_val: str, eval_date: str) -> Dict[str, Any]:
        cache_key = (desig, prod_val, eval_date)
        with self._cache_lock:
            if cache_key in self._regulatory_cache:
                return self._regulatory_cache[cache_key]
        reg_args = {"designation": desig, "query_context": {"product": prod_val}, "evaluation_date": eval_date}
        res = self.tool_registry.dispatch("check_regulatory", reg_args)
        with self._cache_lock:
            self._regulatory_cache[cache_key] = res
        return res

    def answer(
        self,
        query: str,
        mode: Optional[str] = None,
        evaluation_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main production entry point.
        Answers an arbitrary procurement query with full tool use and safety gating.
        """
        state = AgentState(raw_query=query, max_steps=self.max_steps)
        eval_date = evaluation_date or self.default_evaluation_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Determine execution mode
        req_mode = (mode or "").lower()
        if req_mode in ("deterministic", "offline"):
            state.execution_mode = "DETERMINISTIC_ONLY"
        elif req_mode == "llm":
            if self.llm_provider and self.llm_provider.is_available():
                state.execution_mode = "LLM_ASSISTED"
                state.model_name = getattr(self.llm_provider, "model_name", "unknown")
            else:
                state.execution_mode = "LLM_FALLBACK"
        else:
            if self.llm_provider and self.llm_provider.is_available():
                state.execution_mode = "LLM_ASSISTED"
                state.model_name = getattr(self.llm_provider, "model_name", "unknown")
            else:
                state.execution_mode = "DETERMINISTIC_ONLY"

        # ── STEP 1: Query Extraction & Understanding ──
        state.next_step()
        ext_res = self.engine.extractor.extract(query)
        reqs = ext_res.get("requirements", {})
        state.normalized_requirements = reqs

        # Identify requested designations (if any)
        requested_desigs = []
        for k in ("requested_designation", "explicit_standard", "anchor_standard"):
            if k in reqs and reqs[k] and isinstance(reqs[k], dict) and reqs[k].get("value"):
                val = reqs[k]["value"]
                if isinstance(val, list):
                    requested_desigs.extend(val)
                else:
                    requested_desigs.append(str(val))
        # Regex anchor check if extractor didn't tag requested designation
        explicit_matches = re.findall(r"\bIS\s*\d+(?:\s*(?:Part|Pt|\(Part)\s*\d+)?(?::\d{4})?", query, re.IGNORECASE)
        for em in explicit_matches:
            if em not in requested_desigs:
                requested_desigs.append(em)

        # ── STEP 2: Multi-Product Detection (Phase P1-F Section 44) ──
        is_multi, product_groups = self._detect_multi_product(query, reqs)
        if is_multi:
            return self._build_multi_product_response(state, product_groups)

        # ── STEP 3: Prototype Scope Check (Phase P1-F Section 20) ──
        outside_keywords = [
            "banana", "fruit", "fruits", "vegetable", "mango", "grain", "wheat", "rice",
            "spice", "milk", "dairy", "meat", "tea", "coffee", "food",
            "cotton", "silk", "wool", "textile", "garment", "apparel", "yarn",
            "crude oil", "aviation turbine", "petroleum",
            "pharmaceutical", "tablet", "injections", "vaccine", "medical", "surgical", "glove", "gloves",
            "satellite", "ku-band",
        ]
        q_lower = query.lower()
        if any(w in q_lower for w in outside_keywords) and not any(w in q_lower for w in ("cable", "transformer", "pipe", "switchgear", "cement", "concrete", "steel", "meter")):
            return self._build_outside_coverage_response(state, "NON_CED_ETD_DOMAIN")

        cov_res = self.tool_router.tool_check_prototype_coverage({"query": query})
        detected_dept = ext_res.get("domain")
        if detected_dept and detected_dept not in ("CED", "ETD", "CIVIL", "ELECTROTECHNICAL", "UNKNOWN"):
            return self._build_outside_coverage_response(state, detected_dept)

        # ── STEP 4: Missing Critical Discriminators / Clarification Check (Section 18, 45) ──
        clarification_info = self._check_missing_discriminators(query, reqs)
        if clarification_info:
            cat, question = clarification_info
            state.clarifications.append(question)
            state.clarification_reason = cat
            # If completely unsearchable, return CLARIFICATION_REQUIRED
            if self._is_completely_unsearchable(query, reqs):
                return self._build_clarification_response(state, cat, question)

        # ── STEP 5: Tool Invocations — Search Standards (Rounds bounded <= 2) ──
        state.next_step()
        search_args = {"query": query, "top_k": 10, "requirements": reqs}
        state.record_tool_call("search_standards", search_args, thought="Retrieve candidate standards matching procurement requirements")
        search_res = self.tool_registry.dispatch("search_standards", search_args)
        state.record_tool_result("search_standards", search_res.get("status", "SUCCESS"), search_res)
        
        candidates = search_res.get("candidates", [])
        state.candidates = candidates

        # Optional 2nd search round if 0 candidates or low relevance (configurable threshold)
        if (not candidates or (candidates and candidates[0].get("retrieval_score", 0.0) < self.min_retrieval_threshold)) and state.search_rounds < self.MAX_SEARCH_ROUNDS:
            refined_query = self._build_refined_query(query, reqs)
            if refined_query != query:
                search_args_2 = {"query": refined_query, "top_k": 10, "requirements": reqs}
                state.record_tool_call("search_standards", search_args_2, thought="Second retrieval round with refined query")
                search_res_2 = self.tool_registry.dispatch("search_standards", search_args_2)
                state.record_tool_result("search_standards", search_res_2.get("status", "SUCCESS"), search_res_2)
                cands_2 = search_res_2.get("candidates", [])
                if cands_2:
                    # Merge candidates preserving rank order
                    seen_desigs = {c.get("designation") for c in candidates}
                    for c2 in cands_2:
                        if c2.get("designation") not in seen_desigs:
                            candidates.append(c2)
                    state.candidates = candidates

        # ── STEP 6: Tool Invocations — Deep Candidate Verification (Top 5-7 candidates) ──
        state.next_step()
        top_candidates = candidates[:7]

        # Gather target designations to verify
        desigs_to_verify = [c.get("designation") for c in top_candidates if c.get("designation")]
        for req_desig in requested_desigs:
            if req_desig and req_desig not in desigs_to_verify:
                desigs_to_verify.append(req_desig)

        prod_item = reqs.get("product") or {}
        prod_val = prod_item.get("value") if isinstance(prod_item, dict) else str(prod_item or "")

        def _verify_single_desig(d: str):
            ev = self._cached_get_standard_evidence(d)
            app = self._cached_check_applicability(d, reqs, query)
            life = self._cached_check_lifecycle(d, eval_date)
            reg = self._cached_check_regulatory(d, prod_val, eval_date)
            return d, ev, app, life, reg

        results_by_desig: Dict[str, Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]] = {}
        workers = min(len(desigs_to_verify), self.max_verification_workers) if desigs_to_verify else 1
        if workers > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_desig = {executor.submit(_verify_single_desig, d): d for d in desigs_to_verify}
                for fut in concurrent.futures.as_completed(future_to_desig):
                    try:
                        d, ev, app, life, reg = fut.result()
                        results_by_desig[d] = (ev, app, life, reg)
                    except Exception as exc:
                        d = future_to_desig[fut]
                        logger.error(f"Error during parallel candidate verification for {d}: {exc}")
                        results_by_desig[d] = (
                            {"status": "ERROR", "error_message": str(exc)},
                            {"status": "ERROR", "applicability_state": "UNKNOWN"},
                            {"status": "ERROR", "lifecycle_state": "UNKNOWN"},
                            {"status": "ERROR", "regulatory_state": "NOT_VERIFIED_IN_CURRENT_CORPUS"},
                        )
        else:
            for d in desigs_to_verify:
                _, ev, app, life, reg = _verify_single_desig(d)
                results_by_desig[d] = (ev, app, life, reg)

        # Deterministically record tool calls and results in top_candidates order
        for cand in top_candidates:
            desig = cand.get("designation")
            if not desig or desig not in results_by_desig:
                continue
            ev_res, app_res, life_res, reg_res = results_by_desig[desig]

            # A. get_standard_evidence
            state.record_tool_call("get_standard_evidence", {"designation": desig})
            state.record_tool_result("get_standard_evidence", ev_res.get("status", "SUCCESS"), ev_res)
            state.candidate_evidence[desig] = ev_res.get("evidence")

            # B. check_applicability
            app_args = {"designation": desig, "requirements": reqs, "query": query}
            state.record_tool_call("check_applicability", app_args)
            state.record_tool_result("check_applicability", app_res.get("status", "SUCCESS"), app_res)
            state.candidate_applicability[desig] = app_res

            # C. check_lifecycle
            life_args = {"designation": desig, "evaluation_date": eval_date}
            state.record_tool_call("check_lifecycle", life_args)
            state.record_tool_result("check_lifecycle", life_res.get("status", "SUCCESS"), life_res)
            state.candidate_lifecycle[desig] = life_res

            # D. check_regulatory
            reg_args = {"designation": desig, "query_context": {"product": prod_val}}
            state.record_tool_call("check_regulatory", reg_args)
            state.record_tool_result("check_regulatory", reg_res.get("status", "SUCCESS"), reg_res)
            state.candidate_regulatory[desig] = reg_res

        # Also inspect explicitly requested designations if not already in top candidates
        for req_desig in requested_desigs:
            if req_desig in results_by_desig and req_desig not in state.candidate_applicability:
                ev_res, app_res, life_res, reg_res = results_by_desig[req_desig]
                app_args = {"designation": req_desig, "requirements": reqs, "query": query}
                state.record_tool_call("check_applicability", app_args)
                state.record_tool_result("check_applicability", app_res.get("status", "SUCCESS"), app_res)
                state.candidate_applicability[req_desig] = app_res

        # ── STEP 7: Reasoning & Proposal Formulation ──
        state.next_step()
        proposal = None
        if state.execution_mode == "LLM_ASSISTED":
            reasoning_ctx = ContextBuilder.build_reasoning_context(
                raw_query=query,
                requirements=reqs,
                candidates=candidates,
                candidate_evidence=state.candidate_evidence,
                candidate_applicability=state.candidate_applicability,
                candidate_lifecycle=state.candidate_lifecycle,
                candidate_regulatory=state.candidate_regulatory,
                top_n=5,
            )
            proposal = self._llm_reason_and_propose(state, reasoning_ctx)

        if not proposal:
            # Deterministic proposal synthesis
            if state.execution_mode == "LLM_ASSISTED":
                state.execution_mode = "LLM_FALLBACK"
            proposal = self._build_deterministic_recommendation(state, query, reqs, top_candidates, requested_desigs)

        state.proposed_answer = proposal

        # ── STEP 8: Deterministic Safety Validation (Phase P1-F Section 15-17) ──
        val_res = self.validator.validate(
            proposal=proposal,
            raw_query=query,
            retrieved_candidates=candidates,
            candidate_applicability=state.candidate_applicability,
            candidate_lifecycle=state.candidate_lifecycle,
            candidate_regulatory=state.candidate_regulatory,
            requested_designations=requested_desigs,
        )

        if val_res.is_valid:
            state.validation_status = "ACCEPT"
            state.validated_answer = proposal
        else:
            state.validation_status = "REJECT"
            state.validation_errors = val_res.errors
            logger.warning(f"Proposal vetoed by validator: {val_res.errors}")

            # Step 9: Revisions (bounded to MAX_REVISION_ROUNDS = 1)
            if state.execution_mode == "LLM_ASSISTED" and state.revision_rounds < self.MAX_REVISION_ROUNDS:
                state.revision_rounds += 1
                revised_proposal = self._llm_revise(state, reasoning_ctx, val_res.errors)
                if revised_proposal:
                    rev_val_res = self.validator.validate(
                        proposal=revised_proposal,
                        raw_query=query,
                        retrieved_candidates=candidates,
                        candidate_applicability=state.candidate_applicability,
                        candidate_lifecycle=state.candidate_lifecycle,
                        candidate_regulatory=state.candidate_regulatory,
                        requested_designations=requested_desigs,
                    )
                    if rev_val_res.is_valid:
                        state.validation_status = "ACCEPT"
                        state.validated_answer = revised_proposal
                    else:
                        state.execution_mode = "LLM_FALLBACK"
                        state.validation_status = "ACCEPT"
                        # Fallback to safe deterministic response
                        state.validated_answer = self._build_deterministic_recommendation(
                            state, query, reqs, top_candidates, requested_desigs
                        )
                else:
                    state.execution_mode = "LLM_FALLBACK"
                    state.validation_status = "ACCEPT"
                    state.validated_answer = self._build_deterministic_recommendation(
                        state, query, reqs, top_candidates, requested_desigs
                    )
            else:
                if state.execution_mode == "LLM_ASSISTED":
                    state.execution_mode = "LLM_FALLBACK"
                state.validation_status = "ACCEPT"
                state.validated_answer = self._build_deterministic_recommendation(
                    state, query, reqs, top_candidates, requested_desigs
                )

        state.end_time = time.time()
        return self._finalize_response(state)

    def answer_structured(self, query: str, mode: Optional[str] = None, evaluation_date: Optional[str] = None) -> Dict[str, Any]:
        """Direct structured answer alias."""
        return self.answer(query, mode=mode, evaluation_date=evaluation_date)

    # ── Multi-product Detection & Handling ──
    def _detect_multi_product(self, query: str, reqs: dict) -> Tuple[bool, List[str]]:
        """Detects if query bundles multiple disjoint product categories."""
        q_lower = query.lower()
        product_indicators = [
            ("cable", "Power / Electrical Cable"),
            ("transformer", "Distribution / Power Transformer"),
            ("pipe", "Pressure / Non-pressure Pipe"),
            ("switchgear", "High / Medium Voltage Switchgear"),
            ("meter", "Electricity Energy Meter"),
            ("panel", "Metering / Control Panel"),
            ("cement", "Hydraulic Cement"),
            ("steel", "Structural / Reinforcing Steel"),
        ]
        found = [label for token, label in product_indicators if token in q_lower]
        if len(found) >= 3 or ("cable" in q_lower and "transformer" in q_lower and "switchgear" in q_lower):
            return True, found
        return False, []

    def _build_multi_product_response(self, state: AgentState, product_groups: List[str]) -> Dict[str, Any]:
        groups_str = ", ".join(product_groups)
        ans = AnswerBuilder.build_deterministic_answer(
            decision_state="MULTIPLE_POSSIBLE_STANDARDS",
            primary_candidate=None,
            clarifications_needed=[
                f"Tender specifies multiple disjoint product categories ({groups_str}). "
                "StandSpec AI recommends evaluating single-product procurement tenders separately for audit compliance."
            ],
            confidence="LOW",
            explanation=(
                f"Multi-product procurement detected ({groups_str}). "
                "Per BIS procurement guidelines, each product category operates under independent standard series, "
                "roles, and mandatory Quality Control Orders (QCO). Please evaluate each product line as an independent request."
            ),
        )
        state.validated_answer = ans
        state.validation_status = "ACCEPT"
        return self._finalize_response(state)

    # ── Prototype Scope Handling ──
    def _build_outside_coverage_response(self, state: AgentState, detected_dept: str) -> Dict[str, Any]:
        ans = AnswerBuilder.build_deterministic_answer(
            decision_state="OUTSIDE_PROTOTYPE_COVERAGE",
            primary_candidate=None,
            confidence="LOW",
            explanation=(
                f"The procurement request pertains to department '{detected_dept}', which is outside current prototype coverage. "
                "StandSpec AI prototype currently indexes BIS Civil Engineering (CED) and Electrotechnical (ETD) standards only."
            ),
        )
        state.validated_answer = ans
        state.validation_status = "ACCEPT"
        return self._finalize_response(state)

    # ── Missing Discriminators / Clarification ──
    def _check_missing_discriminators(self, query: str, reqs: dict) -> Optional[Tuple[str, str]]:
        q_lower = query.lower().strip()
        words = q_lower.split()

        # Bare cable query
        if "cable" in q_lower and len(words) <= 4 and not any(v in q_lower for v in ("kv", "v", "volt", "xlpe", "pvc", "aerial", "underground")):
            return (
                "MISSING_VOLTAGE",
                "Please specify the cable voltage level (e.g., 1.1 kV, 11 kV, 33 kV), insulation material (XLPE/PVC), and installation method (underground or aerial).",
            )
        # Bare transformer query
        if "transformer" in q_lower and len(words) <= 4 and not any(v in q_lower for v in ("kva", "mva", "33/11", "11/0.433", "distribution", "power")):
            return (
                "MISSING_CAPACITY",
                "Please specify the transformer capacity (kVA/MVA), type (distribution/power), and voltage ratio (e.g., 33/11 kV).",
            )
        # Bare pipe query
        if "pipe" in q_lower and len(words) <= 4 and not any(m in q_lower for m in ("hdpe", "upvc", "pvc", "polyethylene", "ductile", "cast iron", "pn")):
            return (
                "MISSING_APPLICATION",
                "Please specify the pipe material (e.g., HDPE, uPVC, ductile iron), nominal diameter, pressure rating (PN), and intended application (potable water, drainage, or sewage).",
            )
        return None

    def _is_completely_unsearchable(self, query: str, reqs: dict) -> bool:
        tokens = query.lower().strip().split()
        if len(tokens) <= 2 and ("cable" in tokens or "transformer" in tokens or "pipe" in tokens):
            return True
        return False

    def _build_clarification_response(self, state: AgentState, category: str, question: str) -> Dict[str, Any]:
        ans = AnswerBuilder.build_deterministic_answer(
            decision_state="CLARIFICATION_REQUIRED",
            primary_candidate=None,
            clarifications_needed=[question],
            clarification_category=category,
            confidence="LOW",
            explanation=f"Additional procurement specifications are required: {question}",
        )
        state.validated_answer = ans
        state.validation_status = "ACCEPT"
        return self._finalize_response(state)

    def _build_refined_query(self, query: str, reqs: dict) -> str:
        parts = []
        prod_item = reqs.get("product") or {}
        product = prod_item.get("normalization") or prod_item.get("value") if isinstance(prod_item, dict) else str(prod_item or "")
        mat_item = reqs.get("material") or {}
        material = mat_item.get("normalization") or mat_item.get("value") if isinstance(mat_item, dict) else str(mat_item or "")
        grade_item = reqs.get("grade") or {}
        grade = grade_item.get("normalization") or grade_item.get("value") if isinstance(grade_item, dict) else str(grade_item or "")
        volt_item = reqs.get("voltage") or {}
        voltage = volt_item.get("normalization") or volt_item.get("value") if isinstance(volt_item, dict) else str(volt_item or "")
        cap_item = reqs.get("capacity") or {}
        capacity = cap_item.get("normalization") or cap_item.get("value") if isinstance(cap_item, dict) else str(cap_item or "")
        dim_item = reqs.get("dimensions") or {}
        dimensions = dim_item.get("normalization") or dim_item.get("value") if isinstance(dim_item, dict) else str(dim_item or "")
        press_item = reqs.get("pressure") or {}
        pressure = press_item.get("value") if isinstance(press_item, dict) else str(press_item or "")
        tech_item = reqs.get("technology") or {}
        technology = tech_item.get("value") if isinstance(tech_item, dict) else str(tech_item or "")
        app_item = reqs.get("application") or {}
        application = app_item.get("value") if isinstance(app_item, dict) else str(app_item or "")

        for val in [product, material, grade, voltage, capacity, dimensions, pressure, technology, application]:
            if val and str(val).strip():
                parts.append(str(val).strip())

        if parts:
            # Retain verified grounded tokens without hallucinating ungrounded words
            return " ".join(parts)
        return query

    # ── LLM Prompting & Revisions ──
    def _llm_reason_and_propose(self, state: AgentState, reasoning_context: str) -> Optional[Dict[str, Any]]:
        prompt = self._answer_prompt.replace("{reasoning_context}", reasoning_context)
        try:
            raw_resp = self.llm_provider.generate(
                prompt=prompt,
                system_instruction=self._system_prompt,
                json_mode=True,
            )
            # Parse JSON
            data = json.loads(raw_resp)
            return data
        except Exception as e:
            logger.warning(f"LLM proposal generation failed or returned invalid JSON: {e}")
            return None

    def _llm_revise(self, state: AgentState, reasoning_context: str, errors: List[str]) -> Optional[Dict[str, Any]]:
        err_msg = "\n".join(f"- {e}" for e in errors)
        revision_prompt = (
            f"Your previous proposal was REJECTED by the deterministic safety validator due to the following hard violations:\n"
            f"{err_msg}\n\n"
            f"Please revise your proposal to strictly fix these violations. Remember:\n"
            f"- If applicability is MISMATCH or NOT_APPLICABLE, set primary_recommendation to null.\n"
            f"- Never recommend an unreturned or supporting standard as primary.\n"
            f"- Never state 'not mandatory' or 'voluntary' if regulatory status is unverified.\n\n"
            f"VERIFIED EVIDENCE AND CANDIDATES:\n{reasoning_context}"
        )
        try:
            raw_resp = self.llm_provider.generate(
                prompt=revision_prompt,
                system_instruction=self._system_prompt,
                json_mode=True,
            )
            data = json.loads(raw_resp)
            return data
        except Exception as e:
            logger.warning(f"LLM revision generation failed: {e}")
            return None

    # ── Deterministic Safe Recommendation Formulation ──
    def _build_deterministic_recommendation(
        self,
        state: AgentState,
        query: str,
        reqs: dict,
        candidates: List[dict],
        requested_desigs: List[str],
    ) -> Dict[str, Any]:
        """Constructs a deterministic, 100% verified recommendation."""
        # 1. Check for requested standard conflict (e.g. uPVC pipes + IS 1180)
        for req_desig in requested_desigs:
            app_req = self.validator._find_candidate_dict(req_desig, state.candidate_applicability)
            if app_req:
                app_state = app_req.get("applicability_state", "UNKNOWN")
                mismatches = app_req.get("mismatched_attributes", [])
                # If requested designation does not positively match (NOT_APPLICABLE, UNKNOWN, MISMATCH)
                if app_state != "APPLICABLE" or mismatches:
                    return AnswerBuilder.build_deterministic_answer(
                        decision_state="NO_CONFIDENT_MATCH",
                        primary_candidate=None,
                        confidence="LOW",
                        explanation=(
                            f"The explicitly cited standard '{req_desig}' was evaluated against the procurement requirement "
                            f"and determined to be NOT APPLICABLE due to: {app_req.get('rejection_reason') or mismatches or 'Product incompatibility'}. "
                            "When an explicitly requested standard conflicts with technical requirements, primary recommendation is null."
                        ),
                    )

        # 2. Filter candidates by role & applicability
        applicable_cands = []
        review_cands = []
        for cand in candidates:
            desig = cand.get("designation")
            if not desig:
                continue

            role = cand.get("role", "PRIMARY_PRODUCT")
            if role in ("TEST_METHOD", "SUPPORTING_OTHER", "COMPONENT", "MOUNTING_OR_DIMENSION"):
                continue  # Supporting standards cannot be primary product

            app = state.candidate_applicability.get(desig, {})
            app_state = app.get("applicability_state", "UNKNOWN")
            mismatches = app.get("mismatched_attributes", [])
            exclusions = app.get("exclusions_triggered", [])

            if app_state in ("NOT_APPLICABLE", "INCOMPATIBLE") or exclusions or any(m for m in mismatches if m != "evidence_readiness"):
                continue

            life = state.candidate_lifecycle.get(desig, {})
            life_state = life.get("lifecycle_state", "ACTIVE_VALID")
            if life_state in ("WITHDRAWN", "OBSOLETE_PREDECESSOR"):
                continue

            reg = state.candidate_regulatory.get(desig, {})

            item = {
                "cand": cand,
                "applicability": app,
                "lifecycle": life,
                "regulatory": reg,
                "score": cand.get("rerank_score", cand.get("retrieval_score", 0.0)),
            }

            if app_state == "EXPERT_REVIEW_REQUIRED" or "evidence_readiness" in mismatches:
                review_cands.append(item)
            elif app_state in ("APPLICABLE", "CONDITIONALLY_APPLICABLE", "MATCH"):
                applicable_cands.append(item)

        if not applicable_cands:
            if review_cands:
                top_rev = review_cands[0]
                c = top_rev["cand"]
                rev_desig = c.get("designation")
                return AnswerBuilder.build_deterministic_answer(
                    decision_state="EXPERT_REVIEW_REQUIRED",
                    primary_candidate=None,
                    review_candidate={
                        "designation": rev_desig,
                        "title": c.get("title", ""),
                        "reason": "Standard lacks verified scope evidence in current knowledge base; expert engineering review required.",
                        "evidence_gaps": ["SCOPE_MISSING", "APPLICABILITY_EVIDENCE_MISSING"],
                        "evidence_ids": [f"EV_{rev_desig}"],
                    },
                    confidence="LOW",
                    explanation=f"Strong candidate {rev_desig} was retrieved, but complete scope evidence is unready in the current corpus. Expert review required.",
                )
            return AnswerBuilder.build_deterministic_answer(
                decision_state="NO_CONFIDENT_MATCH",
                primary_candidate=None,
                confidence="LOW",
                explanation="No sufficiently supported applicable Indian Standard was identified for the procurement specifications.",
            )

        # 3. Assess if multiple plausible candidates exist
        top = applicable_cands[0]
        top_cand = top["cand"]
        desig = top_cand.get("designation")
        title = top_cand.get("title")
        app = top["applicability"]
        life = top["lifecycle"]
        reg = top["regulatory"]

        alternatives = []
        for other in applicable_cands[1:]:
            c = other["cand"]
            alternatives.append({
                "designation": c.get("designation"),
                "title": c.get("title", ""),
                "reason": "Alternative technically supported candidate standard",
                "evidence_ids": [f"EV_{c.get('designation')}"],
            })

        # Only emit MULTIPLE_POSSIBLE_STANDARDS if explicitly flagged ambiguous or equal top parts
        if state.clarification_reason == "MULTIPLE_PLAUSIBLE_STANDARDS":
            desig_2 = applicable_cands[1]["cand"].get("designation") if len(applicable_cands) >= 2 else "alternate standard"
            return AnswerBuilder.build_deterministic_answer(
                decision_state="MULTIPLE_POSSIBLE_STANDARDS",
                primary_candidate=None,
                alternatives=alternatives,
                clarifications_needed=[f"Both {desig} and {desig_2} appear technically plausible. Please specify exact product subtype or application."],
                confidence="MEDIUM",
            )

        primary_candidate = {
            "designation": desig,
            "title": title,
            "applicability_state": app.get("applicability_state", "APPLICABLE"),
            "claim_level": "VERIFIED",
            "matched_attributes": app.get("matched_attributes", []),
            "reason": f"Standard matches procurement specifications for {app.get('matched_attributes', ['product'])}.",
            "evidence_ids": [f"EV_{desig}"],
        }

        # Format grounded explanation
        explanation = (
            f"Based on retrieved BIS evidence, {desig} ({title}) is the verified primary candidate "
            f"for this procurement requirement. Technical match is confirmed for attributes: {app.get('matched_attributes', [])}. "
            f"Lifecycle status is {life.get('lifecycle_state', 'ACTIVE_VALID')}. "
            f"{reg.get('statement', 'Regulatory mandatory status was not verified in the current regulatory corpus.')}"
        )

        return AnswerBuilder.build_deterministic_answer(
            decision_state="PRIMARY_RECOMMENDATION_AVAILABLE",
            primary_candidate=primary_candidate,
            alternatives=alternatives,
            normalized_requirements=reqs,
            lifecycle_meta=life,
            regulatory_meta=reg,
            confidence="HIGH",
            explanation=explanation,
        )

    # ── Finalize Response with Full Audit ──
    def _finalize_response(self, state: AgentState) -> Dict[str, Any]:
        ans = state.validated_answer or {}
        ans["agent_metadata"] = {
            "agent_run_id": state.agent_run_id,
            "execution_mode": state.execution_mode,
            "model_name": state.model_name,
            "step_count": state.step_count,
            "search_rounds": state.search_rounds,
            "revision_rounds": state.revision_rounds,
            "validator_status": state.validation_status,
            "validation_errors": state.validation_errors,
            "latency_ms": round((state.end_time - state.start_time) * 1000, 2) if state.end_time else 0.0,
            "engine_version": ENGINE_VERSION,
            "release_id": RELEASE_ID,
        }
        ans["tool_calls"] = state.tool_calls
        return ans

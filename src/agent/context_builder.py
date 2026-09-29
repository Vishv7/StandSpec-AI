"""
StandSpec AI — Compact Context Builder (Phase P1-F Section 32)
Formats compact, bounded evidence contexts for LLM consumption.
Enforces the RAG boundary: sends only verified excerpts and top candidates (5-10),
never internal paths, API keys, or raw graph dumps.
"""

from typing import Dict, Any, List, Optional
import json


class ContextBuilder:
    """Constructs bounded, token-efficient prompt contexts for the agent."""

    @staticmethod
    def build_planning_context(
        raw_query: str,
        requirements: Optional[Dict[str, Any]] = None,
        tool_results_summary: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Builds context for the planning/action step."""
        parts = [
            f"User Procurement Request: \"{raw_query}\"",
        ]

        if requirements:
            clean_reqs = {}
            for k, v in requirements.items():
                if isinstance(v, dict) and "value" in v:
                    clean_reqs[k] = v["value"]
                elif v:
                    clean_reqs[k] = v
            parts.append(f"Extracted Requirements: {json.dumps(clean_reqs, ensure_ascii=False)}")

        if tool_results_summary:
            parts.append("Previous Tool Actions and Findings:")
            for item in tool_results_summary[-4:]:  # Keep last 4 results to bound context
                tool_name = item.get("tool")
                status = item.get("status")
                summary = item.get("summary", "")
                parts.append(f"- Tool [{tool_name}] -> {status}: {summary}")

        return "\n\n".join(parts)

    @staticmethod
    def build_reasoning_context(
        raw_query: str,
        requirements: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        candidate_evidence: Dict[str, Any],
        candidate_applicability: Dict[str, Any],
        candidate_lifecycle: Dict[str, Any],
        candidate_regulatory: Dict[str, Any],
        top_n: int = 5,
    ) -> str:
        """
        Builds compact evidence context for comparing candidates and formulating final answer.
        Bounds candidate count to top_n (5-10).
        """
        parts = [
            f"User Procurement Request: \"{raw_query}\"",
        ]

        # Requirements summary
        clean_reqs = {}
        for k, v in requirements.items():
            if isinstance(v, dict) and "value" in v:
                clean_reqs[k] = v["value"]
            elif v:
                clean_reqs[k] = v
        parts.append(f"Technical Requirements: {json.dumps(clean_reqs, ensure_ascii=False)}")

        # Candidates reasoning block
        parts.append(f"Top {min(top_n, len(candidates))} Retrieved Candidate Standards (from BIS Index):")
        
        for idx, cand in enumerate(candidates[:top_n], start=1):
            desig = cand.get("designation", "Unknown")
            title = cand.get("title", "Unknown")
            role = cand.get("role", "PRIMARY_PRODUCT")
            dept = cand.get("department", "UNKNOWN")
            score = cand.get("retrieval_score", 0.0)

            cand_block = [
                f"{idx}. [{desig}] \"{title}\" (Role: {role}, Dept: {dept}, Score: {score})"
            ]

            # Applicability evidence
            app = candidate_applicability.get(desig, {})
            app_state = app.get("applicability_state", "UNKNOWN")
            matched = app.get("matched_attributes", [])
            mismatched = app.get("mismatched_attributes", [])
            cand_block.append(f"   - Applicability: {app_state} | Matched: {matched} | Mismatched: {mismatched}")

            # Lifecycle
            life = candidate_lifecycle.get(desig, {})
            life_state = life.get("lifecycle_state", "ACTIVE_VALID")
            rec_ed = life.get("recommended_edition", desig)
            cand_block.append(f"   - Lifecycle: {life_state} (Recommended Edition: {rec_ed})")

            # Regulatory
            reg = candidate_regulatory.get(desig, {})
            reg_state = reg.get("regulatory_state", "NOT_VERIFIED_IN_CURRENT_CORPUS")
            cand_block.append(f"   - Regulatory: {reg_state}")

            # Scope excerpt if available
            ev = candidate_evidence.get(desig, {})
            if isinstance(ev, dict) and ev.get("scope_summary"):
                cand_block.append(f"   - Scope: {ev['scope_summary'][:200]}...")

            parts.append("\n".join(cand_block))

        return "\n\n".join(parts)

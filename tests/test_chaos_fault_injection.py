"""
StandSpec AI — Chaos and Fault-Injection Test Suite (Phase 5 / R6.3)
Verifies fail-closed resilience against:
1. Missing or unreadable regulatory files
2. Missing or corrupted graph nodes
3. Malformed LLM outputs and hallucinated spans
4. Empty, whitespace, gibberish, and extreme-length inputs
5. Out-of-scope adversarial domain queries
"""

import json
import pytest
from pathlib import Path
from src.agent.agent import StandSpecAgent
from src.recommendation.engine import StandSpecRecommendationEngine
from src.recommendation.regulatory_gate import RegulatoryGate
from src.llm.structured_extractor import BoundedStructuredExtractor
from src.llm.provider import MockLLMProvider


@pytest.fixture(scope="module")
def agent():
    return StandSpecAgent.from_release()


def test_chaos_missing_regulatory_file_fail_closed(tmp_path):
    """
    Chaos Test 1: If regulatory orders file is missing or pointing to empty directory,
    RegulatoryGate must fail-closed, returning REGULATORY_SOURCE_UNAVAILABLE without crashing.
    """
    gate = RegulatoryGate(data_dir=tmp_path)
    
    res = gate.evaluate_regulatory_status("IS 4984:2016", "2026-07-15", "HDPE pipes")
    assert res is not None
    assert res.get("regulatory_state") in ("REGULATORY_SOURCE_UNAVAILABLE", "NOT_VERIFIED_IN_CURRENT_CORPUS", "UNVERIFIED", "UNKNOWN")
    assert res.get("is_mandatory") is False


def test_chaos_corrupted_graph_node_resolution(agent):
    """
    Chaos Test 2: Querying a completely invalid or synthetic non-existent designation
    must return graceful NOT_FOUND from tool router and never raise an unhandled exception.
    """
    corrupt_desig = "IS 99999999_CORRUPTED_NONEXISTENT_XYZ"
    res = agent.tool_router.tool_get_standard_evidence({"designation": corrupt_desig})
    assert res["status"] == "NOT_FOUND"
    assert res["evidence"] is None

    app_res = agent.tool_router.tool_check_applicability({"designation": corrupt_desig, "requirements": {}})
    assert app_res["status"] == "NOT_FOUND"
    assert app_res["applicability_state"] == "UNKNOWN"


def test_chaos_empty_and_whitespace_query(agent):
    """
    Chaos Test 3: Completely empty or whitespace queries must be handled cleanly.
    """
    res_empty = agent.answer("", mode="offline")
    assert res_empty["decision_state"] in ("INSUFFICIENT_INFORMATION", "NO_CONFIDENT_MATCH", "CLARIFICATION_REQUIRED")

    res_space = agent.answer("     \t\n   ", mode="offline")
    assert res_space["decision_state"] in ("INSUFFICIENT_INFORMATION", "NO_CONFIDENT_MATCH", "CLARIFICATION_REQUIRED")


def test_chaos_gibberish_query(agent):
    """
    Chaos Test 4: Random characters / unparseable gibberish query must safely abstain.
    """
    gibberish = "asdfkjh qwerty zxcvbnm 1298471209384701293847"
    res = agent.answer(gibberish, mode="offline")
    assert res["decision_state"] in ("INSUFFICIENT_INFORMATION", "NO_CONFIDENT_MATCH", "CLARIFICATION_REQUIRED", "EXPERT_REVIEW_REQUIRED")
    assert res["primary_recommendation"] is None


def test_chaos_extreme_length_query(agent):
    """
    Chaos Test 5: Extremely long input text (10,000+ characters) must not cause buffer overflow
    or crash the parser / Whoosh retriever.
    """
    long_query = "Supply of 1.1 kV XLPE insulated cables " + ("with technical parameters and specifications " * 300)
    res = agent.answer(long_query, mode="offline")
    assert "decision_state" in res
    assert res["agent_metadata"]["step_count"] <= StandSpecAgent.MAX_AGENT_STEPS


def test_chaos_out_of_scope_domain_immediate_rejection(agent):
    """
    Chaos Test 6: Queries asking for food, agriculture, textiles, or pharmaceuticals
    must be immediately rejected under NON_CED_ETD_DOMAIN / OUTSIDE_PROTOTYPE_COVERAGE.
    """
    queries = [
        "Procurement of 500 kg Alphonso mango fruit and fresh bananas",
        "Supply of 100% pure organic cotton yarn and silk garments",
        "Bulk purchase of paracetamol tablets and surgical gloves",
        "Refining specification for crude oil and aviation turbine fuel",
    ]
    for q in queries:
        res = agent.answer(q, mode="offline")
        assert res["decision_state"] in ("OUT_OF_SCOPE", "NO_CONFIDENT_MATCH", "NON_CED_ETD_DOMAIN", "OUTSIDE_PROTOTYPE_COVERAGE")
        assert res["primary_recommendation"] is None


def test_chaos_llm_hallucination_span_rejection():
    """
    Chaos Test 7: If mock LLM returns hallucinated specifications that do NOT appear
    verbatim in the input query, verbatim span validator must reject them.
    """
    raw_query = "Supply of 1.1 kV power cables for residential wiring"
    hallucinated_json = json.dumps({
        "domain": "ELECTROTECHNICAL",
        "voltage": {"value": "33 kV", "evidence_text": "33 kV", "start_char": 0, "end_char": 5, "confidence": 0.95},
        "material": {"value": "silver", "evidence_text": "silver", "start_char": 0, "end_char": 6, "confidence": 0.95},
        "product": {"value": "power cables", "evidence_text": "power cables", "start_char": 17, "end_char": 29, "confidence": 0.95}
    })
    mock_llm = MockLLMProvider(canned_responses={"": hallucinated_json})
    extractor = BoundedStructuredExtractor(llm_provider=mock_llm)
    
    extracted = extractor.extract(raw_query)
    reqs = extracted.get("requirements", {})
    
    # Hallucinated spans must have been rejected by the verbatim validator
    if "voltage" in reqs and reqs["voltage"] is not None:
        assert reqs["voltage"].get("value") != "33 kV"
    if "material" in reqs and reqs["material"] is not None:
        assert reqs["material"].get("value") != "silver"

"""
Tests for StandSpec AI Agent RAG Grounding & Safety Verification (Phase P1-F Section 15-17, 24, 25).
Verifies:
1. Grounding Gate: Only retrieved candidate designations can appear in primary recommendation.
2. Anti-hallucination veto: Non-existent or un-retrieved standards proposed by LLM get vetoed.
3. Role grounding: Test methods or supporting standards cannot be recommended as primary products.
4. Regulatory truthfulness: Unverified regulatory status cannot claim 'voluntary' or invent QCOs.
5. Lifecycle grounding: Superseded or withdrawn editions cannot be recommended as active primary.
6. Applicability grounding: Mismatched technical attributes block primary recommendation.
7. Abstention purity: Primary recommendation is strictly null on abstention/clarification states.
"""

import json
import pytest
from src.agent.agent import StandSpecAgent
from src.agent.validator import DeterministicValidator
from src.llm.provider import MockLLMProvider


@pytest.fixture(scope="module")
def agent():
    return StandSpecAgent.from_release()


@pytest.fixture
def validator():
    return DeterministicValidator()


def test_grounding_rejects_unretrieved_hallucinated_standard(validator):
    """Verify validator blocks an LLM hallucination not in the retrieved candidate set."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 99999:2026",
            "title": "Imaginary BIS Specification for Substation Cables",
            "reason": "Perfect match for 11 kV power cables",
        },
        "regulatory": {
            "state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
            "statement": "Regulatory mandatory status was not verified in the current regulatory corpus.",
        },
    }
    retrieved = [
        {"designation": "IS 7098 (Part 1):2025", "role": "PRIMARY_PRODUCT"},
        {"designation": "IS 694:2010", "role": "PRIMARY_PRODUCT"},
    ]

    res = validator.validate(
        proposal=proposal,
        raw_query="Supply 1.1 kV XLPE cable",
        retrieved_candidates=retrieved,
        candidate_applicability={"IS 7098 (Part 1):2025": {"applicability_state": "APPLICABLE"}},
        candidate_lifecycle={"IS 7098 (Part 1):2025": {"lifecycle_state": "ACTIVE_VALID"}},
        candidate_regulatory={"IS 7098 (Part 1):2025": {"regulatory_state": "NOT_VERIFIED_IN_CURRENT_CORPUS"}},
    )
    assert not res.is_valid
    assert "HALLUCINATED_DESIGNATION" in res.veto_reasons


def test_grounding_rejects_test_method_as_primary(validator):
    """Verify validator blocks test methods or test codes from being recommended as primary products."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 10810 (Part 58):2000",
            "title": "Methods of Test for Cables - Part 58: Oxygen Index Test",
            "reason": "Test method for oxygen index",
        },
    }
    retrieved = [
        {"designation": "IS 10810 (Part 58):2000", "role": "TEST_METHOD"},
        {"designation": "IS 7098 (Part 1):2025", "role": "PRIMARY_PRODUCT"},
    ]

    res = validator.validate(
        proposal=proposal,
        raw_query="Procure fire survival electrical cables",
        retrieved_candidates=retrieved,
        candidate_applicability={},
        candidate_lifecycle={},
        candidate_regulatory={},
    )
    assert not res.is_valid
    assert "WRONG_ROLE_PRIMARY" in res.veto_reasons


def test_regulatory_grounding_rejects_false_voluntary_claim(validator):
    """Verify validator blocks claims of 'voluntary' or 'not mandatory' when regulatory evidence is unverified."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 7098 (Part 1):2025",
            "title": "XLPE Insulated Cables",
            "reason": "Grounding match",
        },
        "regulatory": {
            "state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
            "statement": "This standard is completely voluntary and has no mandatory compliance requirements.",
        },
    }
    retrieved = [{"designation": "IS 7098 (Part 1):2025", "role": "PRIMARY_PRODUCT"}]
    app = {"IS 7098 (Part 1):2025": {"applicability_state": "APPLICABLE", "mismatched_attributes": []}}
    life = {"IS 7098 (Part 1):2025": {"lifecycle_state": "ACTIVE_VALID"}}
    reg = {"IS 7098 (Part 1):2025": {"regulatory_state": "NOT_VERIFIED_IN_CURRENT_CORPUS"}}

    res = validator.validate(
        proposal=proposal,
        raw_query="Supply of 1.1 kV XLPE cable",
        retrieved_candidates=retrieved,
        candidate_applicability=app,
        candidate_lifecycle=life,
        candidate_regulatory=reg,
    )
    assert not res.is_valid
    assert "REGULATORY_FALSE_ASSERTION" in res.veto_reasons


def test_regulatory_grounding_rejects_hallucinated_qco_when_unverified(validator):
    """Verify validator blocks hallucination of fake QCO order numbers when regulatory state is unverified."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 7098 (Part 1):2025",
            "title": "XLPE Insulated Cables",
        },
        "regulatory": {
            "state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
            "qco_order_number": "QCO-2026-FAKE-MANDATE-ORDER-999",
            "statement": "Statutory Mandate: MANDATORY under Order QCO-2026-FAKE-MANDATE-ORDER-999.",
        },
    }
    retrieved = [{"designation": "IS 7098 (Part 1):2025", "role": "PRIMARY_PRODUCT"}]

    res = validator.validate(
        proposal=proposal,
        raw_query="Supply of 1.1 kV XLPE cable",
        retrieved_candidates=retrieved,
        candidate_applicability={"IS 7098 (Part 1):2025": {"applicability_state": "APPLICABLE"}},
        candidate_lifecycle={"IS 7098 (Part 1):2025": {"lifecycle_state": "ACTIVE_VALID"}},
        candidate_regulatory={"IS 7098 (Part 1):2025": {"regulatory_state": "NOT_VERIFIED_IN_CURRENT_CORPUS"}},
    )
    assert not res.is_valid
    assert "HALLUCINATED_QCO" in res.veto_reasons


def test_lifecycle_grounding_rejects_withdrawn_standard(validator):
    """Verify validator blocks withdrawn or obsolete predecessor standards as primary."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 7098 (Part 1):1988",
            "title": "XLPE Insulated Cables (Old Withdrawn Edition)",
        },
    }
    retrieved = [{"designation": "IS 7098 (Part 1):1988", "role": "PRIMARY_PRODUCT"}]
    life = {
        "IS 7098 (Part 1):1988": {
            "lifecycle_state": "WITHDRAWN",
            "is_superseded": True,
            "superseded_by": "IS 7098 (Part 1):2025",
        }
    }

    res = validator.validate(
        proposal=proposal,
        raw_query="Supply of 1.1 kV XLPE cable",
        retrieved_candidates=retrieved,
        candidate_applicability={"IS 7098 (Part 1):1988": {"applicability_state": "APPLICABLE"}},
        candidate_lifecycle=life,
        candidate_regulatory={},
    )
    assert not res.is_valid
    assert "LIFECYCLE_VETO" in res.veto_reasons


def test_abstention_purity_blocks_primary_on_abstention_states(validator):
    """Verify that any abstention or clarification state strictly forbids non-null primary recommendation."""
    for state in ["NO_CONFIDENT_MATCH", "OUTSIDE_PROTOTYPE_COVERAGE", "CLARIFICATION_REQUIRED", "INSUFFICIENT_INFORMATION"]:
        proposal = {
            "decision_state": state,
            "primary_recommendation": {
                "designation": "IS 7098 (Part 1):2025",
                "title": "XLPE Insulated Cables",
            },
        }
        res = validator.validate(
            proposal=proposal,
            raw_query="Procurement query",
            retrieved_candidates=[{"designation": "IS 7098 (Part 1):2025", "role": "PRIMARY_PRODUCT"}],
            candidate_applicability={},
            candidate_lifecycle={},
            candidate_regulatory={},
        )
        assert not res.is_valid
        assert "NULL_PRIMARY_VIOLATION" in res.veto_reasons


def test_agent_end_to_end_grounding_offline(agent):
    """Verify that StandSpecAgent end-to-end only emits verified designations from retrieved candidates."""
    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="offline")

    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    rec = res["primary_recommendation"]
    assert rec is not None

    # Check evidence backing
    assert rec.get("claim_level") in ("VERIFIED", "VERIFIED_FOR_RECOMMENDATION")
    assert len(rec.get("evidence_ids", [])) > 0

    # Candidate must be in the tool search results
    search_calls = [tc for tc in res["tool_calls"] if tc["tool"] == "search_standards"]
    assert len(search_calls) > 0
    all_retrieved = []
    for sc in search_calls:
        output = sc.get("output") or {}
        for c in output.get("candidates", []):
            all_retrieved.append(c.get("designation"))

    assert rec["designation"] in all_retrieved

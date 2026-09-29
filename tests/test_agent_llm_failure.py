"""
Tests for StandSpec AI Agent LLM Failure Handling & Fallback Hardening (Phase P1-F Section 36, 37).
Verifies:
1. Malformed JSON from LLM: Graceful fallback to deterministic engine without crashing.
2. Exception / Timeout in LLM: Seamless fallback to deterministic recommendation.
3. Provider unavailable: Hermetic offline execution in DETERMINISTIC_ONLY mode.
4. Revision recovery: LLM proposes invalid answer first, succeeds on revision round.
5. Revision exhaustion: Repeated invalid LLM proposals fall back to deterministic safety baseline.
"""

import json
import pytest
from src.agent.agent import StandSpecAgent
from src.llm.provider import BaseLLMProvider, MockLLMProvider


class FailingLLMProvider(BaseLLMProvider):
    """LLM provider that always raises an exception."""
    def __init__(self, exc_to_raise: Exception):
        self.exc_to_raise = exc_to_raise

    def generate(self, prompt: str, system_instruction: str = None, json_mode: bool = False) -> str:
        raise self.exc_to_raise

    def is_available(self) -> bool:
        return True


class MalformedJsonLLMProvider(BaseLLMProvider):
    """LLM provider that returns unparseable or truncated JSON strings."""
    def __init__(self, malformed_text: str = "{ invalid json: true, broken..."):
        self.malformed_text = malformed_text

    def generate(self, prompt: str, system_instruction: str = None, json_mode: bool = False) -> str:
        return self.malformed_text

    def is_available(self) -> bool:
        return True


class SequenceMockLLMProvider(BaseLLMProvider):
    """LLM provider returning a sequence of responses across successive calls."""
    def __init__(self, responses: list):
        self.responses = list(responses)
        self.call_count = 0
        self.prompts_received = []

    def generate(self, prompt: str, system_instruction: str = None, json_mode: bool = False) -> str:
        self.prompts_received.append(prompt)
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return self.responses[-1]

    def is_available(self) -> bool:
        return True


@pytest.fixture(scope="module")
def base_agent():
    return StandSpecAgent.from_release()


def test_agent_handles_malformed_json_fallback(base_agent):
    """Verify agent catches malformed JSON from LLM and falls back to deterministic decision."""
    malformed_provider = MalformedJsonLLMProvider("{'bad': truncated json...")
    agent = StandSpecAgent(engine=base_agent.engine, llm_provider=malformed_provider)

    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="llm")

    # Agent must NOT crash and must fall back safely
    assert res is not None
    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    assert "IS 7098 (Part 1)" in res["primary_recommendation"]["designation"]
    assert res["agent_metadata"]["execution_mode"] == "LLM_FALLBACK"
    assert res["agent_metadata"]["validator_status"] == "ACCEPT"


def test_agent_handles_llm_timeout_fallback(base_agent):
    """Verify agent catches timeout or connection error and falls back to deterministic decision."""
    timeout_provider = FailingLLMProvider(TimeoutError("Gemini API connection timed out after 10.0s"))
    agent = StandSpecAgent(engine=base_agent.engine, llm_provider=timeout_provider)

    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="llm")

    assert res is not None
    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    assert res["primary_recommendation"] is not None
    assert res["agent_metadata"]["execution_mode"] == "LLM_FALLBACK"


def test_agent_runs_offline_when_provider_is_none(base_agent):
    """Verify agent runs hermetically offline when no LLM provider is configured."""
    agent = StandSpecAgent(engine=base_agent.engine, llm_provider=None)

    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="offline")

    assert res["agent_metadata"]["execution_mode"] == "DETERMINISTIC_ONLY"
    assert res["decision_state"] == "PRIMARY_RECOMMENDATION_AVAILABLE"
    assert "IS 7098 (Part 1)" in res["primary_recommendation"]["designation"]


def test_agent_revision_success_flow(base_agent):
    """Verify agent rejects flawed initial proposal, asks LLM to revise with error feedback, and accepts valid revision."""
    invalid_first_proposal = json.dumps({
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 99999:2099",  # Hallucinated standard
            "title": "Fake Standard",
        },
        "alternative_standards": [],
        "clarifications_needed": [],
        "confidence": "HIGH",
    })

    valid_revised_proposal = json.dumps({
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 7098 (Part 1):2025",
            "title": "Crosslinked Polyethylene Insulated Cables",
            "reason": "Matches 1.1 kV XLPE requirements",
            "applicability_state": "APPLICABLE",
            "claim_level": "VERIFIED",
            "evidence_ids": ["EV_IS 7098 (Part 1):2025"],
            "matched_attributes": ["PRODUCT", "VOLTAGE", "MATERIAL"],
        },
        "alternative_standards": [],
        "review_candidate": None,
        "clarifications_needed": [],
        "confidence": "HIGH",
        "regulatory": {
            "state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
            "statement": "Regulatory mandatory status was not verified in the current regulatory corpus.",
        },
        "natural_language_explanation": "IS 7098 (Part 1):2025 matches the procurement specifications.",
    })

    seq_provider = SequenceMockLLMProvider([invalid_first_proposal, valid_revised_proposal])
    agent = StandSpecAgent(engine=base_agent.engine, llm_provider=seq_provider)

    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="llm")

    # Check that revision was triggered
    assert seq_provider.call_count == 2
    assert "HALLUCINATED_DESIGNATION" in seq_provider.prompts_received[1] or "REJECTED" in seq_provider.prompts_received[1]

    # Accepted response
    assert res["agent_metadata"]["execution_mode"] == "LLM_ASSISTED"
    assert res["agent_metadata"]["revision_rounds"] == 1
    assert res["agent_metadata"]["validator_status"] == "ACCEPT"
    assert res["primary_recommendation"]["designation"] == "IS 7098 (Part 1):2025"


def test_agent_revision_exhaustion_fallback(base_agent):
    """Verify that if LLM fails both initial proposal and revision, agent safely falls back to deterministic recommendation."""
    repeated_invalid = json.dumps({
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 99999:2099",  # Repeated hallucination
            "title": "Fake Standard",
        },
        "alternative_standards": [],
        "clarifications_needed": [],
        "confidence": "HIGH",
    })

    seq_provider = SequenceMockLLMProvider([repeated_invalid, repeated_invalid])
    agent = StandSpecAgent(engine=base_agent.engine, llm_provider=seq_provider)

    query = "Supply of 1.1 kV XLPE insulated three-core power cables"
    res = agent.answer(query, mode="llm")

    assert res["agent_metadata"]["execution_mode"] == "LLM_FALLBACK"
    assert res["agent_metadata"]["validator_status"] == "ACCEPT"
    assert res["primary_recommendation"] is not None
    assert "IS 7098 (Part 1)" in res["primary_recommendation"]["designation"]

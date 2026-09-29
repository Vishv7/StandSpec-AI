"""
Tests for StandSpec AI Deterministic Safety Validator (Phase P1-F Section 15-17)
Verifies all 7 safety gates:
1. Candidate presence (anti-hallucination)
2. Role validity (no test methods or supporting standards as primary product)
3. Technical applicability mismatch veto
4. Explicit requested standard conflict check (uPVC pipes with IS 1180)
5. Lifecycle veto (no withdrawn standards)
6. Regulatory truthfulness (no false voluntary claims on unverified status)
7. Null primary enforcement on abstention states
"""

import pytest
from src.agent.validator import DeterministicValidator


@pytest.fixture
def validator():
    return DeterministicValidator()


def test_validator_accepts_valid_proposal(validator):
    """Verify that a compliant, evidence-backed proposal passes validation."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 4984:2016",
            "title": "Polyethylene Pipes for Water Supply",
            "applicability_state": "APPLICABLE",
            "matched_attributes": ["product", "pressure"],
        },
        "regulatory": {
            "state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
            "statement": "Regulatory mandatory status was not verified in the current regulatory corpus.",
        },
    }
    retrieved = [{"designation": "IS 4984:2016", "role": "PRIMARY_PRODUCT"}]
    app = {"IS 4984:2016": {"applicability_state": "APPLICABLE", "mismatched_attributes": []}}
    life = {"IS 4984:2016": {"lifecycle_state": "ACTIVE_VALID"}}
    reg = {"IS 4984:2016": {"regulatory_state": "NOT_VERIFIED_IN_CURRENT_CORPUS"}}

    res = validator.validate(
        proposal=proposal,
        raw_query="Supply of polyethylene pipes for water distribution",
        retrieved_candidates=retrieved,
        candidate_applicability=app,
        candidate_lifecycle=life,
        candidate_regulatory=reg,
    )
    assert res.is_valid
    assert len(res.errors) == 0


def test_validator_vetoes_hallucinated_designation(validator):
    """Verify validator rejects a designation not in retrieved candidates or requested."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 99999:2099",
            "title": "Hallucinated Standard",
        },
    }
    retrieved = [{"designation": "IS 4984:2016", "role": "PRIMARY_PRODUCT"}]

    res = validator.validate(
        proposal=proposal,
        raw_query="Supply of pipes",
        retrieved_candidates=retrieved,
        candidate_applicability={},
        candidate_lifecycle={},
        candidate_regulatory={},
    )
    assert not res.is_valid
    assert "HALLUCINATED_DESIGNATION" in res.veto_reasons


def test_validator_vetoes_wrong_role_primary(validator):
    """Verify validator rejects test method standard proposed as primary product."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 10810 (Part 1)",
            "title": "Methods of Test for Cables",
        },
    }
    retrieved = [{"designation": "IS 10810 (Part 1)", "role": "TEST_METHOD"}]

    res = validator.validate(
        proposal=proposal,
        raw_query="Procure 11 kV XLPE insulated power cables",
        retrieved_candidates=retrieved,
        candidate_applicability={},
        candidate_lifecycle={},
        candidate_regulatory={},
    )
    assert not res.is_valid
    assert "WRONG_ROLE_PRIMARY" in res.veto_reasons


def test_validator_vetoes_applicability_mismatch(validator):
    """Verify validator rejects candidate with attribute mismatch or NOT_APPLICABLE status."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 1239",
            "title": "Steel Tubes",
        },
    }
    retrieved = [{"designation": "IS 1239", "role": "PRIMARY_PRODUCT"}]
    app = {"IS 1239": {"applicability_state": "NOT_APPLICABLE", "mismatched_attributes": ["material"]}}

    res = validator.validate(
        proposal=proposal,
        raw_query="Procure HDPE pipes for drinking water",
        retrieved_candidates=retrieved,
        candidate_applicability=app,
        candidate_lifecycle={},
        candidate_regulatory={},
    )
    assert not res.is_valid
    assert "APPLICABILITY_MISMATCH" in res.veto_reasons or "ATTRIBUTE_MISMATCH" in res.veto_reasons


def test_validator_vetoes_requested_standard_mismatch_upvc_is_1180(validator):
    """
    CRITICAL SAFETY TEST:
    Explicit request 'Supply of uPVC pipes as per IS 1180 Part 1'.
    IS 1180 is for transformers, not uPVC pipes.
    Validator must veto any attempt to recommend IS 1180 as primary!
    """
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 1180 (Part 1)",
            "title": "Outdoor Type Distribution Transformers",
        },
    }
    retrieved = [{"designation": "IS 1180 (Part 1)", "role": "PRIMARY_PRODUCT"}]
    app = {
        "IS 1180 (Part 1)": {
            "applicability_state": "NOT_APPLICABLE",
            "mismatched_attributes": ["product", "material"],
        }
    }

    res = validator.validate(
        proposal=proposal,
        raw_query="Supply of uPVC pipes as per IS 1180 Part 1",
        retrieved_candidates=retrieved,
        candidate_applicability=app,
        candidate_lifecycle={},
        candidate_regulatory={},
        requested_designations=["IS 1180 Part 1"],
    )
    assert not res.is_valid
    assert "REQUESTED_STANDARD_MISMATCH" in res.veto_reasons


def test_validator_vetoes_withdrawn_lifecycle(validator):
    """Verify validator vetoes a withdrawn standard proposed as primary."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 1000:1980",
            "title": "Withdrawn Standard",
        },
    }
    retrieved = [{"designation": "IS 1000:1980", "role": "PRIMARY_PRODUCT"}]
    life = {"IS 1000:1980": {"lifecycle_state": "WITHDRAWN"}}

    res = validator.validate(
        proposal=proposal,
        raw_query="Procure equipment",
        retrieved_candidates=retrieved,
        candidate_applicability={"IS 1000:1980": {"applicability_state": "APPLICABLE"}},
        candidate_lifecycle=life,
        candidate_regulatory={},
    )
    assert not res.is_valid
    assert "LIFECYCLE_VETO" in res.veto_reasons


def test_validator_vetoes_false_voluntary_regulatory_claim(validator):
    """Verify validator vetoes claim that standard is voluntary when status is unverified."""
    proposal = {
        "decision_state": "PRIMARY_RECOMMENDATION_AVAILABLE",
        "primary_recommendation": {
            "designation": "IS 4984:2016",
            "title": "Polyethylene Pipes",
        },
        "regulatory": {
            "state": "NOT_VERIFIED_IN_CURRENT_CORPUS",
            "statement": "This standard is completely voluntary and not mandatory.",
        },
    }
    retrieved = [{"designation": "IS 4984:2016", "role": "PRIMARY_PRODUCT"}]

    res = validator.validate(
        proposal=proposal,
        raw_query="Procure polyethylene pipes",
        retrieved_candidates=retrieved,
        candidate_applicability={"IS 4984:2016": {"applicability_state": "APPLICABLE"}},
        candidate_lifecycle={"IS 4984:2016": {"lifecycle_state": "ACTIVE_VALID"}},
        candidate_regulatory={"IS 4984:2016": {"regulatory_state": "NOT_VERIFIED_IN_CURRENT_CORPUS"}},
    )
    assert not res.is_valid
    assert "REGULATORY_FALSE_ASSERTION" in res.veto_reasons


def test_validator_vetoes_primary_on_abstention_states(validator):
    """Verify that NO_CONFIDENT_MATCH or OUTSIDE_PROTOTYPE_COVERAGE cannot have primary recommendation."""
    proposal = {
        "decision_state": "NO_CONFIDENT_MATCH",
        "primary_recommendation": {
            "designation": "IS 4984:2016",
            "title": "Polyethylene Pipes",
        },
    }
    res = validator.validate(
        proposal=proposal,
        raw_query="Procure something unknown",
        retrieved_candidates=[{"designation": "IS 4984:2016"}],
        candidate_applicability={},
        candidate_lifecycle={},
        candidate_regulatory={},
    )
    assert not res.is_valid
    assert "NULL_PRIMARY_VIOLATION" in res.veto_reasons

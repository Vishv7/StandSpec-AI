"""
Tests for Calibration Subsystem (Phase 12 / Calibration & Abstention).
Verifies Platt scaling, Temperature scaling, ECE, Brier Score, and Selective Abstention policy.
"""

import pytest
from src.calibration import (
    PlattScaler,
    TemperatureScaler,
    compute_ece,
    compute_brier_score,
    compute_risk_coverage,
    compute_false_confident_rate,
    SelectiveAbstentionPolicy,
    CalibrationFeatureExtractor,
)


def test_platt_scaler_monotonicity():
    scaler = PlattScaler(a=2.0, b=-1.0)
    p_low = scaler.predict_proba(0.2)
    p_med = scaler.predict_proba(0.5)
    p_high = scaler.predict_proba(0.9)

    assert 0.0 <= p_low <= 1.0
    assert 0.0 <= p_med <= 1.0
    assert 0.0 <= p_high <= 1.0
    assert p_low < p_med < p_high


def test_temperature_scaler_scaling():
    ts = TemperatureScaler(temperature=2.0)
    p = ts.predict_proba(2.0)
    # sigma(2.0 / 2.0) = sigma(1.0) ~ 0.731
    assert 0.70 <= p <= 0.75


def test_ece_and_brier_score():
    # Perfectly calibrated dummy predictions
    probs = [0.1, 0.2, 0.8, 0.9]
    labels = [0, 0, 1, 1]
    brier = compute_brier_score(probs, labels)
    ece = compute_ece(probs, labels, n_bins=5)

    assert brier >= 0.0
    assert ece >= 0.0
    assert brier < 0.1  # Very low error for good predictions


def test_risk_coverage_curve():
    probs = [0.95, 0.85, 0.75, 0.40, 0.20]
    labels = [1, 1, 1, 0, 0]
    curve = compute_risk_coverage(probs, labels, thresholds=[0.3, 0.7, 0.9])

    assert len(curve) == 3
    # At threshold 0.9, only 1 covered (coverage = 0.2, risk = 0.0)
    high_t = [c for c in curve if c["threshold"] == 0.9][0]
    assert high_t["coverage"] == 0.2
    assert high_t["risk"] == 0.0


def test_selective_abstention_policy_empty():
    policy = SelectiveAbstentionPolicy()
    state, reason, primary, viable = policy.decide([])
    assert state == "NO_CONFIDENT_MATCH"
    assert primary is None
    assert "No candidate" in reason


def test_selective_abstention_policy_recommendation():
    policy = SelectiveAbstentionPolicy(tau_recommend=0.50)
    recs = [
        {"standard_designation": "IS 7098 (Part 2):2011", "confidence_score": 0.95},
        {"standard_designation": "IS 1554 (Part 1):1988", "confidence_score": 0.30},
    ]
    state, reason, primary, viable = policy.decide(recs)
    assert state == "PRIMARY_RECOMMENDATION_AVAILABLE"
    assert primary["standard_designation"] == "IS 7098 (Part 2):2011"
    assert reason is None


def test_selective_abstention_policy_ambiguity():
    policy = SelectiveAbstentionPolicy(delta_margin=0.08)
    recs = [
        {"standard_designation": "IS 4984:2016", "confidence_score": 0.95},
        {"standard_designation": "IS 14885:2022", "confidence_score": 0.94},
    ]
    state, reason, primary, viable = policy.decide(recs)
    assert state == "MULTIPLE_POSSIBLE_STANDARDS"
    assert "margin" in reason.lower()

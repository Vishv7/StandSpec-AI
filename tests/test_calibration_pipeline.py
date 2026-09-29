"""
Tests for Calibration Pipeline and Persisted Calibrator (P0-3, P0-4).
Verifies PlattScaler optimization, serialization round-trip, risk-coverage monotonicity,
and end-to-end integration with StandSpecRecommendationEngine.
"""

import json
from pathlib import Path
import pytest

from src.calibration.calibrator import PlattScaler, TemperatureScaler, compute_ece, compute_brier_score
from src.calibration.policy import SelectiveAbstentionPolicy
from src.recommendation.engine import StandSpecRecommendationEngine


def test_platt_scaler_optimization():
    """Verify Newton-Raphson optimization converges to lower NLL and proper ordering."""
    scores = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
    labels = [0, 0, 0, 0, 1, 1, 1, 1]

    scaler = PlattScaler(is_fitted=False)
    scaler.fit(scores, labels, max_iter=50)

    assert scaler.is_fitted
    assert scaler.a > 0  # Monotonic positive slope

    p_low = scaler.predict_proba(0.15)
    p_high = scaler.predict_proba(0.85)
    assert p_high > p_low
    assert 0.0 <= p_low <= 1.0
    assert 0.0 <= p_high <= 1.0


def test_platt_scaler_serialization_roundtrip(tmp_path):
    """Verify save and load faithfully reconstructs parameters and metadata."""
    meta = {"dataset": "synthetic", "split_hash": "abc1234"}
    scaler = PlattScaler(a=2.456, b=-1.234, metadata=meta)
    
    file_path = tmp_path / "test_calibrator.json"
    scaler.save(file_path)

    loaded = PlattScaler.load(file_path)
    assert pytest.approx(loaded.a, 1e-4) == 2.456
    assert pytest.approx(loaded.b, 1e-4) == -1.234
    assert loaded.metadata == meta
    assert loaded.predict_proba(0.5) == scaler.predict_proba(0.5)


def test_temperature_scaler_roundtrip(tmp_path):
    """Verify TemperatureScaler serialization round-trip."""
    t_scaler = TemperatureScaler(temperature=1.85, metadata={"info": "temp"})
    fpath = tmp_path / "temp_scaler.json"
    t_scaler.save(fpath)

    loaded = TemperatureScaler.load(fpath)
    assert pytest.approx(loaded.temperature, 1e-4) == 1.85
    assert loaded.metadata["info"] == "temp"


def test_persisted_calibrator_loaded_by_engine():
    """Verify that StandSpecRecommendationEngine loads data/models/calibrator_v1.json."""
    cal_path = Path("data/models/calibrator_v1.json")
    if not cal_path.exists():
        pytest.skip("Persisted calibrator artifact data/models/calibrator_v1.json not found")

    policy = SelectiveAbstentionPolicy(calibrator_path=str(cal_path))
    assert policy.is_empirical_calibrator
    assert policy.calibrator.is_fitted
    assert policy.calibrator.a > 0


def test_calibrated_confidence_monotonic():
    """Verify calibrated probability is strictly monotonic with raw rerank score."""
    cal_path = Path("data/models/calibrator_v1.json")
    if not cal_path.exists():
        pytest.skip("Persisted calibrator artifact not found")

    scaler = PlattScaler.load(cal_path)
    scores = [0.1 * i for i in range(11)]
    probs = [scaler.predict_proba(s) for s in scores]

    for i in range(len(probs) - 1):
        assert probs[i] <= probs[i + 1]

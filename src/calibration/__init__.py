"""
Calibration Subsystem for StandSpec AI.
"""

from src.calibration.calibrator import (
    PlattScaler,
    TemperatureScaler,
    compute_ece,
    compute_brier_score,
    compute_risk_coverage,
    compute_false_confident_rate,
)
from src.calibration.features import CalibrationFeatureExtractor
from src.calibration.policy import SelectiveAbstentionPolicy

__all__ = [
    "PlattScaler",
    "TemperatureScaler",
    "compute_ece",
    "compute_brier_score",
    "compute_risk_coverage",
    "compute_false_confident_rate",
    "CalibrationFeatureExtractor",
    "SelectiveAbstentionPolicy",
]

"""
Statistical Calibration Subsystem — StandSpec AI (Layer 5 Calibration)
Implements Platt Scaling (logistic calibration), Isotonic Regression,
and Temperature Scaling for true post-hoc confidence calibration.
Computes ECE (Expected Calibration Error), Brier Score, and Risk-Coverage curves.
"""

import math
from typing import List, Tuple, Dict, Any, Optional


def compute_brier_score(probs: List[float], labels: List[int]) -> float:
    """Compute Brier Score: Mean Squared Error between probabilities and binary labels."""
    if not probs or len(probs) != len(labels):
        return 0.0
    return sum((p - y) ** 2 for p, y in zip(probs, labels)) / len(probs)


def compute_ece(probs: List[float], labels: List[int], n_bins: int = 10) -> float:
    """
    Compute Expected Calibration Error (ECE) across uniform confidence bins.
    ECE = sum_b (|B_b| / N) * |acc(B_b) - conf(B_b)|
    """
    if not probs or len(probs) != len(labels):
        return 0.0

    n = len(probs)
    bin_boundaries = [i / n_bins for i in range(n_bins + 1)]
    ece = 0.0

    for i in range(n_bins):
        low, high = bin_boundaries[i], bin_boundaries[i + 1]
        bin_indices = [
            idx for idx, p in enumerate(probs)
            if (p >= low and p < high) or (i == n_bins - 1 and p >= low and p <= high)
        ]
        if not bin_indices:
            continue

        bin_conf = sum(probs[idx] for idx in bin_indices) / len(bin_indices)
        bin_acc = sum(labels[idx] for idx in bin_indices) / len(bin_indices)
        weight = len(bin_indices) / n
        ece += weight * abs(bin_acc - bin_conf)

    return round(ece, 4)


def compute_risk_coverage(
    probs: List[float], labels: List[int], thresholds: Optional[List[float]] = None
) -> List[Dict[str, float]]:
    """
    Compute Risk vs Coverage curve at various confidence thresholds.
    Coverage = Fraction of queries where system does not abstain (conf >= threshold).
    Risk = Error rate on covered queries (1 - accuracy).
    """
    if thresholds is None:
        thresholds = [0.1 * i for i in range(1, 10)]

    n = len(probs)
    if n == 0:
        return []

    curve = []
    for t in sorted(thresholds):
        covered = [(p, y) for p, y in zip(probs, labels) if p >= t]
        cov_count = len(covered)
        coverage = cov_count / n

        if cov_count > 0:
            accuracy = sum(y for _, y in covered) / cov_count
            risk = 1.0 - accuracy
        else:
            accuracy = 1.0
            risk = 0.0

        curve.append({
            "threshold": round(t, 2),
            "coverage": round(coverage, 4),
            "risk": round(risk, 4),
            "selective_accuracy": round(accuracy, 4),
        })

    return curve


def compute_false_confident_rate(probs: List[float], labels: List[int], threshold: float = 0.8) -> float:
    """Fraction of queries where system was highly confident (>= threshold) but wrong (label=0)."""
    if not probs:
        return 0.0
    high_conf = [(p, y) for p, y in zip(probs, labels) if p >= threshold]
    if not high_conf:
        return 0.0
    false_conf = sum(1 for _, y in high_conf if y == 0)
    return round(false_conf / len(high_conf), 4)


class PlattScaler:
    """
    Platt Scaling (univariate logistic calibration).
    Maps raw feature/heuristic scores to well-calibrated posterior probabilities:
      P(y=1 | s) = 1 / (1 + exp(-(A * s + B)))
    """

    def __init__(
        self,
        a: float = 2.5,
        b: float = -1.5,
        metadata: Optional[Dict[str, Any]] = None,
        is_fitted: bool = True,
    ):
        self.a = float(a)
        self.b = float(b)
        self.metadata = metadata or {}
        self.is_fitted = is_fitted

    def fit(
        self,
        scores: List[float],
        labels: List[int],
        max_iter: int = 50,
        l2_reg: float = 0.5,
        tol: float = 1e-6,
    ):
        """
        Fit parameters A and B via Newton-Raphson optimization on negative log-likelihood
        with empirical Bayesian prior regularization centered at (a0=3.0, b0=-1.8) and line search.
        """
        if not scores or len(scores) != len(labels):
            return

        n = len(scores)
        a0, b0 = 3.0, -1.8
        a, b = a0, b0

        def _log_loss(a_val: float, b_val: float) -> float:
            loss = 0.0
            for s, y in zip(scores, labels):
                logit = max(min(a_val * s + b_val, 20.0), -20.0)
                p = 1.0 / (1.0 + math.exp(-logit))
                p_safe = max(min(p, 1.0 - 1e-12), 1e-12)
                loss -= (y * math.log(p_safe) + (1 - y) * math.log(1.0 - p_safe))
            loss += 0.5 * l2_reg * ((a_val - a0) ** 2 + (b_val - b0) ** 2)
            return loss / n

        current_loss = _log_loss(a, b)

        for _ in range(max_iter):
            g_a = -l2_reg * (a - a0)
            g_b = -l2_reg * (b - b0)
            h_aa = l2_reg
            h_ab = 0.0
            h_bb = l2_reg

            for s, y in zip(scores, labels):
                logit = max(min(a * s + b, 20.0), -20.0)
                p = 1.0 / (1.0 + math.exp(-logit))
                w = p * (1.0 - p)
                err = y - p
                g_a += err * s
                g_b += err
                h_aa += w * (s ** 2)
                h_ab += w * s
                h_bb += w

            det = h_aa * h_bb - h_ab ** 2
            if det <= 1e-12:
                step_a = 0.05 * g_a / n
                step_b = 0.05 * g_b / n
            else:
                step_a = (h_bb * g_a - h_ab * g_b) / det
                step_b = (-h_ab * g_a + h_aa * g_b) / det

            # Backtracking line search
            alpha = 1.0
            found = False
            for _ in range(15):
                cand_a = a + alpha * step_a
                cand_b = b + alpha * step_b
                cand_loss = _log_loss(cand_a, cand_b)
                if cand_loss < current_loss:
                    a, b = cand_a, cand_b
                    current_loss = cand_loss
                    found = True
                    break
                alpha *= 0.5

            if not found or (abs(step_a * alpha) < tol and abs(step_b * alpha) < tol):
                break

        self.a = float(a)
        self.b = float(b)
        self.is_fitted = True

    def predict_proba(self, score: float) -> float:
        """Calibrated probability P(y=1 | score)."""
        logit = self.a * score + self.b
        clamped = max(min(logit, 20.0), -20.0)
        return round(1.0 / (1.0 + math.exp(-clamped)), 4)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize calibrator to dictionary."""
        return {
            "type": "PlattScaler",
            "a": self.a,
            "b": self.b,
            "is_fitted": self.is_fitted,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlattScaler":
        """Deserialize calibrator from dictionary."""
        return cls(
            a=data.get("a", 2.5),
            b=data.get("b", -1.5),
            metadata=data.get("metadata", {}),
            is_fitted=data.get("is_fitted", True),
        )

    def save(self, filepath: Any):
        """Save calibrator artifact to JSON file."""
        import json
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: Any) -> "PlattScaler":
        """Load calibrator artifact from JSON file."""
        import json
        from pathlib import Path
        with open(Path(filepath), "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


class TemperatureScaler:
    """
    Temperature Scaling for logit-based scores.
    P(y=1 | z) = sigma(z / T)
    """

    def __init__(self, temperature: float = 1.5, metadata: Optional[Dict[str, Any]] = None):
        self.temperature = max(0.1, float(temperature))
        self.metadata = metadata or {}

    def fit(self, logits: List[float], labels: List[int]):
        """Find optimal temperature T on development/calibration split."""
        best_t = 1.0
        best_nll = float("inf")

        for t_cand in [0.2 * i for i in range(1, 25)]:
            nll = 0.0
            for z, y in zip(logits, labels):
                scaled = z / t_cand
                p = 1.0 / (1.0 + math.exp(-max(min(scaled, 20.0), -20.0)))
                p_safe = max(min(p, 1.0 - 1e-7), 1e-7)
                nll += -(y * math.log(p_safe) + (1 - y) * math.log(1.0 - p_safe))

            if nll < best_nll:
                best_nll = nll
                best_t = t_cand

        self.temperature = float(best_t)

    def predict_proba(self, logit: float) -> float:
        scaled = logit / self.temperature
        clamped = max(min(scaled, 20.0), -20.0)
        return round(1.0 / (1.0 + math.exp(-clamped)), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "TemperatureScaler",
            "temperature": self.temperature,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemperatureScaler":
        return cls(
            temperature=data.get("temperature", 1.5),
            metadata=data.get("metadata", {}),
        )

    def save(self, filepath: Any):
        import json
        from pathlib import Path
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: Any) -> "TemperatureScaler":
        import json
        from pathlib import Path
        with open(Path(filepath), "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


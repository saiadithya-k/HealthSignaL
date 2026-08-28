import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional

class CUSUMDetector:
    """
    Deterministic CUSUM (Cumulative Sum) Statistical Process Control Surge Detector.
    Detects statistically significant upward demand surges relative to forecast baselines.
    """

    def __init__(self, drift_k: float = 0.5, threshold_h: float = 4.0):
        """
        :param drift_k: Drift/allowance parameter in units of standard deviations (default 0.5 sigma).
        :param threshold_h: Decision threshold in units of standard deviations (default 4.0 sigma).
        """
        if drift_k < 0.0 or threshold_h <= 0.0:
            raise ValueError(f"Invalid CUSUM parameters: drift_k={drift_k}, threshold_h={threshold_h}")
        self.drift_k = float(drift_k)
        self.threshold_h = float(threshold_h)

    def detect_step(
        self,
        observed: float,
        expected: float,
        prev_cusum: float = 0.0,
        sigma: float = 1.0
    ) -> Tuple[float, float, bool]:
        """
        Processes a single observation step.
        Returns: (current_cusum, standardized_residual, is_anomaly)
        """
        if sigma <= 0.0:
            sigma = 1.0

        residual = float(observed - expected)
        z_score = residual / sigma

        # Upward CUSUM recurrence: S_t+ = max(0, S_{t-1}+ + z_score - drift_k)
        curr_cusum = max(0.0, prev_cusum + z_score - self.drift_k)
        is_anomaly = curr_cusum > self.threshold_h

        return float(round(curr_cusum, 4)), float(round(z_score, 4)), is_anomaly

    def detect_series(
        self,
        observed_series: np.ndarray,
        expected_series: np.ndarray,
        sigma: float = 1.0,
        dates: Optional[List[str]] = None,
        syndrome_category: str = "respiratory",
        confidence_score: float = 1.0,
        coverage_ratio: float = 1.0,
        missing_node_count: int = 0,
        model_version: str = "v1.0.0-fed-h7"
    ) -> Dict[str, Any]:
        """
        Runs CUSUM detection over a time-series sequence.
        Returns summary dictionary containing step results and generated candidate alerts.
        """
        if len(observed_series) != len(expected_series):
            raise ValueError("Dimensions of observed_series and expected_series must match")

        if len(observed_series) == 0:
            raise ValueError("Cannot run anomaly detection on empty signal series")

        obs = np.asarray(observed_series, dtype=np.float64)
        exp = np.asarray(expected_series, dtype=np.float64)

        if sigma <= 0.0:
            sigma = float(np.std(obs - exp)) or 1.0

        cusum_history = []
        candidates = []
        curr_cusum = 0.0

        for i in range(len(obs)):
            date_str = dates[i] if dates and i < len(dates) else f"Step-{i+1}"
            y_obs = float(obs[i])
            y_exp = float(exp[i])

            curr_cusum, z_score, is_anomaly = self.detect_step(
                observed=y_obs,
                expected=y_exp,
                prev_cusum=curr_cusum,
                sigma=sigma
            )

            step_res = {
                "step": i + 1,
                "date": date_str,
                "observed": y_obs,
                "expected": y_exp,
                "residual": float(round(y_obs - y_exp, 2)),
                "standardized_residual": z_score,
                "cusum_statistic": curr_cusum,
                "threshold": self.threshold_h,
                "is_anomaly": is_anomaly
            }
            cusum_history.append(step_res)

            if is_anomaly:
                candidate_alert = {
                    "syndrome_category": syndrome_category,
                    "forecast_date": date_str,
                    "observed_value": y_obs,
                    "expected_value": y_exp,
                    "residual": float(round(y_obs - y_exp, 2)),
                    "cusum_statistic": curr_cusum,
                    "threshold": self.threshold_h,
                    "shift_score": curr_cusum,
                    "status": "CANDIDATE",
                    "confidence_score": confidence_score,
                    "coverage_ratio": coverage_ratio,
                    "missing_node_count": missing_node_count,
                    "model_version": model_version
                }
                candidates.append(candidate_alert)

        return {
            "detector_config": {
                "drift_k": self.drift_k,
                "threshold_h": self.threshold_h,
                "residual_sigma": round(sigma, 4)
            },
            "total_observations": len(obs),
            "total_candidates": len(candidates),
            "cusum_history": cusum_history,
            "candidate_alerts": candidates
        }

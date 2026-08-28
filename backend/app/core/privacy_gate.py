import os
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from app.config import settings

class PrivacyGate:
    """
    Pre-Transmission Privacy Gate (FR-017 Layered Boundary):
    Enforces local row-level isolation, minimum group size suppression (MIN_GROUP_SIZE=11),
    contribution parameter bounding, and outbound payload validation before federation.
    """

    def __init__(
        self,
        min_group_size: int = settings.MIN_GROUP_SIZE,
        max_coeff_bound: float = 100.0
    ):
        self.min_group_size = min_group_size
        self.max_coeff_bound = max_coeff_bound

    def validate_outbound_payload(
        self,
        payload: Dict[str, Any],
        institution_id: str
    ) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """
        Validates outbound parameters or aggregate updates before transmission to coordinator.
        Returns (is_valid, error_list, privacy_events_to_log).
        """
        errors = []
        privacy_events = []

        # 1. Prohibited Raw Record Check
        if "raw_records" in payload or "records" in payload or "patient_id" in payload:
            errors.append("PRIVACY VIOLATION: Raw row-level records detected in outbound payload")
            privacy_events.append({
                "institution_id": institution_id,
                "event_type": "REJECTED_OUTBOUND_PAYLOAD",
                "reason": "Attempted raw row transmission",
                "details": {"violating_keys": [k for k in ["raw_records", "records", "patient_id"] if k in payload]}
            })
            return False, errors, privacy_events

        # 2. Numerical Parameter Bound & NaN Check
        coefs = payload.get("coef", [])
        if coefs:
            arr = np.asarray(coefs, dtype=np.float64)
            if np.isnan(arr).any() or np.isinf(arr).any():
                errors.append("NUMERICAL VIOLATION: NaN or infinite values detected in model parameters")
            
            # Check parameter bounding
            if (np.abs(arr) > self.max_coeff_bound).any():
                errors.append(f"BOUNDING VIOLATION: Coefficients exceed maximum bound [-{self.max_coeff_bound}, {self.max_coeff_bound}]")
                privacy_events.append({
                    "institution_id": institution_id,
                    "event_type": "CONTRIBUTION_CLIPPED",
                    "reason": f"Coefficients exceeded bound {self.max_coeff_bound}",
                    "details": {"max_observed": float(np.max(np.abs(arr)))}
                })

        # 3. Minimum Group Size Suppression Check
        sample_count = payload.get("n_samples", 0)
        if sample_count > 0 and sample_count < self.min_group_size:
            errors.append(f"SUPPRESSION VIOLATION: Sample size ({sample_count}) is below minimum group size threshold ({self.min_group_size})")
            privacy_events.append({
                "institution_id": institution_id,
                "event_type": "MIN_GROUP_SUPPRESSION",
                "reason": f"Sample count {sample_count} < MIN_GROUP_SIZE ({self.min_group_size})",
                "details": {"sample_count": sample_count, "threshold": self.min_group_size}
            })

        is_valid = (len(errors) == 0)
        return is_valid, errors, privacy_events

    def apply_small_group_suppression(self, df: pd.DataFrame, count_col: str = "service_count") -> pd.DataFrame:
        """
        Applies minimum group size suppression to aggregate counts below MIN_GROUP_SIZE.
        Counts between 1 and MIN_GROUP_SIZE - 1 are suppressed (replaced with 0 or marked completeness=0).
        """
        if df is None or df.empty or count_col not in df.columns:
            return df

        suppressed_df = df.copy()
        mask = (suppressed_df[count_col] > 0) & (suppressed_df[count_col] < self.min_group_size)
        
        if mask.any():
            suppressed_df.loc[mask, count_col] = 0
            if "data_completeness" in suppressed_df.columns:
                suppressed_df.loc[mask, "data_completeness"] = 0.0

        return suppressed_df

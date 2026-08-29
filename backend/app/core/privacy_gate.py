import os
from typing import Dict, Any, List, Tuple, Optional, Union
import numpy as np
import pandas as pd
from app.config import settings

PROHIBITED_OUTBOUND_KEYS = {
    "patient_id",
    "patient_name",
    "name",
    "phone",
    "email",
    "address",
    "dob",
    "date_of_birth",
    "ssn",
    "consent_token",
    "raw_records",
    "records",
    "raw_symptoms",
    "individual_symptoms",
    "clinical_information",
    "individual_clinical_information",
    "disease_name",
    "disease_label",
    "condition_id",
    "condition_name",
    "diagnosis",
    "true_disease",
    "ground_truth",
    "outbreak_scenario",
    "outbreak_active",
    "scenario_id"
}

class PrivacyGate:
    """
    Pre-Transmission Privacy Gate (FR-017 Layered Boundary):
    Enforces local row-level isolation, minimum group size suppression (MIN_GROUP_SIZE=11),
    contribution parameter bounding/clipping, and outbound payload validation before federation.
    """

    def __init__(
        self,
        min_group_size: int = settings.MIN_GROUP_SIZE,
        max_coeff_bound: float = 100.0,
        expected_num_features: int = 13
    ):
        self.min_group_size = min_group_size
        self.max_coeff_bound = max_coeff_bound
        self.expected_num_features = expected_num_features

    def _detect_prohibited_fields(self, obj: Any) -> List[str]:
        """Recursively scans a dictionary or list for prohibited identifiers or raw records."""
        violations = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).strip().lower()
                if k_lower in PROHIBITED_OUTBOUND_KEYS:
                    violations.append(str(k))
                violations.extend(self._detect_prohibited_fields(v))
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                violations.extend(self._detect_prohibited_fields(item))
        return list(sorted(set(violations)))

    def clip_parameters(
        self,
        param_vec: Union[np.ndarray, List[float]],
        max_norm: Optional[float] = None
    ) -> Tuple[np.ndarray, bool, Dict[str, Any]]:
        """
        Clips parameter vector based on L2 norm and max coefficient bounds.
        Returns: (clipped_param_vec, was_clipped, clipping_details)
        """
        if max_norm is None:
            max_norm = self.max_coeff_bound

        vec = np.asarray(param_vec, dtype=np.float64)
        l2_norm = float(np.linalg.norm(vec))
        was_clipped = False
        
        # 1. L2 Norm clipping if norm exceeds max_norm
        if l2_norm > max_norm and l2_norm > 0:
            scaling_factor = max_norm / l2_norm
            vec = vec * scaling_factor
            was_clipped = True

        # 2. Hard coefficient bounding to [-max_coeff_bound, max_coeff_bound]
        if (np.abs(vec) > self.max_coeff_bound).any():
            vec = np.clip(vec, -self.max_coeff_bound, self.max_coeff_bound)
            was_clipped = True

        details = {
            "original_norm": round(l2_norm, 4),
            "clipped_norm": round(float(np.linalg.norm(vec)), 4),
            "max_norm_threshold": max_norm,
            "was_clipped": was_clipped
        }
        return vec, was_clipped, details

    def validate_outbound_payload(
        self,
        payload: Dict[str, Any],
        institution_id: str,
        enforce_exact_dimension: bool = False
    ) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
        """
        Validates outbound parameters or aggregate updates before transmission to coordinator.
        Returns (is_valid, error_list, privacy_events_to_log).
        """
        errors = []
        privacy_events = []

        if payload is None or not isinstance(payload, dict):
            errors.append("MALFORMED PAYLOAD: Payload must be a non-empty dictionary")
            return False, errors, privacy_events

        # 1. Prohibited Raw Record / PII / Label Check (Recursive)
        violations = self._detect_prohibited_fields(payload)
        if violations:
            errors.append(f"PRIVACY VIOLATION: Prohibited fields detected in outbound payload: {violations}")
            privacy_events.append({
                "institution_id": institution_id,
                "event_type": "REJECTED_OUTBOUND_PAYLOAD",
                "reason": "Attempted transmission of prohibited fields",
                "details": {"violating_fields": violations}
            })
            return False, errors, privacy_events

        # 2. Numerical Parameter Bound & NaN/Inf Check
        coefs = payload.get("coef", [])
        intercept = payload.get("intercept", None)

        if coefs is not None and len(coefs) > 0:
            arr = np.asarray(coefs, dtype=np.float64)
            if np.isnan(arr).any() or np.isinf(arr).any():
                errors.append("NUMERICAL VIOLATION: NaN or infinite values detected in model coefficients")
            
            # Check parameter dimension if requested
            if enforce_exact_dimension and len(arr) != self.expected_num_features:
                errors.append(f"DIMENSION VIOLATION: Expected {self.expected_num_features} coefficients, got {len(arr)}")

            # Check parameter bounding
            if (np.abs(arr) > self.max_coeff_bound).any():
                errors.append(f"BOUNDING VIOLATION: Coefficients exceed maximum bound [-{self.max_coeff_bound}, {self.max_coeff_bound}]")
                privacy_events.append({
                    "institution_id": institution_id,
                    "event_type": "CONTRIBUTION_CLIPPED",
                    "reason": f"Coefficients exceeded bound {self.max_coeff_bound}",
                    "details": {"max_observed": float(np.max(np.abs(arr)))}
                })

        if intercept is not None:
            val = float(intercept)
            if np.isnan(val) or np.isinf(val):
                errors.append("NUMERICAL VIOLATION: NaN or infinite value detected in model intercept")
            elif abs(val) > self.max_coeff_bound * 10:
                errors.append(f"BOUNDING VIOLATION: Intercept {val} exceeds safety bound")

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

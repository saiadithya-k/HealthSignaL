import os
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from app.config import settings
from app.core.privacy_gate import PrivacyGate
from app.core.syndrome_mapping import syndrome_service
from app.ml.features import build_supervised_features, FEATURE_COLUMNS

PROHIBITED_PII_FIELDS = {
    "patient_id",
    "patient_name",
    "name",
    "phone",
    "email",
    "address",
    "ssn",
    "raw_records",
    "records",
    "individual_symptoms",
    "consent_token",
    "diagnosis"
}

class FederatedHandoffRecord(BaseModel):
    """
    Pydantic contract representation for an individual record handed off to federated training.
    Strictly prohibits raw patient identifiers and enforces aggregate boundaries.
    """
    date: str
    node_id: str
    syndrome_category: str
    service_count: int = Field(ge=0, description="Aggregate demand count (0 or >= 11)")
    data_source: str = "all"
    rolling_3d_mean: Optional[float] = 0.0
    rolling_7d_mean: Optional[float] = 0.0
    rolling_7d_std: Optional[float] = 0.0
    lag_1: Optional[float] = 0.0
    lag_7: Optional[float] = 0.0
    lag_14: Optional[float] = 0.0
    growth_rate_7d: Optional[float] = 0.0
    pharmacy_lead_t2: Optional[float] = 0.0
    coverage_ratio: Optional[float] = 1.0
    data_completeness: Optional[float] = 1.0
    completeness_score: Optional[float] = 1.0
    source_reliability: Optional[float] = 0.85

    @classmethod
    def validate_row_dict(cls, row: Dict[str, Any], k_threshold: int = settings.MIN_GROUP_SIZE) -> Tuple[bool, List[str]]:
        """Validates that a row dictionary adheres strictly to privacy and ontology constraints."""
        errors = []
        # Check PII
        violating_pii = [k for k in row.keys() if k.lower() in PROHIBITED_PII_FIELDS]
        if violating_pii:
            errors.append(f"PII VIOLATION: Prohibited fields detected in record: {violating_pii}")

        # Check k suppression
        count_val = row.get("service_count", row.get("count", 0))
        if 0 < count_val < k_threshold:
            errors.append(f"K-SUPPRESSION VIOLATION: Count value {count_val} violates k >= {k_threshold} threshold")

        return len(errors) == 0, errors


class FederatedDataHandoffManager:
    """
    Manages the Data Layer -> Federated Learning Layer boundary.
    Guarantees that raw data, unsuppressed counts (< 11), and PII never reach local model training or Flower.
    """

    def __init__(self, data_dir: str = "data", k_threshold: int = settings.MIN_GROUP_SIZE):
        self.data_dir = data_dir
        self.k_threshold = k_threshold
        self.privacy_gate = PrivacyGate(min_group_size=k_threshold)

    def validate_handoff_dataframe(
        self,
        df: pd.DataFrame,
        node_id: str
    ) -> Tuple[bool, List[str]]:
        """
        Validates that a DataFrame destined for federated model training strictly adheres to the contract.
        """
        errors = []

        if df is None or df.empty:
            errors.append("EMPTY_DATA: DataFrame is None or empty.")
            return False, errors

        # 1. Prohibited PII / Raw field check
        detected_pii = [col for col in df.columns if col.lower() in PROHIBITED_PII_FIELDS]
        if detected_pii:
            errors.append(f"PII_VIOLATION: Prohibited raw/PII columns present: {detected_pii}")

        # 2. Required columns check
        required_cols = {"date", "syndrome_category", "service_count"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            errors.append(f"SCHEMA_VIOLATION: Missing required columns: {missing_cols}")

        # 3. K-Suppression Check (No non-zero count below k_threshold)
        if "service_count" in df.columns:
            violating_counts = df[(df["service_count"] > 0) & (df["service_count"] < self.k_threshold)]
            if len(violating_counts) > 0:
                errors.append(
                    f"K_SUPPRESSION_VIOLATION: Found {len(violating_counts)} records with 1 <= count < {self.k_threshold}."
                )

        # 4. NaN / Inf numerical checks on feature columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if df[numeric_cols].isna().any().any():
            errors.append("NUMERICAL_VIOLATION: NaN values detected in numeric columns.")
        if np.isinf(df[numeric_cols].values).any():
            errors.append("NUMERICAL_VIOLATION: Infinite values detected in numeric columns.")

        return len(errors) == 0, errors

    def prepare_local_federated_features(
        self,
        node_id: str,
        forecast_horizon: int = 7
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Loads and prepares privacy-validated supervised training features for a specific node.
        Applies small-group suppression, standardizes features, and validates the handoff contract.
        """
        node_dir = os.path.join(self.data_dir, node_id)
        csv_path = os.path.join(node_dir, "data.csv")
        meta_path = os.path.join(node_dir, "metadata.json")

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Local dataset not found for node '{node_id}' at {csv_path}")

        raw_df = pd.read_csv(csv_path)
        metadata = {}
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        # Apply mandatory small-group suppression (Layer 3 Privacy Gate)
        clean_df = self.privacy_gate.apply_small_group_suppression(raw_df, count_col="service_count")

        # Validate contract compliance before feature engineering
        is_valid, validation_errors = self.validate_handoff_dataframe(clean_df, node_id=node_id)
        if not is_valid:
            raise ValueError(f"Federated Data Handoff Contract VIOLATION for node '{node_id}': {validation_errors}")

        # Build supervised feature matrix using existing canonical feature engineering
        feature_df = build_supervised_features(clean_df, forecast_horizon=forecast_horizon)

        # Append node-level metadata columns for transparency without leaking PII
        feature_df["node_id"] = node_id
        if "data_completeness" not in feature_df.columns:
            feature_df["data_completeness"] = 1.0

        handoff_metadata = {
            "node_id": node_id,
            "profile": metadata.get("profile", "Unknown"),
            "k_threshold": self.k_threshold,
            "privacy_gate_validated": True,
            "feature_columns": FEATURE_COLUMNS,
            "total_training_samples": len(feature_df),
            "forecast_horizon": forecast_horizon,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

        return feature_df, handoff_metadata


# Global singleton instance
federated_handoff_manager = FederatedDataHandoffManager()

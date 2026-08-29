import os
import json
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from app.data_generation.validator import DatasetValidator
from app.data_generation.schemas import ValidationResult

class LocalInstitutionClient:
    """
    Lightweight abstraction for an isolated local institution node.
    Loads and processes local dataset locally. NEVER transmits raw rows.
    """

    def __init__(self, institution_id: str, data_dir: str = "data"):
        self.institution_id = institution_id
        self.data_dir = data_dir
        self.node_dir = os.path.join(data_dir, institution_id)
        self._local_df: Optional[pd.DataFrame] = None
        self._metadata: Optional[Dict[str, Any]] = None

    def load_local_data(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Loads local CSV data and metadata JSON for this institution only."""
        csv_path = os.path.join(self.node_dir, "data.csv")
        meta_path = os.path.join(self.node_dir, "metadata.json")

        if not os.path.exists(csv_path) or not os.path.exists(meta_path):
            raise FileNotFoundError(f"Local dataset files missing for {self.institution_id} in {self.node_dir}")

        self._local_df = pd.read_csv(csv_path)
        with open(meta_path, "r") as f:
            self._metadata = json.load(f)

        return self._local_df, self._metadata

    def validate_local_data(self) -> ValidationResult:
        """Executes dataset validator on local dataset."""
        if self._local_df is None:
            self.load_local_data()
        return DatasetValidator.validate_dataframe(self._local_df, self.institution_id)

    def get_local_features(self) -> pd.DataFrame:
        """Constructs approved local aggregate feature dataset for training/forecasting."""
        if self._local_df is None:
            self.load_local_data()
            
        df = self._local_df.copy()
        
        # Additional feature engineering (lags, trend_index)
        df["date"] = pd.to_datetime(df["date"])
        df.sort_values(by=["syndrome_category", "date"], inplace=True)
        
        df["lag_1"] = df.groupby("syndrome_category")["service_count"].shift(1).fillna(0)
        df["lag_7"] = df.groupby("syndrome_category")["service_count"].shift(7).fillna(0)
        df["rolling_std_7"] = (
            df.groupby("syndrome_category")["service_count"]
            .transform(lambda x: x.rolling(7, min_periods=1).std().fillna(0).round(2))
        )
        
        return df

    def get_federated_training_data(self, forecast_horizon: int = 7) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Retrieves privacy-gate validated supervised features for local model training.
        Guarantees that raw patient rows and sub-threshold counts are rejected/suppressed before handoff.
        """
        from app.core.federated_handoff import federated_handoff_manager
        return federated_handoff_manager.prepare_local_federated_features(
            node_id=self.institution_id,
            forecast_horizon=forecast_horizon
        )

    def get_local_summary(self) -> Dict[str, Any]:
        """
        Returns SAFE AGGREGATE METADATA only.
        NEVER returns raw institutional rows.
        """
        if self._local_df is None:
            self.load_local_data()

        val_result = self.validate_local_data()
        
        daily_total = self._local_df.groupby("date")["service_count"].sum()
        
        return {
            "institution_id": self.institution_id,
            "profile": self._metadata.get("profile", "Unknown"),
            "scenario": self._metadata.get("scenario", "NORMAL"),
            "total_records": len(self._local_df),
            "date_range": {
                "start": self._metadata.get("start_date"),
                "end": self._metadata.get("end_date")
            },
            "mean_daily_demand": float(round(daily_total.mean(), 2)),
            "std_daily_demand": float(round(daily_total.std(), 2)),
            "is_valid": val_result.is_valid,
            "missing_rate_pct": val_result.missing_rate_pct,
            "ground_truth_events_count": len(self._metadata.get("ground_truth_events", []))
        }

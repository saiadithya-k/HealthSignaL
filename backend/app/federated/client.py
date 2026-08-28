import os
import numpy as np
import pandas as pd
import flwr as fl
from typing import Dict, Tuple, List, Any

from app.core.local_node import LocalInstitutionClient
from app.core.privacy_gate import PrivacyGate
from app.ml.features import build_supervised_features, prepare_chronological_split, FEATURE_COLUMNS
from app.ml.model import LocalForecastModel
from app.federated.model_adapter import model_to_parameters, parameters_to_model, parameters_to_flwr, flwr_to_parameters

class HealthSignalFlowerClient(fl.client.NumPyClient):
    """
    Flower federated client representing a local healthcare institution.
    Loads isolated local data, trains local model, and validates outbound updates via PrivacyGate.
    """

    def __init__(self, institution_id: str, data_dir: str = "data", forecast_horizon: int = 7, alpha: float = 1.0):
        self.institution_id = institution_id
        self.data_dir = data_dir
        self.forecast_horizon = forecast_horizon
        self.alpha = alpha
        self.privacy_gate = PrivacyGate()

        # Load local data strictly via LocalInstitutionClient
        self.client_node = LocalInstitutionClient(self.institution_id, data_dir=self.data_dir)
        df, self.metadata = self.client_node.load_local_data()

        # Build features and chronological splits
        feat_df = build_supervised_features(df, forecast_horizon=self.forecast_horizon)
        self.train_df, self.val_df, self.test_df = prepare_chronological_split(feat_df)

        self.local_model = LocalForecastModel(
            institution_id=self.institution_id,
            alpha=self.alpha,
            forecast_horizon=self.forecast_horizon
        )

    def get_parameters(self, config: Dict[str, Any] = None) -> List[np.ndarray]:
        """Returns initial or current parameters of the local model."""
        if not self.local_model.is_trained:
            self.local_model.fit(self.train_df[FEATURE_COLUMNS], self.train_df["target"])

        vec = model_to_parameters(self.local_model)
        return parameters_to_flwr(vec)

    def fit(self, parameters: List[np.ndarray], config: Dict[str, Any] = None) -> Tuple[List[np.ndarray], int, Dict[str, Any]]:
        """
        Executes local training and returns outbound parameter update.
        Mandatory PrivacyGate validation occurs BEFORE returning data.
        """
        # Fit local Ridge model on local training set
        self.local_model.fit(self.train_df[FEATURE_COLUMNS], self.train_df["target"])
        param_vec = model_to_parameters(self.local_model)

        # -------------------------------------------------------------
        # MANDATORY PRE-TRANSMISSION PRIVACY GATE BOUNDARY
        # -------------------------------------------------------------
        payload = {
            "institution_id": self.institution_id,
            "n_samples": len(self.train_df),
            "coef": [float(c) for c in self.local_model.model.coef_],
            "intercept": float(self.local_model.model.intercept_)
        }

        is_valid, errors, privacy_events = self.privacy_gate.validate_outbound_payload(payload, self.institution_id)

        if not is_valid:
            raise ValueError(f"PrivacyGate REJECTED outbound update for {self.institution_id}: {errors}")

        flwr_params = parameters_to_flwr(param_vec)
        num_examples = len(self.train_df)
        metrics = {
            "institution_id": self.institution_id,
            "n_samples": num_examples,
            "privacy_validated": True
        }

        return flwr_params, num_examples, metrics

    def evaluate(self, parameters: List[np.ndarray], config: Dict[str, Any] = None) -> Tuple[float, int, Dict[str, Any]]:
        """Evaluates global or local parameters on local held-out test set."""
        param_vec = flwr_to_parameters(parameters)
        eval_model = parameters_to_model(
            param_vec,
            institution_id=self.institution_id,
            alpha=self.alpha,
            forecast_horizon=self.forecast_horizon
        )

        metrics = eval_model.evaluate(self.test_df[FEATURE_COLUMNS], self.test_df["target"])
        loss = metrics["mae"]  # Use MAE as loss metric
        num_examples = len(self.test_df)

        return loss, num_examples, metrics

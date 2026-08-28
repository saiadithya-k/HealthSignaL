import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from sklearn.linear_model import Ridge

from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.metrics import compute_eval_metrics

class LocalForecastModel:
    """
    Local Ridge Regression forecasting model for an institution node.
    Provides training, prediction, evaluation, and artifact serialization.
    """

    def __init__(self, institution_id: str, alpha: float = 1.0, forecast_horizon: int = 7):
        self.institution_id = institution_id
        self.alpha = float(alpha)
        self.forecast_horizon = int(forecast_horizon)
        self.model = Ridge(alpha=self.alpha, random_state=42)
        self.is_trained = False
        self.feature_names = FEATURE_COLUMNS.copy()
        self.training_metadata: Dict[str, Any] = {}

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> "LocalForecastModel":
        """Fits Ridge Regression on X_train, y_train."""
        if X_train.empty or len(y_train) == 0:
            raise ValueError(f"Cannot train model for {self.institution_id} on empty training set")

        X_mat = X_train[self.feature_names].values
        y_vec = y_train.values

        self.model.fit(X_mat, y_vec)
        self.is_trained = True

        self.training_metadata = {
            "institution_id": self.institution_id,
            "algorithm": "Ridge Regression",
            "alpha": self.alpha,
            "forecast_horizon": self.forecast_horizon,
            "num_features": len(self.feature_names),
            "features": self.feature_names,
            "coef": [float(round(c, 6)) for c in self.model.coef_],
            "intercept": float(round(self.model.intercept_, 6)),
            "n_samples": int(len(X_mat))
        }
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generates predictions for feature matrix X."""
        if not self.is_trained:
            raise RuntimeError(f"Model for {self.institution_id} is not trained yet")
        if X.empty:
            return np.array([])

        X_mat = X[self.feature_names].values
        preds = self.model.predict(X_mat)
        # Service counts cannot be negative in reality
        return np.maximum(preds, 0.0)

    def evaluate(self, X_eval: pd.DataFrame, y_eval: pd.Series, model_name: str = "local_ridge") -> Dict[str, Any]:
        """Evaluates model performance against ground truth y_eval."""
        preds = self.predict(X_eval)
        metrics = compute_eval_metrics(
            y_true=y_eval.values,
            y_pred=preds,
            institution_id=self.institution_id,
            model_name=model_name,
            forecast_horizon=self.forecast_horizon
        )
        return metrics

    def save_model(self, base_dir: str = "artifacts/local") -> Tuple[str, str]:
        """Saves model binaries (.joblib) and metadata (.json) to node artifact folder."""
        if not self.is_trained:
            raise RuntimeError("Cannot save untrained model")

        inst_dir = os.path.join(base_dir, self.institution_id)
        os.makedirs(inst_dir, exist_ok=True)

        model_path = os.path.join(inst_dir, "model.joblib")
        meta_path = os.path.join(inst_dir, "metadata.json")

        joblib.dump(self.model, model_path)
        with open(meta_path, "w") as f:
            json.dump(self.training_metadata, f, indent=2)

        return model_path, meta_path

    @classmethod
    def load_model(cls, institution_id: str, base_dir: str = "artifacts/local") -> "LocalForecastModel":
        """Loads serialized Ridge model and metadata from node artifact folder."""
        inst_dir = os.path.join(base_dir, institution_id)
        model_path = os.path.join(inst_dir, "model.joblib")
        meta_path = os.path.join(inst_dir, "metadata.json")

        if not os.path.exists(model_path) or not os.path.exists(meta_path):
            raise FileNotFoundError(f"Model artifacts not found for {institution_id} at {inst_dir}")

        with open(meta_path, "r") as f:
            meta = json.load(f)

        instance = cls(
            institution_id=institution_id,
            alpha=meta.get("alpha", 1.0),
            forecast_horizon=meta.get("forecast_horizon", 7)
        )
        instance.model = joblib.load(model_path)
        instance.is_trained = True
        instance.training_metadata = meta
        return instance

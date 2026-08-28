import numpy as np
import pandas as pd
from typing import List, Tuple
from app.ml.features import FEATURE_COLUMNS
from app.ml.model import LocalForecastModel

def model_to_parameters(model: LocalForecastModel) -> np.ndarray:
    """
    Deterministically converts a trained LocalForecastModel (Ridge) into a 1D NumPy parameter vector.
    Format: [coef_1, coef_2, ..., coef_n, intercept]
    """
    if not model.is_trained:
        raise ValueError(f"Cannot extract parameters from untrained model for {model.institution_id}")

    coefs = np.asarray(model.model.coef_, dtype=np.float64)
    intercept = np.float64(model.model.intercept_)

    # Concatenate coefficients and scalar intercept into a single 1D vector
    return np.append(coefs, intercept)


def parameters_to_model(
    params: np.ndarray,
    institution_id: str = "global",
    alpha: float = 1.0,
    forecast_horizon: int = 7
) -> LocalForecastModel:
    """
    Reconstructs a LocalForecastModel from a 1D parameter vector.
    Format: [coef_1, coef_2, ..., coef_n, intercept]
    """
    params_vec = np.asarray(params, dtype=np.float64).flatten()
    expected_len = len(FEATURE_COLUMNS) + 1

    if len(params_vec) != expected_len:
        raise ValueError(f"Incompatible parameter vector length: expected {expected_len}, got {len(params_vec)}")

    coefs = params_vec[:-1]
    intercept = params_vec[-1]

    model = LocalForecastModel(institution_id=institution_id, alpha=alpha, forecast_horizon=forecast_horizon)
    model.model.coef_ = coefs
    model.model.intercept_ = intercept
    model.is_trained = True

    model.training_metadata = {
        "institution_id": institution_id,
        "algorithm": "Ridge Regression (FedAvg)",
        "alpha": alpha,
        "forecast_horizon": forecast_horizon,
        "num_features": len(FEATURE_COLUMNS),
        "features": FEATURE_COLUMNS,
        "coef": [float(round(c, 6)) for c in coefs],
        "intercept": float(round(intercept, 6)),
    }
    return model


def parameters_to_flwr(params: np.ndarray) -> List[np.ndarray]:
    """Converts 1D parameter vector to Flower parameters list format [coef_array, intercept_array]."""
    params_vec = np.asarray(params, dtype=np.float64).flatten()
    coefs = params_vec[:-1]
    intercept = np.array([params_vec[-1]], dtype=np.float64)
    return [coefs, intercept]


def flwr_to_parameters(flwr_params: List[np.ndarray]) -> np.ndarray:
    """Converts Flower parameters list [coef_array, intercept_array] back to 1D parameter vector."""
    if len(flwr_params) != 2:
        raise ValueError(f"Expected 2 Flower parameter arrays [coefs, intercept], got {len(flwr_params)}")

    coefs = np.asarray(flwr_params[0], dtype=np.float64).flatten()
    intercept = np.asarray(flwr_params[1], dtype=np.float64).flatten()
    return np.append(coefs, intercept)

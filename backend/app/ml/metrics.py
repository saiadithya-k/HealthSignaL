import numpy as np
from typing import Dict, Any, Union

def compute_eval_metrics(
    y_true: Union[np.ndarray, list],
    y_pred: Union[np.ndarray, list],
    institution_id: str = "all",
    model_name: str = "ridge",
    forecast_horizon: int = 7
) -> Dict[str, Any]:
    """
    Computes regression evaluation metrics: MAE, RMSE, safe MAPE.
    Guarantees no division-by-zero or infinite values.
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)

    if len(y_t) == 0 or len(y_p) == 0:
        return {
            "mae": 0.0,
            "rmse": 0.0,
            "mape": 0.0,
            "sample_count": 0,
            "forecast_horizon": forecast_horizon,
            "institution_id": institution_id,
            "model_name": model_name
        }

    errors = y_t - y_p
    abs_errors = np.abs(errors)

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # Safe MAPE denominator handling (prevents div zero when y_t == 0)
    safe_denom = np.maximum(np.abs(y_t), 1.0)
    mape = float(np.mean(abs_errors / safe_denom) * 100.0)

    return {
        "mae": float(round(mae, 4)),
        "rmse": float(round(rmse, 4)),
        "mape": float(round(mape, 2)),
        "sample_count": int(len(y_t)),
        "forecast_horizon": forecast_horizon,
        "institution_id": institution_id,
        "model_name": model_name
    }

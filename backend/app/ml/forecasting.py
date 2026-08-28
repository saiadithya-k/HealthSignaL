import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.model import LocalForecastModel
from app.ml.metrics import compute_eval_metrics
from app.core.local_node import LocalInstitutionClient

DEFAULT_HORIZON_DAYS = 7

def validate_forecast_horizon(horizon: int) -> int:
    """Validates that requested forecast horizon is between 7 and 14 days."""
    if not isinstance(horizon, int) or horizon < 7 or horizon > 14:
        raise ValueError(f"Invalid forecast horizon: {horizon}. Must be an integer between 7 and 14 days.")
    return horizon


def load_global_model(artifacts_dir: str = "artifacts") -> LocalForecastModel:
    """Loads the trained global FedAvg forecast model from artifacts directory."""
    global_dir = os.path.join(artifacts_dir, "global")
    model_path = os.path.join(global_dir, "model.joblib")
    meta_path = os.path.join(global_dir, "metadata.json")

    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        raise FileNotFoundError("Global FedAvg model not found. Trigger POST /api/v1/federation/start first.")

    return LocalForecastModel.load_model("global", base_dir=artifacts_dir)


def compute_validation_residuals(model: LocalForecastModel, data_dir: str = "data") -> Tuple[float, Dict[str, Any]]:
    """
    Computes residual standard deviation (sigma) on held-out validation sets.
    Returns (sigma, empirical_coverage_dict).
    """
    all_y_true = []
    all_y_pred = []

    for inst_id in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        client = LocalInstitutionClient(inst_id, data_dir=data_dir)
        df, _ = client.load_local_data()
        feat_df = build_supervised_features(df, forecast_horizon=model.forecast_horizon)
        _, val_df, _ = prepare_chronological_split(feat_df)
        
        preds = model.predict(val_df[FEATURE_COLUMNS])
        all_y_true.extend(val_df["target"].values)
        all_y_pred.extend(preds)

    y_true = np.asarray(all_y_true, dtype=np.float64)
    y_pred = np.asarray(all_y_pred, dtype=np.float64)

    residuals = y_true - y_pred
    sigma = float(np.std(residuals)) if len(residuals) > 0 else 1.0
    sigma = max(sigma, 0.5)  # Floor minimum sigma

    # Empirical Coverage Calculation
    upper_80 = y_pred + 1.2816 * sigma
    lower_80 = np.maximum(y_pred - 1.2816 * sigma, 0.0)
    covered_80 = np.sum((y_true >= lower_80) & (y_true <= upper_80))
    emp_cov_80 = float(round(covered_80 / len(y_true), 4)) if len(y_true) > 0 else 0.80

    upper_95 = y_pred + 1.9600 * sigma
    lower_95 = np.maximum(y_pred - 1.9600 * sigma, 0.0)
    covered_95 = np.sum((y_true >= lower_95) & (y_true <= upper_95))
    emp_cov_95 = float(round(covered_95 / len(y_true), 4)) if len(y_true) > 0 else 0.95

    coverage_info = {
        "residual_sigma": round(sigma, 4),
        "nominal_80": 0.80,
        "empirical_80": emp_cov_80,
        "coverage_error_80": round(emp_cov_80 - 0.80, 4),
        "nominal_95": 0.95,
        "empirical_95": emp_cov_95,
        "coverage_error_95": round(emp_cov_95 - 0.95, 4)
    }

    return sigma, coverage_info


def generate_multiday_forecast(
    history_df: pd.DataFrame,
    model: LocalForecastModel,
    horizon: int = 7,
    missing_node_count: int = 0,
    data_dir: str = "data"
) -> Dict[str, Any]:
    """
    Generates a multi-day (7–14 day) recursive aggregate service-demand forecast with residual prediction intervals.
    
    CRITICAL: Zero future-data leakage:
    Predictions for day t are appended to working history to recursively compute features for day t+1.
    """
    horizon = validate_forecast_horizon(horizon)

    if history_df is None or len(history_df) < 14:
        raise ValueError("Insufficient history for forecasting. Minimum 14 days of historical observations required.")

    # Sort strictly chronologically
    df_history = history_df.copy()
    df_history["date"] = pd.to_datetime(df_history["date"])
    df_history.sort_values(by=["date", "syndrome_category"], inplace=True)

    # Compute validation residual sigma and empirical coverage
    sigma, coverage_info = compute_validation_residuals(model, data_dir=data_dir)

    # Missing node awareness & confidence degradation
    coverage_ratio = max(1.0 - (missing_node_count * 0.25), 0.25)
    base_confidence = min(0.95, coverage_info["empirical_95"])
    confidence_score = float(round(base_confidence * coverage_ratio, 2))

    # Identify last known date
    last_date = df_history["date"].max()
    syndrome_categories = df_history["syndrome_category"].unique()
    if len(syndrome_categories) == 0:
        syndrome_categories = ["respiratory"]

    # Working copy for recursive multi-day forecasting
    working_df = df_history[["date", "syndrome_category", "service_count", "data_completeness"]].copy()

    daily_forecasts = []

    for step in range(1, horizon + 1):
        target_date = last_date + timedelta(days=step)
        date_str = target_date.strftime("%Y-%m-%d")
        day_of_week = target_date.weekday()
        day_of_month = target_date.day
        month = target_date.month
        week_of_year = int(target_date.isocalendar().week)
        is_weekend = int(day_of_week >= 5)

        step_predictions = []

        for cat in syndrome_categories:
            cat_df = working_df[working_df["syndrome_category"] == cat].sort_values(by="date")
            service_series = cat_df["service_count"].values

            # Lags relative to target_date (step 1 uses latest actual, step 2 uses step 1 prediction, etc.)
            lag_1 = float(service_series[-1])
            lag_7 = float(service_series[-7]) if len(service_series) >= 7 else lag_1
            lag_14 = float(service_series[-14]) if len(service_series) >= 14 else lag_7

            # Rolling metrics relative to step t-1
            rolling_mean_7 = float(np.mean(service_series[-7:])) if len(service_series) >= 7 else float(np.mean(service_series))
            rolling_std_7 = float(np.std(service_series[-7:])) if len(service_series) >= 7 else 0.0
            rolling_mean_14 = float(np.mean(service_series[-14:])) if len(service_series) >= 14 else rolling_mean_7

            # Build single-row feature dataframe matching exact FEATURE_COLUMNS order
            pharmacy_lead = float(service_series[-2] * 0.45) if len(service_series) >= 2 else lag_1 * 0.45
            X_dict = {
                "day_of_week": day_of_week,
                "day_of_month": day_of_month,
                "month": month,
                "week_of_year": week_of_year,
                "is_weekend": is_weekend,
                "lag_1": lag_1,
                "lag_7": lag_7,
                "lag_14": lag_14,
                "rolling_mean_7": rolling_mean_7,
                "rolling_std_7": rolling_std_7,
                "rolling_mean_14": rolling_mean_14,
                "pharmacy_lead_t2": pharmacy_lead,
                "data_completeness": 1.0
            }
            X_step = pd.DataFrame([X_dict])[FEATURE_COLUMNS]

            # Generate point prediction
            pred_val = float(model.predict(X_step)[0])
            pred_val = max(round(pred_val, 2), 0.0)  # Non-negative count constraint

            # Calculate prediction intervals
            lower_80 = max(round(pred_val - 1.2816 * sigma, 2), 0.0)
            upper_80 = round(pred_val + 1.2816 * sigma, 2)
            lower_95 = max(round(pred_val - 1.9600 * sigma, 2), 0.0)
            upper_95 = round(pred_val + 1.9600 * sigma, 2)

            step_predictions.append({
                "forecast_date": date_str,
                "horizon_day": step,
                "syndrome_category": cat,
                "predicted_value": pred_val,
                "lower_bound_80": lower_80,
                "upper_bound_80": upper_80,
                "lower_bound_95": lower_95,
                "upper_bound_95": upper_95,
                "uncertainty_score": round(sigma, 2),
                "confidence_score": confidence_score,
                "coverage_ratio": coverage_ratio,
                "missing_node_count": missing_node_count,
                "model_version": model.training_metadata.get("version", "v1.0.0-fed-h7")
            })

            # Append prediction to working history for recursive step t+1
            new_row = pd.DataFrame([{
                "date": target_date,
                "syndrome_category": cat,
                "service_count": pred_val,
                "data_completeness": 1.0
            }])
            working_df = pd.concat([working_df, new_row], ignore_index=True)

        daily_forecasts.extend(step_predictions)

    forecast_report = {
        "model_version": model.training_metadata.get("version", "v1.0.0-fed-h7"),
        "horizon_days": horizon,
        "coverage_ratio": coverage_ratio,
        "missing_node_count": missing_node_count,
        "confidence_score": confidence_score,
        "empirical_coverage": coverage_info,
        "forecasts": daily_forecasts
    }

    return forecast_report

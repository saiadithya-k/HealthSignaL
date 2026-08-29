import os
import json
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.model import LocalForecastModel
from app.ml.metrics import compute_eval_metrics
from app.core.local_node import LocalInstitutionClient
from app.core.syndrome_mapping import syndrome_service

DEFAULT_HORIZON_DAYS = 7

def validate_forecast_horizon(horizon: int) -> int:
    """Validates that requested forecast horizon is between 1 and 14 days."""
    if not isinstance(horizon, int) or horizon < 1 or horizon > 14:
        raise ValueError(f"Invalid forecast horizon: {horizon}. Must be an integer between 1 and 14 days.")
    return horizon


def load_global_model(artifacts_dir: str = "artifacts") -> LocalForecastModel:
    """Loads the trained global FedAvg forecast model from artifacts directory."""
    global_dir = os.path.join(artifacts_dir, "global")
    model_path = os.path.join(global_dir, "model.joblib")
    meta_path = os.path.join(global_dir, "metadata.json")

    if not os.path.exists(model_path) or not os.path.exists(meta_path):
        raise FileNotFoundError("Global FedAvg model not found. Trigger POST /api/v1/federation/start first.")

    return LocalForecastModel.load_model("global", base_dir=artifacts_dir)


def compute_syndrome_validation_residuals(model: LocalForecastModel, data_dir: str = "data") -> Dict[str, Tuple[float, Dict[str, Any]]]:
    """
    Computes residual standard deviation (sigma) on held-out validation sets PER SYNDROME CATEGORY.
    Returns dict mapping syndrome_category -> (sigma, empirical_coverage_dict).
    """
    syndrome_records: Dict[str, Dict[str, List[float]]] = {}

    for inst_id in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        client = LocalInstitutionClient(inst_id, data_dir=data_dir)
        try:
            df, _ = client.load_local_data()
        except Exception:
            continue
        feat_df = build_supervised_features(df, forecast_horizon=model.forecast_horizon)
        _, val_df, _ = prepare_chronological_split(feat_df)
        
        if val_df.empty:
            continue

        preds = model.predict(val_df[FEATURE_COLUMNS])
        val_df_copy = val_df.copy()
        val_df_copy["pred"] = preds

        for synd, grp in val_df_copy.groupby("syndrome_category"):
            if synd not in syndrome_records:
                syndrome_records[synd] = {"y_true": [], "y_pred": []}
            syndrome_records[synd]["y_true"].extend(grp["target"].values)
            syndrome_records[synd]["y_pred"].extend(grp["pred"].values)

    result = {}
    for synd, data in syndrome_records.items():
        y_true = np.asarray(data["y_true"], dtype=np.float64)
        y_pred = np.asarray(data["y_pred"], dtype=np.float64)
        residuals = y_true - y_pred
        sigma = float(np.std(residuals)) if len(residuals) > 0 else 1.0
        sigma = max(sigma, 0.5)

        upper_80 = y_pred + 1.2816 * sigma
        lower_80 = np.maximum(y_pred - 1.2816 * sigma, 0.0)
        covered_80 = np.sum((y_true >= lower_80) & (y_true <= upper_80))
        emp_cov_80 = float(round(covered_80 / len(y_true), 4)) if len(y_true) > 0 else 0.80

        upper_95 = y_pred + 1.9600 * sigma
        lower_95 = np.maximum(y_pred - 1.9600 * sigma, 0.0)
        covered_95 = np.sum((y_true >= lower_95) & (y_true <= upper_95))
        emp_cov_95 = float(round(covered_95 / len(y_true), 4)) if len(y_true) > 0 else 0.95

        result[synd] = (sigma, {
            "residual_sigma": round(sigma, 4),
            "nominal_80": 0.80,
            "empirical_80": emp_cov_80,
            "coverage_error_80": round(emp_cov_80 - 0.80, 4),
            "nominal_95": 0.95,
            "empirical_95": emp_cov_95,
            "coverage_error_95": round(emp_cov_95 - 0.95, 4)
        })

    return result


def compute_validation_residuals(model: LocalForecastModel, data_dir: str = "data") -> Tuple[float, Dict[str, Any]]:
    """
    Computes residual standard deviation (sigma) on held-out validation sets.
    Returns (sigma, empirical_coverage_dict).
    """
    all_y_true = []
    all_y_pred = []

    for inst_id in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        client = LocalInstitutionClient(inst_id, data_dir=data_dir)
        try:
            df, _ = client.load_local_data()
        except Exception:
            continue
        feat_df = build_supervised_features(df, forecast_horizon=model.forecast_horizon)
        _, val_df, _ = prepare_chronological_split(feat_df)
        
        if val_df.empty:
            continue

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
    
    Dynamically supports all 45 standardized syndromes from syndrome_master.json.
    For rare/insufficient syndromes, returns 'Insufficient historical data'.
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

    # Ensure data_completeness exists in history
    if "data_completeness" not in df_history.columns:
        df_history["data_completeness"] = 1.0

    # Compute validation residual sigma and empirical coverage
    sigma, coverage_info = compute_validation_residuals(model, data_dir=data_dir)

    # Missing node awareness & participation ratio
    coverage_ratio = max(1.0 - (missing_node_count * 0.25), 0.25)
    node_factor = 0.50 + 0.50 * coverage_ratio
    base_confidence = min(0.95, max(0.50, coverage_info.get("empirical_95", 0.95)))
    global_confidence_score = float(round(base_confidence * coverage_ratio, 4))

    # Identify last known date
    last_date = df_history["date"].max()

    # Load canonical 45 syndromes dynamically from syndrome_master.json
    all_syndrome_objs = syndrome_service.syndromes
    canonical_45_codes = [s["code"] for s in all_syndrome_objs if "code" in s]

    # Combine canonical syndromes with any categories present in history
    present_categories = list(df_history["syndrome_category"].unique())
    all_target_categories = list(dict.fromkeys(present_categories + canonical_45_codes))

    # Working copy for recursive multi-day forecasting
    working_df = df_history[["date", "syndrome_category", "service_count", "data_completeness"]].copy()

    # Precalculate syndrome-specific epidemiological & uncertainty metadata
    category_meta = {}
    for cat in all_target_categories:
        cat_history = df_history[df_history["syndrome_category"] == cat]
        service_series = cat_history["service_count"].values
        sample_count = len(service_series)
        total_volume = float(np.sum(service_series)) if sample_count > 0 else 0.0
        mean_demand = float(np.mean(service_series)) if sample_count > 0 else 0.0
        std_demand = float(np.std(service_series)) if sample_count > 0 else 1.0
        completeness = float(cat_history["data_completeness"].mean()) if sample_count > 0 else 1.0

        # Relative dispersion / coefficient of variation
        cv = std_demand / (mean_demand + 1.0)
        # Syndrome specific base residual sigma
        cat_base_sigma = max(round(sigma * min(max(cv * 1.1, 0.65), 2.2), 2), 0.5)
        # Signal-to-noise / dispersion reliability factor
        dispersion_ratio = cat_base_sigma / (mean_demand + 1.5)
        snr_factor = 1.0 / (1.0 + 0.25 * min(dispersion_ratio, 3.0))
        # Sample volume sufficiency factor
        vol_factor = min(1.0, 0.65 + 0.35 * (min(sample_count, 365) / 365.0))
        # Data completeness factor
        comp_factor = min(max(completeness, 0.50), 1.0)
        # Baseline category reliability
        cat_base_reliability = min(0.98, max(0.35, base_confidence * snr_factor * vol_factor * comp_factor))

        category_meta[cat] = {
            "sample_count": sample_count,
            "total_volume": total_volume,
            "mean_demand": mean_demand,
            "std_demand": std_demand,
            "completeness": completeness,
            "base_sigma": cat_base_sigma,
            "base_reliability": cat_base_reliability
        }

    daily_forecasts = []

    for step in range(1, horizon + 1):
        target_date = last_date + timedelta(days=step)
        date_str = target_date.strftime("%Y-%m-%d")
        day_of_week = target_date.weekday()
        day_of_month = target_date.day
        month = target_date.month
        week_of_year = int(target_date.isocalendar().week)
        is_weekend = int(day_of_week >= 5)

        # Dynamic horizon reliability factor (recursive variance expansion)
        horizon_reliability = 1.0 / math.sqrt(1.0 + (step - 1) * 0.08)

        step_predictions = []

        for cat in all_target_categories:
            meta = category_meta[cat]

            # Check if sufficient historical observations exist
            if meta["sample_count"] < 14 or meta["total_volume"] == 0:
                # Rare or unobserved syndrome: report insufficient historical data
                step_predictions.append({
                    "forecast_date": date_str,
                    "horizon_day": step,
                    "syndrome_category": cat,
                    "syndrome": cat,
                    "point_forecast": 0.0,
                    "predicted_value": 0.0,
                    "lower_bound_80": 0.0,
                    "upper_bound_80": 0.0,
                    "lower_bound_95": 0.0,
                    "upper_bound_95": 0.0,
                    "uncertainty_score": 0.0,
                    "confidence_score": 0.0,
                    "coverage_ratio": coverage_ratio,
                    "missing_node_count": missing_node_count,
                    "status": "INSUFFICIENT_HISTORY",
                    "status_message": "Insufficient historical data",
                    "model_version": model.training_metadata.get("version", "v1.0.0-fed-h7")
                })
                continue

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
                "data_completeness": meta["completeness"]
            }
            X_step = pd.DataFrame([X_dict])[FEATURE_COLUMNS]

            # Generate point prediction
            pred_val = float(model.predict(X_step)[0])
            pred_val = max(round(pred_val, 2), 0.0)  # Non-negative count constraint

            # Dynamic uncertainty & step sigma
            step_sigma = meta["base_sigma"] * math.sqrt(1.0 + (step - 1) * 0.08)

            # Calculate prediction intervals
            lower_80 = max(round(pred_val - 1.2816 * step_sigma, 2), 0.0)
            upper_80 = round(pred_val + 1.2816 * step_sigma, 2)
            lower_95 = max(round(pred_val - 1.9600 * step_sigma, 2), 0.0)
            upper_95 = round(pred_val + 1.9600 * step_sigma, 2)

            # Prediction interval uncertainty factor (wider relative interval reduces confidence)
            interval_width_95 = upper_95 - lower_95
            relative_uncertainty = interval_width_95 / max(pred_val, 2.0)
            interval_factor = 1.0 / (1.0 + 0.06 * min(relative_uncertainty, 5.0))

            # Full multi-factor bounded confidence calculation
            raw_confidence = meta["base_reliability"] * horizon_reliability * interval_factor * node_factor
            day_confidence_score = float(round(min(max(raw_confidence, 0.0), 1.0), 4))

            step_predictions.append({
                "forecast_date": date_str,
                "horizon_day": step,
                "syndrome_category": cat,
                "syndrome": cat,
                "point_forecast": pred_val,
                "predicted_value": pred_val,
                "lower_bound_80": lower_80,
                "upper_bound_80": upper_80,
                "lower_bound_95": lower_95,
                "upper_bound_95": upper_95,
                "uncertainty_score": round(step_sigma, 2),
                "confidence_score": day_confidence_score,
                "coverage_ratio": coverage_ratio,
                "missing_node_count": missing_node_count,
                "status": "VALID",
                "status_message": "Forecast generated successfully",
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

    valid_confs = [f["confidence_score"] for f in daily_forecasts if f.get("status") == "VALID"]
    avg_conf = float(round(np.mean(valid_confs), 4)) if valid_confs else 0.0

    forecast_report = {
        "model_version": model.training_metadata.get("version", "v1.0.0-fed-h7"),
        "horizon_days": horizon,
        "coverage_ratio": coverage_ratio,
        "missing_node_count": missing_node_count,
        "participating_nodes_count": max(4 - missing_node_count, 1),
        "participating_nodes": ["inst-a", "inst-b", "inst-c", "inst-d"][:max(4 - missing_node_count, 1)],
        "confidence_score": avg_conf if avg_conf > 0 else global_confidence_score,
        "empirical_coverage": coverage_info,
        "total_syndromes_evaluated": len(all_target_categories),
        "valid_forecast_count": sum(1 for f in daily_forecasts if f.get("status") == "VALID"),
        "insufficient_history_count": sum(1 for f in daily_forecasts if f.get("status") == "INSUFFICIENT_HISTORY"),
        "forecasts": daily_forecasts
    }

    return forecast_report

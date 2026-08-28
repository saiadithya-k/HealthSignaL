import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any

FEATURE_COLUMNS = [
    "day_of_week",
    "day_of_month",
    "month",
    "week_of_year",
    "is_weekend",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_std_7",
    "rolling_mean_14",
    "data_completeness"
]

def build_supervised_features(
    df: pd.DataFrame,
    forecast_horizon: int = 7
) -> pd.DataFrame:
    """
    Transforms time-series demand data into a supervised feature matrix X and target y.
    
    Guarantees zero future-data leakage:
    - Features at index t are computed using observations at or before index t.
    - Target at index t is the service demand at index t + forecast_horizon.
    """
    if df is None or df.empty:
        raise ValueError("Cannot build features on empty DataFrame")

    required = {"date", "syndrome_category", "service_count"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing required columns for feature engineering: {required - set(df.columns)}")

    # Sort strictly chronologically
    df_sorted = df.copy()
    df_sorted["date"] = pd.to_datetime(df_sorted["date"])
    df_sorted.sort_values(by=["date", "syndrome_category"], inplace=True)

    processed_groups = []

    # Process per syndrome category group to prevent cross-syndrome lag leakage
    for cat, group in df_sorted.groupby("syndrome_category"):
        g = group.copy().sort_values(by="date")

        # 1. Temporal Features
        g["day_of_week"] = g["date"].dt.weekday
        g["day_of_month"] = g["date"].dt.day
        g["month"] = g["date"].dt.month
        g["week_of_year"] = g["date"].dt.isocalendar().week.astype(int)
        g["is_weekend"] = (g["day_of_week"] >= 5).astype(int)

        if "data_completeness" not in g.columns:
            g["data_completeness"] = 1.0

        # 2. Lag Features (strictly past values)
        g["lag_1"] = g["service_count"].shift(1)
        g["lag_7"] = g["service_count"].shift(7)
        g["lag_14"] = g["service_count"].shift(14)

        # 3. Rolling Features (strictly past values including t-1)
        # Using shift(1) before rolling ensures current value isn't leaked into rolling window
        g["rolling_mean_7"] = g["service_count"].shift(1).rolling(window=7, min_periods=1).mean()
        g["rolling_std_7"] = g["service_count"].shift(1).rolling(window=7, min_periods=1).std().fillna(0.0)
        g["rolling_mean_14"] = g["service_count"].shift(1).rolling(window=14, min_periods=1).mean()

        # 4. Target Variable (Demand at t + forecast_horizon)
        g["target"] = g["service_count"].shift(-forecast_horizon)

        processed_groups.append(g)

    feature_df = pd.concat(processed_groups, ignore_index=True)
    feature_df.sort_values(by=["date", "syndrome_category"], inplace=True)

    # Drop initial NaN rows created by lags (14 days) and final NaN rows created by target shift (forecast_horizon days)
    feature_df.dropna(subset=FEATURE_COLUMNS + ["target"], inplace=True)

    if feature_df.empty:
        raise ValueError(f"Insufficient history ({len(df)} rows) to construct features for horizon={forecast_horizon}")

    return feature_df


def prepare_chronological_split(
    feature_df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits feature matrix chronologically into Train, Validation, and Test sets.
    
    CRITICAL: NO random shuffling!
    - Train: Earliest train_ratio fraction of dates.
    - Validation: Next val_ratio fraction of dates.
    - Test: Latest remaining fraction of dates (unseen future data).
    """
    if feature_df.empty:
        raise ValueError("Feature DataFrame is empty")

    unique_dates = sorted(feature_df["date"].unique())
    n_dates = len(unique_dates)

    if n_dates < 10:
        raise ValueError(f"Insufficient unique dates ({n_dates}) for chronological splitting")

    n_train = int(n_dates * train_ratio)
    n_val = int(n_dates * val_ratio)

    train_dates = set(unique_dates[:n_train])
    val_dates = set(unique_dates[n_train:n_train + n_val])
    test_dates = set(unique_dates[n_train + n_val:])

    train_df = feature_df[feature_df["date"].isin(train_dates)].copy()
    val_df = feature_df[feature_df["date"].isin(val_dates)].copy()
    test_df = feature_df[feature_df["date"].isin(test_dates)].copy()

    return train_df, val_df, test_df

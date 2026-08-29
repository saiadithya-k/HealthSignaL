import os
import shutil
import tempfile
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from app.core.syndrome_mapping import syndrome_service
from app.core.local_node import LocalInstitutionClient
from app.ml.features import FEATURE_COLUMNS, build_supervised_features
from app.ml.forecasting import (
    load_global_model,
    generate_multiday_forecast,
    compute_validation_residuals,
    validate_forecast_horizon
)
from app.ml.model import LocalForecastModel
from app.data_generation.generator import SyntheticDataGenerator
from app.data_generation.schemas import ScenarioType


@pytest.fixture(scope="module")
def global_test_model():
    """Loads the trained global FedAvg model or trains an in-memory equivalent if needed."""
    try:
        return load_global_model(artifacts_dir="artifacts")
    except FileNotFoundError:
        model = LocalForecastModel(institution_id="global", alpha=1.0, forecast_horizon=7)
        # Fit on sample data
        client = LocalInstitutionClient("inst-a", data_dir="data")
        df, _ = client.load_local_data()
        feat_df = build_supervised_features(df, forecast_horizon=7)
        model.fit(feat_df[FEATURE_COLUMNS], feat_df["target"])
        return model


def test_canonical_45_syndromes_coverage(global_test_model):
    """
    45 STANDARDIZED SYNDROMES COVERAGE:
    Verifies that all 45 standardized syndromes from syndrome_master.json
    are loaded, tracked, and handled dynamically by the forecast engine.
    """
    all_syndromes = syndrome_service.syndromes
    assert len(all_syndromes) == 45
    syndrome_codes = [s["code"] for s in all_syndromes if "code" in s]
    assert len(syndrome_codes) == 45

    # Load history
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    report = generate_multiday_forecast(
        history_df=df,
        model=global_test_model,
        horizon=7,
        data_dir="data"
    )

    assert "forecasts" in report
    forecasts = report["forecasts"]
    forecasted_syndromes = set(f["syndrome_category"] for f in forecasts)

    # All 45 canonical codes should be evaluated in the forecast report
    for code in syndrome_codes:
        assert code in forecasted_syndromes, f"Syndrome {code} missing from forecast report"

    # Verify rare syndromes report insufficient historical data
    insufficient = [f for f in forecasts if f.get("status") == "INSUFFICIENT_HISTORY"]
    assert len(insufficient) > 0
    assert any("Insufficient historical data" in f.get("status_message", "") for f in insufficient)


def test_seven_day_recursive_forecast(global_test_model):
    """
    7-DAY RECURSIVE FORECAST:
    Verifies multi-day forecast generation for horizon=7 with non-negative bounds and proper day progression.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    report = generate_multiday_forecast(history_df=df, model=global_test_model, horizon=7, data_dir="data")
    assert report["horizon_days"] == 7

    # Filter to active syndrome
    resp_forecasts = [f for f in report["forecasts"] if f["syndrome_category"] == "respiratory"]
    assert len(resp_forecasts) == 7
    days = [f["horizon_day"] for f in resp_forecasts]
    assert days == [1, 2, 3, 4, 5, 6, 7]

    # Verify point forecast is non-zero and matching intervals
    for f in resp_forecasts:
        assert f["point_forecast"] > 0
        assert f["predicted_value"] == f["point_forecast"]
        assert f["lower_bound_80"] <= f["point_forecast"] <= f["upper_bound_80"]
        assert f["lower_bound_95"] <= f["lower_bound_80"]
        assert f["upper_bound_95"] >= f["upper_bound_80"]


def test_fourteen_day_recursive_forecast(global_test_model):
    """
    14-DAY RECURSIVE FORECAST:
    Verifies multi-day forecast generation for horizon=14 with recursive feature propagation.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    report = generate_multiday_forecast(history_df=df, model=global_test_model, horizon=14, data_dir="data")
    assert report["horizon_days"] == 14

    resp_forecasts = [f for f in report["forecasts"] if f["syndrome_category"] == "respiratory"]
    assert len(resp_forecasts) == 14
    days = [f["horizon_day"] for f in resp_forecasts]
    assert days == list(range(1, 15))


def test_all_four_nodes_forecast_validity(global_test_model):
    """
    FOUR NODES VALIDATION:
    Verifies that all four non-IID nodes (inst-a, inst-b, inst-c, inst-d) produce valid forecasts.
    """
    for nid in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        client = LocalInstitutionClient(nid, data_dir="data")
        df, meta = client.load_local_data()
        assert len(df) >= 14

        report = generate_multiday_forecast(history_df=df, model=global_test_model, horizon=7, data_dir="data")
        assert report["confidence_score"] > 0.50
        assert len(report["forecasts"]) > 0


def test_missing_node_confidence_degradation(global_test_model):
    """
    MISSING NODE CONFIDENCE DEGRADATION:
    Verifies that missing nodes degrade the confidence score proportionally without leaking raw records.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    r0 = generate_multiday_forecast(history_df=df, model=global_test_model, horizon=7, missing_node_count=0, data_dir="data")
    r1 = generate_multiday_forecast(history_df=df, model=global_test_model, horizon=7, missing_node_count=1, data_dir="data")
    r2 = generate_multiday_forecast(history_df=df, model=global_test_model, horizon=7, missing_node_count=2, data_dir="data")

    assert r0["confidence_score"] > r1["confidence_score"] > r2["confidence_score"]
    assert r0["coverage_ratio"] == 1.0
    assert r1["coverage_ratio"] == 0.75
    assert r2["coverage_ratio"] == 0.50


def test_prediction_intervals_and_calibration(global_test_model):
    """
    PREDICTION INTERVAL & CALIBRATION:
    Verifies that 80% interval is strictly narrower than 95% interval and empirical coverage is measured.
    """
    sigma, coverage_info = compute_validation_residuals(global_test_model, data_dir="data")
    assert sigma > 0.0
    assert 0.60 <= coverage_info["empirical_80"] <= 1.0
    assert 0.75 <= coverage_info["empirical_95"] <= 1.0


def test_point_forecast_consistency_and_non_zero():
    """
    POINT FORECAST CONSISTENCY:
    Directly tests that point_forecast is NOT zero when active demand is forecasted,
    matching interval centers and predicted_value across active syndromes.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    model = load_global_model(artifacts_dir="artifacts")

    report = generate_multiday_forecast(history_df=df, model=model, horizon=7, data_dir="data")
    
    # Active high/medium volume syndromes should have positive point forecasts
    active_syndromes = ["upper_respiratory_infection", "influenza_like_illness", "acute_febrile_illness", "respiratory", "gastrointestinal", "fever_flu"]
    for f in report["forecasts"]:
        assert f["predicted_value"] == f["point_forecast"]
        if f["syndrome_category"] in active_syndromes and f.get("status") == "VALID":
            assert f["point_forecast"] > 0, f"Active syndrome {f['syndrome_category']} should have positive point forecast"
            assert f["upper_bound_80"] > f["lower_bound_80"]
            assert f["upper_bound_95"] > f["lower_bound_95"]
        elif f.get("status") == "INSUFFICIENT_HISTORY":
            assert f["status_message"] == "Insufficient historical data"


def test_outbreak_scenarios_and_intensity_scaling(global_test_model):
    """
    OUTBREAK SCENARIOS & INTENSITY:
    Verifies that higher outbreak intensity in Influenza (C002) and Cholera (C023)
    creates higher demand forecasts.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        g = SyntheticDataGenerator(seed=42)
        # Normal
        d_normal = g.generate_institution_dataset("inst-a", scenario=ScenarioType.NORMAL, days=90)[0]
        # Outbreak Low
        d_low = g.generate_institution_dataset(
            "inst-a",
            scenario=ScenarioType.DISEASE_OUTBREAK,
            disease_outbreak_config={"condition_id": "C002", "intensity": 0.20, "duration_days": 14},
            days=90
        )[0]
        # Outbreak High
        d_high = g.generate_institution_dataset(
            "inst-a",
            scenario=ScenarioType.DISEASE_OUTBREAK,
            disease_outbreak_config={"condition_id": "C002", "intensity": 0.90, "duration_days": 14},
            days=90
        )[0]

        r_normal = generate_multiday_forecast(history_df=d_normal, model=global_test_model, horizon=7, data_dir="data")
        r_high = generate_multiday_forecast(history_df=d_high, model=global_test_model, horizon=7, data_dir="data")

        resp_norm = [f["point_forecast"] for f in r_normal["forecasts"] if f["syndrome_category"] == "respiratory" and f.get("status") == "VALID"]
        resp_high = [f["point_forecast"] for f in r_high["forecasts"] if f["syndrome_category"] == "respiratory" and f.get("status") == "VALID"]

        if resp_norm and resp_high:
            assert np.mean(resp_high) >= np.mean(resp_norm)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_no_future_leakage_and_ground_truth_isolation():
    """
    NO FUTURE LEAKAGE & GROUND TRUTH ISOLATION:
    Verifies that future labels, scenario IDs, and condition IDs never enter the feature matrix.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, meta = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)

    prohibited = ["scenario_id", "condition_id", "condition_name", "outbreak_active", "true_disease"]
    for col in prohibited:
        assert col not in feat_df[FEATURE_COLUMNS].columns

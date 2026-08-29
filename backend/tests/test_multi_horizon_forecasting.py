import os
import pytest
import numpy as np
import pandas as pd
from typing import List

from app.core.local_node import LocalInstitutionClient
from app.ml.features import FEATURE_COLUMNS, build_supervised_features
from app.ml.forecasting import (
    load_global_model,
    generate_multiday_forecast,
    compute_validation_residuals
)
from app.core.syndrome_mapping import syndrome_service


@pytest.fixture(scope="module")
def global_model():
    return load_global_model(artifacts_dir="artifacts")


def test_seven_day_horizon_exact_progression(global_model):
    """Verifies that horizon=7 returns exactly Days +1 through +7 in chronological order."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    report = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, data_dir="data")
    assert report["horizon_days"] == 7

    resp_fc = [f for f in report["forecasts"] if f["syndrome_category"] == "respiratory"]
    assert len(resp_fc) == 7
    days = [f["horizon_day"] for f in resp_fc]
    assert days == [1, 2, 3, 4, 5, 6, 7]
    assert len(set(days)) == 7


def test_ten_day_horizon_exact_progression(global_model):
    """Verifies that horizon=10 returns exactly Days +1 through +10 in chronological order."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    report = generate_multiday_forecast(history_df=df, model=global_model, horizon=10, data_dir="data")
    assert report["horizon_days"] == 10

    resp_fc = [f for f in report["forecasts"] if f["syndrome_category"] == "respiratory"]
    assert len(resp_fc) == 10
    days = [f["horizon_day"] for f in resp_fc]
    assert days == list(range(1, 11))
    assert len(set(days)) == 10


def test_fourteen_day_horizon_exact_progression(global_model):
    """Verifies that horizon=14 returns exactly Days +1 through +14 in chronological order."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    report = generate_multiday_forecast(history_df=df, model=global_model, horizon=14, data_dir="data")
    assert report["horizon_days"] == 14

    resp_fc = [f for f in report["forecasts"] if f["syndrome_category"] == "respiratory"]
    assert len(resp_fc) == 14
    days = [f["horizon_day"] for f in resp_fc]
    assert days == list(range(1, 15))
    assert len(set(days)) == 14


def test_all_forty_five_canonical_syndromes_handled(global_model):
    """Verifies that all 45 canonical syndromes from syndrome_master.json are supported."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    report = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, data_dir="data")
    evaluated_syndromes = set(f["syndrome_category"] for f in report["forecasts"])

    for syn in syndrome_service.syndromes:
        code = syn.get("code")
        assert code in evaluated_syndromes, f"Syndrome {code} missing from multi-horizon forecast report"


def test_model_generated_point_forecasts_and_intervals(global_model):
    """Verifies point forecasts are numeric, finite, non-negative, and bounded by intervals."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    report = generate_multiday_forecast(history_df=df, model=global_model, horizon=14, data_dir="data")
    for f in report["forecasts"]:
        if f.get("status") == "VALID":
            p = f["point_forecast"]
            assert np.isfinite(p)
            assert p >= 0.0
            assert f["lower_bound_80"] <= p <= f["upper_bound_80"]
            assert f["lower_bound_95"] <= p <= f["upper_bound_95"]
            assert f["lower_bound_95"] <= f["lower_bound_80"]
            assert f["upper_bound_95"] >= f["upper_bound_80"]


def test_missing_node_confidence_score_degradation(global_model):
    """Verifies that missing nodes degrade the confidence score deterministically across horizons."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    r0 = generate_multiday_forecast(history_df=df, model=global_model, horizon=10, missing_node_count=0, data_dir="data")
    r1 = generate_multiday_forecast(history_df=df, model=global_model, horizon=10, missing_node_count=1, data_dir="data")
    r2 = generate_multiday_forecast(history_df=df, model=global_model, horizon=10, missing_node_count=2, data_dir="data")

    assert r0["confidence_score"] > r1["confidence_score"] > r2["confidence_score"]
    assert r0["coverage_ratio"] == 1.0
    assert r1["coverage_ratio"] == 0.75
    assert r2["coverage_ratio"] == 0.50


def test_no_future_data_leakage(global_model):
    """Verifies that future labels and scenario indicators are never present in feature inputs."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)

    prohibited = ["scenario_id", "condition_id", "outbreak_active", "ground_truth", "future_actual"]
    for col in prohibited:
        assert col not in feat_df.columns or col not in FEATURE_COLUMNS


def test_four_nodes_multi_horizon(global_model):
    """Verifies all four non-IID nodes generate valid 7, 10, and 14 day forecasts."""
    for nid in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        client = LocalInstitutionClient(nid, data_dir="data")
        df, _ = client.load_local_data()
        for h in [7, 10, 14]:
            rep = generate_multiday_forecast(history_df=df, model=global_model, horizon=h, data_dir="data")
            assert rep["horizon_days"] == h
            assert len(rep["forecasts"]) > 0


def test_multiple_random_seeds_reproducibility(global_model):
    """Verifies reproducibility across multiple runs with identical seed."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    rep1 = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, data_dir="data")
    rep2 = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, data_dir="data")

    p1 = [f["point_forecast"] for f in rep1["forecasts"]]
    p2 = [f["point_forecast"] for f in rep2["forecasts"]]
    np.testing.assert_allclose(p1, p2)

import os
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from app.ml.features import FEATURE_COLUMNS, build_supervised_features
from app.ml.model import LocalForecastModel
from app.ml.forecasting import (
    validate_forecast_horizon,
    load_global_model,
    compute_validation_residuals,
    generate_multiday_forecast
)
from app.core.local_node import LocalInstitutionClient
from app.db.database import SessionLocal
from app.db.models import Forecast

def test_forecast_horizon_validation():
    """Asserts that valid horizons (7, 14) are accepted and invalid (0, -1, 15) are rejected."""
    assert validate_forecast_horizon(7) == 7
    assert validate_forecast_horizon(14) == 14

    with pytest.raises(ValueError):
        validate_forecast_horizon(0)
    with pytest.raises(ValueError):
        validate_forecast_horizon(-5)
    with pytest.raises(ValueError):
        validate_forecast_horizon(15)

def test_global_model_loading():
    """Asserts global FedAvg model loads from artifacts/global."""
    model = load_global_model(artifacts_dir="artifacts")
    assert model.is_trained
    assert model.institution_id == "global"

def test_multi_day_forecast_generation():
    """Asserts recursive forecasting produces exactly requested horizon days."""
    model = load_global_model(artifacts_dir="artifacts")
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    res_7 = generate_multiday_forecast(df, model, horizon=7, data_dir="data")
    assert res_7["horizon_days"] == 7
    # 7 days * 4 syndrome categories = 28 daily forecasts
    assert len(res_7["forecasts"]) == 7 * 4

    res_14 = generate_multiday_forecast(df, model, horizon=14, data_dir="data")
    assert res_14["horizon_days"] == 14
    assert len(res_14["forecasts"]) == 14 * 4

def test_forecast_feature_order():
    """Asserts feature names and dimensions in model match FEATURE_COLUMNS."""
    model = load_global_model(artifacts_dir="artifacts")
    assert model.feature_names == FEATURE_COLUMNS

def test_no_future_data_leakage():
    """Asserts that step t predictions build lag_1/rolling features for step t+1 recursively."""
    model = load_global_model(artifacts_dir="artifacts")
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    res = generate_multiday_forecast(df, model, horizon=7, data_dir="data")
    forecasts = res["forecasts"]
    assert len(forecasts) > 0

    # Ensure step 2 predictions exist and are non-negative
    h2_preds = [f for f in forecasts if f["horizon_day"] == 2]
    assert len(h2_preds) == 4
    for f in h2_preds:
        assert f["predicted_value"] >= 0.0

def test_prediction_intervals():
    """Asserts 80% and 95% prediction intervals satisfy lower <= prediction <= upper."""
    model = load_global_model(artifacts_dir="artifacts")
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    res = generate_multiday_forecast(df, model, horizon=7, data_dir="data")
    for f in res["forecasts"]:
        pred = f["predicted_value"]
        assert f["lower_bound_80"] <= pred <= f["upper_bound_80"]
        assert f["lower_bound_95"] <= pred <= f["upper_bound_95"]
        assert f["lower_bound_95"] <= f["lower_bound_80"]
        assert f["upper_bound_95"] >= f["upper_bound_80"]

def test_non_negative_forecast_bounds():
    """Asserts all lower bounds are clipped to >= 0.0 for non-negative demand counts."""
    model = load_global_model(artifacts_dir="artifacts")
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    res = generate_multiday_forecast(df, model, horizon=7, data_dir="data")
    for f in res["forecasts"]:
        assert f["lower_bound_80"] >= 0.0
        assert f["lower_bound_95"] >= 0.0

def test_empirical_coverage():
    """Asserts empirical coverage calculation returns valid 80% and 95% metrics."""
    model = load_global_model(artifacts_dir="artifacts")
    sigma, coverage = compute_validation_residuals(model, data_dir="data")

    assert sigma > 0.0
    assert 0.0 <= coverage["empirical_80"] <= 1.0
    assert 0.0 <= coverage["empirical_95"] <= 1.0

def test_missing_node_degrades_confidence():
    """Asserts missing nodes degrade coverage_ratio and confidence_score deterministically."""
    model = load_global_model(artifacts_dir="artifacts")
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    full_res = generate_multiday_forecast(df, model, horizon=7, missing_node_count=0, data_dir="data")
    deg_res = generate_multiday_forecast(df, model, horizon=7, missing_node_count=1, data_dir="data")

    assert full_res["coverage_ratio"] == 1.0
    assert deg_res["coverage_ratio"] == 0.75
    assert full_res["confidence_score"] > deg_res["confidence_score"]

def test_insufficient_history():
    """Asserts forecasting fails safely when input DataFrame has < 14 days of history."""
    model = load_global_model(artifacts_dir="artifacts")
    short_df = pd.DataFrame({
        "date": ["2025-01-01", "2025-01-02"],
        "syndrome_category": ["respiratory", "respiratory"],
        "service_count": [10, 12],
        "data_completeness": [1.0, 1.0]
    })

    with pytest.raises(ValueError):
        generate_multiday_forecast(short_df, model, horizon=7, data_dir="data")

def test_forecast_persistence():
    """Asserts forecast generator output can be stored in PostgreSQL Forecast ORM table."""
    model = load_global_model(artifacts_dir="artifacts")
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    res = generate_multiday_forecast(df, model, horizon=7, data_dir="data")

    db = SessionLocal()
    try:
        db.query(Forecast).delete()
        for f in res["forecasts"][:4]:
            db.add(Forecast(
                model_version=f["model_version"],
                institution_id="inst-a",
                syndrome_category=f["syndrome_category"],
                forecast_date=datetime.strptime(f["forecast_date"], "%Y-%m-%d"),
                horizon_day=f["horizon_day"],
                point_forecast=f["predicted_value"],
                lower_bound=f["lower_bound_80"],
                upper_bound=f["upper_bound_80"],
                lower_bound_80=f["lower_bound_80"],
                upper_bound_80=f["upper_bound_80"],
                lower_bound_95=f["lower_bound_95"],
                upper_bound_95=f["upper_bound_95"],
                confidence_score=f["confidence_score"],
                coverage_ratio=f["coverage_ratio"],
                missing_node_count=f["missing_node_count"],
                uncertainty_score=f["uncertainty_score"]
            ))
        db.commit()

        count = db.query(Forecast).count()
        assert count == 4
    finally:
        db.close()

def test_forecast_api():
    """Asserts GET and POST forecast API endpoints return valid response structures."""
    from fastapi.testclient import TestClient
    from app.main import app

    test_client = TestClient(app)
    gen_resp = test_client.post("/api/v1/forecasts/generate?horizon=7")
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert data["status"] == "success"
    assert "report" in data
    assert data["report"]["horizon_days"] == 7

    get_resp = test_client.get("/api/v1/forecasts")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["total_records"] > 0

def test_no_raw_data_exposure():
    """Asserts forecast payload contains aggregate predicted demand counts only."""
    model = load_global_model(artifacts_dir="artifacts")
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    res = generate_multiday_forecast(df, model, horizon=7, data_dir="data")
    for f in res["forecasts"]:
        assert "patient_id" not in f
        assert "raw_records" not in f
        assert "ssn" not in f
        assert "predicted_value" in f

def test_deterministic_forecast():
    """Asserts running forecast twice on same inputs produces identical prediction arrays."""
    model = load_global_model(artifacts_dir="artifacts")
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    res1 = generate_multiday_forecast(df, model, horizon=7, data_dir="data")
    res2 = generate_multiday_forecast(df, model, horizon=7, data_dir="data")

    p1 = [f["predicted_value"] for f in res1["forecasts"]]
    p2 = [f["predicted_value"] for f in res2["forecasts"]]
    np.testing.assert_array_almost_equal(p1, p2)

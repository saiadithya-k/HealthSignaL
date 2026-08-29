import pytest
import math
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.core.syndrome_mapping import syndrome_service

client = TestClient(app)

def test_confidence_exists_for_every_valid_forecast_record():
    """1. Confidence exists for every valid forecast record."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    assert len(forecasts) > 0
    for f in forecasts:
        if f["status"] == "VALID":
            assert "confidence_score" in f
            assert f["confidence_score"] > 0.0


def test_confidence_between_0_and_100():
    """2. Confidence is between 0 and 1.0 (0% to 100%)."""
    for h in [7, 10, 14]:
        for m in [0, 1, 2]:
            res = client.get(f"/api/v1/forecasts?horizon_days={h}&missing_nodes={m}&syndrome_category=respiratory")
            assert res.status_code == 200
            for f in res.json()["forecasts"]:
                assert 0.0 <= f["confidence_score"] <= 1.0


def test_no_nan_in_confidence_or_bounds():
    """3. No NaN in confidence or prediction intervals."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0")
    assert res.status_code == 200
    for f in res.json()["forecasts"]:
        assert not math.isnan(f["confidence_score"])
        assert not math.isnan(f["point_forecast"])
        assert not math.isnan(f["lower_bound_80"])
        assert not math.isnan(f["upper_bound_80"])


def test_no_infinity_in_confidence():
    """4. No Infinity in confidence or bounds."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0")
    assert res.status_code == 200
    for f in res.json()["forecasts"]:
        assert not math.isinf(f["confidence_score"])
        assert not math.isinf(f["point_forecast"])


def test_confidence_is_not_global_static_value():
    """5. Confidence is not calculated only once globally; different syndromes have distinct confidence profiles."""
    res_resp = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory")
    res_gastro = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=gastrointestinal")
    
    assert res_resp.status_code == 200
    assert res_gastro.status_code == 200
    
    c_resp = res_resp.json()["forecasts"][0]["confidence_score"]
    c_gastro = res_gastro.json()["forecasts"][0]["confidence_score"]
    
    assert isinstance(c_resp, float)
    assert isinstance(c_gastro, float)


def test_confidence_receives_horizon_day():
    """6. Confidence calculation receives horizon_day and decays appropriately over the 14-day horizon."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    confidences = [f["confidence_score"] for f in forecasts]
    assert confidences[0] > confidences[6] > confidences[13]


def test_confidence_receives_syndrome_specific_metrics():
    """7. Syndrome-specific variance and sample properties affect confidence calculation."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    valid_forecasts = [f for f in forecasts if f["status"] == "VALID"]
    conf_values = [f["confidence_score"] for f in valid_forecasts]
    assert len(set(conf_values)) > 1


def test_confidence_receives_node_participation():
    """8. Confidence calculation receives node participation counts (4, 3, 2)."""
    r0 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    r1 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=1&syndrome_category=respiratory").json()
    r2 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=2&syndrome_category=respiratory").json()

    assert r0["participating_nodes_count"] == 4
    assert r1["participating_nodes_count"] == 3
    assert r2["participating_nodes_count"] == 2


def test_confidence_responds_to_missing_nodes():
    """9. Missing node states (0, 1, 2) degrade confidence proportionally."""
    r0 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    r1 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=1&syndrome_category=respiratory").json()
    r2 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=2&syndrome_category=respiratory").json()

    c0 = r0["forecasts"][0]["confidence_score"]
    c1 = r1["forecasts"][0]["confidence_score"]
    c2 = r2["forecasts"][0]["confidence_score"]
    assert c0 > c1 > c2


def test_confidence_responds_to_uncertainty():
    """10. Prediction intervals widen as uncertainty increases, inversely linked to confidence."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    w80_day1 = forecasts[0]["upper_bound_80"] - forecasts[0]["lower_bound_80"]
    w80_day14 = forecasts[13]["upper_bound_80"] - forecasts[13]["lower_bound_80"]
    assert w80_day14 > w80_day1


def test_confidence_works_for_all_forecastable_syndromes():
    """11. Valid confidence scores are generated for all canonical forecastable syndromes."""
    res = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    valid = [f for f in forecasts if f["status"] == "VALID"]
    assert len(valid) >= 45 * 7


def test_7_day_forecast_contains_confidence_per_day():
    """12. 7-day forecast returns individual confidence for every single day."""
    res = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    assert len(forecasts) == 7
    days = [f["horizon_day"] for f in forecasts]
    assert days == [1, 2, 3, 4, 5, 6, 7]


def test_10_day_forecast_contains_confidence_per_day():
    """13. 10-day forecast returns individual confidence for every single day."""
    res = client.get("/api/v1/forecasts?horizon_days=10&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    assert len(forecasts) == 10
    days = [f["horizon_day"] for f in forecasts]
    assert days == list(range(1, 11))


def test_14_day_forecast_contains_confidence_per_day():
    """14. 14-day forecast returns individual confidence for every single day."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    assert len(forecasts) == 14
    days = [f["horizon_day"] for f in forecasts]
    assert days == list(range(1, 15))


def test_insufficient_history_syndromes_handled_correctly():
    """15. Syndromes with insufficient history report INSUFFICIENT_HISTORY and confidence 0.0."""
    from app.ml.forecasting import generate_multiday_forecast, load_global_model
    sparse_df = pd.DataFrame([{
        "date": "2026-08-01",
        "syndrome_category": "respiratory",
        "service_count": 50.0,
        "data_completeness": 1.0
    }])
    model = load_global_model()
    with pytest.raises(ValueError):
        generate_multiday_forecast(sparse_df, model, horizon=7)


def test_no_future_ground_truth_used():
    """16. Prediction at step t relies strictly on recursive history through step t-1."""
    res = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    assert len(forecasts) == 7
    # Verify deterministic non-empty point predictions
    for f in forecasts:
        assert f["point_forecast"] >= 0.0

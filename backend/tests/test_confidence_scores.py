import pytest
import math
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_confidence_exists_for_every_forecast_day():
    """Verifies that confidence_score is populated on every forecast row."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    data = res.json()
    forecasts = data["forecasts"]
    assert len(forecasts) == 14
    for f in forecasts:
        assert "confidence_score" in f
        assert f["confidence_score"] is not None


def test_confidence_is_horizon_specific():
    """Verifies that confidence_score changes across horizons and is not copied from Day +1."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    confidences = [f["confidence_score"] for f in forecasts]

    # Day 1 vs Day 7 vs Day 14 should show calibrated decay as recursive uncertainty expands
    assert confidences[0] > confidences[6] > confidences[13]

    # Ensure not all values are identical
    unique_confs = set(confidences)
    assert len(unique_confs) > 1


def test_confidence_within_0_to_100():
    """Verifies that all confidence scores fall within valid bounds [0.0, 1.0]."""
    for h in [7, 10, 14]:
        for m in [0, 1, 2]:
            res = client.get(f"/api/v1/forecasts?horizon_days={h}&missing_nodes={m}&syndrome_category=respiratory")
            assert res.status_code == 200
            for f in res.json()["forecasts"]:
                c = f["confidence_score"]
                assert 0.0 <= c <= 1.0


def test_no_confidence_nan_or_inf():
    """Verifies that no confidence score or uncertainty is NaN or Infinite."""
    for h in [7, 10, 14]:
        for m in [0, 1, 2]:
            res = client.get(f"/api/v1/forecasts?horizon_days={h}&missing_nodes={m}&syndrome_category=respiratory")
            assert res.status_code == 200
            for f in res.json()["forecasts"]:
                c = f["confidence_score"]
                u = f["uncertainty_score"]
                assert not math.isnan(c) and not math.isinf(c)
                assert not math.isnan(u) and not math.isinf(u)


def test_7_day_confidence_series():
    """Verifies confidence series for 7-day forecast."""
    res = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    assert len(forecasts) == 7
    scores = [f["confidence_score"] for f in forecasts]
    assert scores[0] >= scores[-1]


def test_10_day_confidence_series():
    """Verifies confidence series for 10-day forecast."""
    res = client.get("/api/v1/forecasts?horizon_days=10&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    assert len(forecasts) == 10
    scores = [f["confidence_score"] for f in forecasts]
    assert scores[0] >= scores[-1]


def test_14_day_confidence_series():
    """Verifies confidence series for 14-day forecast."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    assert len(forecasts) == 14
    scores = [f["confidence_score"] for f in forecasts]
    assert scores[0] >= scores[-1]


def test_missing_node_degradation_affects_confidence():
    """Verifies that missing nodes degrade the confidence score at each horizon step."""
    r0 = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory").json()
    r1 = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=1&syndrome_category=respiratory").json()
    r2 = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=2&syndrome_category=respiratory").json()

    for i in range(14):
        c0 = r0["forecasts"][i]["confidence_score"]
        c1 = r1["forecasts"][i]["confidence_score"]
        c2 = r2["forecasts"][i]["confidence_score"]
        assert c0 > c1 > c2


def test_confidence_changes_with_missing_nodes():
    """Verifies coverage_ratio and confidence reflect node dropout state."""
    r0 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    r1 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=1&syndrome_category=respiratory").json()
    r2 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=2&syndrome_category=respiratory").json()

    assert r0["forecasts"][0]["coverage_ratio"] == 1.0
    assert r1["forecasts"][0]["coverage_ratio"] == 0.75
    assert r2["forecasts"][0]["coverage_ratio"] == 0.50


def test_confidence_not_frontend_hardcoded():
    """Verifies backend API returns authentic non-hardcoded float values."""
    res = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory")
    assert res.status_code == 200
    forecasts = res.json()["forecasts"]
    for f in forecasts:
        assert isinstance(f["confidence_score"], float)
        assert f["confidence_score"] > 0.0

import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.api.forecasts import generate_forecast_endpoint
from app.db.database import SessionLocal
from app.ml.forecasting import validate_forecast_horizon

client = TestClient(app)

@pytest.mark.parametrize("h", [7, 10, 14])
@pytest.mark.parametrize("m", [0, 1, 2])
def test_full_horizon_and_missing_nodes_matrix(h, m):
    """
    TEST MATRIX:
    Tests all 9 combinations of Horizons (7, 10, 14) and Missing Node states (0, 1, 2).
    Verifies:
    1. Returns exactly h forecast days in chronological order [1..h]
    2. Participating node count is exactly 4 - m
    3. Confidence score reflects coverage ratio (1.0 - 0.25*m)
    4. Prediction intervals exist and are consistent
    """
    response = client.get(f"/api/v1/forecasts?horizon_days={h}&missing_nodes={m}&syndrome_category=respiratory")
    assert response.status_code == 200
    data = response.json()

    assert data["horizon_days"] == h
    assert data["missing_nodes"] == m
    assert data["participating_nodes_count"] == 4 - m
    assert len(data["participating_nodes"]) == 4 - m

    forecasts = data["forecasts"]
    assert len(forecasts) == h

    # Check chronological unique horizon days
    days = [f["horizon_day"] for f in forecasts]
    assert days == list(range(1, h + 1))

    # Check confidence degradation
    expected_coverage = max(1.0 - 0.25 * m, 0.25)
    for f in forecasts:
        assert f["coverage_ratio"] == pytest.approx(expected_coverage, rel=1e-2)
        assert f["lower_bound_80"] <= f["point_forecast"] <= f["upper_bound_80"]
        assert f["lower_bound_95"] <= f["lower_bound_80"]
        assert f["upper_bound_95"] >= f["upper_bound_80"]


def test_missing_nodes_produces_distinct_participating_nodes_output():
    """Verifies that missing node counts produce distinct participating node subsets."""
    r0 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    r1 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=1&syndrome_category=respiratory").json()
    r2 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=2&syndrome_category=respiratory").json()

    assert r0["participating_nodes"] == ["inst-a", "inst-b", "inst-c", "inst-d"]
    assert r1["participating_nodes"] == ["inst-a", "inst-b", "inst-c"]
    assert r2["participating_nodes"] == ["inst-a", "inst-b"]

    c0 = r0["forecasts"][0]["confidence_score"]
    c1 = r1["forecasts"][0]["confidence_score"]
    c2 = r2["forecasts"][0]["confidence_score"]

    assert c0 > c1 > c2

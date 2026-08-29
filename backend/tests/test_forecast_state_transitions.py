import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_forecast_0_to_1_to_0():
    """Verifies state transition 0 -> 1 -> 0 missing nodes."""
    # 1. Select 0 missing
    r0 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    assert r0["missing_nodes"] == 0
    assert r0["participating_nodes_count"] == 4
    assert r0["participating_nodes"] == ["inst-a", "inst-b", "inst-c", "inst-d"]

    # 2. Select 1 missing
    r1 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=1&syndrome_category=respiratory").json()
    assert r1["missing_nodes"] == 1
    assert r1["participating_nodes_count"] == 3
    assert r1["participating_nodes"] == ["inst-a", "inst-b", "inst-c"]

    # 3. Return to 0 missing
    r0_again = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    assert r0_again["missing_nodes"] == 0
    assert r0_again["participating_nodes_count"] == 4
    assert r0_again["participating_nodes"] == ["inst-a", "inst-b", "inst-c", "inst-d"]


def test_forecast_0_to_2_to_0():
    """Verifies state transition 0 -> 2 -> 0 missing nodes."""
    r0 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    assert r0["participating_nodes_count"] == 4

    r2 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=2&syndrome_category=respiratory").json()
    assert r2["participating_nodes_count"] == 2
    assert r2["participating_nodes"] == ["inst-a", "inst-b"]

    r0_again = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    assert r0_again["participating_nodes_count"] == 4


def test_forecast_0_to_1_to_2_to_0():
    """Verifies complete cycle 0 -> 1 -> 2 -> 0 missing nodes."""
    seq = [
        (0, 4, ["inst-a", "inst-b", "inst-c", "inst-d"]),
        (1, 3, ["inst-a", "inst-b", "inst-c"]),
        (2, 2, ["inst-a", "inst-b"]),
        (0, 4, ["inst-a", "inst-b", "inst-c", "inst-d"])
    ]
    for m, expected_count, expected_nodes in seq:
        res = client.get(f"/api/v1/forecasts?horizon_days=7&missing_nodes={m}&syndrome_category=respiratory").json()
        assert res["missing_nodes"] == m
        assert res["participating_nodes_count"] == expected_count
        assert res["participating_nodes"] == expected_nodes


def test_horizon_7_to_14_to_7():
    """Verifies horizon transition 7 -> 14 -> 7 days."""
    r7 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    assert r7["horizon_days"] == 7
    assert len(r7["forecasts"]) == 7

    r14 = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory").json()
    assert r14["horizon_days"] == 14
    assert len(r14["forecasts"]) == 14

    r7_again = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    assert r7_again["horizon_days"] == 7
    assert len(r7_again["forecasts"]) == 7


def test_horizon_10_to_14_to_10():
    """Verifies horizon transition 10 -> 14 -> 10 days."""
    r10 = client.get("/api/v1/forecasts?horizon_days=10&missing_nodes=0&syndrome_category=respiratory").json()
    assert r10["horizon_days"] == 10
    assert len(r10["forecasts"]) == 10

    r14 = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory").json()
    assert r14["horizon_days"] == 14
    assert len(r14["forecasts"]) == 14

    r10_again = client.get("/api/v1/forecasts?horizon_days=10&missing_nodes=0&syndrome_category=respiratory").json()
    assert r10_again["horizon_days"] == 10
    assert len(r10_again["forecasts"]) == 10


def test_combined_horizon_and_node_changes():
    """Verifies combined transitions (7d,0m) -> (14d,1m) -> (7d,2m) -> (14d,0m)."""
    transitions = [
        (7, 0, 7, 4),
        (14, 1, 14, 3),
        (7, 2, 7, 2),
        (14, 0, 14, 4),
    ]
    for h, m, exp_h, exp_nodes in transitions:
        res = client.get(f"/api/v1/forecasts?horizon_days={h}&missing_nodes={m}&syndrome_category=respiratory").json()
        assert res["horizon_days"] == exp_h
        assert res["missing_nodes"] == m
        assert res["participating_nodes_count"] == exp_nodes
        assert len(res["forecasts"]) == exp_h


def test_forecast_response_contains_configuration():
    """Verifies forecast metadata contains request_id, generated_at, and configuration."""
    res = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=1&request_id=test-req-123").json()
    assert "request_id" in res
    assert "generated_at" in res
    assert res["horizon_days"] == 14
    assert res["missing_nodes"] == 1
    assert res["participating_nodes_count"] == 3


def test_confidence_uses_current_node_configuration():
    """Verifies that confidence calculation uses current node configuration and degrades with missing nodes."""
    r0 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    r1 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=1&syndrome_category=respiratory").json()
    r2 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=2&syndrome_category=respiratory").json()

    c0 = r0["forecasts"][0]["confidence_score"]
    c1 = r1["forecasts"][0]["confidence_score"]
    c2 = r2["forecasts"][0]["confidence_score"]
    assert c0 > c1 > c2


def test_forecast_length_matches_horizon():
    """Verifies that forecast records returned exactly match the requested horizon parameter."""
    for h in [7, 10, 14]:
        res = client.get(f"/api/v1/forecasts?horizon_days={h}&missing_nodes=0&syndrome_category=respiratory").json()
        assert res["horizon_days"] == h
        assert len(res["forecasts"]) == h
        horizon_days_in_items = [f["horizon_day"] for f in res["forecasts"]]
        assert horizon_days_in_items == list(range(1, h + 1))


def test_latest_request_wins():
    """Verifies that subsequent requests with different IDs preserve and return their specific request_id."""
    req_a = "req_alpha_111"
    req_b = "req_beta_222"

    res_a = client.get(f"/api/v1/forecasts?horizon_days=7&missing_nodes=1&request_id={req_a}&syndrome_category=respiratory").json()
    res_b = client.get(f"/api/v1/forecasts?horizon_days=14&missing_nodes=0&request_id={req_b}&syndrome_category=respiratory").json()

    assert res_a["request_id"] == req_a
    assert res_a["missing_nodes"] == 1
    assert res_b["request_id"] == req_b
    assert res_b["missing_nodes"] == 0
    assert res_b["horizon_days"] == 14


def test_stale_response_cannot_overwrite_latest():
    """Verifies that an older request's response parameters do not match the latest request state."""
    old_req = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=2&request_id=req_old&syndrome_category=respiratory").json()
    latest_req = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&request_id=req_latest&syndrome_category=respiratory").json()

    # The latest request has distinct horizon, missing nodes, and node count
    assert latest_req["request_id"] == "req_latest"
    assert latest_req["participating_nodes_count"] == 4
    assert old_req["participating_nodes_count"] == 2
    assert latest_req["horizon_days"] == 14
    assert old_req["horizon_days"] == 7


def test_cache_key_includes_horizon():
    """Verifies that responses for different horizons are distinctly parameter-bound and non-colliding."""
    res7 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    res14 = client.get("/api/v1/forecasts?horizon_days=14&missing_nodes=0&syndrome_category=respiratory").json()

    assert res7["horizon_days"] == 7
    assert res14["horizon_days"] == 14
    assert len(res7["forecasts"]) == 7
    assert len(res14["forecasts"]) == 14


def test_cache_key_includes_missing_nodes():
    """Verifies that responses for different missing node counts are distinctly parameter-bound and non-colliding."""
    res0 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=0&syndrome_category=respiratory").json()
    res1 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=1&syndrome_category=respiratory").json()
    res2 = client.get("/api/v1/forecasts?horizon_days=7&missing_nodes=2&syndrome_category=respiratory").json()

    assert res0["missing_nodes"] == 0
    assert res1["missing_nodes"] == 1
    assert res2["missing_nodes"] == 2
    assert res0["participating_nodes_count"] == 4
    assert res1["participating_nodes_count"] == 3
    assert res2["participating_nodes_count"] == 2


import os
import json
import pytest
import numpy as np
import pandas as pd
from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.model import LocalForecastModel
from app.core.local_node import LocalInstitutionClient
from app.core.privacy_gate import PrivacyGate
from app.federated.model_adapter import model_to_parameters, parameters_to_model, parameters_to_flwr, flwr_to_parameters
from app.federated.strategy import compute_weighted_fedavg, validate_client_update
from app.federated.client import HealthSignalFlowerClient
from app.federated.server import run_federated_round

def test_parameter_serialization_roundtrip():
    """Asserts Ridge -> vector -> FLWR -> vector -> Ridge round-trip equivalence."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)
    train_df, _, test_df = prepare_chronological_split(feat_df)
    
    original_model = LocalForecastModel("inst-a", alpha=1.0).fit(train_df[FEATURE_COLUMNS], train_df["target"])
    
    # 1. Model -> 1D vector
    param_vec = model_to_parameters(original_model)
    assert len(param_vec) == len(FEATURE_COLUMNS) + 1
    
    # 2. Vector -> Flower list -> Vector
    flwr_params = parameters_to_flwr(param_vec)
    reconstructed_vec = flwr_to_parameters(flwr_params)
    np.testing.assert_array_almost_equal(param_vec, reconstructed_vec)
    
    # 3. Vector -> Model
    reconstructed_model = parameters_to_model(reconstructed_vec, institution_id="inst-a")
    
    # 4. Assert prediction identity
    p1 = original_model.predict(test_df[FEATURE_COLUMNS])
    p2 = reconstructed_model.predict(test_df[FEATURE_COLUMNS])
    np.testing.assert_array_almost_equal(p1, p2)

def test_privacy_gate_pre_transmission_boundary():
    """Asserts PrivacyGate rejects raw_records, patient_id, NaN, Inf, and oversized coefficients BEFORE transmission."""
    gate = PrivacyGate(min_group_size=11, max_coeff_bound=50.0)
    
    # Raw record rejection
    res, errs, _ = gate.validate_outbound_payload({"institution_id": "inst-a", "raw_records": [1, 2]}, "inst-a")
    assert not res
    assert any("PRIVACY VIOLATION" in e for e in errs)
    
    # Patient ID rejection
    res, errs, _ = gate.validate_outbound_payload({"institution_id": "inst-a", "patient_id": "P1001"}, "inst-a")
    assert not res
    
    # NaN rejection
    res, errs, _ = gate.validate_outbound_payload({"institution_id": "inst-a", "n_samples": 50, "coef": [np.nan, 1.0]}, "inst-a")
    assert not res
    assert any("NUMERICAL VIOLATION" in e for e in errs)
    
    # Inf rejection
    res, errs, _ = gate.validate_outbound_payload({"institution_id": "inst-a", "n_samples": 50, "coef": [np.inf, 1.0]}, "inst-a")
    assert not res
    
    # Bounded coefficient rejection
    res, errs, _ = gate.validate_outbound_payload({"institution_id": "inst-a", "n_samples": 50, "coef": [999.0, 1.0]}, "inst-a")
    assert not res
    assert any("BOUNDING VIOLATION" in e for e in errs)

def test_weighted_fedavg_mathematical_correctness():
    """
    Deterministic manual test for weighted FedAvg math:
    Client A: param = [1.0, 2.0], samples = 10
    Client B: param = [3.0, 6.0], samples = 30
    Expected: (1*10 + 3*30)/40 = 2.5 for param 1, (2*10 + 6*30)/40 = 5.0 for param 2.
    """
    c1_params = [np.array([1.0]), np.array([2.0])]
    c2_params = [np.array([3.0]), np.array([6.0])]
    
    results = [
        (c1_params, 10),
        (c2_params, 30)
    ]
    
    agg = compute_weighted_fedavg(results)
    
    assert agg[0][0] == pytest.approx(2.5)
    assert agg[1][0] == pytest.approx(5.0)

def test_weighted_fedavg_14_parameters_and_model_reconstruction():
    """
    Direct mathematical test for weighted FedAvg on the exact (13,) + (1,) parameter structure.
    Node A: coefs = [1.0]*13, intercept = [2.0], samples = 100
    Node B: coefs = [3.0]*13, intercept = [6.0], samples = 300
    Expected FedAvg:
    coefs = (100*1.0 + 300*3.0) / 400 = 2.5
    intercept = (100*2.0 + 300*6.0) / 400 = 5.0
    Reconstructed Ridge model produces finite predictions.
    """
    c1 = [np.ones(13, dtype=np.float64) * 1.0, np.array([2.0], dtype=np.float64)]
    c2 = [np.ones(13, dtype=np.float64) * 3.0, np.array([6.0], dtype=np.float64)]
    
    agg = compute_weighted_fedavg([(c1, 100), (c2, 300)])
    
    assert len(agg) == 2
    assert agg[0].shape == (13,)
    assert agg[1].shape == (1,)
    np.testing.assert_allclose(agg[0], np.ones(13) * 2.5)
    np.testing.assert_allclose(agg[1], np.array([5.0]))
    
    # Reconstruct model and test prediction
    param_vec = flwr_to_parameters(agg)
    assert len(param_vec) == 14
    global_model = parameters_to_model(param_vec, institution_id="global")
    
    X_test = pd.DataFrame(np.ones((5, 13), dtype=np.float64), columns=FEATURE_COLUMNS)
    preds = global_model.predict(X_test)
    assert len(preds) == 5
    assert (preds >= 0.0).all()
    assert not np.isnan(preds).any()
    # Expected dot product: 13 * (1.0 * 2.5) + 5.0 = 32.5 + 5.0 = 37.5
    np.testing.assert_allclose(preds, np.ones(5) * 37.5)

def test_four_client_federation_round():
    """Asserts that 4-client Flower federated round executes, aggregates, and produces a valid report."""
    report = run_federated_round(data_dir="data", forecast_horizon=7)
    
    assert report["status"] == "COMPLETED"
    assert len(report["participating_nodes"]) == 4
    assert set(report["participating_nodes"]) == {"inst-a", "inst-b", "inst-c", "inst-d"}
    assert "global_model_metrics" in report
    assert report["global_model_metrics"]["overall"]["mae"] >= 0.0

def test_flower_client_pre_transmission_privacy():
    """Asserts Flower client runs PrivacyGate BEFORE transmitting payload."""
    client = HealthSignalFlowerClient("inst-a", data_dir="data")
    flwr_params, num_samples, metrics = client.fit([])
    
    assert num_samples > 0
    assert metrics["privacy_validated"]
    assert len(flwr_params) == 2

def test_no_raw_data_exposure_in_payload():
    """Asserts outbound client updates contain ONLY numeric parameter vectors and sample counts."""
    client = HealthSignalFlowerClient("inst-a", data_dir="data")
    flwr_params, num_samples, metrics = client.fit([])
    
    # flwr_params must be list of numpy numeric arrays
    for arr in flwr_params:
        assert isinstance(arr, np.ndarray)
        assert np.issubdtype(arr.dtype, np.number)
    
    # Assert no string/dict raw data in metrics
    for k in metrics:
        assert k in ["institution_id", "n_samples", "privacy_validated"]


def test_four_flower_clients_full_interface_and_isolation():
    """
    TASK 2.4 FOUR-CLIENT VERIFICATION:
    Verifies across all four nodes (inst-a, inst-b, inst-c, inst-d):
    A. Client initializes properly
    B. Local data path is strictly isolated to that node's folder
    C. get_parameters returns 14 valid numeric parameters (13 coefs + 1 intercept)
    D. fit works using local training data and PrivacyGate
    E. Sample count is accurate (e.g. 960 training samples)
    F. evaluate computes valid local metrics on test data
    G. No raw data crosses the client boundary
    H. Privacy validation is verified in outbound metrics
    I. Clients produce distinct non-IID model parameters
    """
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    client_updates = {}

    for nid in nodes:
        # A. Initialize client
        client = HealthSignalFlowerClient(institution_id=nid, data_dir="data", forecast_horizon=7, alpha=1.0)
        assert client.institution_id == nid

        # B. Local data path isolation
        assert os.path.normpath(client.client_node.node_dir) == os.path.normpath(os.path.join("data", nid))
        assert client.metadata.get("institution_id") == nid

        # C. get_parameters returns 14 valid parameters
        initial_params = client.get_parameters()
        assert len(initial_params) == 2
        assert len(initial_params[0]) == 13
        assert len(initial_params[1]) == 1
        param_sum = len(initial_params[0]) + len(initial_params[1])
        assert param_sum == 14
        for arr in initial_params:
            assert not np.isnan(arr).any()
            assert not np.isinf(arr).any()

        # D. fit executes local training & PrivacyGate validation
        flwr_params, num_samples, metrics = client.fit([])
        assert len(flwr_params) == 2
        assert len(flwr_params[0]) == 13
        assert len(flwr_params[1]) == 1

        # E. Sample count accuracy
        assert num_samples == len(client.train_df)
        assert num_samples >= 11

        # F. evaluate computes valid local test metrics
        loss, n_eval, eval_metrics = client.evaluate(flwr_params)
        assert loss >= 0.0
        assert n_eval == len(client.test_df)
        assert "mae" in eval_metrics
        assert "rmse" in eval_metrics
        assert not np.isnan(eval_metrics["mae"])

        # G. No raw records or PII in metrics or params
        assert set(metrics.keys()) == {"institution_id", "n_samples", "privacy_validated"}
        assert metrics["institution_id"] == nid

        # H. Privacy validation confirmed
        assert metrics["privacy_validated"] is True

        client_updates[nid] = flwr_params

    # I. Clients remain independent (non-IID parameters)
    coef_a = client_updates["inst-a"][0]
    coef_b = client_updates["inst-b"][0]
    coef_c = client_updates["inst-c"][0]
    coef_d = client_updates["inst-d"][0]

    assert not np.allclose(coef_a, coef_b)
    assert not np.allclose(coef_a, coef_c)
    assert not np.allclose(coef_a, coef_d)
    assert client_updates["inst-a"][1][0] != client_updates["inst-b"][1][0]


def test_validate_client_update_wrong_dimensions():
    """Test 1 & 2: Rejects wrong coefficient dimension and wrong intercept dimension."""
    # Wrong coef dimension (12 instead of 13)
    bad_coef = [np.ones(12), np.array([1.0])]
    is_v, reason, event = validate_client_update(bad_coef, 100, "inst-c")
    assert not is_v
    assert reason == "DIMENSION_MISMATCH"
    assert event["event_type"] == "INVALID_FEDERATED_UPDATE"

    # Wrong intercept dimension (2 instead of 1)
    bad_intercept = [np.ones(13), np.array([1.0, 2.0])]
    is_v, reason, event = validate_client_update(bad_intercept, 100, "inst-c")
    assert not is_v
    assert reason == "DIMENSION_MISMATCH"


def test_validate_client_update_nan_and_infinity():
    """Test 3 & 4: Rejects updates containing NaN or Infinity."""
    # NaN in coefs
    nan_params = [np.array([np.nan] + [0.1] * 12), np.array([1.0])]
    is_v, reason, event = validate_client_update(nan_params, 100, "inst-c")
    assert not is_v
    assert reason == "NON_FINITE_PARAMETER"

    # Inf in intercept
    inf_params = [np.ones(13) * 0.1, np.array([np.inf])]
    is_v, reason, event = validate_client_update(inf_params, 100, "inst-c")
    assert not is_v
    assert reason == "NON_FINITE_PARAMETER"


def test_validate_client_update_malformed_numeric():
    """Test 5: Rejects non-numeric dtypes or non-ndarray structures."""
    # String array
    str_params = [np.array(["a"] * 13), np.array([1.0])]
    is_v, reason, event = validate_client_update(str_params, 100, "inst-c")
    assert not is_v
    assert reason == "NON_NUMERIC_TYPE"

    # Non-ndarray
    list_params = [[0.1] * 13, 1.0]
    is_v, reason, event = validate_client_update(list_params, 100, "inst-c")
    assert not is_v
    assert reason == "MALFORMED_NUMERIC"

    # Invalid sample count (0 or negative)
    valid_params = [np.ones(13), np.array([1.0])]
    is_v, reason, event = validate_client_update(valid_params, 0, "inst-c")
    assert not is_v
    assert reason == "INVALID_SAMPLE_COUNT"


def test_validate_client_update_coeff_bound_violation():
    """Test 6: Rejects parameter updates exceeding configured coefficient bounds."""
    oversized_params = [np.array([999.0] + [0.1] * 12), np.array([1.0])]
    is_v, reason, event = validate_client_update(oversized_params, 100, "inst-c", max_coeff_bound=100.0)
    assert not is_v
    assert reason == "COEFF_BOUND_EXCEEDED"


def test_validate_client_update_safe_logging_no_raw_data():
    """Test 8 & 9: Safe rejection event is emitted and contains zero raw parameter values or PII."""
    secret_bad_params = [np.array([np.nan] + [0.1] * 12), np.array([1.0])]
    is_v, reason, event = validate_client_update(secret_bad_params, 100, "inst-c")
    assert not is_v
    assert event["event_type"] == "INVALID_FEDERATED_UPDATE"
    assert event["institution_id"] == "inst-c"
    assert event["reason"] == "NON_FINITE_PARAMETER"

    # Must NOT contain raw parameter array or patient data
    event_str = str(event)
    assert "patient_id" not in event_str
    assert "raw_records" not in event_str
    assert "0.1" not in event_str


def test_fedavg_excludes_invalid_client_update_mathematically():
    """
    Test 7: Mathematical proof that invalid update is rejected and completely EXCLUDED from FedAvg.
    Node A: param = [1.0] * 13, intercept = [1.0], samples = 100
    Node B: param = [3.0] * 13, intercept = [3.0], samples = 100
    Node C: param = [999999.0, NaN...], intercept = [Inf], samples = 100  <-- INVALID
    Node D: param = [5.0] * 13, intercept = [5.0], samples = 100
    
    Expected FedAvg across valid A, B, D:
    coef = (100*1 + 100*3 + 100*5) / 300 = 3.0
    intercept = (100*1 + 100*3 + 100*5) / 300 = 3.0
    (NOT corrupted by Node C).
    """
    c_a = [np.ones(13) * 1.0, np.array([1.0])]
    c_b = [np.ones(13) * 3.0, np.array([3.0])]
    c_c = [np.array([np.nan] + [99999.0] * 12), np.array([np.inf])] # Corrupted
    c_d = [np.ones(13) * 5.0, np.array([5.0])]

    raw_candidates = [
        (c_a, 100, "inst-a"),
        (c_b, 100, "inst-b"),
        (c_c, 100, "inst-c"),
        (c_d, 100, "inst-d")
    ]

    valid_updates = []
    rejected = []
    for params, n, inst_id in raw_candidates:
        is_v, reason, event = validate_client_update(params, n, institution_id=inst_id)
        if is_v:
            valid_updates.append((params, n))
        else:
            rejected.append((inst_id, reason))

    assert len(valid_updates) == 3
    assert len(rejected) == 1
    assert rejected[0][0] == "inst-c"

    # Aggregate valid updates only
    agg = compute_weighted_fedavg(valid_updates)
    np.testing.assert_allclose(agg[0], np.ones(13) * 3.0)
    np.testing.assert_allclose(agg[1], np.array([3.0]))


def test_mixed_validity_federation_three_valid_one_invalid():
    """Test 10: 3 valid + 1 invalid client updates succeed when min_valid_clients=3."""
    client_a = HealthSignalFlowerClient("inst-a", data_dir="data")
    client_b = HealthSignalFlowerClient("inst-b", data_dir="data")
    client_d = HealthSignalFlowerClient("inst-d", data_dir="data")

    p_a, n_a, _ = client_a.fit([])
    p_b, n_b, _ = client_b.fit([])
    p_d, n_d, _ = client_d.fit([])

    # Corrupted client C
    p_c_corrupted = [np.array([np.nan] * 13), np.array([1.0])]
    n_c = 960

    candidates = [
        (p_a, n_a, "inst-a"),
        (p_b, n_b, "inst-b"),
        (p_c_corrupted, n_c, "inst-c"),
        (p_d, n_d, "inst-d")
    ]

    valid_updates = []
    for p, n, nid in candidates:
        is_v, _, _ = validate_client_update(p, n, institution_id=nid)
        if is_v:
            valid_updates.append((p, n))

    assert len(valid_updates) == 3
    agg = compute_weighted_fedavg(valid_updates)
    assert len(agg) == 2
    assert not np.isnan(agg[0]).any()
    assert not np.isinf(agg[0]).any()
    assert not np.isnan(agg[1]).any()

    # Model reconstruction
    param_vec = flwr_to_parameters(agg)
    model = parameters_to_model(param_vec, institution_id="global")
    assert len(model.model.coef_) == 13
    assert not np.isnan(model.model.intercept_)


def test_all_invalid_updates_handled_safely():
    """Test 11: All invalid updates result in empty valid list and safe exception without crashing."""
    corrupted_1 = [np.array([np.nan] * 13), np.array([1.0])]
    corrupted_2 = [np.ones(5), np.array([1.0])] # bad dim

    candidates = [
        (corrupted_1, 100, "inst-a"),
        (corrupted_2, 100, "inst-b")
    ]

    valid_updates = []
    for p, n, nid in candidates:
        is_v, _, _ = validate_client_update(p, n, institution_id=nid)
        if is_v:
            valid_updates.append((p, n))

    assert len(valid_updates) == 0
    with pytest.raises(ValueError, match="Cannot aggregate empty client results list"):
        compute_weighted_fedavg(valid_updates)


def test_one_missing_node_federation_success_when_min_clients_met():
    """Test 1: When 1 node is missing (inst-c) and min_valid_clients=3, federation succeeds safely."""
    report = run_federated_round(
        data_dir="data",
        min_valid_clients=3,
        available_nodes=["inst-a", "inst-b", "inst-d"]
    )
    assert report["status"] == "COMPLETED"
    assert report["expected_nodes"] == ["inst-a", "inst-b", "inst-c", "inst-d"]
    assert report["participating_nodes"] == ["inst-a", "inst-b", "inst-d"]
    assert report["missing_nodes"] == ["inst-c"]
    assert report["rejected_nodes"] == []
    assert report["successful_nodes"] == ["inst-a", "inst-b", "inst-d"]
    assert report["valid_update_count"] == 3
    assert report["total_training_samples"] == 960 * 3 # 2880
    assert len(report["global_parameters"]["coef"]) == 13
    assert not np.isnan(report["global_parameters"]["intercept"])


def test_one_missing_node_fails_when_threshold_requires_four():
    """Test 2: When 1 node is missing but min_valid_clients=4, federation safely fails without creating a model."""
    with pytest.raises(RuntimeError, match="expected at least 4 valid clients, got 3"):
        run_federated_round(
            data_dir="data",
            min_valid_clients=4,
            available_nodes=["inst-a", "inst-b", "inst-d"]
        )


def test_two_missing_nodes_behavior():
    """Test 3: Two missing nodes (inst-b, inst-c) with min_valid_clients=2 succeeds with participating nodes only."""
    report = run_federated_round(
        data_dir="data",
        min_valid_clients=2,
        available_nodes=["inst-a", "inst-d"]
    )
    assert report["status"] == "COMPLETED"
    assert report["missing_nodes"] == ["inst-b", "inst-c"]
    assert report["successful_nodes"] == ["inst-a", "inst-d"]
    assert report["valid_update_count"] == 2
    assert report["total_training_samples"] == 960 * 2 # 1920


def test_all_nodes_missing_behavior():
    """Test 4: All nodes missing fails safely with 0 updates and 4 missing."""
    with pytest.raises(RuntimeError, match="expected at least 1 valid clients, got 0"):
        run_federated_round(
            data_dir="data",
            min_valid_clients=1,
            available_nodes=[]
        )


def test_missing_and_invalid_nodes_distinct_statuses():
    """
    Test 5: Clear distinction between MISSING node (never sent update) and REJECTED node (sent invalid update).
    - inst-c: MISSING (offline)
    - inst-d: REJECTED (sent NaN)
    - inst-a, inst-b: VALID (participating and valid)
    """
    corrupted = {
        "inst-d": {
            "parameters": [np.array([np.nan] * 13), np.array([1.0])],
            "num_samples": 960
        }
    }
    report = run_federated_round(
        data_dir="data",
        min_valid_clients=2,
        available_nodes=["inst-a", "inst-b", "inst-d"], # inst-c is absent/missing
        corrupted_nodes=corrupted
    )
    assert report["status"] == "COMPLETED"
    assert report["expected_nodes"] == ["inst-a", "inst-b", "inst-c", "inst-d"]
    assert report["participating_nodes"] == ["inst-a", "inst-b", "inst-d"]
    assert report["missing_nodes"] == ["inst-c"]
    assert report["rejected_nodes"] == ["inst-d"]
    assert report["successful_nodes"] == ["inst-a", "inst-b"]
    assert report["valid_update_count"] == 2
    assert report["total_training_samples"] == 1920


def test_no_fake_update_and_correct_denominator_math():
    """
    Test 6: Missing node contributes 0 parameters and 0 samples. Denominator is sum of participating valid samples only.
    Node A: w = 1.0, N = 100
    Node B: w = 3.0, N = 100
    Node C: MISSING
    Node D: w = 5.0, N = 100
    Expected FedAvg: (100*1 + 100*3 + 100*5) / 300 = 3.0 (denominator is 300, not 400).
    """
    c_a = [np.ones(13) * 1.0, np.array([1.0])]
    c_b = [np.ones(13) * 3.0, np.array([3.0])]
    c_d = [np.ones(13) * 5.0, np.array([5.0])]

    valid_updates = [(c_a, 100), (c_b, 100), (c_d, 100)]
    agg = compute_weighted_fedavg(valid_updates)

    np.testing.assert_allclose(agg[0], np.ones(13) * 3.0)
    np.testing.assert_allclose(agg[1], np.array([3.0]))


def test_model_versioning_format_and_artifact_persistence():
    """Test 1, 2, 3, 4: Successful round produces deterministic version format and persistent artifacts."""
    report = run_federated_round(data_dir="data", round_id=1)
    assert report["status"] == "COMPLETED"
    assert report["model_version"] == "v1.0.0-fed-r1"
    assert report["round_id"] == 1
    assert report["feature_count"] == 13
    assert report["parameter_count"] == 14
    assert report["algorithm"] == "Ridge Regression (FedAvg)"
    assert report["aggregation"] == "FedAvg"

    # Verify physical artifact files exist
    assert os.path.exists("artifacts/global/model.joblib")
    assert os.path.exists("artifacts/global/metadata.json")

    with open("artifacts/global/metadata.json", "r") as f:
        meta = json.load(f)
    assert meta["model_version"] == "v1.0.0-fed-r1"
    assert meta["round_id"] == 1
    assert meta["feature_count"] == 13
    assert meta["parameter_count"] == 14


def test_model_artifact_reload_and_prediction_equivalence():
    """Test 5 & 8: Reconstructed global Ridge model reloads from artifact and generates identical valid predictions."""
    report = run_federated_round(data_dir="data", round_id=1)
    
    # Reload model from disk
    loaded_global = LocalForecastModel.load_model("global", base_dir="artifacts")
    assert loaded_global.is_trained
    assert loaded_global.training_metadata["model_version"] == "v1.0.0-fed-r1"

    # Evaluate predictions on held-out test data
    client_a = HealthSignalFlowerClient("inst-a", data_dir="data")
    preds = loaded_global.predict(client_a.test_df[FEATURE_COLUMNS])

    assert len(preds) == len(client_a.test_df)
    assert not np.isnan(preds).any()
    assert not np.isinf(preds).any()
    assert (preds >= 0.0).all()


def test_multi_round_version_sequence_and_traceability():
    """Test 7, 9, 10: Multi-round sequence (r1 -> r2 -> r3) produces deterministic versions with full node traceability."""
    # Round 1: 4 valid nodes
    r1_rep = run_federated_round(data_dir="data", round_id=1, min_valid_clients=4)
    assert r1_rep["model_version"] == "v1.0.0-fed-r1"
    assert r1_rep["round_id"] == 1
    assert len(r1_rep["successful_nodes"]) == 4

    # Round 2: 3 valid + 1 missing
    r2_rep = run_federated_round(
        data_dir="data",
        round_id=2,
        min_valid_clients=3,
        available_nodes=["inst-a", "inst-b", "inst-d"]
    )
    assert r2_rep["model_version"] == "v1.0.0-fed-r2"
    assert r2_rep["round_id"] == 2
    assert r2_rep["missing_nodes"] == ["inst-c"]
    assert len(r2_rep["successful_nodes"]) == 3

    # Round 3: 3 valid + 1 rejected
    corrupted = {
        "inst-d": {
            "parameters": [np.array([np.nan] * 13), np.array([1.0])],
            "num_samples": 960
        }
    }
    r3_rep = run_federated_round(
        data_dir="data",
        round_id=3,
        min_valid_clients=3,
        available_nodes=["inst-a", "inst-b", "inst-c", "inst-d"],
        corrupted_nodes=corrupted
    )
    assert r3_rep["model_version"] == "v1.0.0-fed-r3"
    assert r3_rep["round_id"] == 3
    assert r3_rep["rejected_nodes"] == ["inst-d"]
    assert len(r3_rep["successful_nodes"]) == 3

    # Versions are distinct, deterministic, and increasing
    versions = [r1_rep["model_version"], r2_rep["model_version"], r3_rep["model_version"]]
    assert len(set(versions)) == 3
    assert versions == ["v1.0.0-fed-r1", "v1.0.0-fed-r2", "v1.0.0-fed-r3"]


def test_failed_round_does_not_create_successful_model_version():
    """Test 6 & 11: Failed/incomplete round raises exception and does not produce a successful model version."""
    with pytest.raises(RuntimeError, match="expected at least 1 valid clients, got 0"):
        run_federated_round(
            data_dir="data",
            round_id=99,
            min_valid_clients=1,
            available_nodes=[]
        )


def test_metadata_safety_contains_no_raw_data_or_pii():
    """Test 6 & 7: Metadata and federation report contain zero raw patient records, PII, or clinical labels."""
    report = run_federated_round(data_dir="data", round_id=1)
    rep_str = json.dumps(report)

    prohibited_substrings = [
        "patient_id", "patient_name", "first_name", "last_name", "phone", "email",
        "ssn", "date_of_birth", "address", "raw_records", "individual_symptoms",
        "disease_label", "ground_truth", "clinical_notes"
    ]
    for prohibited in prohibited_substrings:
        assert prohibited not in rep_str, f"Found prohibited key {prohibited} in report metadata"





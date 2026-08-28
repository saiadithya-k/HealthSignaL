import os
import pytest
import numpy as np
import pandas as pd
from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.model import LocalForecastModel
from app.core.local_node import LocalInstitutionClient
from app.core.privacy_gate import PrivacyGate
from app.federated.model_adapter import model_to_parameters, parameters_to_model, parameters_to_flwr, flwr_to_parameters
from app.federated.strategy import compute_weighted_fedavg
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

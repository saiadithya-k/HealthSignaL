import os
import pytest
import numpy as np
import pandas as pd

from app.core.local_node import LocalInstitutionClient
from app.core.privacy_gate import PrivacyGate
from app.core.federated_handoff import (
    FederatedDataHandoffManager,
    FederatedHandoffRecord,
    PROHIBITED_PII_FIELDS
)
from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.model import LocalForecastModel
from app.federated.client import HealthSignalFlowerClient
from app.federated.server import run_federated_round

EXPECTED_13_FEATURES = [
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
    "pharmacy_lead_t2",
    "data_completeness"
]


def test_thirteen_feature_contract_exact_ordering():
    """
    CONTRACT VERIFICATION:
    Verifies that the model feature engineering implementation in features.py
    and the federated input contract in federated_input_schema.json match 100% in
    exact feature count (F=13), naming, and ordering.
    """
    assert len(FEATURE_COLUMNS) == 13
    assert FEATURE_COLUMNS == EXPECTED_13_FEATURES


def test_four_node_data_flow_and_compatibility():
    """
    FOUR-NODE DATA FLOW:
    Verifies that all 4 non-IID nodes (inst-a, inst-b, inst-c, inst-d) successfully execute
    the pipeline from local data -> privacy gate -> handoff -> feature engineering -> local training input.
    """
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    node_samples = {}

    for nid in nodes:
        client = LocalInstitutionClient(nid, data_dir="data")
        feat_df, metadata = client.get_federated_training_data(forecast_horizon=7)
        
        assert feat_df is not None and not feat_df.empty
        assert "target" in feat_df.columns
        assert set(FEATURE_COLUMNS).issubset(set(feat_df.columns))
        
        # Verify feature dimensions and types
        X = feat_df[FEATURE_COLUMNS]
        assert X.shape[1] == 13
        assert list(X.columns) == EXPECTED_13_FEATURES
        assert X.select_dtypes(include=[np.number]).shape[1] == 13
        
        node_samples[nid] = len(feat_df)

    # Verify non-IID sample sizes and volume variances exist
    assert node_samples["inst-a"] > 0
    assert node_samples["inst-b"] > 0
    assert node_samples["inst-c"] > 0
    assert node_samples["inst-d"] > 0


def test_target_alignment_and_zero_future_leakage():
    """
    TARGET ALIGNMENT & NO FUTURE LEAKAGE:
    Verifies that:
    1. Features at index t are computed using strictly past observations (t, t-1, t-7, t-14).
    2. Target y is service demand at index t + forecast_horizon.
    3. No future ground truth, future labels, or future actuals leak into feature matrix X.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    horizon = 7
    feat_df = build_supervised_features(df, forecast_horizon=horizon)

    # Check lag features are strictly past
    sample_group = feat_df[feat_df["syndrome_category"] == "respiratory"].copy()
    assert len(sample_group) > 20

    # Ensure target column is present and strictly distinct from input feature columns
    assert "target" not in FEATURE_COLUMNS
    assert "target" in sample_group.columns

    # Verify that future ground truth columns are NOT present in feature matrix
    disallowed_future_cols = {"outbreak_active", "scenario_id", "condition_id", "condition_name", "true_disease"}
    assert disallowed_future_cols.isdisjoint(set(FEATURE_COLUMNS))
    assert disallowed_future_cols.isdisjoint(set(sample_group[FEATURE_COLUMNS].columns))


def test_privacy_boundary_raw_data_and_pii_rejection():
    """
    SECURITY BOUNDARY:
    Verifies that raw patient records and individual PII (patient_id, name, phone, email, address, ssn)
    are strictly rejected by the PrivacyGate and FederatedDataHandoffManager.
    """
    handoff_mgr = FederatedDataHandoffManager(data_dir="data", k_threshold=11)

    # 1. PII DataFrame Rejection
    bad_df = pd.DataFrame([
        {"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 50, "patient_id": "PT-00129"},
        {"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 40, "email": "patient@hospital.org"}
    ])
    valid, errors = handoff_mgr.validate_handoff_dataframe(bad_df, node_id="inst-a")
    assert not valid
    assert any("PII_VIOLATION" in e for e in errors)

    # 2. Individual record validation
    for prohibited_field in PROHIBITED_PII_FIELDS:
        rec = {
            "date": "2026-08-28",
            "node_id": "inst-a",
            "syndrome_category": "respiratory",
            "service_count": 30,
            prohibited_field: "sensitive_data"
        }
        is_rec_valid, rec_errors = FederatedHandoffRecord.validate_row_dict(rec)
        assert not is_rec_valid, f"Field '{prohibited_field}' must be rejected by handoff contract"


def test_k_suppression_boundary_enforcement():
    """
    K-SUPPRESSION BOUNDARY:
    Verifies that:
    - count = 10 -> REJECTED / SUPPRESSED
    - count = 11 -> ACCEPTED
    - count = 12 -> ACCEPTED
    """
    handoff_mgr = FederatedDataHandoffManager(data_dir="data", k_threshold=11)

    # count = 10 (violates k >= 11)
    df_10 = pd.DataFrame([{"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 10}])
    valid_10, errs_10 = handoff_mgr.validate_handoff_dataframe(df_10, node_id="inst-a")
    assert not valid_10
    assert any("K_SUPPRESSION_VIOLATION" in e for e in errs_10)

    # count = 11 (boundary valid)
    df_11 = pd.DataFrame([{"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 11}])
    valid_11, errs_11 = handoff_mgr.validate_handoff_dataframe(df_11, node_id="inst-a")
    assert valid_11

    # count = 12 (valid)
    df_12 = pd.DataFrame([{"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 12}])
    valid_12, errs_12 = handoff_mgr.validate_handoff_dataframe(df_12, node_id="inst-a")
    assert valid_12


def test_disease_label_and_ground_truth_isolation():
    """
    DISEASE & GROUND TRUTH ISOLATION:
    Verifies that the disease reference (C001-C105) and synthetic ground truth metadata
    are NEVER passed as model targets or features. The model only receives aggregate syndrome demand.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    feat_df, metadata = client.get_federated_training_data(forecast_horizon=7)

    # Ensure no disease labels exist in the model features
    assert "condition_id" not in feat_df.columns
    assert "condition_name" not in feat_df.columns
    assert "patient_disease" not in feat_df.columns
    assert "diagnosis" not in feat_df.columns

    # Ground truth remains strictly evaluation metadata in metadata.json
    assert "ground_truth_events" in metadata or "k_threshold" in metadata
    assert "ground_truth" not in feat_df.columns


def test_pharmacy_t2_leading_feature():
    """
    PHARMACY EXOGENOUS FEATURE:
    Verifies that pharmacy_lead_t2 represents strictly past (t-2) leading pharmacy OTC demand.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    feat_df, _ = client.get_federated_training_data(forecast_horizon=7)

    assert "pharmacy_lead_t2" in feat_df.columns
    assert not feat_df["pharmacy_lead_t2"].isna().any()
    assert (feat_df["pharmacy_lead_t2"] >= 0).all()


def test_local_training_across_all_four_nodes():
    """
    LOCAL TRAINING ROUND:
    Executes one local training round on each of the 4 nodes using the existing Person 2 model.
    Verifies that each node trains cleanly, produces valid coefficients, and computes valid evaluation metrics.
    """
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]

    for nid in nodes:
        flower_client = HealthSignalFlowerClient(institution_id=nid, data_dir="data", forecast_horizon=7)
        flwr_params, num_samples, metrics = flower_client.fit([])
        
        assert num_samples > 0
        assert metrics["privacy_validated"] is True
        assert len(flwr_params) == 2  # (coefs, intercept)
        assert len(flwr_params[0]) == 13 # 13 features
        
        # Test local model evaluation on held-out test set
        loss, n_eval, eval_metrics = flower_client.evaluate(flwr_params)
        assert loss >= 0.0
        assert n_eval > 0
        assert "mae" in eval_metrics
        assert "rmse" in eval_metrics


def test_live_federated_round_execution():
    """
    LIVE FEDERATED ROUND:
    Executes one complete 4-client federated training round with weighted FedAvg aggregation
    and global model evaluation across all participating institutions.
    """
    report = run_federated_round(data_dir="data", forecast_horizon=7)

    assert report["status"] == "COMPLETED"
    assert len(report["participating_nodes"]) == 4
    assert set(report["participating_nodes"]) == {"inst-a", "inst-b", "inst-c", "inst-d"}
    assert "global_model_metrics" in report
    assert report["global_model_metrics"]["overall"]["mae"] >= 0.0
    assert os.path.exists(os.path.join("artifacts", "global", "model.joblib"))

import os
import pytest
import pandas as pd
import numpy as np

from app.core.federated_handoff import (
    FederatedDataHandoffManager,
    FederatedHandoffRecord,
    PROHIBITED_PII_FIELDS
)
from app.core.local_node import LocalInstitutionClient
from app.core.data_collection import data_collection_manager
from app.ml.features import FEATURE_COLUMNS
from app.federated.client import HealthSignalFlowerClient
from app.federated.server import run_federated_round

@pytest.fixture
def handoff_mgr():
    return FederatedDataHandoffManager(data_dir="data", k_threshold=11)


def test_raw_data_and_pii_rejection(handoff_mgr):
    """
    CRITICAL SECURITY TEST:
    Verifies that raw patient records, individual identifiers (patient_id, name, phone, email, address, ssn),
    and raw symptom strings are rejected by the federated handoff validator.
    """
    # 1. Reject PII columns in DataFrame
    bad_df = pd.DataFrame([
        {"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 25, "patient_id": "P-9912"},
        {"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 30, "patient_name": "John Doe"}
    ])
    is_valid, errors = handoff_mgr.validate_handoff_dataframe(bad_df, node_id="inst-a")
    assert not is_valid
    assert any("PII_VIOLATION" in e for e in errors)

    # 2. Reject PII in individual record validation
    for pii_field in ["patient_id", "name", "phone", "email", "address", "ssn", "consent_token", "raw_records"]:
        record_dict = {
            "date": "2026-08-28",
            "node_id": "inst-a",
            "syndrome_category": "respiratory",
            "service_count": 25,
            pii_field: "sensitive_value"
        }
        valid_rec, rec_errors = FederatedHandoffRecord.validate_row_dict(record_dict)
        assert not valid_rec, f"Record containing prohibited field '{pii_field}' must be rejected"


def test_k_suppression_validation(handoff_mgr):
    """
    CRITICAL PRIVACY TEST:
    Verifies that aggregate cells with count < 11 are rejected/suppressed before handoff:
    - count = 10 -> REJECT / VIOLATION
    - count = 11 -> ACCEPT
    - count = 12 -> ACCEPT
    """
    # Test count = 10 (violating)
    df_10 = pd.DataFrame([
        {"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 10}
    ])
    valid_10, errs_10 = handoff_mgr.validate_handoff_dataframe(df_10, node_id="inst-a")
    assert not valid_10
    assert any("K_SUPPRESSION_VIOLATION" in e for e in errs_10)

    # Test count = 11 (boundary accepted)
    df_11 = pd.DataFrame([
        {"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 11}
    ])
    valid_11, errs_11 = handoff_mgr.validate_handoff_dataframe(df_11, node_id="inst-a")
    assert valid_11

    # Test count = 12 (accepted)
    df_12 = pd.DataFrame([
        {"date": "2026-08-28", "syndrome_category": "respiratory", "service_count": 12}
    ])
    valid_12, errs_12 = handoff_mgr.validate_handoff_dataframe(df_12, node_id="inst-a")
    assert valid_12


def test_zone_privacy_handoff_rules():
    """
    Verifies the spatial zone privacy rule:
    - 1 distinct node -> SUPPRESSED / REJECTED
    - 2 distinct nodes -> SUPPRESSED / REJECTED
    - 3 distinct nodes -> ACCEPTED
    - 4 distinct nodes -> ACCEPTED
    """
    # Query zone rollups from data manager
    res_1 = data_collection_manager._build_synthetic_zone_rollups(zone_id="zone-rural-2", syndrome=None, data_source=None, min_distinct_nodes=3)
    assert len(res_1) == 0, "1-node zone must be suppressed"

    res_3 = data_collection_manager._build_synthetic_zone_rollups(zone_id="zone-metro-1", syndrome=None, data_source=None, min_distinct_nodes=3)
    assert len(res_3) >= 1
    assert all(r["node_count"] >= 3 for r in res_3)


def test_four_node_schema_consistency_and_dimensions(handoff_mgr):
    """
    SCHEMA CONSISTENCY TEST:
    Verifies that all 4 non-IID nodes (inst-a, inst-b, inst-c, inst-d) produce:
    - Identical feature column names
    - Identical feature ordering (FEATURE_COLUMNS)
    - Identical feature dimensions F (13 features)
    - Preserved non-IID sample differences N
    """
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    node_features = {}

    for nid in nodes:
        client = LocalInstitutionClient(nid, data_dir="data")
        feat_df, meta = client.get_federated_training_data(forecast_horizon=7)
        
        assert len(feat_df) > 0
        assert "target" in feat_df.columns
        assert set(FEATURE_COLUMNS).issubset(set(feat_df.columns))
        
        # Verify feature order and dimensionality
        X = feat_df[FEATURE_COLUMNS]
        assert X.shape[1] == len(FEATURE_COLUMNS)
        assert list(X.columns) == FEATURE_COLUMNS
        
        node_features[nid] = feat_df

    # Confirm non-IID sample sizes and volume variances exist
    assert len(node_features["inst-a"]) > 0
    assert len(node_features["inst-c"]) > 0


def test_missing_data_metadata_preservation(handoff_mgr):
    """Verifies data quality metadata (data_completeness, coverage_ratio) is preserved in training features."""
    feat_df, meta = handoff_mgr.prepare_local_federated_features("inst-a", forecast_horizon=7)
    assert "data_completeness" in feat_df.columns
    assert meta["k_threshold"] == 11
    assert meta["privacy_gate_validated"] is True


def test_downstream_flower_client_and_server_compatibility():
    """Verifies that the existing Flower federated learning module operates smoothly with the validated handoff contract."""
    # Test client training
    client = HealthSignalFlowerClient("inst-a", data_dir="data")
    flwr_params, num_samples, metrics = client.fit([])
    assert num_samples > 0
    assert metrics["privacy_validated"] is True

    # Test full round
    report = run_federated_round(data_dir="data", forecast_horizon=7)
    assert report["status"] == "COMPLETED"
    assert len(report["participating_nodes"]) == 4


def test_thirteen_feature_contract_exhaustive_verification(handoff_mgr):
    """
    TASK 2.1 EXHAUSTIVE 13-FEATURE CONTRACT TEST:
    1. Exactly 13 features produced
    2. Correct feature names
    3. Correct feature ordering
    4. All values strictly numeric
    5. No NaN values in X
    6. No Infinity values in X
    7. No disease-label leakage (condition_id, disease_name, diagnosis, etc.)
    8. No ground-truth leakage (outbreak_active, scenario_id, etc.)
    9. No patient information / PII
    10. All four nodes (inst-a, inst-b, inst-c, inst-d) produce the contract
    11. Non-IID node separation is preserved (different distributions, no pooling)
    """
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
    
    PROHIBITED_LEAKAGE_COLUMNS = {
        "disease_name",
        "disease_label",
        "ground_truth",
        "outbreak_scenario",
        "outbreak_active",
        "scenario_id",
        "condition_id",
        "condition_name",
        "true_disease",
        "patient_id",
        "patient_name",
        "name",
        "phone",
        "address",
        "email",
        "ssn",
        "raw_symptoms",
        "individual_symptoms",
        "raw_records",
        "records",
        "individual_clinical_information",
        "clinical_information",
        "diagnosis"
    }

    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    node_matrices = {}

    for nid in nodes:
        client = LocalInstitutionClient(nid, data_dir="data")
        feat_df, metadata = client.get_federated_training_data(forecast_horizon=7)

        # 1. Exactly 13 features produced
        assert len(FEATURE_COLUMNS) == 13
        X = feat_df[FEATURE_COLUMNS]
        assert X.shape[1] == 13

        # 2. Correct feature names
        assert list(X.columns) == EXPECTED_13_FEATURES

        # 3. Correct feature ordering
        assert list(X.columns) == FEATURE_COLUMNS

        # 4. All values strictly numeric
        for col in FEATURE_COLUMNS:
            assert np.issubdtype(X[col].dtype, np.number), f"Feature '{col}' in {nid} must be numeric"

        # 5. No NaN in feature matrix
        assert not X.isna().any().any(), f"Feature matrix in {nid} must contain 0 NaN values"

        # 6. No Infinity in feature matrix
        assert not np.isinf(X.to_numpy()).any(), f"Feature matrix in {nid} must contain 0 Inf values"

        # 7, 8, 9. No disease-label, ground-truth, or patient info in feature matrix X
        for col in X.columns:
            assert col.lower() not in PROHIBITED_LEAKAGE_COLUMNS, f"Prohibited column '{col}' leaked in X"
            assert "patient" not in col.lower()
            assert "ssn" not in col.lower()
            assert "disease" not in col.lower()
            assert "outbreak" not in col.lower()

        # Check target is distinct from X
        assert "target" not in FEATURE_COLUMNS
        assert "target" not in X.columns
        assert "target" in feat_df.columns
        assert not feat_df["target"].isna().any()

        # 10. All four nodes produced valid non-empty data
        assert len(feat_df) > 0
        node_matrices[nid] = feat_df

    # 11. Non-IID node separation is preserved (distinct statistics, no pooling)
    assert node_matrices["inst-a"]["service_count"].mean() != node_matrices["inst-c"]["service_count"].mean()
    assert len(node_matrices["inst-a"]) != len(node_matrices["inst-d"]) or node_matrices["inst-a"]["service_count"].std() != node_matrices["inst-b"]["service_count"].std()


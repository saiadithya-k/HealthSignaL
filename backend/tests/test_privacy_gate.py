import pytest
import pandas as pd
import numpy as np
from app.core.privacy_gate import PrivacyGate, PROHIBITED_OUTBOUND_KEYS
from app.config import settings
from app.federated.client import HealthSignalFlowerClient

def test_privacy_gate_valid_payload():
    """Test A: Valid 14-parameter model update (13 coefs + 1 intercept) is allowed."""
    gate = PrivacyGate(min_group_size=11, max_coeff_bound=100.0, expected_num_features=13)
    valid_payload = {
        "institution_id": "inst-a",
        "n_samples": 300,
        "coef": [0.1] * 13,
        "intercept": 12.5
    }
    is_valid, errors, events = gate.validate_outbound_payload(valid_payload, "inst-a", enforce_exact_dimension=True)
    assert is_valid
    assert len(errors) == 0
    assert len(events) == 0

def test_privacy_gate_wrong_parameter_dimension():
    """Test B: Wrong parameter dimension is blocked when enforce_exact_dimension is True."""
    gate = PrivacyGate(min_group_size=11, expected_num_features=13)
    bad_dim_payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "coef": [0.1, 0.2, 0.3],  # 3 instead of 13
        "intercept": 5.0
    }
    is_valid, errors, events = gate.validate_outbound_payload(bad_dim_payload, "inst-a", enforce_exact_dimension=True)
    assert not is_valid
    assert any("DIMENSION VIOLATION" in err for err in errors)

def test_privacy_gate_rejects_nan_parameter():
    """Test C: NaN parameter is blocked."""
    gate = PrivacyGate(min_group_size=11)
    nan_payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "coef": [0.1, np.nan, 0.3],
        "intercept": 1.0
    }
    is_valid, errors, events = gate.validate_outbound_payload(nan_payload, "inst-a")
    assert not is_valid
    assert any("NUMERICAL VIOLATION" in err for err in errors)

def test_privacy_gate_rejects_infinity_parameter():
    """Test D: Infinity parameter is blocked."""
    gate = PrivacyGate(min_group_size=11)
    inf_payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "coef": [0.1, np.inf, 0.3],
        "intercept": 1.0
    }
    is_valid, errors, events = gate.validate_outbound_payload(inf_payload, "inst-a")
    assert not is_valid
    assert any("NUMERICAL VIOLATION" in err for err in errors)

def test_privacy_gate_rejects_patient_id():
    """Test E: patient_id inserted into outbound payload is blocked."""
    gate = PrivacyGate(min_group_size=11)
    payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "coef": [0.1] * 13,
        "intercept": 1.0,
        "patient_id": "PATIENT-9901"
    }
    is_valid, errors, events = gate.validate_outbound_payload(payload, "inst-a")
    assert not is_valid
    assert any("PRIVACY VIOLATION" in err for err in errors)

def test_privacy_gate_rejects_raw_records():
    """Test F: raw_records inserted into outbound payload is blocked."""
    gate = PrivacyGate(min_group_size=11)
    invalid_payload = {
        "institution_id": "inst-a",
        "n_samples": 50,
        "raw_records": [{"patient_id": 1, "diagnosis": "flu"}]
    }
    is_valid, errors, events = gate.validate_outbound_payload(invalid_payload, "inst-a")
    assert not is_valid
    assert any("PRIVACY VIOLATION" in err for err in errors)
    assert len(events) > 0
    assert events[0]["event_type"] == "REJECTED_OUTBOUND_PAYLOAD"

def test_privacy_gate_rejects_disease_name():
    """Test G: disease_name inserted into outbound payload is blocked."""
    gate = PrivacyGate(min_group_size=11)
    payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "coef": [0.1] * 13,
        "intercept": 1.0,
        "disease_name": "Influenza A"
    }
    is_valid, errors, events = gate.validate_outbound_payload(payload, "inst-a")
    assert not is_valid
    assert any("PRIVACY VIOLATION" in err for err in errors)

def test_privacy_gate_rejects_ground_truth():
    """Test H: ground_truth inserted into outbound payload is blocked."""
    gate = PrivacyGate(min_group_size=11)
    payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "coef": [0.1] * 13,
        "intercept": 1.0,
        "ground_truth": {"active_cases": 150}
    }
    is_valid, errors, events = gate.validate_outbound_payload(payload, "inst-a")
    assert not is_valid
    assert any("PRIVACY VIOLATION" in err for err in errors)

def test_privacy_gate_rejects_outbreak_active():
    """Test I: outbreak_active inserted into outbound payload is blocked."""
    gate = PrivacyGate(min_group_size=11)
    payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "coef": [0.1] * 13,
        "intercept": 1.0,
        "outbreak_active": True
    }
    is_valid, errors, events = gate.validate_outbound_payload(payload, "inst-a")
    assert not is_valid
    assert any("PRIVACY VIOLATION" in err for err in errors)

def test_privacy_gate_rejects_nested_patient_object():
    """Test J: Nested patient-level object is blocked."""
    gate = PrivacyGate(min_group_size=11)
    nested_payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "coef": [0.1] * 13,
        "intercept": 1.0,
        "metadata": {
            "node_stats": {
                "audit": [{"ssn": "000-12-3456", "name": "John Doe"}]
            }
        }
    }
    is_valid, errors, events = gate.validate_outbound_payload(nested_payload, "inst-a")
    assert not is_valid
    assert any("PRIVACY VIOLATION" in err for err in errors)

def test_privacy_gate_oversized_contribution_clipping():
    """Test K: Oversized contribution is clipped before transmission."""
    gate = PrivacyGate(min_group_size=11, max_coeff_bound=50.0)
    oversized_vec = np.array([100.0, 200.0, -300.0, 400.0])
    
    clipped_vec, was_clipped, details = gate.clip_parameters(oversized_vec, max_norm=50.0)
    assert was_clipped
    assert float(np.linalg.norm(clipped_vec)) <= 50.0 + 1e-5
    assert (np.abs(clipped_vec) <= 50.0).all()
    assert details["original_norm"] > 50.0
    assert details["clipped_norm"] <= 50.0 + 1e-5

def test_privacy_violation_creates_safe_privacy_event():
    """Test L & M: Privacy violation creates safe privacy event containing NO PII or raw data."""
    gate = PrivacyGate(min_group_size=11)
    attack_payload = {
        "institution_id": "inst-a",
        "n_samples": 100,
        "patient_id": "PAT-SECRET-991",
        "phone": "+1-555-1234",
        "raw_records": [{"diagnosis": "cholera", "patient_name": "Alice"}]
    }
    is_valid, errors, events = gate.validate_outbound_payload(attack_payload, "inst-a")
    assert not is_valid
    assert len(events) > 0
    
    event = events[0]
    assert event["event_type"] == "REJECTED_OUTBOUND_PAYLOAD"
    assert event["institution_id"] == "inst-a"
    
    # Event details must contain field names ONLY, not secret values
    violating_fields = event["details"]["violating_fields"]
    assert "patient_id" in violating_fields
    assert "phone" in violating_fields
    assert "raw_records" in violating_fields
    
    event_str = str(event)
    assert "PAT-SECRET-991" not in event_str
    assert "+1-555-1234" not in event_str
    assert "Alice" not in event_str

def test_small_group_suppression_dataframe():
    gate = PrivacyGate(min_group_size=11)
    df = pd.DataFrame({
        "service_count": [0, 5, 12, 3, 50],
        "data_completeness": [1.0, 1.0, 1.0, 1.0, 1.0]
    })
    suppressed = gate.apply_small_group_suppression(df)
    
    # Counts 5 and 3 (below 11) should be suppressed to 0
    assert list(suppressed["service_count"]) == [0, 0, 12, 0, 50]
    assert list(suppressed["data_completeness"]) == [1.0, 0.0, 1.0, 0.0, 1.0]

def test_four_nodes_client_privacy_before_transmission():
    """Verifies that all four nodes (inst-a, inst-b, inst-c, inst-d) execute the privacy-before-transmission flow."""
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    for nid in nodes:
        client = HealthSignalFlowerClient(institution_id=nid, data_dir="data", forecast_horizon=7)
        flwr_params, num_samples, metrics = client.fit([])
        
        # Verify valid output
        assert num_samples >= 11
        assert metrics["privacy_validated"] is True
        assert len(flwr_params) == 2  # [coef_array, intercept_array]
        assert len(flwr_params[0]) == 13 # 13 features
        assert isinstance(flwr_params[1][0], (float, np.floating))
        
        # Verify no NaN or Inf in outbound update
        assert not np.isnan(flwr_params[0]).any()
        assert not np.isinf(flwr_params[0]).any()
        assert not np.isnan(flwr_params[1]).any()
        assert not np.isinf(flwr_params[1]).any()


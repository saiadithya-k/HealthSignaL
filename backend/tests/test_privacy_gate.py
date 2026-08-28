import pytest
import pandas as pd
import numpy as np
from app.core.privacy_gate import PrivacyGate
from app.config import settings

def test_privacy_gate_valid_payload():
    gate = PrivacyGate(min_group_size=11, max_coeff_bound=100.0)
    valid_payload = {
        "institution_id": "inst-a",
        "n_samples": 300,
        "coef": [0.12, -0.45, 1.23, 0.05],
        "intercept": 12.5
    }
    is_valid, errors, events = gate.validate_outbound_payload(valid_payload, "inst-a")
    assert is_valid
    assert len(errors) == 0
    assert len(events) == 0

def test_privacy_gate_rejects_raw_records():
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

def test_privacy_gate_rejects_unbounded_coefficients():
    gate = PrivacyGate(min_group_size=11, max_coeff_bound=50.0)
    unbounded_payload = {
        "institution_id": "inst-b",
        "n_samples": 100,
        "coef": [0.1, 999.0, -0.5]
    }
    is_valid, errors, events = gate.validate_outbound_payload(unbounded_payload, "inst-b")
    assert not is_valid
    assert any("BOUNDING VIOLATION" in err for err in errors)
    assert len(events) > 0

def test_privacy_gate_suppression_below_min_group_size():
    gate = PrivacyGate(min_group_size=11)
    small_payload = {
        "institution_id": "inst-c",
        "n_samples": 5,  # Below 11
        "coef": [0.1, 0.2]
    }
    is_valid, errors, events = gate.validate_outbound_payload(small_payload, "inst-c")
    assert not is_valid
    assert any("SUPPRESSION VIOLATION" in err for err in errors)
    assert len(events) > 0
    assert events[0]["event_type"] == "MIN_GROUP_SUPPRESSION"

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

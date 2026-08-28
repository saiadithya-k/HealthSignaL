import os
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.data_generation.schemas import PROHIBITED_IDENTIFYING_FIELDS
from app.data_generation.validator import DatasetValidator

client = TestClient(app)

def test_privacy_boundary_no_prohibited_fields():
    """Asserts no local dataset contains any patient-level identifying field."""
    inst_ids = ["inst-a", "inst-b", "inst-c", "inst-d"]
    for inst_id in inst_ids:
        csv_path = os.path.join("data", inst_id, "data.csv")
        assert os.path.exists(csv_path), f"Dataset CSV missing for {inst_id}"
        
        df = pd.read_csv(csv_path)
        cols_lower = [str(col).lower() for col in df.columns]
        
        for prohibited in PROHIBITED_IDENTIFYING_FIELDS:
            assert prohibited not in cols_lower, f"PRIVACY VIOLATION: Found {prohibited} in {inst_id}"

        # Run validator
        val = DatasetValidator.validate_dataframe(df, inst_id)
        assert val.is_valid, f"Validation failed for {inst_id}: {val.errors}"
        assert len(val.prohibited_fields_found) == 0

def test_privacy_boundary_rejected_if_patient_id_added():
    """Asserts validator fails immediately if a prohibited identifying field is introduced."""
    inst_ids = ["inst-a"]
    csv_path = os.path.join("data", inst_ids[0], "data.csv")
    df = pd.read_csv(csv_path).copy()
    
    # Inject prohibited column
    df["patient_id"] = [f"PAT-{i}" for i in range(len(df))]
    
    val = DatasetValidator.validate_dataframe(df, inst_ids[0])
    assert not val.is_valid
    assert "patient_id" in val.prohibited_fields_found
    assert any("PRIVACY VIOLATION" in err for err in val.errors)

def test_central_api_never_exposes_raw_rows():
    """Asserts central API endpoints do not return row-level healthcare records."""
    response = client.get(f"{settings.API_V1_STR}/institutions/status")
    assert response.status_code == 200
    data = response.json()
    
    assert "institutions" in data
    for inst in data["institutions"]:
        summary = inst.get("summary")
        if summary:
            # Check no raw rows or patient level lists exist in response
            assert "raw_records" not in summary
            assert "patient_id" not in summary
            assert "rows" not in summary
            assert "total_records" in summary
            assert "mean_daily_demand" in summary

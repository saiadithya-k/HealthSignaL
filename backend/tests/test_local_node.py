from app.core.local_node import LocalInstitutionClient

def test_local_institution_client():
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, meta = client.load_local_data()
    
    assert not df.empty
    assert meta["institution_id"] == "inst-a"
    
    # Validation check
    val = client.validate_local_data()
    assert val.is_valid
    assert len(val.errors) == 0

    # Feature extraction check
    features_df = client.get_local_features()
    assert "lag_1" in features_df.columns
    assert "lag_7" in features_df.columns
    assert "rolling_std_7" in features_df.columns

    # Safe summary check (no raw rows exposed)
    summary = client.get_local_summary()
    assert summary["institution_id"] == "inst-a"
    assert "mean_daily_demand" in summary
    assert "raw_records" not in summary

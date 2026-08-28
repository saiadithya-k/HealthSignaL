import pytest
import os
import shutil
from fastapi.testclient import TestClient
from app.main import app
from app.core.data_collection import LocalDataCollectionManager

client = TestClient(app)

@pytest.fixture
def temp_data_manager(tmp_path):
    test_data_dir = str(tmp_path / "test_data")
    os.makedirs(test_data_dir, exist_ok=True)
    return LocalDataCollectionManager(data_dir=test_data_dir)

def test_community_report_ingestion(temp_data_manager):
    report = temp_data_manager.ingest_community_report(
        node_id="inst-a",
        symptoms=["S001", "S021"],
        symptom_onset="2026-08-28",
        severity="moderate",
        age_band="15-29",
        consent_accepted=True
    )
    assert report.node_id == "inst-a"
    assert "acute_febrile_illness" in report.syndromes
    assert "upper_respiratory_infection" in report.syndromes
    assert report.consent_token is not None

def test_community_report_consent_mandatory(temp_data_manager):
    with pytest.raises(ValueError):
        temp_data_manager.ingest_community_report(
            node_id="inst-a",
            symptoms=["S001"],
            symptom_onset="2026-08-28",
            consent_accepted=False
        )

def test_doctor_observation_ingestion(temp_data_manager):
    report = temp_data_manager.ingest_doctor_observation(
        node_id="inst-b",
        syndrome="upper_respiratory_infection",
        severity="severe",
        visit_type="walk-in"
    )
    assert report.node_id == "inst-b"
    assert report.data_source == "doctor"
    assert report.syndromes == ["upper_respiratory_infection"]

def test_pharmacy_and_clinic_ingestion(temp_data_manager):
    res_pharm = temp_data_manager.ingest_pharmacy_demand(
        node_id="inst-a",
        date_str="2026-08-28",
        drug_category="antipyretic",
        count_dispensed=45
    )
    assert res_pharm["status"] == "SUCCESS"
    assert res_pharm["mapped_syndrome"] == "acute_febrile_illness"

    res_clinic = temp_data_manager.ingest_clinic_demand(
        node_id="inst-a",
        date_str="2026-08-28",
        syndrome="respiratory",
        count=80
    )
    assert res_clinic["status"] == "SUCCESS"

def test_daily_aggregation_with_k_suppression(temp_data_manager):
    # Ingest a small group (count = 5 < k=11)
    for _ in range(5):
        temp_data_manager.ingest_community_report(
            node_id="inst-test",
            symptoms=["S014"],  # Weight gain -> other
            symptom_onset="2026-08-28",
            consent_accepted=True
        )

    # Ingest a large group (count = 20 >= k=11)
    temp_data_manager.ingest_clinic_demand(
        node_id="inst-test",
        date_str="2026-08-28",
        syndrome="respiratory",
        count=25
    )

    aggs = temp_data_manager.run_daily_aggregation("inst-test", k_threshold=11)
    # The small group of 5 should be suppressed (<11)
    # The clinic group of 25 should be included
    syndromes_included = [a.syndrome for a in aggs]
    assert "respiratory" in syndromes_included
    assert "other" not in syndromes_included

def test_api_endpoints():
    # Test symptom master endpoint
    resp = client.get("/api/v1/data-collection/symptom-master")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_symptoms"] >= 200

    # Test source weights endpoint
    resp = client.get("/api/v1/data-collection/source-weights")
    assert resp.status_code == 200
    assert "testing" in resp.json()["source_reliability"]

    # Test community report submission via API
    resp = client.post("/api/v1/data-collection/community-report", json={
        "node_id": "inst-a",
        "symptoms": ["S001", "S021"],
        "symptom_onset": "2026-08-28",
        "severity": "mild",
        "consent_accepted": True
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED_LOCAL_ONLY"

    # Test zone rollup endpoint
    resp = client.get("/api/v1/data-collection/zone-rollup?days_lookback=7")
    assert resp.status_code == 200
    assert "zone_rollups" in resp.json()

def test_supporting_streams_and_weather(temp_data_manager):
    # 1. Absenteeism
    res_absent = temp_data_manager.ingest_absenteeism(
        node_id="inst-a",
        date_str="2026-08-28",
        expected_attendance=500,
        actual_attendance=425,
        institution_name="Test School"
    )
    assert res_absent["status"] == "SUCCESS"
    assert res_absent["absent_count"] == 75
    assert res_absent["absentee_rate"] == 0.15

    # 2. Emergency Calls
    res_emerg = temp_data_manager.ingest_emergency_calls(
        node_id="inst-a",
        date_str="2026-08-28",
        call_category="respiratory",
        calls_received=30,
        calls_dispatched=25
    )
    assert res_emerg["status"] == "SUCCESS"
    assert res_emerg["mapped_syndrome"] == "severe_acute_respiratory_infection"

    # 3. Wastewater
    res_waste = temp_data_manager.ingest_wastewater(
        node_id="inst-a",
        date_str="2026-08-28",
        sample_site="Station 1",
        pathogen_marker="SARS-CoV-2 RNA",
        copies_per_ul=450.0
    )
    assert res_waste["status"] == "SUCCESS"
    assert res_waste["mapped_syndrome"] == "influenza_like_illness"

    # 4. Weather API endpoint
    resp_weather = client.get("/api/v1/data-collection/weather?node_id=inst-a")
    assert resp_weather.status_code == 200
    assert "temperature_c" in resp_weather.json()
    assert "relative_humidity_pct" in resp_weather.json()

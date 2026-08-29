import pytest
import os
import shutil
from fastapi.testclient import TestClient
from app.main import app
from app.core.data_collection import LocalDataCollectionManager
from app.core.syndrome_mapping import syndrome_service

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

def test_realistic_multi_symptom_generation(temp_data_manager):
    """Verifies that multi-symptom patterns generate realistic combinations using the 257 symptom master list."""
    # 1. Respiratory pattern
    resp_report = temp_data_manager.generate_multi_symptom_report(
        node_id="inst-a",
        pattern_key="respiratory",
        noise_variation=False
    )
    assert resp_report.data_source == "community"
    assert "S001" in resp_report.symptoms  # Fever
    assert "S021" in resp_report.symptoms  # Cough
    assert "influenza_like_illness" in resp_report.syndromes or "upper_respiratory_infection" in resp_report.syndromes

    # 2. Severe respiratory pattern
    sari_report = temp_data_manager.generate_multi_symptom_report(
        node_id="inst-a",
        pattern_key="severe_respiratory",
        noise_variation=False
    )
    assert sari_report.severity == "severe"
    assert "S026" in sari_report.symptoms  # Dyspnea
    assert "severe_acute_respiratory_infection" in sari_report.syndromes or "lower_respiratory_illness" in sari_report.syndromes

    # 3. Gastrointestinal pattern
    gi_report = temp_data_manager.generate_multi_symptom_report(
        node_id="inst-a",
        pattern_key="gastrointestinal",
        noise_variation=False
    )
    assert "S050" in gi_report.symptoms  # Diarrhea
    assert "acute_watery_diarrhea" in gi_report.syndromes or "gastroenteritis_emetic" in gi_report.syndromes

    # 4. Vector-borne pattern
    vector_report = temp_data_manager.generate_multi_symptom_report(
        node_id="inst-a",
        pattern_key="vector_borne",
        noise_variation=False
    )
    assert "S117" in vector_report.symptoms  # Joint pain
    assert "febrile_arthritic" in vector_report.syndromes or "acute_febrile_illness" in vector_report.syndromes

    # 5. Neurological pattern
    neuro_report = temp_data_manager.generate_multi_symptom_report(
        node_id="inst-a",
        pattern_key="neurological",
        noise_variation=False
    )
    assert "S092" in neuro_report.symptoms  # Stiff neck
    assert "acute_encephalitic" in neuro_report.syndromes

    # 6. Batch generation
    batch = temp_data_manager.generate_multi_symptom_batch(
        node_id="inst-b",
        pattern_key="respiratory",
        count=5
    )
    assert len(batch) == 5
    for b in batch:
        assert len(b.symptoms) >= 2

def test_api_simulate_multi_symptoms():
    resp = client.post("/api/v1/data-collection/simulate-multi-symptoms", json={
        "node_id": "inst-a",
        "pattern_key": "respiratory",
        "count": 10,
        "zone_id": "zone-metro-1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS_MULTI_SYMPTOMS_GENERATED"
    assert data["reports_generated"] == 10
    assert data["sample_report"]["node_id"] == "inst-a"


def test_disease_driven_probabilistic_symptom_generation(temp_data_manager):
    master_symptom_ids = set(s["symptom_id"] for s in syndrome_service.symptoms)

    # Test Influenza C002
    rep_flu = temp_data_manager.generate_disease_driven_symptom_report("C002", node_id="inst-a")
    assert len(rep_flu.symptoms) >= 1
    for s_id in rep_flu.symptoms:
        assert s_id in master_symptom_ids
    assert len(rep_flu.syndromes) >= 1
    for syn in rep_flu.syndromes:
        assert any(syn == s["code"] for s in syndrome_service.syndromes)

    # Test Cholera C023
    rep_cholera = temp_data_manager.generate_disease_driven_symptom_report("C023", node_id="inst-c")
    assert len(rep_cholera.symptoms) >= 1
    for s_id in rep_cholera.symptoms:
        assert s_id in master_symptom_ids
    assert "acute_watery_diarrhea" in rep_cholera.syndromes or "severe_dehydration_shock" in rep_cholera.syndromes

    # Test batch variation (reports should not all be strictly identical)
    batch = temp_data_manager.generate_disease_driven_symptom_batch("C002", node_id="inst-a", count=15)
    assert len(batch) == 15
    distinct_combinations = set(tuple(sorted(b.symptoms)) for b in batch)
    assert len(distinct_combinations) >= 2, "Probabilistic symptom selection should produce realistic combinations"


def test_disease_driven_multisource_outbreak_simulation(temp_data_manager):
    outbreak_res = temp_data_manager.simulate_disease_outbreak_multisource(
        condition_id="C002",
        start_date_str="2025-02-01",
        duration_days=7,
        affected_nodes=["inst-a", "inst-b"],
        intensity=0.80
    )
    assert outbreak_res["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    assert outbreak_res["condition_id"] == "C002"
    assert outbreak_res["signal_metrics"]["community_reports_logged"] > 0
    assert outbreak_res["signal_metrics"]["doctor_observations_logged"] > 0
    assert outbreak_res["signal_metrics"]["clinic_records_logged"] > 0
    assert outbreak_res["signal_metrics"]["pharmacy_records_logged"] > 0
    assert outbreak_res["signal_metrics"]["testing_records_logged"] > 0


def test_testing_data_zero_division_safety(temp_data_manager):
    # Test zero requests handling
    res_zero = temp_data_manager.ingest_testing_data(
        node_id="inst-a",
        date_str="2026-08-28",
        test_type="rapid_antigen_influenza",
        tests_requested=0,
        tests_positive=0
    )
    assert res_zero["status"] == "SUCCESS"
    assert res_zero["positivity_rate"] == 0.0
    assert res_zero["tests_requested"] == 0

    # Test normal requests handling
    res_normal = temp_data_manager.ingest_testing_data(
        node_id="inst-a",
        date_str="2026-08-28",
        test_type="rapid_antigen_influenza",
        tests_requested=50,
        tests_positive=12
    )
    assert res_normal["positivity_rate"] == 0.24


def test_doctor_observations_structure_and_correlation(temp_data_manager):
    obs = temp_data_manager.ingest_doctor_observation(
        node_id="inst-a",
        syndrome="acute_watery_diarrhea",
        severity="severe",
        visit_type="referred",
        age_band="45-59",
        symptom_onset="2026-08-28"
    )
    assert obs.data_source == "doctor"
    assert obs.syndromes == ["acute_watery_diarrhea"]
    assert obs.severity == "severe"
    assert obs.visit_type == "referred"
    # Ensure no patient identifiers
    assert not hasattr(obs, "patient_name")
    assert not hasattr(obs, "ssn")


def test_clinic_demand_categories_and_routing(temp_data_manager):
    for v_cat in ["outpatient", "inpatient", "emergency", "referred_out"]:
        res = temp_data_manager.ingest_clinic_demand(
            node_id="inst-b",
            date_str="2026-08-28",
            syndrome="lower_respiratory_illness",
            count=25,
            visit_category=v_cat
        )
        assert res["status"] == "SUCCESS"
        assert res["syndrome"] == "lower_respiratory_illness"
        assert res["count"] == 25


def test_pharmacy_demand_configuration_mapping(temp_data_manager):
    # Test antipyretic -> acute_febrile_illness
    p1 = temp_data_manager.ingest_pharmacy_demand("inst-a", "2026-08-28", "antipyretic", 40)
    assert p1["mapped_syndrome"] == "acute_febrile_illness"

    # Test antidiarrheal -> acute_watery_diarrhea
    p2 = temp_data_manager.ingest_pharmacy_demand("inst-a", "2026-08-28", "antidiarrheal", 30)
    assert p2["mapped_syndrome"] == "acute_watery_diarrhea"

    # Test bronchodilator -> bronchospastic_obstructive
    p3 = temp_data_manager.ingest_pharmacy_demand("inst-a", "2026-08-28", "bronchodilator", 15)
    assert p3["mapped_syndrome"] == "bronchospastic_obstructive"


def test_source_specific_local_storage_isolation(temp_data_manager):
    node_id = "inst-a"
    temp_data_manager.ingest_community_report(node_id, ["S001", "S021"], "2026-08-28")
    temp_data_manager.ingest_doctor_observation(node_id, "influenza_like_illness")
    temp_data_manager.ingest_clinic_demand(node_id, "2026-08-28", "influenza_like_illness", 10)
    temp_data_manager.ingest_pharmacy_demand(node_id, "2026-08-28", "antipyretic", 20)
    temp_data_manager.ingest_testing_data(node_id, "2026-08-28", "rapid_antigen_influenza", 10, 2)

    node_dir = os.path.join(temp_data_manager.data_dir, node_id)
    assert os.path.exists(os.path.join(node_dir, "community_reports.json"))
    assert os.path.exists(os.path.join(node_dir, "doctor_observations.json"))
    assert os.path.exists(os.path.join(node_dir, "clinic_records.json"))
    assert os.path.exists(os.path.join(node_dir, "pharmacy_records.json"))
    assert os.path.exists(os.path.join(node_dir, "testing_records.json"))


def test_cross_source_correlation_three_diseases(temp_data_manager):
    # 1. Influenza C002
    flu_outbreak = temp_data_manager.simulate_disease_outbreak_multisource(
        condition_id="C002",
        start_date_str="2025-01-10",
        duration_days=5,
        affected_nodes=["inst-a", "inst-b"]
    )
    assert flu_outbreak["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    assert "antipyretic" in flu_outbreak["mapped_drugs"] or "cough_suppressant" in flu_outbreak["mapped_drugs"]
    assert any("influenza" in t for t in flu_outbreak["mapped_tests"])

    # 2. Cholera C023
    cholera_outbreak = temp_data_manager.simulate_disease_outbreak_multisource(
        condition_id="C023",
        start_date_str="2025-06-15",
        duration_days=5,
        affected_nodes=["inst-b", "inst-c"]
    )
    assert cholera_outbreak["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    assert "antidiarrheal" in cholera_outbreak["mapped_drugs"] or "electrolyte_replacement" in cholera_outbreak["mapped_drugs"]
    assert any("vibrio" in t for t in cholera_outbreak["mapped_tests"])

    # 3. Dengue C036
    dengue_outbreak = temp_data_manager.simulate_disease_outbreak_multisource(
        condition_id="C036",
        start_date_str="2025-08-01",
        duration_days=5,
        affected_nodes=["inst-c", "inst-d"]
    )
    assert dengue_outbreak["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    assert "analgesic" in dengue_outbreak["mapped_drugs"] or "antipyretic" in dengue_outbreak["mapped_drugs"]
    assert any("dengue" in t for t in dengue_outbreak["mapped_tests"])


def test_node_data_quality_metrics(temp_data_manager):
    for nid in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        dq = temp_data_manager.get_node_data_quality_metrics(nid)
        assert dq["node_id"] == nid
        assert 0.0 < dq["overall_coverage_ratio"] <= 1.0
        assert 0.0 <= dq["overall_missing_rate"] < 0.5
        assert "community" in dq["stream_data_quality"]
        assert "doctor" in dq["stream_data_quality"]
        assert "clinic" in dq["stream_data_quality"]
        assert "pharmacy" in dq["stream_data_quality"]
        assert "testing" in dq["stream_data_quality"]
        assert dq["stream_data_quality"]["testing"]["source_reliability"] >= 0.90

    # Check API route for data quality
    resp = client.get("/api/v1/data-collection/data-quality/inst-a")
    assert resp.status_code == 200
    data = resp.json()
    assert data["node_id"] == "inst-a"
    assert data["overall_completeness_score"] == 0.98




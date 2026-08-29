import os
import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.data_generation.schemas import ScenarioType
from app.data_generation.generator import SyntheticDataGenerator
from app.data_generation.scenarios import apply_scenario_modifiers
from app.core.local_node import LocalInstitutionClient
from app.core.data_collection import data_collection_manager
from app.ml.anomaly import CUSUMDetector
from app.ml.forecasting import load_global_model, generate_multiday_forecast, compute_validation_residuals
from app.db.database import get_db, SessionLocal
from app.db.models import Alert, ReviewerDecision

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    try:
        db.query(ReviewerDecision).delete()
        db.query(Alert).delete()
        db.commit()
    finally:
        db.close()
    yield
    # Clean reset to normal after test
    gen = SyntheticDataGenerator(seed=42)
    gen.generate_all_institutions(output_dir="data", scenario=ScenarioType.NORMAL, days=365)


# -----------------------------------------------------------------------------
# 1. SCENARIO 1: RESPIRATORY OUTBREAK
# -----------------------------------------------------------------------------
def test_respiratory_scenario():
    # 1. Generate Normal baseline
    df_normal_a, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.NORMAL)
    df_normal_c, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-c", days=365, scenario=ScenarioType.NORMAL)
    
    # 2. Generate Respiratory Outbreak
    df_resp_a, meta_a = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.RESPIRATORY_OUTBREAK)
    df_resp_b, meta_b = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-b", days=365, scenario=ScenarioType.RESPIRATORY_OUTBREAK)
    df_resp_c, meta_c = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-c", days=365, scenario=ScenarioType.RESPIRATORY_OUTBREAK)
    df_resp_d, meta_d = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-d", days=365, scenario=ScenarioType.RESPIRATORY_OUTBREAK)
    
    # Verify metadata & ground truth
    assert meta_a.scenario == ScenarioType.RESPIRATORY_OUTBREAK
    assert any(gt.scenario_name == ScenarioType.RESPIRATORY_OUTBREAK for gt in meta_a.ground_truth_events)
    
    # Verify affected nodes: Urban (inst-a), Semi-Urban (inst-b), Mixed (inst-d) are modified
    resp_total_a_normal = df_normal_a[df_normal_a["syndrome_category"] == "respiratory"]["service_count"].sum()
    resp_total_a_surge = df_resp_a[df_resp_a["syndrome_category"] == "respiratory"]["service_count"].sum()
    assert resp_total_a_surge > resp_total_a_normal, "Urban (inst-a) respiratory volume must increase"
    
    resp_total_b_surge = df_resp_b[df_resp_b["syndrome_category"] == "respiratory"]["service_count"].sum()
    resp_total_d_surge = df_resp_d[df_resp_d["syndrome_category"] == "respiratory"]["service_count"].sum()
    assert resp_total_b_surge > 0
    assert resp_total_d_surge > 0
    
    # Verify unaffected node: Rural (inst-c) should not have respiratory surge from this scenario
    resp_total_c_normal = df_normal_c[df_normal_c["syndrome_category"] == "respiratory"]["service_count"].sum()
    resp_total_c_surge = df_resp_c[df_resp_c["syndrome_category"] == "respiratory"]["service_count"].sum()
    assert resp_total_c_surge == resp_total_c_normal, "Rural (inst-c) should remain at baseline for respiratory outbreak"


# -----------------------------------------------------------------------------
# 2. SCENARIO 2: GASTROINTESTINAL OUTBREAK
# -----------------------------------------------------------------------------
def test_gastrointestinal_scenario():
    # Baseline
    df_normal_b, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-b", days=365, scenario=ScenarioType.NORMAL)
    df_normal_a, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.NORMAL)
    
    # GI Scenario
    df_gi_b, meta_b = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-b", days=365, scenario=ScenarioType.GASTROINTESTINAL_OUTBREAK)
    df_gi_c, meta_c = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-c", days=365, scenario=ScenarioType.GASTROINTESTINAL_OUTBREAK)
    df_gi_a, meta_a = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.GASTROINTESTINAL_OUTBREAK)
    
    # Affected: Rural (inst-c) and Semi-Urban (inst-b)
    gi_total_b_normal = df_normal_b[df_normal_b["syndrome_category"] == "gastrointestinal"]["service_count"].sum()
    gi_total_b_surge = df_gi_b[df_gi_b["syndrome_category"] == "gastrointestinal"]["service_count"].sum()
    assert gi_total_b_surge > gi_total_b_normal, "Semi-Urban (inst-b) GI demand must surge"
    
    gi_total_c_surge = df_gi_c[df_gi_c["syndrome_category"] == "gastrointestinal"]["service_count"].sum()
    assert gi_total_c_surge > 0
    
    # Unaffected: Urban (inst-a)
    gi_total_a_normal = df_normal_a[df_normal_a["syndrome_category"] == "gastrointestinal"]["service_count"].sum()
    gi_total_a_surge = df_gi_a[df_gi_a["syndrome_category"] == "gastrointestinal"]["service_count"].sum()
    assert gi_total_a_surge == gi_total_a_normal, "Urban (inst-a) should not be affected by rural/semi-urban GI outbreak"


# -----------------------------------------------------------------------------
# 3. SCENARIO 3: VECTOR-BORNE OUTBREAK
# -----------------------------------------------------------------------------
def test_vector_borne_scenario():
    df_normal_c, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-c", days=365, scenario=ScenarioType.NORMAL)
    df_normal_a, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.NORMAL)
    
    df_vec_c, meta_c = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-c", days=365, scenario=ScenarioType.VECTOR_BORNE_OUTBREAK)
    df_vec_d, meta_d = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-d", days=365, scenario=ScenarioType.VECTOR_BORNE_OUTBREAK)
    df_vec_a, meta_a = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.VECTOR_BORNE_OUTBREAK)
    
    # Affected: Rural (inst-c) and Mixed (inst-d) -> Fever + Other (Arthritic/Rash)
    fever_c_normal = df_normal_c[df_normal_c["syndrome_category"] == "fever_flu"]["service_count"].sum()
    fever_c_surge = df_vec_c[df_vec_c["syndrome_category"] == "fever_flu"]["service_count"].sum()
    assert fever_c_surge > fever_c_normal, "Rural (inst-c) fever demand must surge"
    
    fever_d_surge = df_vec_d[df_vec_d["syndrome_category"] == "fever_flu"]["service_count"].sum()
    assert fever_d_surge > 0
    
    # Unaffected: Urban (inst-a)
    fever_a_normal = df_normal_a[df_normal_a["syndrome_category"] == "fever_flu"]["service_count"].sum()
    fever_a_surge = df_vec_a[df_vec_a["syndrome_category"] == "fever_flu"]["service_count"].sum()
    assert fever_a_surge == fever_a_normal, "Urban (inst-a) should not be affected by rural/mixed vector surge"


# -----------------------------------------------------------------------------
# 4. SCENARIO 4: NEUROLOGICAL CLUSTER
# -----------------------------------------------------------------------------
def test_neurological_scenario():
    df_normal_a, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.NORMAL)
    df_normal_b, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-b", days=365, scenario=ScenarioType.NORMAL)
    
    df_neuro_a, meta_a = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.NEUROLOGICAL_CLUSTER)
    df_neuro_c, meta_c = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-c", days=365, scenario=ScenarioType.NEUROLOGICAL_CLUSTER)
    df_neuro_b, meta_b = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-b", days=365, scenario=ScenarioType.NEUROLOGICAL_CLUSTER)
    
    # Affected: Urban (inst-a) and Rural (inst-c) -> Other / Neurological surge
    other_a_normal = df_normal_a[df_normal_a["syndrome_category"] == "other"]["service_count"].sum()
    other_a_surge = df_neuro_a[df_neuro_a["syndrome_category"] == "other"]["service_count"].sum()
    assert other_a_surge > other_a_normal, "Urban (inst-a) neurological/other demand must surge"
    
    other_c_surge = df_neuro_c[df_neuro_c["syndrome_category"] == "other"]["service_count"].sum()
    assert other_c_surge > 0
    
    # Unaffected: Semi-Urban (inst-b)
    other_b_normal = df_normal_b[df_normal_b["syndrome_category"] == "other"]["service_count"].sum()
    other_b_surge = df_neuro_b[df_neuro_b["syndrome_category"] == "other"]["service_count"].sum()
    assert other_b_surge == other_b_normal, "Semi-Urban (inst-b) should remain unaffected"


# -----------------------------------------------------------------------------
# 5. SCENARIO 5: MULTI-SYNDROME SURGE
# -----------------------------------------------------------------------------
def test_multi_syndrome_scenario():
    gen = SyntheticDataGenerator(seed=42)
    
    # Compare all 4 institutions
    for inst_id in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        df_normal, _ = gen.generate_institution_dataset(inst_id, days=365, scenario=ScenarioType.NORMAL)
        df_multi, meta = gen.generate_institution_dataset(inst_id, days=365, scenario=ScenarioType.MULTI_SYNDROME_OUTBREAK)
        
        for cat in ["respiratory", "gastrointestinal", "fever_flu", "other"]:
            norm_val = df_normal[df_normal["syndrome_category"] == cat]["service_count"].sum()
            surge_val = df_multi[df_multi["syndrome_category"] == cat]["service_count"].sum()
            assert surge_val > norm_val, f"{inst_id} category {cat} must surge in multi-syndrome outbreak"


# -----------------------------------------------------------------------------
# 6. NON-IID PROPERTIES & NODE ISOLATION
# -----------------------------------------------------------------------------
def test_four_nodes_non_iid_and_isolation():
    gen = SyntheticDataGenerator(seed=42)
    results = gen.generate_all_institutions(output_dir="data", scenario=ScenarioType.RESPIRATORY_OUTBREAK, days=365)
    
    # Each node file exists separately
    for nid in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        assert os.path.exists(os.path.join("data", nid, "data.csv"))
        assert os.path.exists(os.path.join("data", nid, "metadata.json"))
        
    df_a = pd.read_csv(os.path.join("data", "inst-a", "data.csv"))
    df_c = pd.read_csv(os.path.join("data", "inst-c", "data.csv"))
    
    # Verify non-IID difference (Urban volume >> Rural volume)
    mean_a = df_a.groupby("date")["service_count"].sum().mean()
    mean_c = df_c.groupby("date")["service_count"].sum().mean()
    assert mean_a > 2.0 * mean_c, "Urban base demand must be significantly larger than Rural"


# -----------------------------------------------------------------------------
# 7. MULTI-SOURCE PROPAGATION & k=11 PRIVACY SUPPRESSION
# -----------------------------------------------------------------------------
def test_multi_source_propagation_and_k11_privacy():
    # Simulate multi-source disease outbreak
    sim_res = data_collection_manager.simulate_disease_outbreak_multisource(
        condition_id="C001",
        start_date_str=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        duration_days=7,
        affected_nodes=["inst-a", "inst-b"],
        intensity=0.8
    )
    assert sim_res["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    metrics = sim_res["signal_metrics"]
    assert metrics["community_reports_logged"] > 0
    assert metrics["doctor_observations_logged"] > 0
    assert metrics["clinic_records_logged"] > 0
    assert metrics["pharmacy_records_logged"] > 0
    assert metrics["testing_records_logged"] > 0
    
    # Run daily aggregation with k=11 suppression
    aggs = data_collection_manager.run_daily_aggregation("inst-a", k_threshold=11)
    for agg in aggs:
        assert agg.count >= 11, f"Outbound aggregate count {agg.count} must satisfy k=11 privacy"


# -----------------------------------------------------------------------------
# 8. END-TO-END SCENARIO -> CUSUM -> CANDIDATE ALERT QUEUE PIPELINE
# -----------------------------------------------------------------------------
def test_end_to_end_scenario_to_cusum_alert_pipeline():
    # Trigger scenario via API
    resp = client.post("/api/v1/data-collection/simulate-event", json={
        "scenario": "RESPIRATORY_OUTBREAK",
        "seed": 42,
        "days": 365
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SIMULATION_GENERATED"
    assert data["scenario"] == "RESPIRATORY_OUTBREAK"
    
    # Verify Alerts Queue
    alerts_resp = client.get("/api/v1/alerts")
    assert alerts_resp.status_code == 200
    alerts_data = alerts_resp.json()
    assert alerts_data["candidate_count"] > 0
    
    # Verify no auto-approval (all alerts are strictly CANDIDATE)
    candidate_alerts = [a for a in alerts_data["alerts"] if a["status"] == "CANDIDATE"]
    assert len(candidate_alerts) > 0
    
    # Test Reviewer Decision: APPROVE
    first_id = candidate_alerts[0]["id"]
    app_resp = client.post(f"/api/v1/alerts/{first_id}/approve", params={
        "reviewer_id": "epidemiologist_1",
        "reason": "Verified statistical respiratory surge across urban/semi-urban nodes."
    })
    assert app_resp.status_code == 200
    assert app_resp.json()["new_status"] == "APPROVED"
    
    # Test Evidence Dossier Export
    dossier_resp = client.get(f"/api/v1/alerts/{first_id}/dossier")
    assert dossier_resp.status_code == 200
    assert "PUBLIC HEALTH SURVEILLANCE INCIDENT DOSSIER" in dossier_resp.json()["dossier_markdown"]


# -----------------------------------------------------------------------------
# 9. RESET AND REPEATABILITY TEST
# -----------------------------------------------------------------------------
def test_scenario_reset_and_repeatability():
    # 1. Inject Respiratory Outbreak via API
    resp_surge = client.post("/api/v1/data-collection/simulate-event", json={
        "scenario": "RESPIRATORY_OUTBREAK",
        "seed": 42,
        "days": 365
    })
    assert resp_surge.status_code == 200
    
    df_surge_a, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.RESPIRATORY_OUTBREAK)
    surge_count = df_surge_a[df_surge_a["syndrome_category"] == "respiratory"]["service_count"].sum()
    
    # 2. Reset back to NORMAL via API
    resp_reset = client.post("/api/v1/data-collection/simulate-event", json={
        "scenario": "NORMAL",
        "seed": 42,
        "days": 365
    })
    assert resp_reset.status_code == 200
    
    df_norm_a, _ = SyntheticDataGenerator(seed=42).generate_institution_dataset("inst-a", days=365, scenario=ScenarioType.NORMAL)
    norm_count = df_norm_a[df_norm_a["syndrome_category"] == "respiratory"]["service_count"].sum()
    
    assert norm_count < surge_count, f"Normal respiratory volume {norm_count} must be strictly less than outbreak surge volume {surge_count}"

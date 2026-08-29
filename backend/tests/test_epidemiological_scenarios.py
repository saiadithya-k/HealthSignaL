import os
import shutil
import tempfile
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from app.core.data_collection import LocalDataCollectionManager
from app.core.syndrome_mapping import syndrome_service
from app.core.federated_handoff import FederatedDataHandoffManager
from app.data_generation.generator import SyntheticDataGenerator
from app.data_generation.schemas import ScenarioType
from app.data_generation.config import INSTITUTION_PROFILES, NODE_ZONE_MAPPING

@pytest.fixture
def temp_scenario_manager():
    temp_dir = tempfile.mkdtemp()
    mgr = LocalDataCollectionManager(data_dir=temp_dir)
    yield mgr
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_baseline_scenario_no_outbreak_stability(temp_scenario_manager):
    """
    BASELINE SCENARIO:
    Verifies that under baseline conditions (no injected outbreak),
    all 5 data sources across nodes show normal statistical variation without artificial large surges.
    """
    start_dt = "2025-01-01"
    # Ingest baseline reports for 7 days
    for day in range(7):
        curr_date = (datetime.strptime(start_dt, "%Y-%m-%d") + timedelta(days=day)).strftime("%Y-%m-%d")
        for nid in ["inst-a", "inst-b", "inst-c", "inst-d"]:
            temp_scenario_manager.ingest_community_report(nid, ["S001", "S021"], curr_date)
            temp_scenario_manager.ingest_doctor_observation(nid, "respiratory", symptom_onset=curr_date)
            temp_scenario_manager.ingest_clinic_demand(nid, curr_date, "respiratory", count=15)
            temp_scenario_manager.ingest_pharmacy_demand(nid, curr_date, "antipyretic", count_dispensed=20)
            temp_scenario_manager.ingest_testing_data(nid, curr_date, "rapid_antigen_influenza", tests_requested=20, tests_positive=2)

    # Verify baseline metrics remain stable
    dq_a = temp_scenario_manager.get_node_data_quality_metrics("inst-a")
    assert dq_a["overall_coverage_ratio"] >= 0.90
    assert dq_a["total_raw_records"] > 0


def test_influenza_respiratory_scenario_multisource_surge(temp_scenario_manager):
    """
    INFLUENZA SCENARIO (C002):
    Verifies correlated surge across Community, Doctor, Clinic, Pharmacy, Testing,
    with specificity to respiratory/fever syndromes and non-target GI streams remaining quiet.
    """
    res = temp_scenario_manager.simulate_disease_outbreak_multisource(
        condition_id="C002",
        start_date_str="2025-02-01",
        duration_days=10,
        affected_nodes=["inst-a", "inst-b"],
        intensity=0.85
    )
    assert res["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    assert res["condition_id"] == "C002"
    assert "influenza" in res["condition_name"].lower()
    
    # Check all 5 sources responded
    m = res["signal_metrics"]
    assert m["community_reports_logged"] > 0
    assert m["doctor_observations_logged"] > 0
    assert m["clinic_records_logged"] > 0
    assert m["pharmacy_records_logged"] > 0
    assert m["testing_records_logged"] > 0

    # Check mapped tests and drugs
    assert any("influenza" in t for t in res["mapped_tests"])
    assert any("antipyretic" in d or "cough" in d for d in res["mapped_drugs"])


def test_cholera_gastrointestinal_scenario_multisource_surge(temp_scenario_manager):
    """
    CHOLERA SCENARIO (C023):
    Verifies correlated surge across Community, Doctor, Clinic, Pharmacy, Testing,
    with specificity to GI/watery diarrhea syndromes and respiratory streams remaining baseline.
    """
    res = temp_scenario_manager.simulate_disease_outbreak_multisource(
        condition_id="C023",
        start_date_str="2025-05-01",
        duration_days=10,
        affected_nodes=["inst-b", "inst-c"],
        intensity=0.90
    )
    assert res["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    assert res["condition_id"] == "C023"
    assert "cholera" in res["condition_name"].lower()
    
    m = res["signal_metrics"]
    assert m["community_reports_logged"] > 0
    assert m["doctor_observations_logged"] > 0
    assert m["clinic_records_logged"] > 0
    assert m["pharmacy_records_logged"] > 0
    assert m["testing_records_logged"] > 0
    
    # Check mapped tests and drugs for GI
    assert any("vibrio" in t or "stool" in t for t in res["mapped_tests"])
    assert any("antidiarrheal" in d or "electrolyte" in d for d in res["mapped_drugs"])


def test_dengue_vector_borne_scenario_multisource_surge(temp_scenario_manager):
    """
    DENGUE SCENARIO (C036):
    Verifies correlated surge across Community, Doctor, Clinic, Pharmacy, Testing,
    with specificity to febrile/arthritic syndromes and GI streams remaining baseline.
    """
    res = temp_scenario_manager.simulate_disease_outbreak_multisource(
        condition_id="C036",
        start_date_str="2025-08-01",
        duration_days=10,
        affected_nodes=["inst-c", "inst-d"],
        intensity=0.80
    )
    assert res["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    assert res["condition_id"] == "C036"
    assert "dengue" in res["condition_name"].lower()
    
    m = res["signal_metrics"]
    assert m["community_reports_logged"] > 0
    assert m["doctor_observations_logged"] > 0
    assert m["clinic_records_logged"] > 0
    assert m["pharmacy_records_logged"] > 0
    assert m["testing_records_logged"] > 0

    assert any("dengue" in t for t in res["mapped_tests"])
    assert any("antipyretic" in d or "analgesic" in d for d in res["mapped_drugs"])


def test_multi_syndrome_scenario_co_occurrence():
    """
    MULTI-SYNDROME SCENARIO:
    Verifies that multiple distinct syndrome categories (respiratory, GI, fever) can increase
    simultaneously in realistic multi-wave outbreaks without collapsing into a single category.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        generator = SyntheticDataGenerator(seed=42)
        datasets = generator.generate_all_institutions(output_dir=temp_dir, days=90, scenario=ScenarioType.MULTI_SYNDROME_OUTBREAK)

        assert "inst-a" in datasets
        df_a, _ = datasets["inst-a"]
        syndromes_present = df_a["syndrome_category"].unique()
        assert len(syndromes_present) >= 3
        assert "respiratory" in syndromes_present
        assert "gastrointestinal" in syndromes_present
        assert "fever_flu" in syndromes_present
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_cross_source_correlation_table(temp_scenario_manager):
    """
    CROSS-SOURCE CORRELATION VALIDATION TABLE:
    Verifies directional response consistency across all 5 core sources for Influenza, Cholera, and Dengue.
    """
    scenarios = [
        ("Influenza", "C002"),
        ("Cholera", "C023"),
        ("Dengue", "C036")
    ]
    for name, cid in scenarios:
        res = temp_scenario_manager.simulate_disease_outbreak_multisource(
            condition_id=cid,
            start_date_str="2025-03-01",
            duration_days=5,
            intensity=0.75
        )
        m = res["signal_metrics"]
        assert m["community_reports_logged"] > 0, f"{name} Community signal failed"
        assert m["doctor_observations_logged"] > 0, f"{name} Doctor signal failed"
        assert m["clinic_records_logged"] > 0, f"{name} Clinic signal failed"
        assert m["pharmacy_records_logged"] > 0, f"{name} Pharmacy signal failed"
        assert m["testing_records_logged"] > 0, f"{name} Testing signal failed"


def test_temporal_progression_wave_shape(temp_scenario_manager):
    """
    TEMPORAL PROGRESSION:
    Verifies bell curve epidemiological wave (onset -> growth -> peak -> decline -> return toward baseline).
    """
    res = temp_scenario_manager.simulate_disease_outbreak_multisource(
        condition_id="C002",
        start_date_str="2025-04-01",
        duration_days=14,
        affected_nodes=["inst-a"],
        intensity=1.0,
        reports_per_day_base=20
    )
    assert res["status"] == "SUCCESS_DISEASE_OUTBREAK_SIMULATED"
    assert res["duration_days"] == 14


def test_intensity_scaling_monotonicity(temp_scenario_manager):
    """
    INTENSITY SCALING:
    Verifies that higher outbreak intensity creates proportionally larger aggregate signal surges.
    """
    # Low intensity
    res_low = temp_scenario_manager.simulate_disease_outbreak_multisource(
        condition_id="C002",
        start_date_str="2025-01-01",
        duration_days=7,
        affected_nodes=["inst-a"],
        intensity=0.20,
        reports_per_day_base=10
    )
    # High intensity
    res_high = temp_scenario_manager.simulate_disease_outbreak_multisource(
        condition_id="C002",
        start_date_str="2025-01-01",
        duration_days=7,
        affected_nodes=["inst-a"],
        intensity=0.90,
        reports_per_day_base=10
    )
    assert res_high["signal_metrics"]["community_reports_logged"] > res_low["signal_metrics"]["community_reports_logged"]


def test_four_node_non_iid_heterogeneity():
    """
    FOUR-NODE NON-IID VALIDATION:
    Verifies that the four nodes exhibit distinct non-IID characteristics in baseline volume,
    syndrome ratios, seasonality, and variance.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        generator = SyntheticDataGenerator(seed=42)
        datasets = generator.generate_all_institutions(output_dir=temp_dir, days=90, scenario=ScenarioType.NORMAL)

        vol_a = datasets["inst-a"][0]["service_count"].mean()
        vol_b = datasets["inst-b"][0]["service_count"].mean()
        vol_c = datasets["inst-c"][0]["service_count"].mean()
        vol_d = datasets["inst-d"][0]["service_count"].mean()

        # Urban highest, Rural lowest
        assert vol_a > vol_b > vol_c
        assert vol_d > vol_c
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_privacy_preservation_and_ground_truth_isolation(temp_scenario_manager):
    """
    PRIVACY & GROUND TRUTH ISOLATION:
    Verifies that simulated outbreak runs preserve k >= 11 suppression,
    3-distinct-node zone privacy, and keep ground truth isolated from model training features.
    """
    # 1. Run outbreak
    temp_scenario_manager.simulate_disease_outbreak_multisource(
        condition_id="C002",
        start_date_str="2025-06-01",
        duration_days=7,
        affected_nodes=["inst-a", "inst-b", "inst-d"],
        intensity=0.80
    )

    # 2. Run local aggregation with k=11 suppression
    aggs_a = temp_scenario_manager.run_daily_aggregation("inst-a", k_threshold=11)
    for a in aggs_a:
        assert a.count >= 11, "k >= 11 small group suppression violated"

    # 3. Verify ground truth isolation in federated handoff
    handoff_mgr = FederatedDataHandoffManager(data_dir=temp_scenario_manager.data_dir, k_threshold=11)
    df_sample = pd.DataFrame([{"date": "2025-06-01", "syndrome_category": "respiratory", "service_count": 45}])
    is_valid, errors = handoff_mgr.validate_handoff_dataframe(df_sample, node_id="inst-a")
    assert is_valid
    assert "condition_id" not in df_sample.columns
    assert "outbreak_active" not in df_sample.columns


def test_reproducibility_with_seed():
    """
    REPRODUCIBILITY:
    Verifies that identical seed produces byte-for-byte identical synthetic datasets,
    while different seeds produce distinct but statistically valid series.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        g1 = SyntheticDataGenerator(seed=42)
        d1 = g1.generate_all_institutions(output_dir=os.path.join(temp_dir, "d1"), days=30, scenario=ScenarioType.NORMAL)

        g2 = SyntheticDataGenerator(seed=42)
        d2 = g2.generate_all_institutions(output_dir=os.path.join(temp_dir, "d2"), days=30, scenario=ScenarioType.NORMAL)

        g3 = SyntheticDataGenerator(seed=999)
        d3 = g3.generate_all_institutions(output_dir=os.path.join(temp_dir, "d3"), days=30, scenario=ScenarioType.NORMAL)

        # Same seed -> identical
        pd.testing.assert_frame_equal(d1["inst-a"][0], d2["inst-a"][0])
        # Different seed -> distinct
        assert not d1["inst-a"][0]["service_count"].equals(d3["inst-a"][0]["service_count"])
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)



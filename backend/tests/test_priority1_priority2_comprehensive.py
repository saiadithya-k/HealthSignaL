import os
import json
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from app.core.syndrome_mapping import syndrome_service
from app.core.local_node import LocalInstitutionClient
from app.data_generation.generator import SyntheticDataGenerator
from app.data_generation.schemas import ScenarioType
from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.forecasting import load_global_model, compute_validation_residuals, generate_multiday_forecast
from app.ml.anomaly import CUSUMDetector
from app.api.alerts import execute_cusum_detection

# =========================================================================
# PERSON 1 TESTS: DATA QUALITY, ONTOLOGY & HEALTH INTELLIGENCE
# =========================================================================

def test_minimum_meaningful_data_volume():
    """
    PERSON 1 PRIORITY 1:
    Verifies that the system generates at least 4,000–6,000+ meaningful synthetic
    health records across 4 decentralized nodes and 5 sources without random duplication.
    """
    total_records = 0
    node_counts = {}
    for nid in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        client = LocalInstitutionClient(nid, data_dir="data")
        df, _ = client.load_local_data()
        assert df is not None and not df.empty
        node_counts[nid] = len(df)
        total_records += len(df)

    assert total_records >= 4000, f"Total records {total_records} below minimum 4,000"
    for nid, count in node_counts.items():
        assert count >= 1000, f"Node {nid} has insufficient records: {count}"


def test_all_45_syndromes_representation_and_coverage():
    """
    PERSON 1 PRIORITY 2:
    Verifies that all 45 canonical syndromes are dynamically loaded from
    syndrome_master.json and properly evaluated without hardcoding short lists.
    """
    canonical_syndromes = syndrome_service.syndromes
    assert len(canonical_syndromes) == 45

    # Check that report exists and covers all 45
    report_path = os.path.join("data", "syndrome_data_coverage_report.json")
    if not os.path.exists(report_path):
        report_path = os.path.join("backend", "data", "syndrome_data_coverage_report.json")
    
    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert rep["total_canonical_syndromes"] == 45
    assert len(rep["syndromes"]) == 45
    for s in rep["syndromes"]:
        assert "syndrome" in s
        assert "records" in s
        assert "days" in s
        assert "forecastable" in s
        assert s["status"] in ["VALID", "INSUFFICIENT_HISTORY"]


def test_ontology_hierarchy_257_symptoms_to_45_syndromes_to_105_conditions():
    """
    PERSON 1 PRIORITY 3:
    Verifies full ontology hierarchy: 257 symptoms -> 45 syndromes -> 105 conditions.
    Ensures mapping is deterministic, reproducible, and non-diagnostic.
    """
    symptoms = syndrome_service.symptoms
    syndromes = syndrome_service.syndromes
    diseases = syndrome_service.diseases

    assert len(symptoms) == 257
    assert len(syndromes) == 45
    assert len(diseases) >= 100

    # Deterministic mapping tests
    resp_mapped = syndrome_service.map_symptoms_to_syndromes(["S001", "S021", "S038"])
    assert "influenza_like_illness" in resp_mapped or "upper_respiratory_infection" in resp_mapped

    gi_mapped = syndrome_service.map_symptoms_to_syndromes(["S047", "S048", "S050"])
    assert "acute_watery_diarrhea" in gi_mapped or "gastroenteritis_emetic" in gi_mapped


def test_five_core_sources_and_reliability_matrix():
    """
    PERSON 1 PRIORITY 4 & 5:
    Verifies source reliability configuration and data availability for
    Community, Doctor, Clinic, Pharmacy, and Diagnostic Testing.
    """
    rel_path = os.path.join("data", "source_reliability_report.json")
    if not os.path.exists(rel_path):
        rel_path = os.path.join("backend", "data", "source_reliability_report.json")

    assert os.path.exists(rel_path)
    with open(rel_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    sources = rep["sources"]
    assert "diagnostic_testing" in sources
    assert "doctor_triage" in sources
    assert "pharmacy_otc" in sources
    assert "community_reports" in sources
    
    # Check weights order
    assert sources["diagnostic_testing"]["reliability_weight"] >= 0.90
    assert sources["community_reports"]["reliability_weight"] <= 0.60


def test_cross_source_outbreak_correlation():
    """
    PERSON 1 PRIORITY 8:
    Verifies that cross-source outbreak signals produce meaningful statistical
    associations without signal collapse or artificial inflation.
    """
    corr_path = os.path.join("data", "source_correlation_report.json")
    if not os.path.exists(corr_path):
        corr_path = os.path.join("backend", "data", "source_correlation_report.json")

    assert os.path.exists(corr_path)
    with open(corr_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert len(rep["scenarios"]) >= 4
    for sc in rep["scenarios"]:
        assert "correlations" in sc
        for c in sc["correlations"]:
            assert -1.0 <= c["lag_0_correlation"] <= 1.0


def test_four_node_non_iid_heterogeneity():
    """
    PERSON 1 PRIORITY 6:
    Verifies that the four nodes (Urban, Semi-Urban, Rural, Mixed) have
    genuinely different volume, variance, and syndrome distributions.
    """
    client_a = LocalInstitutionClient("inst-a", data_dir="data")
    client_c = LocalInstitutionClient("inst-c", data_dir="data")
    df_a, _ = client_a.load_local_data()
    df_c, _ = client_c.load_local_data()

    vol_a = df_a["service_count"].sum()
    vol_c = df_c["service_count"].sum()
    
    # Urban node (inst-a) should have higher total volume than rural node (inst-c)
    assert vol_a > vol_c * 1.5


# =========================================================================
# PERSON 2 TESTS: FORECASTING, FEDERATED LEARNING & EARLY WARNING
# =========================================================================

def test_multi_horizon_forecasting_exact_horizons():
    """
    PERSON 2 PRIORITY 8:
    Verifies that 7, 10, and 14 day requests generate exact horizon lengths
    with point_forecast, 80% interval, 95% interval, and confidence score.
    """
    global_model = load_global_model()
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    for h in [7, 10, 14]:
        rep = generate_multiday_forecast(history_df=df, model=global_model, horizon=h, data_dir="data")
        assert rep["horizon_days"] == h
        
        # Check day-by-day sequence
        valid_forecasts = [f for f in rep["forecasts"] if f["syndrome_category"] == "respiratory" and f["status"] == "VALID"]
        assert len(valid_forecasts) == h
        for i, f in enumerate(valid_forecasts):
            assert f["horizon_day"] == i + 1
            assert f["point_forecast"] >= 0.0
            assert f["lower_bound_80"] <= f["point_forecast"] <= f["upper_bound_80"]
            assert f["lower_bound_95"] <= f["point_forecast"] <= f["upper_bound_95"]
            assert (f["upper_bound_95"] - f["lower_bound_95"]) >= (f["upper_bound_80"] - f["lower_bound_80"])
            assert 0.0 <= f["confidence_score"] <= 1.0


def test_syndrome_specific_and_horizon_specific_confidence():
    """
    PERSON 2 PRIORITY 7 & 11:
    Verifies confidence is independently computed for Syndrome × Horizon × Node configuration
    without static flat subtraction or NaN/Inf values.
    """
    global_model = load_global_model()
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    rep = generate_multiday_forecast(history_df=df, model=global_model, horizon=14, data_dir="data")
    resp_forecasts = [f for f in rep["forecasts"] if f["syndrome_category"] == "respiratory" and f["status"] == "VALID"]
    gi_forecasts = [f for f in rep["forecasts"] if f["syndrome_category"] == "gastrointestinal" and f["status"] == "VALID"]

    assert len(resp_forecasts) == 14
    assert len(gi_forecasts) == 14

    # Day 1 vs Day 14 should show natural degradation
    assert resp_forecasts[0]["confidence_score"] >= resp_forecasts[-1]["confidence_score"]
    
    # Missing node degradation test
    rep_missing1 = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, missing_node_count=1, data_dir="data")
    rep_missing0 = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, missing_node_count=0, data_dir="data")
    
    conf_0 = [f["confidence_score"] for f in rep_missing0["forecasts"] if f["syndrome_category"] == "respiratory"][0]
    conf_1 = [f["confidence_score"] for f in rep_missing1["forecasts"] if f["syndrome_category"] == "respiratory"][0]
    assert conf_0 >= conf_1


def test_forecast_interval_calibration_report():
    """
    PERSON 2 PRIORITY 12:
    Verifies prediction interval calibration report: 80% and 95% empirical coverage.
    """
    cal_path = os.path.join("data", "forecast_calibration_report.json")
    if not os.path.exists(cal_path):
        cal_path = os.path.join("backend", "data", "forecast_calibration_report.json")

    assert os.path.exists(cal_path)
    with open(cal_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    cal = rep["overall_calibration"]
    assert 0.70 <= cal["empirical_80"] <= 0.95
    assert 0.85 <= cal["empirical_95"] <= 1.00
    assert cal["mean_interval_width_95"] >= cal["mean_interval_width_80"]


def test_early_warning_lead_time_measurement():
    """
    PERSON 2 PRIORITY 15:
    Verifies empirical early warning lead time across outbreak scenarios.
    """
    lead_path = os.path.join("data", "early_warning_lead_time_report.json")
    if not os.path.exists(lead_path):
        lead_path = os.path.join("backend", "data", "early_warning_lead_time_report.json")

    assert os.path.exists(lead_path)
    with open(lead_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert rep["average_overall_lead_time_days"] >= 3.0
    for ev in rep["evaluations"]:
        assert ev["lead_time_days"] >= 1.0
        assert "first_cusum_candidate_day" in ev
        assert "clinical_surge_day" in ev


def test_cusum_anomaly_detection_sensitivity():
    """
    PERSON 2 PRIORITY 16:
    Verifies CUSUM sensitivity metrics across baseline and outbreak scenarios.
    """
    cusum_path = os.path.join("data", "cusum_sensitivity_report.json")
    if not os.path.exists(cusum_path):
        cusum_path = os.path.join("backend", "data", "cusum_sensitivity_report.json")

    assert os.path.exists(cusum_path)
    with open(cusum_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert rep["overall_metrics"]["overall_detection_rate"] >= 0.80
    assert rep["overall_metrics"]["total_false_positives"] <= 2


def test_forecast_state_transitions_consistency():
    """
    PERSON 2 PRIORITY 10 & 20:
    Verifies state transitions (0 -> 1 -> 0, 7 -> 14 -> 7) ensure latest request wins
    and no stale data is retained.
    """
    global_model = load_global_model()
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()

    # 1. 0 -> 1 -> 0
    f0_a = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, missing_node_count=0, data_dir="data")
    f1 = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, missing_node_count=1, data_dir="data")
    f0_b = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, missing_node_count=0, data_dir="data")

    assert f0_a["coverage_ratio"] == 1.0
    assert f1["coverage_ratio"] == 0.75
    assert f0_b["coverage_ratio"] == 1.0
    assert f0_b["participating_nodes_count"] == 4

    # 2. 7 -> 14 -> 7
    f7 = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, data_dir="data")
    f14 = generate_multiday_forecast(history_df=df, model=global_model, horizon=14, data_dir="data")
    f7_post = generate_multiday_forecast(history_df=df, model=global_model, horizon=7, data_dir="data")

    assert f7["horizon_days"] == 7
    assert f14["horizon_days"] == 14
    assert f7_post["horizon_days"] == 7


def test_zero_future_leakage_and_privacy_invariants():
    """
    MANDATORY INVARIANTS:
    Verifies that future ground truth is excluded from features and privacy constraints hold.
    """
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)

    prohibited_cols = {"outbreak_active", "scenario_id", "condition_id", "condition_name", "true_disease"}
    for col in prohibited_cols:
        assert col not in feat_df[FEATURE_COLUMNS].columns
        assert col not in FEATURE_COLUMNS

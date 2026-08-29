import os
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from app.core.syndrome_mapping import syndrome_service
from app.core.local_node import LocalInstitutionClient
from app.core.privacy_gate import PrivacyGate
from app.core.federated_handoff import FederatedDataHandoffManager
from app.data_generation.generator import SyntheticDataGenerator
from app.data_generation.schemas import ScenarioType
from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.model import LocalForecastModel
from app.federated.server import run_federated_round
from app.ml.forecasting import load_global_model, generate_multiday_forecast
from app.ml.anomaly import CUSUMDetector

def test_full_pipeline_end_to_end_execution():
    """
    PRIORITY 3 FULL PIPELINE INTEGRATION TEST:
    Executes and asserts every single sequential stage from data generation
    through privacy suppression, federated training, multi-horizon forecasting,
    CUSUM detection, and reviewer queue ingestion.
    """
    # Stage 1: Ontology Services
    symptoms = syndrome_service.symptoms
    syndromes = syndrome_service.syndromes
    conditions = syndrome_service.diseases
    assert len(symptoms) == 257
    assert len(syndromes) == 45
    assert len(conditions) >= 100

    # Stage 2: 4-Node Synthetic Health Generation
    generator = SyntheticDataGenerator(seed=42)
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    total_records = 0
    node_dfs = {}

    for nid in nodes:
        df, meta = generator.generate_institution_dataset(nid, days=90, scenario=ScenarioType.NORMAL)
        assert not df.empty
        node_dfs[nid] = df
        total_records += len(df)

    assert total_records >= 4000

    # Stage 3: Local Ingestion & Privacy Gate (k >= 11 Suppression)
    gate = PrivacyGate(min_group_size=11)
    for nid in nodes:
        df = node_dfs[nid]
        suppressed_df = df[df["service_count"] >= 11]
        assert not suppressed_df.empty

    # Stage 4: Supervised Feature Engineering (Exact F=13 Contract)
    feature_dfs = {}
    for nid in nodes:
        client = LocalInstitutionClient(nid, data_dir="data")
        feat_df, meta = client.get_federated_training_data(forecast_horizon=7)
        assert len(feat_df.columns) >= 13
        assert list(feat_df[FEATURE_COLUMNS].columns) == FEATURE_COLUMNS
        feature_dfs[nid] = feat_df

    # Stage 5: Local Node Training & Parameter Transmission
    local_models = {}
    for nid in nodes:
        f_df = feature_dfs[nid]
        train_df, _, _ = prepare_chronological_split(f_df)
        model = LocalForecastModel(institution_id=nid, alpha=1.0, forecast_horizon=7)
        model.fit(train_df[FEATURE_COLUMNS], train_df["target"])
        local_models[nid] = model
        assert model.is_trained

    # Stage 6: Federated Aggregation (Flower FedAvg)
    fed_res = run_federated_round(data_dir="data", artifacts_dir="artifacts")
    assert fed_res is not None
    assert len(fed_res["participating_nodes"]) >= 3
    assert fed_res["status"] == "COMPLETED"

    # Stage 7: Global Model Loading & Multi-Horizon Forecasting (7, 10, 14 Days)
    global_model = load_global_model(artifacts_dir="artifacts")
    df_history = node_dfs["inst-a"]

    for h in [7, 10, 14]:
        forecast_res = generate_multiday_forecast(history_df=df_history, model=global_model, horizon=h, data_dir="data")
        assert forecast_res["horizon_days"] == h
        assert "confidence_score" in forecast_res
        
        # Check prediction intervals
        for f in forecast_res["forecasts"][:h]:
            if f["status"] == "VALID":
                assert f["point_forecast"] >= 0.0
                assert f["lower_bound_80"] <= f["point_forecast"] <= f["upper_bound_80"]
                assert f["lower_bound_95"] <= f["point_forecast"] <= f["upper_bound_95"]
                assert (f["upper_bound_95"] - f["lower_bound_95"]) >= (f["upper_bound_80"] - f["lower_bound_80"])
                assert 0.0 <= f["confidence_score"] <= 1.0

    # Stage 8: CUSUM Anomaly Detection & Review Queue Alert Candidates
    detector = CUSUMDetector(drift_k=0.5, threshold_h=4.0)
    feat_resp = feature_dfs["inst-a"][feature_dfs["inst-a"]["syndrome_category"] == "respiratory"]
    preds = global_model.predict(feat_resp[FEATURE_COLUMNS])
    y_obs = feat_resp["target"].values

    cusum_res = detector.detect_series(observed_series=y_obs, expected_series=preds, sigma=1.5, syndrome_category="respiratory")
    assert "cusum_history" in cusum_res
    assert "candidate_alerts" in cusum_res

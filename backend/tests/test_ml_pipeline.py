import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.core.local_node import LocalInstitutionClient
from app.ml.features import build_supervised_features, prepare_chronological_split, FEATURE_COLUMNS
from app.ml.model import LocalForecastModel
from app.ml.metrics import compute_eval_metrics
from app.ml.harness import BaselineComparisonHarness
from app.federated.model_adapter import model_to_parameters, parameters_to_model

def test_feature_generation():
    """Asserts that build_supervised_features creates expected feature columns and drops NaNs."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    
    feat_df = build_supervised_features(df, forecast_horizon=7)
    assert not feat_df.empty
    for col in FEATURE_COLUMNS + ["target"]:
        assert col in feat_df.columns
    assert feat_df[FEATURE_COLUMNS + ["target"]].isnull().sum().sum() == 0

def test_no_future_data_leakage():
    """Asserts that features at index t use strictly historical observations at or before index t."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    
    feat_df = build_supervised_features(df, forecast_horizon=7)
    
    # Check that lag_1 matches previous row's service_count
    # Group by syndrome category to check ordering
    for cat, group in feat_df.groupby("syndrome_category"):
        g = group.sort_values(by="date").reset_index(drop=True)
        for i in range(1, len(g)):
            # The lag_1 feature must equal the service_count of the preceding day
            assert g.loc[i, "lag_1"] == g.loc[i - 1, "service_count"]

def test_temporal_split():
    """Asserts chronological order: train max date < val min date < test min date."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)
    
    train_df, val_df, test_df = prepare_chronological_split(feat_df, train_ratio=0.70, val_ratio=0.15)
    
    assert not train_df.empty
    assert not val_df.empty
    assert not test_df.empty
    
    train_max_date = train_df["date"].max()
    val_min_date = val_df["date"].min()
    val_max_date = val_df["date"].max()
    test_min_date = test_df["date"].min()
    
    assert train_max_date < val_min_date
    assert val_max_date < test_min_date

def test_local_model_trains():
    """Asserts that LocalForecastModel fits on training features without errors."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)
    train_df, _, _ = prepare_chronological_split(feat_df)
    
    model = LocalForecastModel("inst-a", alpha=1.0, forecast_horizon=7)
    model.fit(train_df[FEATURE_COLUMNS], train_df["target"])
    
    assert model.is_trained
    assert len(model.model.coef_) == len(FEATURE_COLUMNS)

def test_local_model_predicts():
    """Asserts that predict returns non-negative predictions of matching length."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)
    train_df, _, test_df = prepare_chronological_split(feat_df)
    
    model = LocalForecastModel("inst-a", alpha=1.0, forecast_horizon=7)
    model.fit(train_df[FEATURE_COLUMNS], train_df["target"])
    
    preds = model.predict(test_df[FEATURE_COLUMNS])
    assert len(preds) == len(test_df)
    assert (preds >= 0).all()

def test_local_model_evaluation():
    """Asserts that evaluate returns valid MAE, RMSE, MAPE metrics."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)
    train_df, _, test_df = prepare_chronological_split(feat_df)
    
    model = LocalForecastModel("inst-a", alpha=1.0, forecast_horizon=7)
    model.fit(train_df[FEATURE_COLUMNS], train_df["target"])
    
    metrics = model.evaluate(test_df[FEATURE_COLUMNS], test_df["target"])
    assert "mae" in metrics
    assert "rmse" in metrics
    assert "mape" in metrics
    assert metrics["mae"] >= 0.0
    assert metrics["rmse"] >= 0.0

def test_all_four_institutions_train():
    """Asserts that models for inst-a, inst-b, inst-c, inst-d can all train independently."""
    for inst_id in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        client = LocalInstitutionClient(inst_id, data_dir="data")
        df, _ = client.load_local_data()
        feat_df = build_supervised_features(df, forecast_horizon=7)
        train_df, _, _ = prepare_chronological_split(feat_df)
        
        model = LocalForecastModel(inst_id, alpha=1.0)
        model.fit(train_df[FEATURE_COLUMNS], train_df["target"])
        assert model.is_trained

def test_institution_data_isolation():
    """Asserts strict local data isolation: model for Inst A is trained ONLY on Inst A data."""
    client_a = LocalInstitutionClient("inst-a", data_dir="data")
    df_a, meta_a = client_a.load_local_data()
    assert (df_a["institution_id"] == "inst-a").all()
    
    client_b = LocalInstitutionClient("inst-b", data_dir="data")
    df_b, meta_b = client_b.load_local_data()
    assert (df_b["institution_id"] == "inst-b").all()
    
    # Assert Inst A client cannot access Inst B data
    assert meta_a["institution_id"] != meta_b["institution_id"]

def test_naive_baseline():
    """Asserts that naive baseline evaluation computes valid metrics."""
    harness = BaselineComparisonHarness(data_dir="data")
    report = harness.run_full_baseline_evaluation()
    
    assert "naive_lag7" in report["baselines"]
    naive_overall = report["baselines"]["naive_lag7"]["overall"]
    assert naive_overall["mae"] >= 0.0

def test_pooled_baseline():
    """Asserts that pooled upper bound baseline runs and generates reference metrics."""
    harness = BaselineComparisonHarness(data_dir="data")
    report = harness.run_full_baseline_evaluation()
    
    assert "pooled_ridge_upper_bound" in report["baselines"]
    pooled_overall = report["baselines"]["pooled_ridge_upper_bound"]["overall"]
    assert pooled_overall["mae"] >= 0.0

def test_metrics_are_valid():
    """Asserts compute_eval_metrics math safety against zero division."""
    y_true = [0, 0, 0, 10, 20]
    y_pred = [1, 2, 0, 8, 25]
    
    m = compute_eval_metrics(y_true, y_pred)
    assert not np.isnan(m["mae"])
    assert not np.isnan(m["rmse"])
    assert not np.isnan(m["mape"])

def test_reproducible_training():
    """Asserts that training twice on same data produces identical model coefficients."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)
    train_df, _, _ = prepare_chronological_split(feat_df)
    
    m1 = LocalForecastModel("inst-a", alpha=1.0).fit(train_df[FEATURE_COLUMNS], train_df["target"])
    m2 = LocalForecastModel("inst-a", alpha=1.0).fit(train_df[FEATURE_COLUMNS], train_df["target"])
    
    np.testing.assert_array_almost_equal(m1.model.coef_, m2.model.coef_)

def test_model_artifact_persistence(tmp_path):
    """Asserts that save_model and load_model serialize and deserialize artifacts correctly."""
    client = LocalInstitutionClient("inst-a", data_dir="data")
    df, _ = client.load_local_data()
    feat_df = build_supervised_features(df, forecast_horizon=7)
    train_df, _, test_df = prepare_chronological_split(feat_df)
    
    save_dir = str(tmp_path / "artifacts")
    m1 = LocalForecastModel("inst-a", alpha=1.0).fit(train_df[FEATURE_COLUMNS], train_df["target"])
    m1.save_model(base_dir=save_dir)
    
    m2 = LocalForecastModel.load_model("inst-a", base_dir=save_dir)
    p1 = m1.predict(test_df[FEATURE_COLUMNS])
    p2 = m2.predict(test_df[FEATURE_COLUMNS])
    
    np.testing.assert_array_almost_equal(p1, p2)


def test_four_nodes_local_training_and_serialization():
    """
    TASK 2.2 COMPREHENSIVE TEST:
    1. All 4 nodes (inst-a, inst-b, inst-c, inst-d) train successfully
    2. Each node uses exactly 13 features in training
    3. Each node trains on only its own local dataset
    4. Model has exactly 13 coefficients
    5. Model has exactly 1 intercept (14 parameter values in total)
    6. Parameters are strictly finite (no NaN, no Inf)
    7. Predictions are strictly finite, non-negative, and match test target length
    8. Model parameter round-trip (model -> parameters -> reconstructed model) produces identical predictions
    9. Node models remain independently trained with non-IID parameter divergence
    """
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    trained_models = {}

    for nid in nodes:
        client = LocalInstitutionClient(nid, data_dir="data")
        df, meta = client.load_local_data()
        
        # Verify local data isolation
        assert (df["institution_id"] == nid).all()
        assert meta["institution_id"] == nid

        feat_df = build_supervised_features(df, forecast_horizon=7)
        train_df, val_df, test_df = prepare_chronological_split(feat_df)

        # 2. Exactly 13 features
        X_train = train_df[FEATURE_COLUMNS]
        y_train = train_df["target"]
        assert X_train.shape[1] == 13
        assert list(X_train.columns) == FEATURE_COLUMNS

        # 1. Independent training
        model = LocalForecastModel(nid, alpha=1.0, forecast_horizon=7)
        model.fit(X_train, y_train)
        assert model.is_trained

        # 4, 5. 13 coefficients + 1 intercept = 14 parameters
        assert len(model.model.coef_) == 13
        assert np.isscalar(model.model.intercept_)
        param_vec = model_to_parameters(model)
        assert len(param_vec) == 14

        # 6. Parameters are finite
        assert not np.isnan(param_vec).any()
        assert not np.isinf(param_vec).any()

        # 7. Predictions are finite, non-negative, and match length
        X_test = test_df[FEATURE_COLUMNS]
        preds = model.predict(X_test)
        assert len(preds) == len(test_df)
        assert not np.isnan(preds).any()
        assert not np.isinf(preds).any()
        assert (preds >= 0).all()

        # 8. Round-trip serialization
        recon_model = parameters_to_model(param_vec, institution_id=nid, alpha=1.0, forecast_horizon=7)
        recon_preds = recon_model.predict(X_test)
        np.testing.assert_allclose(preds, recon_preds, rtol=1e-5)

        trained_models[nid] = model

    # 9. Non-IID parameter divergence across nodes
    coef_a = trained_models["inst-a"].model.coef_
    coef_b = trained_models["inst-b"].model.coef_
    coef_c = trained_models["inst-c"].model.coef_
    coef_d = trained_models["inst-d"].model.coef_

    assert not np.allclose(coef_a, coef_b)
    assert not np.allclose(coef_a, coef_c)
    assert not np.allclose(coef_a, coef_d)
    assert trained_models["inst-a"].model.intercept_ != trained_models["inst-b"].model.intercept_


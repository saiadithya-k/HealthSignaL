import os
import json
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple

from app.core.local_node import LocalInstitutionClient
from app.ml.features import build_supervised_features, prepare_chronological_split, FEATURE_COLUMNS
from app.ml.model import LocalForecastModel
from app.ml.metrics import compute_eval_metrics

INSTITUTION_IDS = ["inst-a", "inst-b", "inst-c", "inst-d"]

class BaselineComparisonHarness:
    """
    Phase 3 Baseline Comparison Harness:
    Executes and compares three baseline evaluation modes:
    - Baseline A: Local-Only Ridge Regression (Independent node models)
    - Baseline B: Pooled Upper Bound Ridge Regression (Evaluation-only centralized reference)
    - Baseline C: Simple Naive Baseline (Same-day-last-week lag_7 prediction)
    """

    def __init__(self, data_dir: str = "data", forecast_horizon: int = 7, alpha: float = 1.0):
        self.data_dir = data_dir
        self.forecast_horizon = forecast_horizon
        self.alpha = alpha

    def run_full_baseline_evaluation(self, artifacts_dir: str = "artifacts") -> Dict[str, Any]:
        node_splits: Dict[str, Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
        
        # 1. Load data via LocalInstitutionClient and construct chronological splits per node
        for inst_id in INSTITUTION_IDS:
            client = LocalInstitutionClient(inst_id, data_dir=self.data_dir)
            df, _ = client.load_local_data()
            
            feat_df = build_supervised_features(df, forecast_horizon=self.forecast_horizon)
            train_df, val_df, test_df = prepare_chronological_split(feat_df, train_ratio=0.70, val_ratio=0.15)
            node_splits[inst_id] = (train_df, val_df, test_df)

        # -------------------------------------------------------------
        # BASELINE A: Local-Only Ridge Models
        # -------------------------------------------------------------
        local_results = {}
        local_models = {}
        local_test_preds = []
        local_test_targets = []

        for inst_id in INSTITUTION_IDS:
            train_df, _, test_df = node_splits[inst_id]
            
            model = LocalForecastModel(institution_id=inst_id, alpha=self.alpha, forecast_horizon=self.forecast_horizon)
            model.fit(train_df[FEATURE_COLUMNS], train_df["target"])
            
            metrics = model.evaluate(test_df[FEATURE_COLUMNS], test_df["target"], model_name="local_ridge")
            local_results[inst_id] = metrics
            local_models[inst_id] = model

            # Save local model artifact
            model.save_model(base_dir=os.path.join(artifacts_dir, "local"))

            preds = model.predict(test_df[FEATURE_COLUMNS])
            local_test_preds.extend(preds)
            local_test_targets.extend(test_df["target"].values)

        local_overall = compute_eval_metrics(
            y_true=local_test_targets,
            y_pred=local_test_preds,
            institution_id="overall",
            model_name="local_ridge",
            forecast_horizon=self.forecast_horizon
        )

        # -------------------------------------------------------------
        # BASELINE B: Pooled Upper Bound Ridge (Evaluation-Only)
        # -------------------------------------------------------------
        pooled_train_dfs = [node_splits[inst_id][0] for inst_id in INSTITUTION_IDS]
        pooled_train = pd.concat(pooled_train_dfs, ignore_index=True)

        pooled_model = LocalForecastModel(institution_id="pooled_upper_bound", alpha=self.alpha, forecast_horizon=self.forecast_horizon)
        pooled_model.fit(pooled_train[FEATURE_COLUMNS], pooled_train["target"])

        # Save pooled model artifact
        pooled_model.save_model(base_dir=os.path.join(artifacts_dir, "pooled"))

        pooled_results = {}
        pooled_test_preds = []
        pooled_test_targets = []

        for inst_id in INSTITUTION_IDS:
            _, _, test_df = node_splits[inst_id]
            metrics = pooled_model.evaluate(test_df[FEATURE_COLUMNS], test_df["target"], model_name="pooled_ridge")
            pooled_results[inst_id] = metrics

            preds = pooled_model.predict(test_df[FEATURE_COLUMNS])
            pooled_test_preds.extend(preds)
            pooled_test_targets.extend(test_df["target"].values)

        pooled_overall = compute_eval_metrics(
            y_true=pooled_test_targets,
            y_pred=pooled_test_preds,
            institution_id="overall",
            model_name="pooled_ridge",
            forecast_horizon=self.forecast_horizon
        )

        # -------------------------------------------------------------
        # BASELINE C: Naive Seasonal Baseline (Same-Day-Last-Week lag_7)
        # -------------------------------------------------------------
        naive_results = {}
        naive_test_preds = []
        naive_test_targets = []

        for inst_id in INSTITUTION_IDS:
            _, _, test_df = node_splits[inst_id]
            # Naive rule: predict target = lag_7
            naive_preds = test_df["lag_7"].values
            targets = test_df["target"].values

            metrics = compute_eval_metrics(
                y_true=targets,
                y_pred=naive_preds,
                institution_id=inst_id,
                model_name="naive_lag7",
                forecast_horizon=self.forecast_horizon
            )
            naive_results[inst_id] = metrics

            naive_test_preds.extend(naive_preds)
            naive_test_targets.extend(targets)

        naive_overall = compute_eval_metrics(
            y_true=naive_test_targets,
            y_pred=naive_test_preds,
            institution_id="overall",
            model_name="naive_lag7",
            forecast_horizon=self.forecast_horizon
        )

        # -------------------------------------------------------------
        # Comparison Report Assembly
        # -------------------------------------------------------------
        report = {
            "forecast_horizon": self.forecast_horizon,
            "alpha": self.alpha,
            "evaluation_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "baselines": {
                "naive_lag7": {
                    "by_institution": naive_results,
                    "overall": naive_overall
                },
                "local_ridge": {
                    "by_institution": local_results,
                    "overall": local_overall
                },
                "pooled_ridge_upper_bound": {
                    "by_institution": pooled_results,
                    "overall": pooled_overall,
                    "disclaimer": "EVALUATION-ONLY CENTRALIZED BASELINE (Upper Bound Reference Condition)"
                }
            },
            "comparison_matrix": {
                "inst-a": {
                    "naive_mae": naive_results["inst-a"]["mae"],
                    "local_ridge_mae": local_results["inst-a"]["mae"],
                    "pooled_ridge_mae": pooled_results["inst-a"]["mae"]
                },
                "inst-b": {
                    "naive_mae": naive_results["inst-b"]["mae"],
                    "local_ridge_mae": local_results["inst-b"]["mae"],
                    "pooled_ridge_mae": pooled_results["inst-b"]["mae"]
                },
                "inst-c": {
                    "naive_mae": naive_results["inst-c"]["mae"],
                    "local_ridge_mae": local_results["inst-c"]["mae"],
                    "pooled_ridge_mae": pooled_results["inst-c"]["mae"]
                },
                "inst-d": {
                    "naive_mae": naive_results["inst-d"]["mae"],
                    "local_ridge_mae": local_results["inst-d"]["mae"],
                    "pooled_ridge_mae": pooled_results["inst-d"]["mae"]
                },
                "overall": {
                    "naive_mae": naive_overall["mae"],
                    "local_ridge_mae": local_overall["mae"],
                    "pooled_ridge_mae": pooled_overall["mae"]
                }
            }
        }

        # Save evaluation report to data directory
        report_path = os.path.join(self.data_dir, "phase3_evaluation_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report

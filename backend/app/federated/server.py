import os
import json
import numpy as np
import pandas as pd
import flwr as fl
from typing import Dict, Any, List, Tuple

from app.federated.client import HealthSignalFlowerClient
from app.federated.strategy import HealthSignalFedAvg, compute_weighted_fedavg
from app.federated.model_adapter import model_to_parameters, parameters_to_model, flwr_to_parameters, parameters_to_flwr
from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.metrics import compute_eval_metrics
from app.core.local_node import LocalInstitutionClient

INSTITUTION_IDS = ["inst-a", "inst-b", "inst-c", "inst-d"]

def run_federated_round(
    data_dir: str = "data",
    forecast_horizon: int = 7,
    alpha: float = 1.0,
    artifacts_dir: str = "artifacts"
) -> Dict[str, Any]:
    """
    Executes a 4-client federated training round across Institutions A, B, C, D.
    
    1. Instantiates 4 independent HealthSignalFlowerClients.
    2. Runs PrivacyGate validation and collects outbound parameters.
    3. Aggregates updates using weighted FedAvg via HealthSignalFedAvg.
    4. Evaluates reconstructed Global Forecast Model against node held-out test sets.
    5. Saves global model artifact to artifacts/global/model.joblib.
    """
    clients: Dict[str, HealthSignalFlowerClient] = {}
    valid_updates: List[Tuple[List[np.ndarray], int]] = []
    participating_nodes: List[str] = []
    overall_test_preds = []
    overall_test_targets = []
    node_eval_metrics: Dict[str, Dict[str, Any]] = {}

    # 1. Instantiate 4 local institution Flower clients
    for inst_id in INSTITUTION_IDS:
        client = HealthSignalFlowerClient(
            institution_id=inst_id,
            data_dir=data_dir,
            forecast_horizon=forecast_horizon,
            alpha=alpha
        )
        clients[inst_id] = client

        # Execute client fit (includes PrivacyGate validation)
        flwr_params, num_samples, metrics = client.fit([])
        valid_updates.append((flwr_params, num_samples))
        participating_nodes.append(inst_id)

    if len(valid_updates) < 4:
        raise RuntimeError(f"Federated round incomplete: expected 4 clients, got {len(valid_updates)}")

    # 2. Execute weighted FedAvg parameter aggregation
    aggregated_flwr_params = compute_weighted_fedavg(valid_updates)
    global_param_vec = flwr_to_parameters(aggregated_flwr_params)

    # 3. Reconstruct Global Model from aggregated parameters
    global_model = parameters_to_model(
        global_param_vec,
        institution_id="global",
        alpha=alpha,
        forecast_horizon=forecast_horizon
    )

    # 4. Evaluate Global Model against test sets of all 4 institutions
    for inst_id in INSTITUTION_IDS:
        client = clients[inst_id]
        test_df = client.test_df
        
        preds = global_model.predict(test_df[FEATURE_COLUMNS])
        eval_m = compute_eval_metrics(
            y_true=test_df["target"].values,
            y_pred=preds,
            institution_id=inst_id,
            model_name="federated_fedavg",
            forecast_horizon=forecast_horizon
        )
        node_eval_metrics[inst_id] = eval_m

        overall_test_preds.extend(preds)
        overall_test_targets.extend(test_df["target"].values)

    overall_metrics = compute_eval_metrics(
        y_true=overall_test_targets,
        y_pred=overall_test_preds,
        institution_id="overall",
        model_name="federated_fedavg",
        forecast_horizon=forecast_horizon
    )

    # 5. Save Global Model Artifact
    global_dir = os.path.join(artifacts_dir, "global")
    os.makedirs(global_dir, exist_ok=True)
    global_model.save_model(base_dir=artifacts_dir)

    report = {
        "status": "COMPLETED",
        "algorithm": "Ridge Regression (FedAvg)",
        "forecast_horizon": forecast_horizon,
        "participating_nodes": participating_nodes,
        "total_training_samples": sum(n for _, n in valid_updates),
        "global_model_metrics": {
            "by_institution": node_eval_metrics,
            "overall": overall_metrics
        },
        "global_parameters": {
            "coef": [float(round(c, 6)) for c in global_model.model.coef_],
            "intercept": float(round(global_model.model.intercept_, 6))
        }
    }

    report_path = os.path.join(data_dir, "phase4_federated_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    print("Starting 4-Client Flower Federated Training Round...")
    res = run_federated_round()
    print("Federated Round Completed Successfully!")
    print("Overall Global FedAvg Model MAE:", res["global_model_metrics"]["overall"]["mae"])

import os
import json
import numpy as np
import pandas as pd
import flwr as fl
from typing import Dict, Any, List, Tuple, Optional

from app.federated.client import HealthSignalFlowerClient
from app.federated.strategy import HealthSignalFedAvg, compute_weighted_fedavg, validate_client_update
from app.federated.model_adapter import model_to_parameters, parameters_to_model, flwr_to_parameters, parameters_to_flwr
from app.ml.features import FEATURE_COLUMNS, build_supervised_features, prepare_chronological_split
from app.ml.metrics import compute_eval_metrics
from app.core.local_node import LocalInstitutionClient

INSTITUTION_IDS = ["inst-a", "inst-b", "inst-c", "inst-d"]

def run_federated_round(
    data_dir: str = "data",
    forecast_horizon: int = 7,
    alpha: float = 1.0,
    artifacts_dir: str = "artifacts",
    min_valid_clients: int = 4,
    available_nodes: Optional[List[str]] = None,
    expected_nodes: Optional[List[str]] = None,
    corrupted_nodes: Optional[Dict[str, Any]] = None,
    round_id: int = 1
) -> Dict[str, Any]:
    """
    Executes a federated training round across institutions.
    
    1. Tracks expected, participating, missing, rejected, and successful nodes.
    2. Instantiates independent HealthSignalFlowerClients for available nodes.
    3. Runs client-side PrivacyGate validation and server-side update validation.
    4. Enforces minimum valid client participation rule (min_valid_clients).
    5. Aggregates valid updates using sample-weighted FedAvg.
    6. Evaluates reconstructed Global Forecast Model against test sets.
    7. Saves global model artifact and generates safe operational report with model versioning.
    """
    expected = list(expected_nodes) if expected_nodes is not None else list(INSTITUTION_IDS)
    available = list(available_nodes) if available_nodes is not None else list(expected)
    corrupted = corrupted_nodes or {}

    missing_nodes = [n for n in expected if n not in available]
    participating_nodes = [n for n in expected if n in available]
    
    clients: Dict[str, HealthSignalFlowerClient] = {}
    valid_updates: List[Tuple[List[np.ndarray], int]] = []
    rejected_updates: List[Dict[str, Any]] = []
    rejected_nodes: List[str] = []
    successful_nodes: List[str] = []
    overall_test_preds = []
    overall_test_targets = []
    node_eval_metrics: Dict[str, Dict[str, Any]] = {}

    # 1. Collect updates from participating nodes
    for inst_id in participating_nodes:
        client = HealthSignalFlowerClient(
            institution_id=inst_id,
            data_dir=data_dir,
            forecast_horizon=forecast_horizon,
            alpha=alpha
        )
        clients[inst_id] = client

        # Check if simulated corrupted update is provided
        if inst_id in corrupted:
            flwr_params = corrupted[inst_id].get("parameters")
            num_samples = corrupted[inst_id].get("num_samples", 100)
            metrics = {"institution_id": inst_id, "privacy_validated": True}
        else:
            flwr_params, num_samples, metrics = client.fit([])

        # Server-side validation
        is_valid, failure_reason, rejection_event = validate_client_update(
            flwr_params,
            num_samples,
            institution_id=inst_id,
            max_coeff_bound=100.0
        )

        if is_valid:
            valid_updates.append((flwr_params, num_samples))
            successful_nodes.append(inst_id)
        else:
            rejected_nodes.append(inst_id)
            if rejection_event:
                rejected_updates.append(rejection_event)

    if len(valid_updates) < min_valid_clients:
        raise RuntimeError(
            f"Federated round incomplete: expected at least {min_valid_clients} valid clients, "
            f"got {len(valid_updates)} (missing: {missing_nodes}, rejected: {rejected_nodes})"
        )

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

    # 4. Evaluate Global Model against test sets of available institutions
    for inst_id in successful_nodes:
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

    # 5. Save Global Model Artifact and Traceable Safe Metadata
    model_version = f"v1.0.0-fed-r{round_id}"
    global_model.training_metadata = {
        "model_version": model_version,
        "round_id": round_id,
        "institution_id": "global",
        "algorithm": "Ridge Regression (FedAvg)",
        "aggregation": "FedAvg",
        "forecast_horizon": forecast_horizon,
        "alpha": alpha,
        "feature_count": len(FEATURE_COLUMNS),
        "parameter_count": len(FEATURE_COLUMNS) + 1,
        "features": FEATURE_COLUMNS,
        "coef": [float(round(c, 6)) for c in global_model.model.coef_],
        "intercept": float(round(global_model.model.intercept_, 6)),
        "expected_nodes": expected,
        "participating_nodes": participating_nodes,
        "missing_nodes": missing_nodes,
        "rejected_nodes": rejected_nodes,
        "successful_nodes": successful_nodes,
        "valid_update_count": len(valid_updates),
        "total_training_samples": sum(n for _, n in valid_updates),
        "metrics": {
            "by_institution": node_eval_metrics,
            "overall": overall_metrics
        }
    }

    global_dir = os.path.join(artifacts_dir, "global")
    os.makedirs(global_dir, exist_ok=True)
    global_model.save_model(base_dir=artifacts_dir)

    report = {
        "status": "COMPLETED",
        "model_version": model_version,
        "round_id": round_id,
        "algorithm": "Ridge Regression (FedAvg)",
        "aggregation": "FedAvg",
        "forecast_horizon": forecast_horizon,
        "feature_count": len(FEATURE_COLUMNS),
        "parameter_count": len(FEATURE_COLUMNS) + 1,
        "expected_nodes": expected,
        "participating_nodes": participating_nodes,
        "missing_nodes": missing_nodes,
        "rejected_nodes": rejected_nodes,
        "successful_nodes": successful_nodes,
        "valid_update_count": len(valid_updates),
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

    global_report_path = os.path.join(global_dir, "federated_report.json")
    with open(global_report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    print("Starting 4-Client Flower Federated Training Round...")
    res = run_federated_round()
    print("Federated Round Completed Successfully!")
    print("Overall Global FedAvg Model MAE:", res["global_model_metrics"]["overall"]["mae"])

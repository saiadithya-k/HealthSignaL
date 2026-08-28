import os
import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Any
import flwr as fl
from flwr.common import Parameters, Scalar, FitRes, NDArrays, ndarrays_to_parameters, parameters_to_ndarrays
from flwr.server.client_proxy import ClientProxy

from app.db.database import SessionLocal
from app.db.models import FederatedRound, RoundParticipant, ModelVersion, PrivacyEvent
from app.federated.model_adapter import flwr_to_parameters, parameters_to_flwr, parameters_to_model
from app.ml.features import FEATURE_COLUMNS

def compute_weighted_fedavg(results: List[Tuple[NDArrays, int]]) -> NDArrays:
    """
    Computes weighted FedAvg parameter aggregation:
    w_global = sum((n_i / N) * w_i) for all eligible valid client updates.
    """
    if not results:
        raise ValueError("Cannot aggregate empty client results list")

    total_samples = sum(num_examples for _, num_examples in results)
    if total_samples <= 0:
        raise ValueError(f"Invalid total samples count for FedAvg: {total_samples}")

    # Initialize zero arrays matching param shape
    num_params = len(results[0][0])
    aggregated_ndarrays: List[np.ndarray] = [
        np.zeros_like(param_arr, dtype=np.float64) for param_arr in results[0][0]
    ]

    for client_params, num_examples in results:
        weight = num_examples / total_samples
        for i in range(num_params):
            aggregated_ndarrays[i] += weight * client_params[i]

    return aggregated_ndarrays


class HealthSignalFedAvg(fl.server.strategy.FedAvg):
    """
    Custom Flower FedAvg strategy integrating incoming parameter validation,
    weighted aggregation, and PostgreSQL metadata logging.
    """

    def __init__(
        self,
        min_fit_clients: int = 4,
        min_available_clients: int = 4,
        max_coeff_bound: float = 100.0,
        **kwargs
    ):
        super().__init__(
            min_fit_clients=min_fit_clients,
            min_available_clients=min_available_clients,
            **kwargs
        )
        self.min_fit_clients = min_fit_clients
        self.max_coeff_bound = max_coeff_bound
        self.current_round_id: Optional[str] = None
        self.latest_global_parameters: Optional[NDArrays] = None

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """
        Validates incoming client updates and computes weighted FedAvg aggregation.
        Updates PostgreSQL metadata for FederatedRound and RoundParticipant.
        """
        valid_updates: List[Tuple[NDArrays, int]] = []
        participating_insts: List[str] = []
        failed_insts: List[str] = []

        db = SessionLocal()
        try:
            # Create ORM record for current round
            round_version = f"v1.0.0-fed-r{server_round}"
            fed_round = FederatedRound(
                global_model_version=round_version,
                status="IN_PROGRESS",
                expected_clients=self.min_fit_clients,
                successful_clients=0,
                failed_clients=len(failures)
            )
            db.add(fed_round)
            db.commit()
            db.refresh(fed_round)
            self.current_round_id = fed_round.round_id

            for client_proxy, fit_res in results:
                inst_id = fit_res.metrics.get("institution_id", "unknown_inst")
                participating_insts.append(inst_id)

                client_params = parameters_to_ndarrays(fit_res.parameters)
                param_vec = flwr_to_parameters(client_params)

                # Validation checks
                is_valid = True
                failure_reason = None

                if len(param_vec) != len(FEATURE_COLUMNS) + 1:
                    is_valid = False
                    failure_reason = f"Parameter dimension mismatch: expected {len(FEATURE_COLUMNS) + 1}, got {len(param_vec)}"
                elif np.isnan(param_vec).any() or np.isinf(param_vec).any():
                    is_valid = False
                    failure_reason = "NaN or Inf values detected in client parameters"
                elif (np.abs(param_vec[:-1]) > self.max_coeff_bound).any():
                    is_valid = False
                    failure_reason = f"Coefficients exceeded bound {self.max_coeff_bound}"

                # Record participant status in ORM
                participant = RoundParticipant(
                    round_id=fed_round.round_id,
                    institution_id=inst_id,
                    status="SUBMITTED" if is_valid else "FAILED",
                    update_status="VALIDATED" if is_valid else "REJECTED",
                    failure_reason=failure_reason
                )
                db.add(participant)

                if is_valid:
                    valid_updates.append((client_params, fit_res.num_examples))

            for failure in failures:
                inst_id = "failed_client"
                failed_insts.append(inst_id)

            db.commit()

            # Verify minimum participation threshold
            if len(valid_updates) < self.min_fit_clients:
                fed_round.status = "INCOMPLETE"
                fed_round.successful_clients = len(valid_updates)
                fed_round.failed_clients = len(failures) + (self.min_fit_clients - len(valid_updates))
                db.commit()
                return None, {"status": "INCOMPLETE", "valid_updates": len(valid_updates)}

            # Compute weighted FedAvg aggregation
            aggregated_ndarrays = compute_weighted_fedavg(valid_updates)
            self.latest_global_parameters = aggregated_ndarrays

            fed_round.status = "COMPLETED"
            fed_round.successful_clients = len(valid_updates)
            fed_round.failed_clients = len(failures)
            db.commit()

            # Record ModelVersion in ORM
            model_ver = db.query(ModelVersion).filter(ModelVersion.version == round_version).first()
            if not model_ver:
                db.add(ModelVersion(
                    version=round_version,
                    algorithm="Ridge Regression (FedAvg)",
                    metrics={"participating_nodes": participating_insts, "successful_updates": len(valid_updates)}
                ))
                db.commit()

            parameters_aggregated = ndarrays_to_parameters(aggregated_ndarrays)
            metrics_aggregated = {
                "round_id": fed_round.round_id,
                "version": round_version,
                "successful_updates": len(valid_updates),
                "total_samples": sum(n for _, n in valid_updates)
            }

            return parameters_aggregated, metrics_aggregated

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

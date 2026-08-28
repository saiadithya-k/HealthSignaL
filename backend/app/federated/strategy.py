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

def validate_client_update(
    client_params: Any,
    num_examples: Any,
    institution_id: str = "unknown_inst",
    max_coeff_bound: float = 100.0,
    expected_num_features: int = len(FEATURE_COLUMNS)
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validates incoming client update prior to FedAvg aggregation.
    Returns: (is_valid, failure_reason, safe_rejection_event)
    Rejection event contains only metadata and reason, never raw parameters or PII.
    """
    # 1. Structure check: must be a list or tuple of 2 numpy arrays
    if not isinstance(client_params, (list, tuple)) or len(client_params) != 2:
        reason = "INVALID_STRUCTURE"
        event = {
            "event_type": "INVALID_FEDERATED_UPDATE",
            "institution_id": institution_id,
            "reason": reason,
            "details": {"error": f"Expected list of 2 arrays, got {type(client_params).__name__} with length {len(client_params) if isinstance(client_params, (list, tuple)) else 'N/A'}"}
        }
        return False, reason, event

    coef_arr, intercept_arr = client_params[0], client_params[1]

    # 2. Array type check
    if not isinstance(coef_arr, np.ndarray) or not isinstance(intercept_arr, np.ndarray):
        reason = "MALFORMED_NUMERIC"
        event = {
            "event_type": "INVALID_FEDERATED_UPDATE",
            "institution_id": institution_id,
            "reason": reason,
            "details": {"error": "Parameters must be numpy ndarrays"}
        }
        return False, reason, event

    # 3. Shape check
    if coef_arr.shape != (expected_num_features,):
        reason = "DIMENSION_MISMATCH"
        event = {
            "event_type": "INVALID_FEDERATED_UPDATE",
            "institution_id": institution_id,
            "reason": reason,
            "details": {"error": f"Expected coef shape ({expected_num_features},), got {coef_arr.shape}"}
        }
        return False, reason, event

    if intercept_arr.shape != (1,) and intercept_arr.shape != ():
        reason = "DIMENSION_MISMATCH"
        event = {
            "event_type": "INVALID_FEDERATED_UPDATE",
            "institution_id": institution_id,
            "reason": reason,
            "details": {"error": f"Expected intercept shape (1,) or (), got {intercept_arr.shape}"}
        }
        return False, reason, event

    # 4. Numeric dtype check
    if not np.issubdtype(coef_arr.dtype, np.number) or not np.issubdtype(intercept_arr.dtype, np.number):
        reason = "NON_NUMERIC_TYPE"
        event = {
            "event_type": "INVALID_FEDERATED_UPDATE",
            "institution_id": institution_id,
            "reason": reason,
            "details": {"error": "Parameter arrays must have numeric dtype"}
        }
        return False, reason, event

    # 5. NaN / Infinity check
    if np.isnan(coef_arr).any() or np.isinf(coef_arr).any() or np.isnan(intercept_arr).any() or np.isinf(intercept_arr).any():
        reason = "NON_FINITE_PARAMETER"
        event = {
            "event_type": "INVALID_FEDERATED_UPDATE",
            "institution_id": institution_id,
            "reason": reason,
            "details": {"error": "NaN or infinite values detected"}
        }
        return False, reason, event

    # 6. Bound check
    if (np.abs(coef_arr) > max_coeff_bound).any():
        reason = "COEFF_BOUND_EXCEEDED"
        event = {
            "event_type": "INVALID_FEDERATED_UPDATE",
            "institution_id": institution_id,
            "reason": reason,
            "details": {"error": f"Coefficients exceeded bound {max_coeff_bound}"}
        }
        return False, reason, event

    # 7. Sample count check
    if not isinstance(num_examples, (int, np.integer)) or num_examples <= 0:
        reason = "INVALID_SAMPLE_COUNT"
        event = {
            "event_type": "INVALID_FEDERATED_UPDATE",
            "institution_id": institution_id,
            "reason": reason,
            "details": {"error": f"Invalid sample count: {num_examples}"}
        }
        return False, reason, event

    return True, None, None


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
    missing node tracking, weighted aggregation, and PostgreSQL metadata logging.
    """

    def __init__(
        self,
        min_fit_clients: int = 4,
        min_available_clients: int = 4,
        max_coeff_bound: float = 100.0,
        expected_institutions: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(
            min_fit_clients=min_fit_clients,
            min_available_clients=min_available_clients,
            **kwargs
        )
        self.min_fit_clients = min_fit_clients
        self.max_coeff_bound = max_coeff_bound
        self.expected_institutions = expected_institutions or ["inst-a", "inst-b", "inst-c", "inst-d"]
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
        successful_insts: List[str] = []
        rejected_insts: List[str] = []

        db = SessionLocal()
        try:
            # Create ORM record for current round
            round_version = f"v1.0.0-fed-r{server_round}"
            fed_round = FederatedRound(
                global_model_version=round_version,
                status="IN_PROGRESS",
                expected_clients=len(self.expected_institutions),
                successful_clients=0,
                failed_clients=0
            )
            db.add(fed_round)
            db.commit()
            db.refresh(fed_round)
            self.current_round_id = fed_round.round_id

            for client_proxy, fit_res in results:
                inst_id = fit_res.metrics.get("institution_id", "unknown_inst")
                participating_insts.append(inst_id)

                client_params = parameters_to_ndarrays(fit_res.parameters)
                
                # Robust validation check
                is_valid, failure_reason, rejection_event = validate_client_update(
                    client_params,
                    fit_res.num_examples,
                    institution_id=inst_id,
                    max_coeff_bound=self.max_coeff_bound
                )

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
                    successful_insts.append(inst_id)
                else:
                    rejected_insts.append(inst_id)

            # Identify missing / offline nodes
            missing_insts = [inst for inst in self.expected_institutions if inst not in participating_insts]
            for missing_id in missing_insts:
                missing_participant = RoundParticipant(
                    round_id=fed_round.round_id,
                    institution_id=missing_id,
                    status="MISSING",
                    update_status=None,
                    failure_reason="NODE_OFFLINE_OR_UNAVAILABLE"
                )
                db.add(missing_participant)

            db.commit()

            # Verify minimum participation threshold
            if len(valid_updates) < self.min_fit_clients:
                fed_round.status = "INCOMPLETE"
                fed_round.successful_clients = len(valid_updates)
                fed_round.failed_clients = len(missing_insts) + len(rejected_insts)
                db.commit()
                return None, {
                    "status": "INCOMPLETE",
                    "expected_nodes": self.expected_institutions,
                    "participating_nodes": participating_insts,
                    "missing_nodes": missing_insts,
                    "rejected_nodes": rejected_insts,
                    "valid_updates": len(valid_updates)
                }

            # Compute weighted FedAvg aggregation
            aggregated_ndarrays = compute_weighted_fedavg(valid_updates)
            self.latest_global_parameters = aggregated_ndarrays

            fed_round.status = "COMPLETED"
            fed_round.successful_clients = len(valid_updates)
            fed_round.failed_clients = len(missing_insts) + len(rejected_insts)
            db.commit()

            # Record ModelVersion in ORM
            model_ver = db.query(ModelVersion).filter(ModelVersion.version == round_version).first()
            if not model_ver:
                db.add(ModelVersion(
                    version=round_version,
                    algorithm="Ridge Regression (FedAvg)",
                    metrics={
                        "expected_nodes": self.expected_institutions,
                        "participating_nodes": participating_insts,
                        "missing_nodes": missing_insts,
                        "rejected_nodes": rejected_insts,
                        "successful_nodes": successful_insts,
                        "successful_updates": len(valid_updates)
                    }
                ))
                db.commit()

            parameters_aggregated = ndarrays_to_parameters(aggregated_ndarrays)
            metrics_aggregated = {
                "round_id": fed_round.round_id,
                "version": round_version,
                "expected_nodes": self.expected_institutions,
                "participating_nodes": participating_insts,
                "missing_nodes": missing_insts,
                "rejected_nodes": rejected_insts,
                "successful_nodes": successful_insts,
                "successful_updates": len(valid_updates),
                "total_samples": sum(n for _, n in valid_updates)
            }

            return parameters_aggregated, metrics_aggregated

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

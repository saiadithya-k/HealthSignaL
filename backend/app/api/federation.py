import os
import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import FederatedRound, ModelVersion
from app.federated.server import run_federated_round

router = APIRouter()

@router.get("/status", tags=["Federation"])
def get_federation_status(db: Session = Depends(get_db)):
    """Returns status of latest federated training rounds and active global model."""
    latest_round = db.query(FederatedRound).order_by(FederatedRound.started_at.desc()).first()
    
    report_path = os.path.join("data", "phase4_federated_report.json")
    alt_report_path = os.path.join("artifacts", "global", "federated_report.json")
    report = None
    if os.path.exists(report_path):
        try:
            with open(report_path, "r") as f:
                report = json.load(f)
        except Exception:
            report = None
    elif os.path.exists(alt_report_path):
        try:
            with open(alt_report_path, "r") as f:
                report = json.load(f)
        except Exception:
            report = None

    status_str = latest_round.status if latest_round else (report.get("status", "NOT_STARTED") if report else "NOT_STARTED")
    round_dict = {
        "round_id": latest_round.round_id if latest_round else (str(report.get("round_id", 1)) if report else None),
        "version": latest_round.global_model_version if latest_round else (report.get("model_version", "v1.0.0-fed-r1") if report else None),
        "expected_clients": 4,
        "successful_clients": latest_round.successful_clients if latest_round else (len(report.get("successful_nodes", [])) if report else 0),
        "failed_clients": latest_round.failed_clients if latest_round else (len(report.get("rejected_nodes", [])) if report else 0),
    } if (latest_round or report) else None

    return {
        "status": status_str,
        "latest_round": round_dict,
        "federated_report": report
    }

@router.post("/start", tags=["Federation"])
def start_federated_round(
    forecast_horizon: int = Query(7, ge=1, le=14),
    alpha: float = Query(1.0, gt=0.0),
    db: Session = Depends(get_db)
):
    """
    Triggers execution of a 4-client Flower federated training round (Institutions A, B, C, D),
    validates outbound updates via PrivacyGate, aggregates via FedAvg, and saves global model version.
    """
    try:
        report = run_federated_round(data_dir="data", forecast_horizon=forecast_horizon, alpha=alpha)
        
        # Update PostgreSQL model registry
        version_str = f"v1.0.0-fed-h{forecast_horizon}"
        existing = db.query(ModelVersion).filter(ModelVersion.version == version_str).first()
        if not existing:
            db.add(ModelVersion(
                version=version_str,
                algorithm="Ridge Regression (FedAvg)",
                metrics=report["global_model_metrics"]["overall"]
            ))
        else:
            existing.metrics = report["global_model_metrics"]["overall"]

        # Also persist round in DB
        db.add(FederatedRound(
            global_model_version=report.get("model_version", version_str),
            status="COMPLETED",
            expected_clients=len(report.get("expected_nodes", [])),
            successful_clients=len(report.get("successful_nodes", [])),
            failed_clients=len(report.get("rejected_nodes", []))
        ))
            
        db.commit()

        return {
            "status": "success",
            "message": f"Successfully executed 4-client Flower federated training round (horizon={forecast_horizon})",
            "report": report
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

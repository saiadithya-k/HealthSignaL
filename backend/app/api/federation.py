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
    report = None
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            report = json.load(f)

    return {
        "status": latest_round.status if latest_round else "NOT_STARTED",
        "latest_round": {
            "round_id": latest_round.round_id if latest_round else None,
            "version": latest_round.global_model_version if latest_round else None,
            "expected_clients": 4,
            "successful_clients": latest_round.successful_clients if latest_round else 0,
            "failed_clients": latest_round.failed_clients if latest_round else 0,
        } if latest_round else None,
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
            
        db.commit()

        return {
            "status": "success",
            "message": f"Successfully executed 4-client Flower federated training round (horizon={forecast_horizon})",
            "report": report
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

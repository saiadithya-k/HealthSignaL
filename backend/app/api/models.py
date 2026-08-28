import os
import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ModelVersion
from app.ml.harness import BaselineComparisonHarness
from app.ml.model import LocalForecastModel

router = APIRouter()

@router.get("/baselines", tags=["Models"])
def get_baseline_comparison():
    """
    Returns Phase 3 baseline comparison metrics across:
    1. Baseline A — Local-Only Ridge
    2. Baseline B — Pooled Ridge Upper Bound (Evaluation-Only)
    3. Baseline C — Naive Seasonal Baseline (lag_7)
    """
    report_path = os.path.join("data", "phase3_evaluation_report.json")
    if not os.path.exists(report_path):
        # Run evaluation if report doesn't exist yet
        harness = BaselineComparisonHarness(data_dir="data")
        return harness.run_full_baseline_evaluation()

    with open(report_path, "r") as f:
        return json.load(f)

@router.get("/local/{institution_id}", tags=["Models"])
def get_local_model_status(institution_id: str):
    """Returns local model status, features, and metadata for a specific institution node."""
    if institution_id not in ["inst-a", "inst-b", "inst-c", "inst-d"]:
        raise HTTPException(status_code=400, detail=f"Invalid institution_id: {institution_id}")

    try:
        model = LocalForecastModel.load_model(institution_id=institution_id)
        return {
            "status": "trained",
            "metadata": model.training_metadata
        }
    except FileNotFoundError:
        return {
            "status": "not_trained",
            "institution_id": institution_id,
            "message": "Local model artifact not found. Trigger POST /api/v1/models/train-local first."
        }

@router.post("/train-local", tags=["Models"])
def train_and_evaluate_baselines(
    forecast_horizon: int = Query(7, ge=1, le=14),
    alpha: float = Query(1.0, gt=0.0),
    db: Session = Depends(get_db)
):
    """
    Triggers local training for all 4 institutions (Ridge), trains pooled baseline,
    and updates the central PostgreSQL model_versions registry with safe aggregate metrics.
    """
    try:
        harness = BaselineComparisonHarness(data_dir="data", forecast_horizon=forecast_horizon, alpha=alpha)
        report = harness.run_full_baseline_evaluation()

        # Record metrics in PostgreSQL model_versions table
        model_record = db.query(ModelVersion).filter(ModelVersion.version == "v1.0.0").first()
        if not model_record:
            model_record = ModelVersion(
                version="v1.0.0",
                algorithm="Ridge Regression (Baseline Harness)",
                metrics=report["comparison_matrix"]
            )
            db.add(model_record)
        else:
            model_record.metrics = report["comparison_matrix"]

        db.commit()

        return {
            "status": "success",
            "message": f"Successfully trained local models & evaluated baselines (horizon={forecast_horizon}, alpha={alpha})",
            "report": report
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

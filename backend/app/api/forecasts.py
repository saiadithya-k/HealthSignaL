import os
import json
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Forecast
from app.ml.forecasting import load_global_model, generate_multiday_forecast, validate_forecast_horizon
from app.core.local_node import LocalInstitutionClient

router = APIRouter()

@router.get("", tags=["Forecasts"])
def get_stored_forecasts(
    institution_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Returns stored 7–14 day forecasts from database."""
    query = db.query(Forecast)
    if institution_id:
        query = query.filter(Forecast.institution_id == institution_id)

    forecast_records = query.order_by(Forecast.forecast_date.asc(), Forecast.horizon_day.asc()).all()

    report_path = os.path.join("data", "phase5_forecast_report.json")
    report = None
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            report = json.load(f)

    return {
        "total_records": len(forecast_records),
        "report": report,
        "forecasts": [
            {
                "id": f.id,
                "model_version": f.model_version,
                "institution_id": f.institution_id,
                "syndrome_category": f.syndrome_category,
                "forecast_date": f.forecast_date.strftime("%Y-%m-%d"),
                "horizon_day": f.horizon_day,
                "predicted_value": f.point_forecast,
                "lower_bound_80": f.lower_bound_80 or f.lower_bound,
                "upper_bound_80": f.upper_bound_80 or f.upper_bound,
                "lower_bound_95": f.lower_bound_95 or f.lower_bound,
                "upper_bound_95": f.upper_bound_95 or f.upper_bound,
                "confidence_score": f.confidence_score,
                "coverage_ratio": f.coverage_ratio,
                "missing_node_count": f.missing_node_count,
                "generated_at": f.generated_at.strftime("%Y-%m-%d %H:%M:%S")
            } for f in forecast_records
        ]
    }

@router.post("/generate", tags=["Forecasts"])
def generate_forecast_endpoint(
    horizon: int = Query(7, ge=7, le=14),
    missing_nodes: int = Query(0, ge=0, le=3),
    db: Session = Depends(get_db)
):
    """
    Generates a 7–14 day aggregate demand forecast using the global FedAvg model.
    Calculates residual-based uncertainty prediction intervals (80% & 95%) and confidence scores.
    """
    try:
        horizon = validate_forecast_horizon(horizon)
        global_model = load_global_model()

        # Load aggregate history across active nodes
        dfs = []
        for inst_id in ["inst-a", "inst-b", "inst-c", "inst-d"]:
            client = LocalInstitutionClient(inst_id, data_dir="data")
            df, _ = client.load_local_data()
            dfs.append(df)

        combined_df = pd.concat(dfs, ignore_index=True)
        # Group to regional aggregate service count per date and category
        agg_df = combined_df.groupby(["date", "syndrome_category"])["service_count"].sum().reset_index()
        agg_df["data_completeness"] = 1.0

        forecast_report = generate_multiday_forecast(
            history_df=agg_df,
            model=global_model,
            horizon=horizon,
            missing_node_count=missing_nodes,
            data_dir="data"
        )

        # Clear existing forecasts and persist new forecast records to DB
        db.query(Forecast).delete()
        for f in forecast_report["forecasts"]:
            db.add(Forecast(
                model_version=f["model_version"],
                institution_id=None,  # Regional aggregate
                syndrome_category=f["syndrome_category"],
                forecast_date=datetime.strptime(f["forecast_date"], "%Y-%m-%d"),
                horizon_day=f["horizon_day"],
                point_forecast=f["predicted_value"],
                lower_bound=f["lower_bound_80"],
                upper_bound=f["upper_bound_80"],
                lower_bound_80=f["lower_bound_80"],
                upper_bound_80=f["upper_bound_80"],
                lower_bound_95=f["lower_bound_95"],
                upper_bound_95=f["upper_bound_95"],
                confidence_score=f["confidence_score"],
                coverage_ratio=f["coverage_ratio"],
                missing_node_count=f["missing_node_count"],
                uncertainty_score=f["uncertainty_score"]
            ))

        db.commit()

        # Save Phase 5 Evaluation Report
        report_path = os.path.join("data", "phase5_forecast_report.json")
        with open(report_path, "w") as f:
            json.dump(forecast_report, f, indent=2)

        return {
            "status": "success",
            "message": f"Successfully generated {horizon}-day forecast with prediction intervals",
            "report": forecast_report
        }

    except FileNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

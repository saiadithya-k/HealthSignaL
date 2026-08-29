import os
import json
import uuid
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timezone
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
    syndrome_category: Optional[str] = Query(None),
    horizon_days: Optional[int] = Query(None),
    horizon: Optional[int] = Query(None),
    missing_nodes: Optional[int] = Query(None),
    request_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Returns stored 7–14 day forecasts from database or dynamically generates them if parameters are requested."""
    target_horizon = horizon_days or horizon
    if target_horizon is not None or missing_nodes is not None:
        h = target_horizon or 7
        m = missing_nodes or 0
        gen_res = generate_forecast_endpoint(
            horizon=h,
            horizon_days=h,
            missing_nodes=m,
            request_id=request_id,
            db=db
        )
        forecasts = gen_res.get("forecasts", [])
        if syndrome_category:
            forecasts = [f for f in forecasts if f.get("syndrome_category") == syndrome_category]
        return {
            "total_records": len(forecasts),
            "request_id": gen_res.get("request_id", request_id or str(uuid.uuid4())),
            "generated_at": gen_res.get("generated_at", datetime.now(timezone.utc).isoformat()),
            "horizon_days": h,
            "missing_nodes": m,
            "participating_nodes": gen_res.get("participating_nodes", ["inst-a", "inst-b", "inst-c", "inst-d"]),
            "participating_nodes_count": gen_res.get("participating_nodes_count", 4),
            "confidence_mode": gen_res.get("confidence_mode", "normal"),
            "report": gen_res,
            "forecasts": forecasts
        }

    query = db.query(Forecast)
    if institution_id:
        query = query.filter(Forecast.institution_id == institution_id)
    if syndrome_category:
        query = query.filter(Forecast.syndrome_category == syndrome_category)

    forecast_records = query.order_by(Forecast.forecast_date.asc(), Forecast.horizon_day.asc()).all()

    report_path = os.path.join("data", "phase5_forecast_report.json")
    report = None
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            report = json.load(f)

    # Format forecast list
    forecast_list = [
        {
            "id": f.id,
            "model_version": f.model_version,
            "institution_id": f.institution_id,
            "syndrome_category": f.syndrome_category,
            "forecast_date": f.forecast_date.strftime("%Y-%m-%d"),
            "horizon_day": f.horizon_day,
            "point_forecast": f.point_forecast,
            "predicted_value": f.point_forecast,
            "lower_bound_80": f.lower_bound_80 if f.lower_bound_80 is not None else f.lower_bound,
            "upper_bound_80": f.upper_bound_80 if f.upper_bound_80 is not None else f.upper_bound,
            "lower_bound_95": f.lower_bound_95 if f.lower_bound_95 is not None else f.lower_bound,
            "upper_bound_95": f.upper_bound_95 if f.upper_bound_95 is not None else f.upper_bound,
            "confidence_score": f.confidence_score,
            "coverage_ratio": f.coverage_ratio,
            "missing_node_count": f.missing_node_count,
            "status": "VALID" if f.point_forecast > 0 else "INSUFFICIENT_HISTORY",
            "status_message": "Forecast generated successfully" if f.point_forecast > 0 else "Insufficient historical data",
            "generated_at": f.generated_at.strftime("%Y-%m-%d %H:%M:%S")
        } for f in forecast_records
    ]

    # If DB is empty but report exists in file, populate from report
    if not forecast_list and report and "forecasts" in report:
        forecast_list = [
            {
                **fc,
                "point_forecast": fc.get("point_forecast", fc.get("predicted_value", 0.0)),
                "predicted_value": fc.get("predicted_value", fc.get("point_forecast", 0.0))
            } for fc in report["forecasts"]
            if not syndrome_category or fc.get("syndrome_category") == syndrome_category
        ]

    max_h = max([f.get("horizon_day", 7) for f in forecast_list], default=7)
    m_count = forecast_list[0].get("missing_node_count", 0) if forecast_list else 0

    return {
        "total_records": len(forecast_list),
        "request_id": request_id or str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "horizon_days": max_h,
        "missing_nodes": m_count,
        "participating_nodes": ["inst-a", "inst-b", "inst-c", "inst-d"][:max(1, 4 - m_count)],
        "participating_nodes_count": max(1, 4 - m_count),
        "confidence_mode": "degraded" if m_count > 0 else "normal",
        "report": report,
        "forecasts": forecast_list
    }

@router.get("/generate", tags=["Forecasts"])
@router.post("/generate", tags=["Forecasts"])
def generate_forecast_endpoint(
    horizon: int = Query(7, ge=1, le=14),
    horizon_days: Optional[int] = Query(None),
    missing_nodes: int = Query(0, ge=0, le=3),
    request_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Generates a 7–14 day aggregate demand forecast using the global FedAvg model.
    Calculates residual-based uncertainty prediction intervals (80% & 95%) and confidence scores.
    """
    try:
        if isinstance(horizon_days, int):
            eff_horizon = horizon_days
        elif isinstance(horizon, int):
            eff_horizon = horizon
        else:
            eff_horizon = 7
        eff_horizon = validate_forecast_horizon(eff_horizon)

        m_nodes = missing_nodes if isinstance(missing_nodes, int) else 0

        # Deterministic node participation
        all_nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
        if m_nodes == 0:
            participating_nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
        elif m_nodes == 1:
            participating_nodes = ["inst-a", "inst-b", "inst-c"] # inst-d offline
        elif m_nodes == 2:
            participating_nodes = ["inst-a", "inst-b"]           # inst-c, inst-d offline
        else:
            participating_nodes = ["inst-a"]

        # Always run FedAvg model for exact participating nodes to prevent stale model state
        from app.federated.server import run_federated_round
        run_federated_round(
            data_dir="data",
            available_nodes=participating_nodes,
            forecast_horizon=eff_horizon,
            min_valid_clients=len(participating_nodes)
        )
        active_model = load_global_model()

        # Load aggregate history across participating nodes only
        dfs = []
        for inst_id in participating_nodes:
            client = LocalInstitutionClient(inst_id, data_dir="data")
            df, _ = client.load_local_data()
            dfs.append(df)

        combined_df = pd.concat(dfs, ignore_index=True)
        agg_df = combined_df.groupby(["date", "syndrome_category"])["service_count"].sum().reset_index()
        agg_df["data_completeness"] = 1.0

        forecast_report = generate_multiday_forecast(
            history_df=agg_df,
            model=active_model,
            horizon=eff_horizon,
            missing_node_count=missing_nodes,
            data_dir="data"
        )
        forecast_report["participating_nodes"] = participating_nodes
        forecast_report["participating_nodes_count"] = len(participating_nodes)
        forecast_report["confidence_mode"] = "degraded" if missing_nodes > 0 else "normal"

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
            "request_id": request_id or str(uuid.uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "message": f"Successfully generated {eff_horizon}-day forecast with prediction intervals",
            "horizon_days": eff_horizon,
            "missing_nodes": missing_nodes,
            "participating_nodes": participating_nodes,
            "participating_nodes_count": len(participating_nodes),
            "confidence_mode": "degraded" if missing_nodes > 0 else "normal",
            "report": forecast_report,
            "forecasts": forecast_report["forecasts"]
        }

    except FileNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Alert, ReviewerDecision
from app.ml.anomaly import CUSUMDetector
from app.ml.forecasting import load_global_model, generate_multiday_forecast, compute_validation_residuals
from app.core.local_node import LocalInstitutionClient

router = APIRouter()

@router.get("", tags=["Alerts"])
def get_alerts_queue(
    status: Optional[str] = Query(None, description="Filter by status: CANDIDATE, APPROVED, REJECTED"),
    db: Session = Depends(get_db)
):
    """Returns alert candidates / reviewer queue for public health analysts."""
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status.upper())

    alerts = query.order_by(Alert.detected_at.desc()).all()

    report_path = os.path.join("data", "phase6_anomaly_report.json")
    report = None
    if os.path.exists(report_path):
        with open(report_path, "r") as f:
            report = json.load(f)

    return {
        "total_alerts": len(alerts),
        "candidate_count": sum(1 for a in alerts if a.status == "CANDIDATE"),
        "approved_count": sum(1 for a in alerts if a.status == "APPROVED"),
        "rejected_count": sum(1 for a in alerts if a.status == "REJECTED"),
        "report": report,
        "alerts": [
            {
                "id": a.id,
                "institution_scope": a.institution_scope,
                "syndrome_category": a.syndrome_category,
                "detected_at": a.detected_at.strftime("%Y-%m-%d %H:%M:%S"),
                "shift_score": a.shift_score,
                "status": a.status,
                "evidence_data": a.evidence_data,
                "forecast_reference": a.forecast_reference
            } for a in alerts
        ]
    }

@router.get("/{alert_id}", tags=["Alerts"])
def get_alert_detail(alert_id: str, db: Session = Depends(get_db)):
    """Returns detailed alert metadata and reviewer decisions history."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    decisions = db.query(ReviewerDecision).filter(ReviewerDecision.alert_id == alert_id).all()

    return {
        "id": alert.id,
        "institution_scope": alert.institution_scope,
        "syndrome_category": alert.syndrome_category,
        "detected_at": alert.detected_at.strftime("%Y-%m-%d %H:%M:%S"),
        "shift_score": alert.shift_score,
        "status": alert.status,
        "evidence_data": alert.evidence_data,
        "forecast_reference": alert.forecast_reference,
        "decisions": [
            {
                "id": d.id,
                "reviewer_id": d.reviewer_id,
                "decision": d.decision,
                "reason": d.reason,
                "created_at": d.created_at.strftime("%Y-%m-%d %H:%M:%S")
            } for d in decisions
        ]
    }

@router.post("/{alert_id}/approve", tags=["Alerts"])
def approve_alert(
    alert_id: str,
    reviewer_id: str = Query("public_health_analyst"),
    reason: Optional[str] = Query("Approved after statistical and clinical verification"),
    db: Session = Depends(get_db)
):
    """Transitions alert status from CANDIDATE -> APPROVED. Rejects repeated operations."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    if alert.status == "APPROVED":
        raise HTTPException(status_code=400, detail=f"Alert '{alert_id}' is already APPROVED")

    if alert.status == "REJECTED":
        raise HTTPException(status_code=400, detail=f"Cannot approve alert '{alert_id}' because it has already been REJECTED")

    alert.status = "APPROVED"
    decision_record = ReviewerDecision(
        alert_id=alert.id,
        reviewer_id=reviewer_id,
        decision="APPROVED",
        reason=reason
    )
    db.add(decision_record)
    db.commit()

    return {
        "status": "success",
        "message": f"Alert '{alert_id}' successfully APPROVED",
        "alert_id": alert.id,
        "new_status": alert.status
    }

@router.post("/{alert_id}/reject", tags=["Alerts"])
def reject_alert(
    alert_id: str,
    reviewer_id: str = Query("public_health_analyst"),
    reason: Optional[str] = Query("Rejected: false positive due to data reporting noise"),
    db: Session = Depends(get_db)
):
    """Transitions alert status from CANDIDATE -> REJECTED. Rejects repeated operations."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")

    if alert.status == "REJECTED":
        raise HTTPException(status_code=400, detail=f"Alert '{alert_id}' is already REJECTED")

    if alert.status == "APPROVED":
        raise HTTPException(status_code=400, detail=f"Cannot reject alert '{alert_id}' because it has already been APPROVED")

    alert.status = "REJECTED"
    decision_record = ReviewerDecision(
        alert_id=alert.id,
        reviewer_id=reviewer_id,
        decision="REJECTED",
        reason=reason
    )
    db.add(decision_record)
    db.commit()

    return {
        "status": "success",
        "message": f"Alert '{alert_id}' successfully REJECTED",
        "alert_id": alert.id,
        "new_status": alert.status
    }

@router.post("/detect", tags=["Alerts"])
def trigger_anomaly_detection(
    drift_k: float = Query(0.5, ge=0.0),
    threshold_h: float = Query(4.0, gt=0.0),
    missing_nodes: int = Query(0, ge=0, le=3),
    db: Session = Depends(get_db)
):
    """
    Executes Phase 6 CUSUM anomaly detection comparing forecast vs observed signals.
    Generates CANDIDATE alerts for qualifying threshold crossings without auto-approving.
    """
    try:
        global_model = load_global_model()
        detector = CUSUMDetector(drift_k=drift_k, threshold_h=threshold_h)
        sigma, _ = compute_validation_residuals(global_model, data_dir="data")

        # Load aggregate historical data
        dfs = []
        for inst_id in ["inst-a", "inst-b", "inst-c", "inst-d"]:
            client = LocalInstitutionClient(inst_id, data_dir="data")
            df, _ = client.load_local_data()
            dfs.append(df)

        combined_df = pd.concat(dfs, ignore_index=True)
        agg_df = combined_df.groupby(["date", "syndrome_category"])["service_count"].sum().reset_index()
        agg_df["data_completeness"] = 1.0
        agg_df["date"] = pd.to_datetime(agg_df["date"])
        agg_df.sort_values(by="date", inplace=True)

        unique_dates = sorted(agg_df["date"].unique())
        if len(unique_dates) < 28:
            raise HTTPException(status_code=400, detail="Insufficient history for anomaly detection (minimum 28 days required)")

        cutoff_date = unique_dates[-14]
        history_df = agg_df[agg_df["date"] < cutoff_date].copy()
        eval_df = agg_df[agg_df["date"] >= cutoff_date].copy()

        # Generate 14-day forecast using history prior to cutoff
        fcst_res = generate_multiday_forecast(
            history_df=history_df,
            model=global_model,
            horizon=14,
            missing_node_count=missing_nodes,
            data_dir="data"
        )

        expected_by_cat: Dict[str, List[float]] = {}
        dates_by_cat: Dict[str, List[str]] = {}
        for f in fcst_res["forecasts"]:
            cat = f["syndrome_category"]
            if cat not in expected_by_cat:
                expected_by_cat[cat] = []
                dates_by_cat[cat] = []
            expected_by_cat[cat].append(f["predicted_value"])
            dates_by_cat[cat].append(f["forecast_date"])

        all_created_alerts = []

        for cat in expected_by_cat:
            cat_obs_df = eval_df[eval_df["syndrome_category"] == cat].sort_values(by="date")
            obs_vals = cat_obs_df["service_count"].values
            exp_vals = np.array(expected_by_cat[cat][:len(obs_vals)])

            if len(obs_vals) == len(exp_vals) and len(obs_vals) > 0:
                res = detector.detect_series(
                    observed_series=obs_vals,
                    expected_series=exp_vals,
                    sigma=sigma,
                    dates=dates_by_cat[cat][:len(obs_vals)],
                    syndrome_category=cat,
                    confidence_score=fcst_res["confidence_score"],
                    coverage_ratio=fcst_res["coverage_ratio"],
                    missing_node_count=missing_nodes,
                    model_version=fcst_res["model_version"]
                )

                for cand in res["candidate_alerts"]:
                    alert = Alert(
                        institution_scope="REGIONAL",
                        syndrome_category=cand["syndrome_category"],
                        detected_at=datetime.utcnow(),
                        shift_score=cand["cusum_statistic"],
                        status="CANDIDATE",
                        evidence_data={
                            "forecast_date": cand["forecast_date"],
                            "observed_value": cand["observed_value"],
                            "expected_value": cand["expected_value"],
                            "residual": cand["residual"],
                            "cusum_statistic": cand["cusum_statistic"],
                            "threshold": cand["threshold"],
                            "confidence_score": cand["confidence_score"],
                            "coverage_ratio": cand["coverage_ratio"],
                            "missing_node_count": cand["missing_node_count"],
                            "model_version": cand["model_version"]
                        },
                        forecast_reference=cand["model_version"]
                    )
                    db.add(alert)
                    all_created_alerts.append(alert)

        db.commit()

        candidates_count = db.query(Alert).filter(Alert.status == "CANDIDATE").count()
        approved_count = db.query(Alert).filter(Alert.status == "APPROVED").count()
        rejected_count = db.query(Alert).filter(Alert.status == "REJECTED").count()

        anomaly_report = {
            "detector_config": {
                "drift_k": drift_k,
                "threshold_h": threshold_h,
                "residual_sigma": round(sigma, 4)
            },
            "new_candidates_generated": len(all_created_alerts),
            "total_candidates": candidates_count,
            "total_approved": approved_count,
            "total_rejected": rejected_count,
            "confidence_score": fcst_res["confidence_score"],
            "coverage_ratio": fcst_res["coverage_ratio"],
            "missing_node_count": missing_nodes,
            "model_version": fcst_res["model_version"]
        }

        report_path = os.path.join("data", "phase6_anomaly_report.json")
        with open(report_path, "w") as f:
            json.dump(anomaly_report, f, indent=2)

        return {
            "status": "success",
            "message": f"Successfully executed CUSUM surge detection. Generated {len(all_created_alerts)} candidate alerts.",
            "report": anomaly_report
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

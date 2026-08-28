import os
import pytest
import numpy as np
from datetime import datetime

from app.ml.anomaly import CUSUMDetector
from app.db.database import SessionLocal
from app.db.models import Alert, ReviewerDecision
from app.core.privacy_gate import PrivacyGate

def test_cusum_initialization():
    """Asserts valid CUSUMDetector initialization and rejection of invalid parameters."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=4.0)
    assert det.drift_k == 0.5
    assert det.threshold_h == 4.0

    with pytest.raises(ValueError):
        CUSUMDetector(drift_k=-1.0, threshold_h=4.0)
    with pytest.raises(ValueError):
        CUSUMDetector(drift_k=0.5, threshold_h=0.0)

def test_normal_no_surge_signal():
    """Asserts that normal baseline noise signal produces 0 candidate alerts."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=4.0)
    np.random.seed(42)
    obs = np.random.normal(loc=50.0, scale=2.0, size=14)
    exp = np.full(14, 50.0)

    res = det.detect_series(obs, exp, sigma=2.0)
    assert res["total_candidates"] == 0

def test_synthetic_upward_surge_detection():
    """Asserts that a sudden upward surge triggers anomaly detection."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=4.0)
    exp = np.full(10, 50.0)
    obs = np.array([50.0, 51.0, 50.0, 52.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0])

    res = det.detect_series(obs, exp, sigma=2.0)
    assert res["total_candidates"] > 0
    assert any(c["is_anomaly"] for c in res["cusum_history"])

def test_threshold_crossing():
    """Asserts that CUSUM statistic > threshold_h sets is_anomaly=True."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=3.0)
    curr_cusum, z_score, is_anomaly = det.detect_step(observed=70.0, expected=50.0, prev_cusum=2.0, sigma=2.0)
    
    assert curr_cusum > 3.0
    assert is_anomaly is True

def test_no_future_data_leakage():
    """Asserts that CUSUM calculation at step t depends strictly on history up to t."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=4.0)
    obs1 = np.array([50.0, 60.0, 70.0])
    obs2 = np.array([50.0, 60.0, 100.0])
    exp = np.array([50.0, 50.0, 50.0])

    res1 = det.detect_series(obs1, exp, sigma=2.0)
    res2 = det.detect_series(obs2, exp, sigma=2.0)

    # Step 1 and Step 2 CUSUM statistics must be identical
    assert res1["cusum_history"][0]["cusum_statistic"] == res2["cusum_history"][0]["cusum_statistic"]
    assert res1["cusum_history"][1]["cusum_statistic"] == res2["cusum_history"][1]["cusum_statistic"]

def test_deterministic_detection():
    """Asserts that running CUSUM twice on identical inputs produces identical results."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=4.0)
    obs = np.array([50.0, 52.0, 65.0, 75.0])
    exp = np.array([50.0, 50.0, 50.0, 50.0])

    r1 = det.detect_series(obs, exp, sigma=2.0)
    r2 = det.detect_series(obs, exp, sigma=2.0)

    assert r1 == r2

def test_insufficient_history_handling():
    """Asserts empty series input raises ValueError safely."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=4.0)
    with pytest.raises(ValueError):
        det.detect_series(np.array([]), np.array([]), sigma=1.0)

def test_candidate_alert_creation():
    """Asserts Alert ORM record creation with status=CANDIDATE."""
    db = SessionLocal()
    try:
        alert = Alert(
            institution_scope="REGIONAL",
            syndrome_category="respiratory",
            shift_score=5.2,
            status="CANDIDATE",
            evidence_data={"observed": 75.0, "expected": 50.0}
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        assert alert.id is not None
        assert alert.status == "CANDIDATE"
    finally:
        db.close()

def test_candidate_to_approved_transition():
    """Asserts CANDIDATE -> APPROVED status transition."""
    db = SessionLocal()
    try:
        alert = Alert(
            institution_scope="REGIONAL",
            syndrome_category="respiratory",
            shift_score=5.5,
            status="CANDIDATE"
        )
        db.add(alert)
        db.commit()

        alert.status = "APPROVED"
        db.commit()

        fetched = db.query(Alert).filter(Alert.id == alert.id).first()
        assert fetched.status == "APPROVED"
    finally:
        db.close()

def test_candidate_to_rejected_transition():
    """Asserts CANDIDATE -> REJECTED status transition."""
    db = SessionLocal()
    try:
        alert = Alert(
            institution_scope="REGIONAL",
            syndrome_category="respiratory",
            shift_score=4.8,
            status="CANDIDATE"
        )
        db.add(alert)
        db.commit()

        alert.status = "REJECTED"
        db.commit()

        fetched = db.query(Alert).filter(Alert.id == alert.id).first()
        assert fetched.status == "REJECTED"
    finally:
        db.close()

def test_invalid_repeated_approval_rejection():
    """Asserts repeated approval or rejection on resolved alerts fails via API."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    db = SessionLocal()
    try:
        alert = Alert(
            institution_scope="REGIONAL",
            syndrome_category="fever_flu",
            shift_score=6.0,
            status="CANDIDATE"
        )
        db.add(alert)
        db.commit()
        alert_id = alert.id

        # First approval -> 200
        r1 = client.post(f"/api/v1/alerts/{alert_id}/approve")
        assert r1.status_code == 200

        # Second approval -> 400
        r2 = client.post(f"/api/v1/alerts/{alert_id}/approve")
        assert r2.status_code == 400

        # Rejecting APPROVED alert -> 400
        r3 = client.post(f"/api/v1/alerts/{alert_id}/reject")
        assert r3.status_code == 400
    finally:
        db.close()

def test_reviewer_decision_persistence():
    """Asserts ReviewerDecision record is created and linked to Alert."""
    db = SessionLocal()
    try:
        alert = Alert(
            institution_scope="REGIONAL",
            syndrome_category="respiratory",
            shift_score=5.1,
            status="CANDIDATE"
        )
        db.add(alert)
        db.commit()

        decision = ReviewerDecision(
            alert_id=alert.id,
            reviewer_id="analyst_1",
            decision="APPROVED",
            reason="Confirmed by local hospital surge reporting"
        )
        db.add(decision)
        db.commit()

        fetched_dec = db.query(ReviewerDecision).filter(ReviewerDecision.alert_id == alert.id).first()
        assert fetched_dec is not None
        assert fetched_dec.decision == "APPROVED"
        assert fetched_dec.reviewer_id == "analyst_1"
    finally:
        db.close()

def test_missing_node_confidence_integration():
    """Asserts candidate alert evidence retains coverage_ratio and missing_node_count."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=3.0)
    obs = np.array([50.0, 75.0])
    exp = np.array([50.0, 50.0])

    res = det.detect_series(
        obs, exp, sigma=2.0,
        confidence_score=0.70,
        coverage_ratio=0.50,
        missing_node_count=2
    )

    cand = res["candidate_alerts"][0]
    assert cand["coverage_ratio"] == 0.50
    assert cand["missing_node_count"] == 2
    assert cand["confidence_score"] == 0.70

def test_raw_data_non_exposure():
    """Asserts alert evidence contains aggregate values only and zero raw patient fields."""
    det = CUSUMDetector(drift_k=0.5, threshold_h=3.0)
    obs = np.array([50.0, 80.0])
    exp = np.array([50.0, 50.0])

    res = det.detect_series(obs, exp, sigma=2.0)
    for cand in res["candidate_alerts"]:
        assert "patient_id" not in cand
        assert "raw_records" not in cand
        assert "ssn" not in cand
        assert "observed_value" in cand

def test_api_get_alerts_queue():
    """Asserts GET /api/v1/alerts returns alert queue and counts."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_alerts" in data
    assert "candidate_count" in data
    assert "alerts" in data

def test_api_approve_endpoint():
    """Asserts POST /api/v1/alerts/{id}/approve updates status to APPROVED."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    db = SessionLocal()
    try:
        alert = Alert(
            institution_scope="REGIONAL",
            syndrome_category="respiratory",
            shift_score=5.8,
            status="CANDIDATE"
        )
        db.add(alert)
        db.commit()

        resp = client.post(f"/api/v1/alerts/{alert.id}/approve?reviewer_id=test_user")
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "APPROVED"
    finally:
        db.close()

def test_api_reject_endpoint():
    """Asserts POST /api/v1/alerts/{id}/reject updates status to REJECTED."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    db = SessionLocal()
    try:
        alert = Alert(
            institution_scope="REGIONAL",
            syndrome_category="respiratory",
            shift_score=4.9,
            status="CANDIDATE"
        )
        db.add(alert)
        db.commit()

        resp = client.post(f"/api/v1/alerts/{alert.id}/reject?reviewer_id=test_user")
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_status"] == "REJECTED"
    finally:
        db.close()

def test_full_anomaly_to_review_workflow():
    """Asserts full end-to-end anomaly detection -> CANDIDATE -> Reviewer APPROVE workflow."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 1. Trigger Anomaly Detection
    det_resp = client.post("/api/v1/alerts/detect?drift_k=0.5&threshold_h=3.0")
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    assert det_data["status"] == "success"

    # 2. Get Alerts Queue
    queue_resp = client.get("/api/v1/alerts?status=CANDIDATE")
    assert queue_resp.status_code == 200
    queue_data = queue_resp.json()
    
    if queue_data["total_alerts"] > 0:
        target_id = queue_data["alerts"][0]["id"]
        
        # 3. Approve candidate alert
        app_resp = client.post(f"/api/v1/alerts/{target_id}/approve")
        assert app_resp.status_code == 200
        assert app_resp.json()["new_status"] == "APPROVED"

        # 4. Detail endpoint confirms ReviewerDecision record
        detail_resp = client.get(f"/api/v1/alerts/{target_id}")
        assert detail_resp.status_code == 200
        assert len(detail_resp.json()["decisions"]) > 0

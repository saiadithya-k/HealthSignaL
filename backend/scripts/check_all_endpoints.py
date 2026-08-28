import sys
import os
import json
from fastapi.testclient import TestClient

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)

def run_endpoint_checks():
    results = []
    
    def check(method, path, name, **kwargs):
        try:
            if method.upper() == "GET":
                resp = client.get(path, **kwargs)
            elif method.upper() == "POST":
                resp = client.post(path, **kwargs)
            elif method.upper() == "PUT":
                resp = client.put(path, **kwargs)
            
            is_ok = 200 <= resp.status_code < 300
            
            # Extract sample preview
            try:
                data = resp.json()
                preview = f"Keys: {list(data.keys())[:5]}" if isinstance(data, dict) else f"Items: {len(data)}"
            except Exception:
                preview = resp.text[:40]

            results.append({
                "name": name,
                "method": method.upper(),
                "path": path,
                "status_code": resp.status_code,
                "passed": is_ok,
                "preview": preview
            })
            return resp
        except Exception as e:
            results.append({
                "name": name,
                "method": method.upper(),
                "path": path,
                "status_code": 500,
                "passed": False,
                "preview": str(e)
            })
            return None

    print("\n--- Checking all HealthSignal API Endpoints (including P1/P2 Streams) ---\n")

    # 1. Health & Root
    check("GET", "/", "Root Welcome")
    check("GET", "/api/v1/health", "System Health Check")
    check("GET", "/api/v1/version", "System Version Info")

    # 2. Institutions
    check("GET", "/api/v1/institutions/status", "List Institutions Status")
    check("GET", "/api/v1/institutions/non-iid-summary", "Non-IID Proof Summary")
    check("POST", "/api/v1/institutions/generate-data?scenario=NORMAL&seed=42&days=365", "Synthetic Data Generation Trigger")

    # 3. Baseline Models
    check("GET", "/api/v1/models/baselines", "3-Way Baseline Evaluation Comparison")
    check("POST", "/api/v1/models/train-local", "Train Local Isolated Ridge Models")

    # 4. Federated Training
    check("GET", "/api/v1/federation/status", "Federation Status & Global Weights")
    check("POST", "/api/v1/federation/start?forecast_horizon=7&alpha=1.0", "Trigger Flower FedAvg Round")

    # 5. Multi-Horizon Forecasting
    check("GET", "/api/v1/forecasts", "Fetch Forecasts & 80%/95% Intervals")
    check("POST", "/api/v1/forecasts/generate?horizon=7&missing_nodes=0", "Generate 7-14d Recursive Forecast")

    # 6. CUSUM Anomalies & Reviewer Queue
    check("POST", "/api/v1/alerts/detect?drift_k=0.5&threshold_h=4.0&missing_nodes=0", "Trigger CUSUM Surge Detector")
    queue_resp = check("GET", "/api/v1/alerts", "List CUSUM Reviewer Queue")
    
    # Check alert detail, dossier, approve, reject if candidates exist
    if queue_resp and queue_resp.status_code == 200:
        data = queue_resp.json()
        alerts = data.get("alerts", [])
        if alerts:
            first_alert_id = alerts[0]["id"]
            check("GET", f"/api/v1/alerts/{first_alert_id}", "Get Alert Detail & Audit")
            check("GET", f"/api/v1/alerts/{first_alert_id}/dossier", "Export Public Health Incident Dossier")
            check("POST", f"/api/v1/alerts/{first_alert_id}/approve?reviewer_id=analyst_lead&reason=Verified", "Approve Candidate Alert")
            if len(alerts) > 1:
                second_alert_id = alerts[1]["id"]
                check("POST", f"/api/v1/alerts/{second_alert_id}/reject?reviewer_id=analyst_lead&reason=FalseAlarm", "Reject Candidate Alert")

    # 7. Multi-Source Ingestion & Ontology Endpoints
    check("GET", "/api/v1/data-collection/symptom-master", "257-Symptom Master Catalog")
    check("GET", "/api/v1/data-collection/syndrome-master", "45-Syndrome Master Catalog")
    check("GET", "/api/v1/data-collection/disease-reference", "100+ Reference Disease Catalog")
    check("GET", "/api/v1/data-collection/source-weights", "Source Reliability Weights Matrix")
    check("GET", "/api/v1/data-collection/weather?node_id=inst-a", "Open-Meteo Regional Weather Context")

    # Ingestion submissions
    check("POST", "/api/v1/data-collection/community-report", "Submit Community Symptom Form", json={
        "node_id": "inst-a",
        "symptoms": ["S001", "S021"],
        "symptom_onset": "2026-08-28",
        "severity": "moderate",
        "age_band": "15-29",
        "sex": "prefer_not_to_say",
        "zone_id": "zone-1",
        "consent_accepted": True
    })

    check("POST", "/api/v1/data-collection/doctor-observation", "Submit Doctor Observation", json={
        "node_id": "inst-b",
        "syndrome": "upper_respiratory_infection",
        "severity": "moderate",
        "visit_type": "walk-in",
        "zone_id": "zone-1"
    })

    check("POST", "/api/v1/data-collection/clinic-demand", "Submit Clinic Daily Demand", json={
        "node_id": "inst-c",
        "date": "2026-08-28",
        "syndrome": "acute_febrile_illness",
        "count": 50,
        "zone_id": "zone-2"
    })

    check("POST", "/api/v1/data-collection/pharmacy-demand", "Submit Pharmacy OTC Dispensing", json={
        "node_id": "inst-a",
        "date": "2026-08-28",
        "drug_category": "antipyretic",
        "count_dispensed": 65,
        "zone_id": "zone-1"
    })

    check("POST", "/api/v1/data-collection/testing-data", "Submit Diagnostic Lab Testing Data", json={
        "node_id": "inst-d",
        "date": "2026-08-28",
        "test_type": "rapid_antigen_influenza",
        "tests_requested": 40,
        "tests_positive": 14,
        "zone_id": "zone-3"
    })

    check("POST", "/api/v1/data-collection/absenteeism", "Submit Absenteeism Surveillance Data", json={
        "node_id": "inst-a",
        "date": "2026-08-28",
        "expected_attendance": 500,
        "actual_attendance": 420,
        "institution_name": "Metro High",
        "category": "school",
        "zone_id": "zone-1"
    })

    check("POST", "/api/v1/data-collection/emergency-calls", "Submit Emergency Dispatch Call Data", json={
        "node_id": "inst-a",
        "date": "2026-08-28",
        "call_category": "respiratory",
        "calls_received": 25,
        "calls_dispatched": 20,
        "zone_id": "zone-1"
    })

    check("POST", "/api/v1/data-collection/wastewater", "Submit Wastewater Genomic Viral Load", json={
        "node_id": "inst-a",
        "date": "2026-08-28",
        "sample_site": "Plant 1",
        "pathogen_marker": "SARS-CoV-2 RNA",
        "copies_per_ul": 350.0,
        "sample_volume_ml": 100.0,
        "quality_flag": "PASS",
        "zone_id": "zone-1"
    })

    check("POST", "/api/v1/data-collection/aggregate-now", "Run Local Daily Aggregation (k=11)", json={
        "date": "2026-08-28",
        "min_group_size": 11
    })

    check("GET", "/api/v1/data-collection/zone-rollup", "Zone-Level Rollup Aggregation")
    
    check("POST", "/api/v1/data-collection/simulate-event", "Trigger 5-Scenario Event Simulation", json={
        "scenario": "RESPIRATORY_OUTBREAK",
        "seed": 42,
        "days": 365
    })

    # Summary table output
    print(f"{'STATUS':<8} | {'METHOD':<6} | {'STATUS CODE':<11} | {'ENDPOINT PATH':<48} | {'PREVIEW':<25}")
    print("-" * 108)
    passed_count = 0
    for r in results:
        sym = "[PASS]" if r["passed"] else "[FAIL]"
        if r["passed"]:
            passed_count += 1
        print(f"{sym:<8} | {r['method']:<6} | {r['status_code']:<11} | {r['path'][:48]:<48} | {r['preview']:<25}")

    print("-" * 108)
    print(f"\nEndpoint Verification Summary: {passed_count}/{len(results)} endpoints passed successfully ({(passed_count/len(results))*100:.1f}%).\n")
    return passed_count == len(results)

if __name__ == "__main__":
    success = run_endpoint_checks()
    sys.exit(0 if success else 1)

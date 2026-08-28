# HealthSignal — Federated Community Health Trend Forecasting

[![Problem Statement](https://img.shields.io/badge/Challenge-IIC%202026%20S5-blue)](file:///d:/hackathons/inno5/HealthSignal_SRS_Revised.md)
[![Architecture](https://img.shields.io/badge/Architecture-Flower%20FedAvg-emerald)](file:///d:/hackathons/inno5/HealthSignal_TDS.md)
[![Forecasting Engine](https://img.shields.io/badge/Forecasting-7--14%20Day%20Recursive-indigo)](file:///d:/hackathons/inno5/backend/app/ml/forecasting.py)
[![Surge Detection](https://img.shields.io/badge/Anomaly-CUSUM%20h%3D4.0-amber)](file:///d:/hackathons/inno5/backend/app/ml/anomaly.py)
[![Privacy Enforcement](https://img.shields.io/badge/Privacy-FR--017%20Gate%20%2B%20Suppression-purple)](file:///d:/hackathons/inno5/HealthSignal_SRS_Revised.md#L260)
[![Test Suite](https://img.shields.io/badge/Tests-70%2F70%20PASSED-brightgreen)](file:///d:/hackathons/inno5/backend/tests)

HealthSignal is a privacy-preserving, federated analytics and decision-support system designed to forecast short-term (7–14 day) aggregate daily syndrome-category service demand across multiple decentralized institutions without centralizing row-level patient records.

> **Privacy & Non-Medical Disclaimer:** *Federated learning reduces the need to centralize raw records, but it does not by itself guarantee formal privacy. System outputs represent aggregate public-health service-demand indicators with statistical uncertainty bounds. System outputs do NOT represent medical predictions, clinical diagnoses, or individual patient risk factors.*

---

## 🏛 1. End-to-End System Architecture

```text
                                [ Decentralized Local Nodes ]
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ Local Node A     │  │ Local Node B     │  │ Local Node C     │  │ Local Node D     │
  │ (Urban High Vol) │  │ (Semi-urban)     │  │ (Rural High Var) │  │ (Mixed Seasonal) │
  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
           │                     │                     │                     │
           ▼                     ▼                     ▼                     ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                      Mandatory Privacy Gate (FR-017)                             │
  │  - Raw record rejection (No patient_id, SSN, or CSV rows)                         │
  │  - Coefficient bounding [-100, 100], NaN/Inf rejection                           │
  │  - Small-group suppression (MIN_GROUP_SIZE = 11)                                 │
  └────────────────────────────────────────┬─────────────────────────────────────────┘
                                           │ (Numeric Parameter Vectors Only)
                                           ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                      Flower Federated Coordinator (FedAvg)                       │
  │  - Weighted Aggregation: w_global = sum((n_i / N) * w_i)                         │
  │  - Model Artifact: artifacts/global/model.joblib (v1.0.0-fed-h7)                │
  └────────────────────────────────────────┬─────────────────────────────────────────┘
                                           │
                                           ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                      Phase 5 — 7–14 Day Forecast Engine                          │
  │  - Multi-Day Recursive Feature Rollout (Zero future-data leakage)                │
  │  - Residual Prediction Intervals (80% & 95%) & Empirical Coverage               │
  │  - Missing-Node Confidence Degradation (1.0 vs 0.75 vs 0.50)                     │
  └────────────────────────────────────────┬─────────────────────────────────────────┘
                                           │
                                           ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                   Phase 6 — CUSUM Anomaly & Reviewer Queue                       │
  │  - Statistical Process Control: S_t+ = max(0, S_{t-1}+ + z_score - drift_k)       │
  │  - Decision Threshold: h = 4.0 * sigma -> CANDIDATE ALERT                        │
  │  - Human Reviewer Queue: Public Health Analyst APPROVE / REJECT                  │
  │  - PostgreSQL Metadata & ReviewerDecision Audit Trail                            │
  └──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 2. Model Performance Comparison Matrix (7-Day Horizon MAE)

```text
Model Architecture                     Inst A   Inst B   Inst C   Inst D   Overall MAE   Overall RMSE
-----------------------------------------------------------------------------------------------------
Baseline C: Naive Baseline (lag_7)     3.42     5.12     3.97     6.78     4.82          6.51
Baseline A: Local Ridge Models         4.58     5.07     3.10     5.86     4.65          6.26
Global Model: Flower FedAvg            4.12     4.40     3.24     5.37     4.28          5.82
Baseline B: Pooled Ridge Upper Bound*  3.44     3.80     3.47     5.50     4.05          5.49
```
*\*Pooled Ridge is an evaluation-only centralized benchmark.*

---

## 🔒 3. Privacy & Data Locality Guarantees

1. **Strict Data Locality:** Local institution nodes (A, B, C, D) keep raw row-level records inside local directories (`data/inst-a/`, `data/inst-b/`, etc.).
2. **Pre-Transmission Boundary (`FR-017`):** Executed inside `HealthSignalFlowerClient.fit()` **BEFORE** parameter transmission.
3. **Small-Group Suppression:** Suppresses aggregate reporting for group counts below `MIN_GROUP_SIZE = 11`.

---

## ⚡ 4. REST API Overview

* `GET /api/v1/health` — Operational status & DB connectivity
* `GET /api/v1/institutions/status` — Decentralized node ready status & records count
* `GET /api/v1/institutions/non-iid-summary` — Kolmogorov-Smirnov statistical non-IID proof
* `GET /api/v1/models/baselines` — Benchmark comparison matrix
* `GET /api/v1/federation/status` — Federated round status & global model version
* `POST /api/v1/federation/start` — Triggers 4-client Flower FedAvg training round
* `GET /api/v1/forecasts` — Stored multi-day forecasts
* `POST /api/v1/forecasts/generate?horizon=7` — Generates 7–14 day forecast with uncertainty bounds
* `GET /api/v1/alerts` — Returns reviewer queue with candidate/approved/rejected counts
* `POST /api/v1/alerts/detect` — Runs CUSUM surge detection and generates candidate alerts
* `POST /api/v1/alerts/{id}/approve` — Transitions candidate alert to APPROVED
* `POST /api/v1/alerts/{id}/reject` — Transitions candidate alert to REJECTED

---

## 🐳 5. Docker Compose Quickstart

```bash
# Build and run complete multi-container stack (Frontend + Backend + PostgreSQL)
docker compose up --build -d

# Verify container health
docker compose ps
```

* **Frontend Dashboard:** `http://localhost:3000`
* **FastAPI Backend:** `http://localhost:8000`
* **OpenAPI Interactive Documentation:** `http://localhost:8000/docs`

---

## 🧪 6. Local Development & Testing

```bash
# 1. Backend Pytest Verification
cd backend
.\venv\Scripts\pytest

# 2. Frontend Production Build
cd frontend
npm run build
```

---

## 📜 7. Evaluation Artifacts

* `data/phase4_federated_report.json` — Phase 4 Flower FedAvg evaluation metrics
* `data/phase5_forecast_report.json` — Phase 5 forecast & empirical coverage report
* `data/phase6_anomaly_report.json` — Phase 6 CUSUM anomaly detection report
* `data/phase7_final_report.json` — Phase 7 final system readiness evaluation report

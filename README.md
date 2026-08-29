# HealthSignal — Federated Syndromic Surveillance & Forecasting Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-emerald.svg)](https://fastapi.tiangolo.com)
[![Federated Learning](https://img.shields.io/badge/Federation-Flower%20FedAvg-purple.svg)](https://flower.ai)
[![Ontology](https://img.shields.io/badge/Ontology-257%20Symptoms%20%7C%2045%20Syndromes%20%7C%20105%20Conditions-orange.svg)](file:///d:/INNO5/HealthSignaL/backend/app/core/syndrome_master.json)
[![Tests](https://img.shields.io/badge/Tests-261%2B%20PASSED-brightgreen.svg)](file:///d:/INNO5/HealthSignaL/backend/tests)
[![Status](https://img.shields.io/badge/Status-READY%20FOR%20DEMO-brightgreen.svg)](file:///d:/INNO5/HealthSignaL/docs/DEMO_RUNBOOK.md)

HealthSignal is a privacy-preserving federated analytics and public-health decision-support platform designed to forecast aggregate daily syndromic service demand across decentralized healthcare institutions 1 to 14 days in advance without centralizing row-level patient records.

> [!IMPORTANT]
> **Public-Health Decision Support & Non-Medical Disclaimer:**  
> HealthSignal is a public-health syndromic surveillance and service-demand forecasting prototype. It is **NOT** an individual medical diagnostic system. Outputs represent population-level syndromic demand trajectories with statistical uncertainty bounds and do not represent clinical diagnoses or individual patient risk factors.

---

## 🏛 1. End-to-End System Architecture

```text
                                 [ 4 Decentralized Local Nodes ]
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ Node A: Urban    │  │ Node B: Semi-Urb │  │ Node C: Rural    │  │ Node D: Mixed    │
  │ (High Volume)    │  │ (GI Heavy)       │  │ (High Variance)  │  │ (Seasonal Hub)   │
  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
           │                     │                     │                     │
           ▼                     ▼                     ▼                     ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                      Mandatory Privacy Gate (Layered Boundary)                   │
  │  - Zero raw patient records / Zero PII (Rejection of 15 identifying fields)       │
  │  - Small-group suppression (k >= 11) & Spatial rollups (COUNT >= 3 nodes)         │
  │  - Parameter bounding & L2 norm clipping before federation                       │
  └────────────────────────────────────────┬─────────────────────────────────────────┘
                                           │ (F=13 Numeric Parameter Updates Only)
                                           ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                      Flower Federated Coordinator (FedAvg)                       │
  │  - Aggregates model weights: w_global = sum((n_i / N) * w_i)                     │
  │  - Global Model Artifact: artifacts/global/model.joblib (v1.0.0-fed-h7)          │
  └────────────────────────────────────────┬─────────────────────────────────────────┘
                                           │
                                           ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                      Recursive Multi-Horizon Forecasting Engine                  │
  │  - 7, 10, and 14-day aggregate service projections (45 standardized syndromes)   │
  │  - Calibrated 80% and 95% prediction intervals (Empirical coverage verified)     │
  │  - Syndrome x Horizon x Node bounded confidence scoring ([0, 100])               │
  └────────────────────────────────────────┬─────────────────────────────────────────┘
                                           │
                                           ▼
  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                      CUSUM Anomaly Detection & Human Review Queue                │
  │  - Statistical Process Control: S_t+ = max(0, S_{t-1}+ + (y_t - yhat_t)/sigma - k)│
  │  - Decision Threshold: h = 4.0 * sigma -> Candidate Outbreak Alert               │
  │  - Analyst Review Queue: PENDING -> APPROVED / REJECTED with full audit trail    │
  └──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 2. Standardized Multi-Tier Ontology Layer

- **257 Standardized Symptoms**: Hierarchical symptom catalog (`symptoms_master.json`) with deterministic aliases and many-to-many associations.
- **45 Standardized Syndromes**: Comprehensive syndromic surveillance master catalog (`syndrome_master.json`) spanning Respiratory, Gastrointestinal, Vector-borne, Neurological, Dermatological, and Febrile domains.
- **105 Condition Reference Profiles**: Non-diagnostic epidemiological reference knowledge (`disease_reference.json`) used for simulation and ground-truth validation.
- **5 Core Data Sources**:
  1. Community USSD / Mobile self-reports
  2. Clinician triage observations
  3. Clinic and hospital demand
  4. Pharmacy over-the-counter dispensing
  5. Diagnostic laboratory testing

---

## 📈 3. Baseline Model Performance Comparison (7-Day Horizon)

| Model Architecture | MAE | RMSE | Coverage 80% | Coverage 95% | Mean Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Naive Lag-7 Model** | 3.12 | 4.55 | 74.2% | 89.1% | N/A |
| **Local Ridge (Node inst-a)** | 2.84 | 3.98 | 78.1% | 93.6% | 76.5% |
| **Federated FedAvg (Global)** | **2.62** | **3.71** | **80.4%** | **95.8%** | **79.5%** |
| **Centralized Upper Bound (Pooled)** | 2.51 | 3.58 | 81.2% | 96.1% | 82.0% |

---

## ⚡ 4. Early-Warning Outbreak Lead Times

| Outbreak Scenario | Primary Syndrome | Early Warning Lead Time | Detection Status |
| :--- | :--- | :--- | :--- |
| **Influenza A/B (ILI)** | Respiratory | **+5.0 Days** prior to clinical surge | ✅ High Confidence Lead |
| **Cholera Outbreak** | Gastrointestinal | **+5.0 Days** prior to clinical surge | ✅ High Confidence Lead |
| **Dengue Seasonal Surge** | Fever / Flu | **+6.0 Days** prior to clinical surge | ✅ High Confidence Lead |
| **Multi-Syndrome Wave** | Concurrent Resp + GI | **+5.0 Days** prior to clinical surge | ✅ High Confidence Lead |

---

## 🚀 5. Getting Started & Running Locally

### Backend API Server
```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### React Surveillance Dashboard
```powershell
cd frontend
npm install
npm run dev
```

### Automated Pytest Suite
```powershell
cd backend
.venv\Scripts\pytest.exe -v
```

---

## 📖 6. Documentation & Runbooks
- **Live Demo Instructions**: [docs/DEMO_RUNBOOK.md](file:///d:/INNO5/HealthSignaL/docs/DEMO_RUNBOOK.md)
- **Master Validation Report**: [data/HEALTHSIGNAL_FINAL_REPORT.md](file:///d:/INNO5/HealthSignaL/data/HEALTHSIGNAL_FINAL_REPORT.md)
- **Priority 2 Summary**: [data/priority2_summary.md](file:///d:/INNO5/HealthSignaL/data/priority2_summary.md)

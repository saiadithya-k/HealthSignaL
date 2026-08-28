# HealthSignal — Federated Community Health Trend Forecasting

[![Problem Statement](https://img.shields.io/badge/Challenge-IIC%202026%20S5-blue)](file:///d:/hackathons/inno5/HealthSignal_SRS_Revised.md)
[![Architecture](https://img.shields.io/badge/Architecture-Federated%20Learning-emerald)](file:///d:/hackathons/inno5/HealthSignal_TDS.md)
[![Privacy Enforcement](https://img.shields.io/badge/Privacy-FR--017%20Gate%20%2B%20Suppression-purple)](file:///d:/hackathons/inno5/HealthSignal_SRS_Revised.md#L260)

HealthSignal is a federated analytics and decision-support platform designed to forecast short-term (7–14 day) aggregate daily syndrome-category service demand across multiple decentralized institutions without centralizing patient-level records.

---

## 🏛 System Architecture Overview

Each simulated local institution node (A, B, C, D) retains its row-level records locally. Outbound updates are checked by a hard pre-transmission **Privacy Gate (`FR-017`)** to guarantee no raw row-level records ever cross the local trust boundary. A **Federated Coordinator** trains a global forecasting model using **FedAvg** (with Ridge Regression as the operational baseline model), while a statistical **CUSUM Shift Detector** identifies early demand surges.

```text
[ Local Institutions A - D ] ──(Privacy Gate)──> [ Federated Coordinator ] ──> [ Global Forecast Engine ]
                                                                                      │
                                                                                      ▼
[ Audit Log ] <──(Immutable Audit)── [ Public Health Reviewer Queue ] <── (Shift Detector & Uncertainty)
```

---

## 📊 Phase 3 — Local Feature Engineering & Baseline Comparison

Phase 3 implements the local machine learning foundation and baseline comparison harness for 7–14 day aggregate demand forecasting.

### 1. Feature Engineering (Zero Future-Data Leakage)
* **Temporal Features:** `day_of_week`, `day_of_month`, `month`, `week_of_year`, `is_weekend`.
* **Lag Features:** `lag_1`, `lag_7`, `lag_14`.
* **Rolling Features:** `rolling_mean_7`, `rolling_std_7`, `rolling_mean_14`.
* **Chronological Splitting:** Chronological 70% Train / 15% Validation / 15% Test split (Zero random shuffling).

### 2. Three Baseline Evaluation Modes
* **Baseline A — Local-Only Ridge:** Each institution node ($i \in \{A, B, C, D\}$) trains a `LocalForecastModel` exclusively on its own local dataset.
* **Baseline B — Pooled Upper Bound Ridge:** An evaluation-only reference condition where data from all nodes is centralized to establish an offline accuracy upper bound.
* **Baseline C — Simple Naive Baseline:** Same-day-last-week prediction ($\hat{y}_t = \text{lag\_7}$).

### 3. Baseline Comparison Matrix (7-Day Horizon)
```text
Model Architecture                     Inst A   Inst B   Inst C   Inst D   Overall MAE   Overall RMSE
-----------------------------------------------------------------------------------------------------
Baseline C: Naive Baseline (lag_7)     3.42     5.12     3.97     6.78     4.82          6.51
Baseline A: Local Ridge Models         4.58     5.07     3.10     5.86     4.65          6.26
Baseline B: Pooled Ridge Upper Bound*  3.44     3.80     3.47     5.50     4.05          5.49
```
*\*Pooled Ridge is an evaluation-only centralized benchmark.*

---

## 🛠 Tech Stack

* **Frontend:** React + Vite, Recharts, CSS Variables & Glassmorphism
* **Backend:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, Scikit-Learn
* **Federation:** Flower (`flwr`) + Ridge Regression FedAvg Baseline
* **Database:** PostgreSQL 15
* **Deployment:** Docker & Docker Compose
* **Testing:** `pytest` unit & integration test framework

---

## 🚀 Quickstart Guide

### 1. Requirements
* Docker Desktop & Docker Compose
* Python 3.11+ (for local development/testing)
* Node.js 18+ (optional, for frontend local dev)

### 2. Running with Docker Compose
```bash
# Copy environment template
cp .env.example .env

# Build and start all services
docker-compose up --build -d
```

Access the services:
* **Dashboard (Frontend):** [http://localhost:3000](http://localhost:3000)
* **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **API Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 3. Local Development (Without Docker)

#### Backend Setup & ML Evaluation
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt

# Run complete Phase 1 + Phase 2 + Phase 3 test suite (27 tests)
pytest

# Train local models & generate Phase 3 baseline evaluation report
python -c "from app.ml.harness import BaselineComparisonHarness; BaselineComparisonHarness().run_full_baseline_evaluation()"
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🔍 Database Schema (PostgreSQL Tables)

1. `institutions` — Decentralized node registry (A, B, C, D)
2. `federated_rounds` — Federated training round metadata
3. `round_participants` — Client round participation status
4. `model_versions` — Global model versions & metrics
5. `forecasts` — 7–14 day aggregate demand predictions & prediction intervals
6. `alerts` — Candidate distribution-shift alerts
7. `reviewer_decisions` — Human reviewer decisions (Approve / Reject)
8. `privacy_events` — Pre-transmission rejection & suppression event logs
9. `audit_logs` — Tamper-evident append-only audit trail

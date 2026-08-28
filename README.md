# HealthSignal — Federated Community Health Trend Forecasting

[![Problem Statement](https://img.shields.io/badge/Challenge-IIC%202026%20S5-blue)](file:///d:/hackathons/inno5/HealthSignal_SRS_Revised.md)
[![Architecture](https://img.shields.io/badge/Architecture-Flower%20FedAvg-emerald)](file:///d:/hackathons/inno5/HealthSignal_TDS.md)
[![Forecasting Engine](https://img.shields.io/badge/Forecasting-7--14%20Day%20Recursive-indigo)](file:///d:/hackathons/inno5/backend/app/ml/forecasting.py)
[![Privacy Enforcement](https://img.shields.io/badge/Privacy-FR--017%20Gate%20%2B%20Suppression-purple)](file:///d:/hackathons/inno5/HealthSignal_SRS_Revised.md#L260)

HealthSignal is a federated analytics and decision-support platform designed to forecast short-term (7–14 day) aggregate daily syndrome-category service demand across multiple decentralized institutions without centralizing patient-level records.

> **Privacy & Medical Disclaimer:** *Federated learning reduces the need to centralize raw records, but it does not by itself guarantee formal privacy. Forecasts represent aggregate public-health service-demand predictions with statistical uncertainty bounds. Forecasts do NOT represent medical predictions or individual patient diagnoses.*

---

## 🏛 System Architecture Overview

Each simulated local institution node (A, B, C, D) retains its row-level records locally. Outbound update payloads pass through a mandatory pre-transmission **Privacy Gate (`FR-017`)** to guarantee no raw row-level records or patient identifiers ever cross the local trust boundary. A **Flower Federated Coordinator** aggregates valid client updates using **FedAvg**, producing a versioned global forecasting model consumed by the **Phase 5 Multi-Day Forecasting Engine**.

```text
[ Local Node A ] ──(Privacy Gate)──┐
[ Local Node B ] ──(Privacy Gate)──┼──> [ Flower Coordinator (FedAvg) ] ──> [ Global Forecast Model ]
[ Local Node C ] ──(Privacy Gate)──┤                                                   │
[ Local Node D ] ──(Privacy Gate)──┘                                                   ▼
                                                                        [ Phase 5 Forecasting Engine ]
                                                                        [ 7–14 Day Recursive Prediction ]
                                                                        [ 80% & 95% Residual Intervals  ]
```

---

## 📈 Phase 5 — 7–14 Day Forecast & Uncertainty Engine

Phase 5 implements a data-driven multi-day recursive forecasting engine powered by the global Flower FedAvg model (`artifacts/global/model.joblib`).

### 1. Horizon & Multi-Day Recursive Forecasting
* **Supported Horizons:** 7 to 14 days (configurable via API query or configuration). Rejects horizon $\le 0$ or $> 14$.
* **Recursive Feature Rollout:** Day $t+1$ predictions use predicted values from day $t$ to compute subsequent lag (`lag_1`, `lag_7`, `lag_14`) and rolling metrics (`rolling_mean_7`, `rolling_std_7`, `rolling_mean_14`) recursively without future data leakage.

### 2. Residual-Based Prediction Intervals & Empirical Coverage
* **Residual Standard Deviation ($\sigma$):** Computed from validation set errors $(y - \hat{y})$.
* **80% Prediction Interval:** $\hat{y} \pm 1.2816 \cdot \sigma$ (lower bound clipped at $0.0$).
* **95% Prediction Interval:** $\hat{y} \pm 1.9600 \cdot \sigma$ (lower bound clipped at $0.0$).
* **Empirical Coverage Tracking:** Validates actual observations falling within 80% ($\sim 81.5\%$) and 95% ($\sim 93.8\%$) prediction intervals.

### 3. Missing-Node Degradation & Confidence Scoring
* **Data Coverage Ratio:** $1.0$ when all 4 nodes participate, $0.75$ when 1 node is missing, $0.50$ when 2 nodes are missing.
* **Forecast Confidence Score:** Decreases deterministically as data coverage ratio degrades or residual variance increases.

---

## 🛠 Tech Stack

* **Frontend:** React + Vite, Recharts, CSS Variables & Glassmorphism
* **Backend:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, Scikit-Learn
* **Federation:** Flower (`flwr`) + Ridge Regression FedAvg
* **Database:** PostgreSQL 15 / SQLite
* **Testing:** `pytest` unit & integration test framework

---

## 🚀 Quickstart Guide

### 1. Generating Forecasts via API
```bash
# Trigger 7-Day Forecast Generation
curl -X POST "http://localhost:8000/api/v1/forecasts/generate?horizon=7"
```

### 2. Running Unit & Integration Tests
```bash
cd backend
pytest
```

---

## 🔍 Database Schema (PostgreSQL Tables)

1. `institutions` — Decentralized node registry (A, B, C, D)
2. `federated_rounds` — Federated training round metadata
3. `round_participants` — Client round participation status
4. `model_versions` — Global model versions & metrics
5. `forecasts` — 7–14 day aggregate demand predictions, 80%/95% uncertainty bounds, confidence scores, coverage ratios
6. `alerts` — Candidate distribution-shift alerts
7. `reviewer_decisions` — Human reviewer decisions
8. `privacy_events` — Pre-transmission rejection & suppression logs
9. `audit_logs` — Tamper-evident append-only audit trail

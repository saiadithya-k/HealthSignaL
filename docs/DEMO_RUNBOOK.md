# HealthSignal — Demonstration Runbook

This runbook details step-by-step instructions for performing a live demonstration of the HealthSignal platform.

---

## Prerequisites & Environment Setup

1. **Backend Python Environment**:
   ```powershell
   cd d:\INNO5\HealthSignaL\backend
   .venv\Scripts\activate
   ```
2. **Frontend React/Vite Environment**:
   ```powershell
   cd d:\INNO5\HealthSignaL\frontend
   npm install
   ```

---

## Live Demonstration Walkthrough Steps

### Step 1: Start Backend API Server
```powershell
cd d:\INNO5\HealthSignaL\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Verify API docs at `http://localhost:8000/docs`.*

### Step 2: Start React Surveillance Dashboard
```powershell
cd d:\INNO5\HealthSignaL\frontend
npm run dev
```
*Open dashboard at `http://localhost:5173`.*

### Step 3: Multi-Node Data Overview (Tab 1)
- Review the 4 decentralized nodes:
  - `inst-a`: Urban Tertiary Hospital (High Volume)
  - `inst-b`: Semi-Urban Regional Center (GI Vulnerable)
  - `inst-c`: Rural Primary Clinics (High Variance, Dispersed)
  - `inst-d`: Mixed Semi-Urban Center (Seasonal Waves)
- Show small-group privacy suppression ($k \ge 11$) and spatial isolation ($N \ge 3$ nodes).

### Step 4: Outbreak Simulation (Tab 4)
- Select scenario **Influenza (ILI)**, **Cholera**, or **Dengue**.
- Trigger simulation: Observe multi-source telemetry logging:
  - Community symptom reports
  - Pharmacy OTC antipyretic sales
  - Clinician triage observations
  - Lab test logs
  - Wastewater samples
- Review Non-IID Wasserstein divergence ($W$) metrics.

### Step 5: Federated Training Round (Tab 5 / Forecaster)
- Click **Run FedAvg Round**:
  - 4 local Ridge models fit locally on $F=13$ feature vectors.
  - Mandatory privacy gate validates zero PII, clips parameters, and sends updates to Flower coordinator.
  - Global model artifact is saved at `artifacts/global/model.joblib`.

### Step 6: Multi-Horizon Forecasting & Prediction Intervals (Tab 5)
- Select Horizon: **7 Days**, **10 Days**, or **14 Days**.
- Select Missing Nodes: **0 Missing (All 4)** vs **1 Missing (3 Nodes)** vs **2 Missing (2 Nodes)**.
- Inspect:
  - Point Forecast curve (green).
  - 80% Prediction Interval (cyan).
  - 95% Prediction Interval (indigo).
  - Multi-factor bounded Confidence Score ($[0, 100]$).
  - Early-Warning Lead Time table showing 4 to 6 days early alert prior to clinical surge.

### Step 7: CUSUM Anomaly Detection & Human Review Queue (Tab 6)
- Click **Run CUSUM Surge Detector**:
  - SPC algorithm calculates cumulative standardized residuals ($h=4.0\sigma$, $k=0.5\sigma$).
  - Candidate anomaly alerts appear in the review queue.
- Click **Approve** or **Reject** on candidate alert:
  - Add reviewer notes and verify database audit trail preservation.

---

## Automated Verification Tests
Run the comprehensive test suite:
```powershell
cd d:\INNO5\HealthSignaL\backend
.venv\Scripts\pytest.exe -v
```

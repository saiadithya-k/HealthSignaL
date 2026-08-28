# HealthSignal — Technical Design Specification (TDS)

**Project:** HealthSignal — Federated Community Health Trend Forecasting  
**Problem Statement:** S5 — ML & Privacy-Preserving Public Health  
**Document Type:** Technical Design Specification  
**Status:** Implementation Baseline  
**Version:** 1.0

---

## 1. Purpose

This Technical Design Specification translates the HealthSignal Software Requirements Specification (SRS) into an implementation-oriented technical design.

The design covers:

- four or more simulated decentralized institutions;
- local retention of row-level records;
- privacy-safe aggregate feature generation;
- federated model training;
- 7–14 day aggregate syndrome-category service-demand forecasting;
- distribution-shift detection;
- uncertainty estimation;
- small-group disclosure prevention;
- privacy leakage testing;
- missing-node resilience;
- human public-health review;
- audit logging;
- three-way model evaluation;
- dashboard presentation; and
- deployment and testing.

The TDS describes the intended prototype architecture and technical interfaces. It does not contain production source code.

---

# 2. Design Principles

HealthSignal shall follow these principles:

1. **Raw-data locality** — row-level records remain inside their originating institution.
2. **Aggregate forecasting** — the operational prediction target is daily aggregate syndrome-category service demand.
3. **Federated collaboration** — institutions collaborate through federated model training rather than centralizing raw records.
4. **Privacy by enforcement** — privacy controls are implemented at explicit system boundaries and tested.
5. **Human oversight** — generated alerts are review candidates and do not become actionable public-health decisions automatically.
6. **Evidence and auditability** — model rounds, participant events, privacy events, failures, and reviewer decisions are recorded.
7. **Measurable evaluation** — local-only, federated, and pooled-data baselines are compared on held-out data.
8. **Safe failure** — missing participants, invalid updates, poor-quality data, and high-uncertainty forecasts must not silently produce misleading results.
9. **Reproducibility** — synthetic data generation, experiments, model versions, and configuration shall be versioned.

---

# 3. System Scope

## 3.1 In Scope

The prototype includes:

- four simulated institutions;
- synthetic/de-identified aggregate health-service data;
- local data processing;
- local feature engineering;
- local forecasting model training;
- federated training;
- global model generation;
- 7–14 day forecasting;
- uncertainty intervals;
- distribution-shift detection;
- privacy filtering and minimum-group suppression;
- privacy leakage experiments;
- alert generation;
- human reviewer workflow;
- dashboard visualization;
- audit logging;
- failure/recovery handling;
- baseline experiments;
- deployment through containerized services.

## 3.2 Out of Scope

The system shall not provide:

- individual diagnosis;
- individual risk scoring;
- patient-level clinical recommendations;
- re-identification;
- centralized operational storage of raw patient-level records;
- autonomous public-health alerts;
- autonomous clinical decisions;
- real hospital integration.

---

# 4. High-Level Architecture

```text
┌───────────────────────────────────────────────────────────────────┐
│                    LOCAL INSTITUTION LAYER                        │
├──────────────┬──────────────┬──────────────┬──────────────────────┤
│ Institution A│ Institution B│ Institution C│ Institution D        │
│              │              │              │                      │
│ Raw Local DB │ Raw Local DB │ Raw Local DB │ Raw Local DB         │
│      ↓       │      ↓       │      ↓       │       ↓              │
│ Validation   │ Validation   │ Validation   │ Validation            │
│      ↓       │      ↓       │      ↓       │       ↓              │
│ Aggregation  │ Aggregation  │ Aggregation  │ Aggregation           │
│      ↓       │      ↓       │      ↓       │       ↓              │
│ Features     │ Features     │ Features     │ Features              │
│      ↓       │      ↓       │      ↓       │       ↓              │
│ Privacy Gate │ Privacy Gate │ Privacy Gate │ Privacy Gate          │
│      ↓       │      ↓       │      ↓       │       ↓              │
│ Local Model  │ Local Model  │ Local Model  │ Local Model            │
└──────┬───────┴──────┬───────┴──────┬───────┴──────────┬───────────┘
       │              │              │                  │
       └──────────────┴──────────────┴──────────────────┘
                              │
                     Permitted Updates Only
                              │
                              ▼
                 ┌────────────────────────┐
                 │ Federated Coordinator  │
                 │                        │
                 │ Client Registry         │
                 │ Round Orchestrator      │
                 │ Update Validator        │
                 │ Aggregator              │
                 └───────────┬────────────┘
                             │
                         Global Model
                             │
                             ▼
                 ┌────────────────────────┐
                 │ Forecasting Service    │
                 └───────────┬────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       Forecast Output  Uncertainty   Shift Detector
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                 ┌────────────────────────┐
                 │ Alert / Review Service │
                 └───────────┬────────────┘
                             ▼
                 ┌────────────────────────┐
                 │ Public Health Dashboard│
                 │ Human Reviewer         │
                 └───────────┬────────────┘
                             ▼
                     Audit / Event Log
```

---

# 5. Component Architecture

## 5.1 Local Institution Node

Each simulated institution is an isolated logical client.

Responsibilities:

- store its own local records;
- validate local data;
- aggregate row-level observations;
- generate approved features;
- train its local model;
- validate the outbound payload;
- participate in federation;
- report client status;
- recover after temporary disconnection.

The node must never expose its raw database to the coordinator.

## 5.2 Federated Coordinator

Responsibilities:

- register and authenticate clients;
- create training rounds;
- select participating clients;
- distribute the current global model;
- receive permitted model updates;
- validate updates;
- perform aggregation;
- handle missing clients;
- publish the resulting global model;
- record round metadata.

The coordinator shall not receive raw local records.

## 5.3 Forecasting Service

Responsibilities:

- load the approved global model;
- construct the required forecast input;
- generate 7–14 day forecasts;
- generate prediction intervals;
- return forecast metadata;
- expose forecast results to the dashboard.

## 5.4 Distribution-Shift Detector

Responsibilities:

- compare expected and observed aggregate demand;
- compute a shift/anomaly score;
- identify sustained deviations;
- generate an alert candidate;
- attach evidence and detection metadata.

A statistical residual-based detector such as CUSUM may be used as the initial implementation.

## 5.5 Uncertainty Service

Responsibilities:

- calculate prediction intervals;
- associate uncertainty with each forecast;
- calculate forecast confidence indicators;
- identify forecasts whose uncertainty is too high for strong interpretation.

The implementation shall not represent uncertainty as a guarantee of correctness.

## 5.6 Review Service

Responsibilities:

- receive alert candidates;
- rank or categorize them;
- present evidence;
- allow a reviewer to approve, reject, or request review;
- record the decision and timestamp.

## 5.7 Audit Service

Responsibilities:

- record training rounds;
- participant events;
- model versions;
- privacy events;
- failures;
- reviewer decisions;
- system configuration changes.

---

# 6. Institution Simulation Design

Four institutions shall be simulated:

| Node | Population Profile | Characteristics |
|---|---|---|
| Institution A | Urban | Higher service volume, stronger weekday pattern |
| Institution B | Semi-urban | Moderate volume, different syndrome proportions |
| Institution C | Rural | Lower volume, higher variability |
| Institution D | Mixed | Different seasonality and category distribution |

These profiles are engineering choices used to create non-identical/non-IID data.

The institution distributions shall intentionally differ in:

- average service volume;
- syndrome-category proportions;
- seasonal behavior;
- weekday effects;
- missingness patterns;
- magnitude and timing of demand surges.

No institution should contain exactly the same generated distribution as another.

---

# 7. Synthetic Data Design

## 7.1 Data Generation Objective

The synthetic dataset shall represent aggregate service-demand observations while allowing controlled experiments.

The generator shall support:

- normal baseline demand;
- weekly seasonality;
- longer-term trend;
- random variation;
- institution-specific behavior;
- syndrome-category differences;
- missing observations;
- demand surges;
- distribution shifts.

## 7.2 Primary Data Grain

The operational aggregate grain is:

```text
institution × date × syndrome_category
```

Example:

```text
2026-01-15 | Institution-A | respiratory | 137
```

The prototype may generate underlying local synthetic records for demonstrating the local boundary, but those records remain inside the institution node.

## 7.3 Primary Target

The forecasting target is:

> Daily aggregate syndrome-category service demand for the next 7–14 days.

Target variable:

```text
service_count
```

at:

```text
institution + date + syndrome_category
```

level.

The model does not predict an individual patient's outcome.

---

# 8. Local Data Schema

A local synthetic record may contain:

| Field | Type | Description |
|---|---|---|
| local_record_id | string | Local-only synthetic identifier |
| institution_id | string | Originating institution |
| service_date | date | Date of service |
| syndrome_category | enum | Aggregate syndrome category |
| age_group_band | enum | Non-identifying age band |
| sex_category | enum | Non-identifying category if required |
| service_type | enum | Service category |
| outcome_count | integer | Local observation/count |
| source_quality | float | Local data-quality indicator |

These fields are local-only.

No raw record containing these fields shall be transmitted to the central coordinator.

---

# 9. Approved Aggregate Feature Schema

After local processing, the model receives aggregate features.

Core features:

| Feature | Description |
|---|---|
| service_count | Current aggregate daily demand |
| lag_1 | Previous-day demand |
| lag_7 | Demand seven days earlier |
| rolling_mean_7 | Seven-day rolling mean |
| rolling_std_7 | Seven-day rolling standard deviation |
| rolling_mean_14 | Fourteen-day rolling mean |
| day_of_week | Calendar feature |
| week_of_year | Seasonal calendar feature |
| trend_index | Local trend indicator |
| data_completeness | Aggregate completeness indicator |
| prior_shift_flag | Previous shift indicator |

The final feature dictionary shall be versioned.

Features shall be reviewed before being permitted through the transmission boundary.

---

# 10. Feature Engineering Pipeline

```text
Local Raw Records
       ↓
Schema Validation
       ↓
Missing/Invalid Value Handling
       ↓
Daily Aggregation
       ↓
Syndrome Category Grouping
       ↓
Time-Series Sorting
       ↓
Lag Features
       ↓
Rolling Statistics
       ↓
Calendar Features
       ↓
Data Completeness Features
       ↓
Approved Feature Dictionary
       ↓
Privacy / Transmission Gate
```

The same deterministic feature-generation logic shall be used during training and inference.

---

# 11. Data Quality Processing

Each local node shall perform:

1. schema validation;
2. data-type validation;
3. date validation;
4. category validation;
5. missing-value detection;
6. duplicate detection;
7. range checks;
8. aggregate consistency checks.

Invalid records shall be rejected or handled according to a documented rule.

Data-quality events shall be logged locally and, where safe, represented through aggregate metadata.

---

# 12. Train / Validation / Test Strategy

The system shall use time-aware splitting.

Random shuffling of time-series observations shall not be used as the primary evaluation split.

Recommended structure:

```text
Historical Period
├── Training Window
├── Validation Window
└── Held-Out Test Window
```

The held-out test period shall contain scenarios not used to tune the final model.

Separate evaluation scenarios shall include:

- normal demand;
- regional surge;
- distribution shift;
- missing institution.

---

# 13. Local Forecasting Model

The system shall use a supervised time-series regression approach based on engineered lag, rolling, calendar, and trend features.

The model-selection process shall compare suitable candidate models rather than assuming that a more complex neural architecture is automatically better.

Candidate implementations may include:

- gradient-boosted regression;
- tree-based regression;
- neural time-series regression where justified.

The selected model shall be determined using:

- held-out forecasting performance;
- cross-institution performance;
- federated convergence;
- computational cost;
- uncertainty/calibration behavior.

The final selected model shall be documented in the implementation configuration.

---

# 14. Forecast Construction

For each institution and syndrome category, the forecasting engine shall generate:

```text
Day +1
Day +2
...
Day +7
```

and support extension through:

```text
Day +14
```

The implementation shall support a requested forecast horizon within the 7–14 day range.

Forecast output:

| Field | Description |
|---|---|
| forecast_date | Date being predicted |
| institution_id | Institution scope |
| syndrome_category | Category |
| point_forecast | Predicted demand |
| lower_bound | Lower prediction bound |
| upper_bound | Upper prediction bound |
| uncertainty_score | Uncertainty measure |
| model_version | Model used |
| generated_at | Timestamp |

---

# 15. Federated Learning Architecture

## 15.1 Training Flow

```text
Coordinator
    │
    ├── sends global model
    │
    ▼
Institution Nodes
    │
    ├── train locally
    ├── validate local result
    ├── execute privacy gate
    └── produce permitted model update
    │
    ▼
Coordinator
    │
    ├── validate updates
    ├── exclude failed/invalid updates
    └── aggregate
    │
    ▼
New Global Model
```

## 15.2 Aggregation

The initial implementation shall use **Federated Averaging (FedAvg)**.

Conceptually:

```text
Global Model(t+1)
=
weighted average of
valid participating client model parameters
```

Client weighting shall use an approved local training-size statistic rather than transmitting raw records.

## 15.3 Training Round Metadata

Each round shall record:

- round ID;
- start time;
- end time;
- global model version;
- expected participants;
- participating clients;
- failed clients;
- rejected updates;
- aggregation status;
- resulting model version.

---

# 16. Client Authentication and Registration

Each simulated institution shall have:

- unique client ID;
- authentication credential;
- enabled/disabled status;
- model compatibility version;
- registration timestamp.

The coordinator shall reject unknown or disabled clients.

Client authentication is separate from authorization to access dashboard/reviewer functions.

---

# 17. Federated Update Validation

Before aggregation, each update shall be checked for:

- authenticated client;
- expected model version;
- expected parameter structure;
- numeric validity;
- finite parameter values;
- abnormal update magnitude;
- duplicate/replayed round;
- protocol compliance.

Invalid updates shall be rejected and logged.

The system shall not silently aggregate malformed updates.

---

# 18. Privacy Boundary

The most important architectural boundary is:

```text
             LOCAL TRUST BOUNDARY
─────────────────────────────────────────────
Raw records
Local identifiers
Local row-level data
Local raw database
─────────────────────────────────────────────
             PRIVACY GATE
─────────────────────────────────────────────
Approved aggregate features
Permitted model update
Safe metadata
─────────────────────────────────────────────
             CENTRAL SYSTEM
```

The central system must never receive local row-level records.

---

# 19. Pre-Transmission Privacy Gate

The local node shall execute a mandatory pre-transmission check.

Checks shall include:

- forbidden field detection;
- row-level identifier detection;
- unexpected schema detection;
- payload type validation;
- payload-size anomaly checks;
- minimum-group-size checks where applicable.

If a forbidden payload is detected:

```text
Reject payload
      ↓
Log privacy event
      ↓
Do not transmit payload
      ↓
Mark round/client state appropriately
```

This is a hard enforcement point, not merely a warning.

---

# 20. Small-Group Suppression

Dashboard queries and exported aggregate results shall be subject to a configurable minimum-group-size rule.

The prototype threshold shall be configurable rather than treated as an immutable official value.

For any query that violates the minimum-group-size rule:

```text
Request
  ↓
Privacy Check
  ↓
Below Threshold?
  ├── YES → SUPPRESS + LOG
  └── NO  → Return Aggregate
```

Suppressed outputs shall not reveal the underlying value through alternate displays.

---

# 21. Privacy Leakage Testing

The evaluation harness shall test whether model outputs or exposed aggregates can reveal sensitive membership information.

Testing shall include an appropriate membership-inference/privacy-leakage experiment.

The result shall be reported separately from forecasting accuracy.

Federated learning shall not be described as an automatic guarantee of privacy.

---

# 22. Uncertainty Estimation

Every forecast shall include an uncertainty representation.

The prototype may use:

- prediction intervals derived from validation residuals;
- quantile regression;
- conformal-style interval construction if implemented and validated.

The selected method shall be documented.

Suggested outputs:

```text
Point Forecast
Lower Bound
Upper Bound
Interval Width
Uncertainty Score
```

If uncertainty is high, the dashboard shall visually distinguish the forecast and avoid presenting it as a high-confidence prediction.

---

# 23. Distribution-Shift Detection

The detector compares observed demand against expected demand.

Initial design:

```text
Observed Demand
      -
Expected Demand
      ↓
Residual
      ↓
Shift Detector
      ↓
Shift Score
      ↓
Threshold / Persistence Rule
      ↓
Alert Candidate
```

A residual-based CUSUM-style detector may be used as the initial implementation.

The detector shall distinguish between:

- normal random variation;
- sustained demand increase;
- sustained demand decrease;
- unusual institution-specific behavior.

The detection threshold shall be configurable and evaluated on held-out injected-shift scenarios.

---

# 24. Alert Generation

An alert candidate shall contain:

| Field | Description |
|---|---|
| alert_id | Unique identifier |
| detected_at | Detection timestamp |
| institution_scope | Institution/region |
| syndrome_category | Category |
| observed_value | Aggregate observation |
| expected_value | Expected demand |
| shift_score | Detection score |
| evidence_window | Time window |
| forecast_reference | Model/forecast version |
| uncertainty | Associated uncertainty |
| status | Review status |

Possible states:

```text
CANDIDATE
UNDER_REVIEW
APPROVED
REJECTED
EXPIRED
```

No alert becomes actionable solely because an algorithm generated it.

---

# 25. Human Review Workflow

```text
Shift Detector
      ↓
Alert Candidate
      ↓
Reviewer Queue
      ↓
Reviewer examines:
- forecast
- uncertainty
- observed trend
- shift evidence
- institution coverage
- model version
      ↓
Approve / Reject
      ↓
Decision Logged
```

Reviewer decisions shall include:

- decision;
- reviewer ID;
- timestamp;
- optional reason;
- alert version.

---

# 26. Three-Baseline Evaluation Architecture

The system shall maintain a separate evaluation harness.

## Baseline A — Local Only

Each institution trains independently.

No model collaboration occurs.

Purpose:

> Determine how well institutions perform without collaboration.

## Baseline B — Federated

The proposed operational architecture.

Institutions train locally and contribute permitted model updates.

Purpose:

> Measure privacy-preserving collaborative performance.

## Baseline C — Pooled Upper Bound

A separate offline experiment trains on pooled data.

Purpose:

> Estimate the performance ceiling when centralized training data is available.

The pooled baseline shall not be used as the operational architecture.

---

# 27. Evaluation Metrics

## Forecast Accuracy

Primary:

- MAE.

Additional:

- MAPE where valid;
- WAPE or another suitable alternative when zero/near-zero actual values make MAPE inappropriate.

## Federated Uplift

A suitable comparison shall be reported between federated and local-only performance.

For an error metric where lower is better:

```text
Uplift (%) =
(Local Error - Federated Error)
/
Local Error
× 100
```

## Shift Detection

Measure:

- recall;
- false-positive behavior;
- lead time before surge peak.

## Privacy

Measure:

- row-level transmission violations;
- suppression compliance;
- privacy leakage experiment results.

## Resilience

Measure:

- successful continuation after missing-node failure;
- round completion;
- model consistency after recovery.

## Cross-Institution Performance

Report results separately by institution to identify whether the global model benefits or disadvantages specific node populations.

---

# 28. Database Design

The central database shall not contain raw patient-level records.

## 28.1 Institutions

```text
institutions
-----------------------------
id
name
profile
status
model_version
created_at
```

## 28.2 Federated Rounds

```text
federated_rounds
-----------------------------
round_id
global_model_version
started_at
completed_at
status
expected_clients
successful_clients
failed_clients
```

## 28.3 Participants

```text
round_participants
-----------------------------
id
round_id
institution_id
status
update_status
failure_reason
timestamp
```

## 28.4 Model Versions

```text
model_versions
-----------------------------
id
version
parent_version
algorithm
metrics
created_at
artifact_reference
```

## 28.5 Forecasts

```text
forecasts
-----------------------------
id
model_version
institution_id
syndrome_category
forecast_date
point_forecast
lower_bound
upper_bound
uncertainty_score
generated_at
```

## 28.6 Alerts

```text
alerts
-----------------------------
id
institution_scope
syndrome_category
detected_at
shift_score
status
forecast_reference
```

## 28.7 Reviewer Decisions

```text
reviewer_decisions
-----------------------------
id
alert_id
reviewer_id
decision
reason
created_at
```

## 28.8 Privacy Events

```text
privacy_events
-----------------------------
id
institution_id
event_type
severity
description
created_at
```

## 28.9 Audit Logs

```text
audit_logs
-----------------------------
id
actor_type
actor_id
event_type
entity_type
entity_id
metadata
created_at
```

---

# 29. API Architecture

The backend shall expose APIs for system orchestration and presentation.

## 29.1 Institution Registration

```text
POST /api/institutions/register
```

Purpose:

Register a simulated institution.

## 29.2 Federated Round

```text
POST /api/federation/rounds
```

Purpose:

Start a federated training round.

## 29.3 Client Participation

```text
POST /api/federation/rounds/{round_id}/participate
```

Purpose:

Record client participation and permitted update status.

## 29.4 Forecast Retrieval

```text
GET /api/forecasts
```

Purpose:

Retrieve authorized aggregate forecasts.

## 29.5 Alert Retrieval

```text
GET /api/alerts
```

Purpose:

Retrieve reviewer-visible alert candidates.

## 29.6 Reviewer Decision

```text
POST /api/alerts/{alert_id}/decision
```

Purpose:

Approve or reject an alert candidate.

## 29.7 Audit Log

```text
GET /api/audit
```

Purpose:

Retrieve authorized audit information.

## 29.8 Privacy Event

```text
GET /api/privacy/events
```

Purpose:

Display privacy-control events to authorized users.

---

# 30. API Security

API access shall use authentication and role-based authorization.

Roles:

| Role | Main Permissions |
|---|---|
| Institution Node | Local federation operations |
| System Administrator | System configuration and monitoring |
| Public-Health Reviewer | Alerts and reviewer decisions |
| Auditor | Read-only audit information |

Raw local data shall never be exposed through central APIs.

---

# 31. Dashboard Architecture

The dashboard shall contain the following primary views.

## 31.1 Overview

Displays:

- current demand;
- forecast;
- forecast horizon;
- uncertainty;
- active alert candidates.

## 31.2 Forecast View

Displays:

- historical demand;
- predicted demand;
- prediction interval;
- syndrome category;
- institution scope.

## 31.3 Federation View

Displays:

- current round;
- participating institutions;
- failed/disconnected nodes;
- global model version;
- round completion status.

## 31.4 Shift Detection View

Displays:

- observed vs expected demand;
- shift score;
- detection time;
- alert state.

## 31.5 Privacy View

Displays:

- privacy events;
- suppressed queries;
- rejected payload attempts;
- compliance indicators.

No suppressed query shall expose the protected underlying value.

## 31.6 Reviewer Queue

Displays:

- candidate alerts;
- evidence;
- uncertainty;
- model version;
- reviewer decision controls.

## 31.7 Audit View

Displays:

- training rounds;
- participant events;
- failures;
- privacy events;
- reviewer decisions.

---

# 32. Failure and Recovery Design

## 32.1 Missing Institution During Training

```text
Round Started
      ↓
Institution Disconnects
      ↓
Timeout
      ↓
Mark Participant FAILED / MISSING
      ↓
Continue With Valid Participants
      ↓
Aggregate
      ↓
Complete Round
      ↓
Log Failure
```

The system shall not fabricate an update for the missing institution.

## 32.2 Invalid Model Update

```text
Update Received
      ↓
Validation
      ↓
Invalid
      ↓
Reject
      ↓
Log
      ↓
Continue if minimum valid participation is satisfied
```

## 32.3 High Forecast Uncertainty

High uncertainty shall not automatically generate a strong operational alert.

The dashboard shall identify the uncertainty and route the information for human interpretation.

## 32.4 Data Quality Failure

If a local node has insufficient or invalid data, it shall report a controlled failure rather than silently training on invalid input.

---

# 33. Model Versioning

Every model shall have a unique version.

Model metadata shall include:

- model version;
- parent version;
- algorithm;
- feature-schema version;
- training round;
- participating clients;
- evaluation metrics;
- creation timestamp.

A forecast shall always reference the model version used to generate it.

---

# 34. Reproducibility

The following shall be version controlled:

- synthetic data generator;
- random seeds;
- institution profiles;
- feature dictionary;
- model configuration;
- federation configuration;
- evaluation configuration;
- shift-detector parameters;
- uncertainty method;
- experiment results.

A complete experiment shall be reproducible from its configuration.

---

# 35. Deployment Architecture

The prototype shall use containerized services.

Recommended deployment:

```text
Docker Compose
│
├── coordinator
├── institution-a
├── institution-b
├── institution-c
├── institution-d
├── backend-api
├── database
└── frontend
```

The four institution containers represent isolated local nodes.

Their local storage shall be separated from the central database.

The central database shall store only permitted metadata, forecasts, alerts, model metadata, and audit information.

---

# 36. Recommended Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React / Next.js |
| Visualization | Recharts or Plotly |
| Backend | Python + FastAPI |
| Federated Learning | Flower (`flwr`) |
| ML | scikit-learn and/or PyTorch |
| Database | PostgreSQL |
| Containerization | Docker / Docker Compose |
| API Format | REST/JSON |
| Authentication | Token-based authentication with role-based authorization |
| Testing | pytest + integration test framework |

The exact model library shall depend on the final model selected through the evaluation process.

---

# 37. End-to-End Operational Flow

```text
1. Institution receives local synthetic data
          ↓
2. Local schema validation
          ↓
3. Local cleaning and aggregation
          ↓
4. Local feature generation
          ↓
5. Privacy gate
          ↓
6. Local model training
          ↓
7. Model update validation
          ↓
8. Federated coordinator aggregation
          ↓
9. Global model version created
          ↓
10. Global forecast generated
          ↓
11. Prediction intervals generated
          ↓
12. Distribution shift evaluated
          ↓
13. Alert candidate created if warranted
          ↓
14. Human reviewer examines evidence
          ↓
15. Reviewer approves/rejects
          ↓
16. Decision and system events audited
```

---

# 38. Testing Architecture

## 38.1 Unit Tests

Test:

- feature generation;
- aggregation;
- privacy checks;
- suppression;
- forecasting;
- shift detection;
- uncertainty;
- API validation.

## 38.2 Integration Tests

Test:

- local node → coordinator;
- coordinator → global model;
- global model → forecast;
- forecast → alert;
- alert → reviewer;
- reviewer → audit log.

## 38.3 Privacy Tests

Test:

- row-level payload rejection;
- forbidden-field detection;
- small-group suppression;
- leakage experiment;
- central database inspection.

## 38.4 Federated Tests

Test:

- normal four-client round;
- one client failure;
- invalid client update;
- duplicate update;
- version mismatch;
- recovery.

## 38.5 ML Tests

Test:

- temporal leakage;
- held-out performance;
- cross-institution performance;
- forecast horizon;
- calibration/interval coverage;
- distribution shift.

---

# 39. Live Demonstration Design

## Scenario 1 — Four-Institution Federation

Initial state:

```text
A ✓
B ✓
C ✓
D ✓
```

Demonstrate:

- local datasets;
- no raw rows entering coordinator;
- training round;
- global model generation;
- audit record.

Pass condition:

> No row-level records are transmitted or stored centrally.

## Scenario 2 — Regional Demand Surge

Initial:

```text
Normal demand
```

Action:

```text
Inject regional surge
```

Expected:

```text
Observed demand rises
       ↓
Residual rises
       ↓
Shift detector triggers
       ↓
Forecast updates
       ↓
Uncertainty displayed
       ↓
Alert candidate created
```

## Scenario 3 — Missing Node

Initial:

```text
A ✓ B ✓ C ✓ D ✓
```

Action:

```text
C disconnects mid-round
```

Expected:

```text
C marked failed
       ↓
Round continues with valid clients
       ↓
Global model produced
       ↓
Failure logged
```

## Scenario 4 — Small-Group Query

Action:

```text
Reviewer requests protected small-group result
```

Expected:

```text
Query rejected/suppressed
       ↓
Protected value not revealed
       ↓
Privacy event logged
```

---

# 40. Unseen Scenario / Qualification Testing

The implementation shall not hard-code the prepared demonstration.

The test harness shall support changed inputs such as:

- different surge magnitude;
- different surge timing;
- different institution;
- different syndrome category;
- different missing node;
- different forecast horizon;
- different population distribution;
- different missingness pattern.

The system must respond using the actual forecasting, federation, privacy, and detection logic.

---

# 41. Requirements-to-Design Traceability

| SRS Area | Technical Design |
|---|---|
| Four simulated institutions | Institution Node Architecture |
| Non-identical populations | Institution Simulation Design |
| Local row-level retention | Local Data Boundary |
| Aggregate features | Feature Engineering Pipeline |
| Federated training | Federated Learning Architecture |
| 7–14 day forecast | Forecast Construction |
| Distribution shift | Shift Detection |
| Uncertainty | Uncertainty Estimation |
| Privacy suppression | Small-Group Suppression |
| Privacy leakage | Privacy Leakage Testing |
| Missing-node resilience | Failure and Recovery |
| Human review | Review Workflow |
| Auditability | Audit Service / Audit Database |
| Local baseline | Baseline A |
| Federated baseline | Baseline B |
| Pooled upper bound | Baseline C |
| Held-out evaluation | Train/Validation/Test Strategy |
| Unseen testing | Qualification Testing |
| Live demonstration | Demonstration Design |

---

# 42. Key Configuration Parameters

The following shall be configurable rather than hard-coded:

```text
MIN_GROUP_SIZE
FORECAST_HORIZON
FEDERATION_ROUNDS
CLIENT_TIMEOUT
SHIFT_DETECTION_THRESHOLD
SHIFT_PERSISTENCE
UNCERTAINTY_LEVEL
MODEL_VERSION
FEATURE_SCHEMA_VERSION
RANDOM_SEED
```

Configuration changes shall be recorded for reproducibility.

---

# 43. Design Decisions and Rationale

## Decision 1 — Aggregate Forecast Target

**Decision:** Forecast daily aggregate syndrome-category service demand.

**Reason:** It directly addresses the S5 forecasting objective while avoiding individual clinical prediction.

## Decision 2 — Four Simulated Nodes

**Decision:** Use four isolated simulated institutions.

**Reason:** It satisfies the distributed-institution requirement and enables non-IID and missing-node experiments.

## Decision 3 — FedAvg as Initial Aggregator

**Decision:** Use FedAvg as the first federated aggregation mechanism.

**Reason:** It provides a clear, interpretable baseline for collaborative model training. More advanced aggregation can be evaluated later if justified.

## Decision 4 — Statistical Shift Detection

**Decision:** Start with residual-based detection such as CUSUM.

**Reason:** It is interpretable, testable, and directly connected to the forecast residual.

## Decision 5 — Human Review

**Decision:** Treat algorithmic alerts as review candidates.

**Reason:** The system is decision support rather than autonomous public-health decision-making.

## Decision 6 — Pooled Model as Offline Benchmark

**Decision:** Maintain a pooled-data model only for evaluation.

**Reason:** It provides an upper-bound benchmark without changing the privacy-preserving operational architecture.

---

# 44. Implementation Order

The implementation should proceed in dependency order:

### Stage 1 — Data Foundation

- synthetic generator;
- four institution profiles;
- local storage;
- aggregate target;
- feature schema.

### Stage 2 — Local ML

- feature pipeline;
- local forecasting;
- temporal evaluation;
- baseline metrics.

### Stage 3 — Federation

- client registration;
- coordinator;
- training rounds;
- FedAvg;
- model versioning.

### Stage 4 — Forecast Intelligence

- 7–14 day forecast;
- uncertainty;
- distribution-shift detector.

### Stage 5 — Privacy

- pre-transmission gate;
- suppression;
- privacy events;
- leakage experiments.

### Stage 6 — Governance

- alerts;
- reviewer workflow;
- audit logs.

### Stage 7 — Dashboard

- forecasts;
- uncertainty;
- shift alerts;
- federation status;
- privacy events;
- review queue.

### Stage 8 — Resilience

- client disconnect;
- invalid update;
- recovery;
- unseen scenarios.

### Stage 9 — Evaluation

- local-only;
- federated;
- pooled upper bound;
- held-out test;
- cross-institution metrics.

### Stage 10 — Final Demonstration

Execute the four official scenarios and qualification/unseen-input tests.

---

# 45. Final Technical Acceptance Criteria

The implementation is technically acceptable when all of the following are demonstrated:

1. Four simulated institutions participate in federation.
2. Institution populations are demonstrably non-identical.
3. Raw row-level data remains inside local nodes.
4. Central APIs cannot receive raw row-level records.
5. Aggregate features are generated locally.
6. Federated training produces a global model.
7. Local-only and pooled baselines can be evaluated.
8. The system produces forecasts for the requested 7–14 day horizon.
9. Forecasts include uncertainty information.
10. Distribution shifts can be detected on injected scenarios.
11. A missing institution does not cause silent corruption of the training round.
12. Invalid model updates are rejected.
13. Small-group outputs are suppressed.
14. Privacy events are logged.
15. Reviewer decisions are logged.
16. No individual diagnosis or individual risk score is produced.
17. Forecast performance is measured on held-out data.
18. Federated performance is compared with local-only performance.
19. Cross-institution performance is reported.
20. Privacy leakage testing is performed.
21. The four official demonstration scenarios pass.
22. The system responds to changed/unseen inputs without hard-coded demo behavior.

---

# 46. Conclusion

HealthSignal is designed as a privacy-preserving federated forecasting platform in which decentralized institutions collaborate without centralizing row-level records.

The technical architecture separates local data processing from central coordination, explicitly enforces a privacy boundary, and provides a complete path from local observations to aggregate forecasting, uncertainty estimation, distribution-shift detection, human review, and auditability.

The three-baseline evaluation design allows the project to measure whether federated collaboration improves forecasting relative to local-only training while retaining the pooled-data model as an offline upper-bound benchmark.

The design is intended to provide a clear implementation contract for the HealthSignal prototype while preserving the safety, privacy, evaluation, resilience, and human-oversight requirements defined by the S5 problem statement.

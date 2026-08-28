---
status: Competition-ready implementation blueprint
subtitle: Federated Community Health Trend Forecasting
title: HealthSignal --- Final Master Solution
version: Final Master Solution --- 28 August 2026
---

# 1. Executive Decision

## Recommendation

**PROCEED with HealthSignal.**

The solution is a strong fit for the S5 problem statement because it
directly addresses the central constraint: multiple community-health
institutions need to learn regional service-demand trends without
centralizing row-level records.

The final solution is deliberately framed as a **privacy-preserving
public-health forecasting and decision-support system**, not as a
diagnosis engine.

The most important design principle is:

> **Raw rows stay local. Only approved aggregate information and
> privacy-filtered model updates cross the institutional boundary.
> Forecasts are aggregate, uncertainty is explicit, anomalies are
> evidence for review, and no operational alert becomes actionable
> without human public-health approval.**

This version keeps the scope feasible for a competition prototype while
making the architecture defensible under the qualification test.

------------------------------------------------------------------------

# 2. Problem Statement Being Solved

Community clinics and health centers can observe local changes in
symptoms, service demand, or syndrome categories before a regional
system reacts. However, raw records cannot simply be pooled because of
privacy, governance, and institutional-boundary constraints.

HealthSignal solves this by allowing at least four institutions to
collaborate through federated learning:

``` text
Institution A ─┐
Institution B ─┤
Institution C ─┼──> Federated Coordinator ──> Global Forecast Model
Institution D ─┘
      │
      └── Raw row-level records never leave the institution
```

The system:

1.  keeps row-level data at each local institution;
2.  converts local records into approved aggregate features;
3.  trains a shared forecasting model through federated rounds;
4.  forecasts aggregate syndrome-category/service demand for 7--14 days;
5.  reports calibrated uncertainty;
6.  detects distribution shifts and demand surges;
7.  enforces small-group privacy suppression;
8.  handles missing institutions and invalid updates safely;
9.  presents alerts as reviewer candidates;
10. records training, privacy, failure, and reviewer events in an audit
    trail.

------------------------------------------------------------------------

# 3. Final Scope

## 3.1 In scope

-   Four or more simulated institutions.
-   Non-identical/non-IID synthetic populations.
-   Local row-level storage.
-   Local preprocessing and aggregate feature generation.
-   Privacy boundary enforcement.
-   Federated model training.
-   Local-only baseline.
-   Federated model.
-   Pooled-data upper-bound benchmark for evaluation only.
-   7--14 day aggregate demand forecasting.
-   Distribution-shift detection.
-   Regional demand-surge simulation.
-   Forecast uncertainty.
-   Missing-node recovery.
-   Invalid-update rejection.
-   Minimum-group-size suppression.
-   Privacy leakage testing.
-   Human reviewer workflow.
-   Audit logging.
-   Dashboard and exports.
-   Model cards and data cards.
-   Qualification-test readiness.

## 3.2 Explicitly out of scope

-   Individual diagnosis.
-   Individual risk scoring.
-   Patient-level prediction.
-   Central storage of identifiable records.
-   Re-identification.
-   Clinical treatment recommendations.
-   Automatic emergency dispatch.
-   Automatic external communication of alerts.
-   Integration with real hospital records for the competition
    prototype.
-   Claiming that federated learning alone provides formal privacy.
-   Claiming formal differential privacy unless a measured DP mechanism
    and privacy budget are actually implemented.

This boundary is a major strength of the project because it prevents the
system from drifting into an unsafe clinical product.

------------------------------------------------------------------------

# 4. Core Innovation / Novelty

## 4.1 What is genuinely novel

The novelty should **not** be presented as inventing a new
federated-learning algorithm. FedAvg, CUSUM, prediction intervals, and
minimum-group-size suppression are established techniques.

The stronger novelty is the **system-level combination and
demonstration** of:

### A. Privacy-first federated public-health forecasting

The system connects decentralized community-health observations to
regional forecasting without moving raw rows.

### B. Privacy is enforced as an architectural boundary

Privacy is not only a policy statement.

Each institution has a local boundary:

``` text
LOCAL NODE
├── raw records
├── preprocessing
├── feature generation
├── local training
└── outbound privacy gate
        │
        ├── allowed aggregate/update
        └── rejected payload
```

A hard pre-transmission validator prevents row-level-shaped payloads
from being sent.

### C. Federated forecasting + anomaly detection + uncertainty

The platform does not stop at "train a federated model."

It connects:

``` text
Federated learning
        ↓
7–14 day forecasting
        ↓
Prediction uncertainty
        ↓
Residual/distribution-shift detection
        ↓
Evidence-backed alert candidate
        ↓
Human review
```

This complete operational loop is the strongest differentiator.

### D. Three-way evaluation

The project evaluates:

``` text
Local-only model
       vs
Federated model
       vs
Pooled-data upper-bound benchmark
```

The pooled model is not a deployment mode.

This lets the team answer the important question:

> "Does privacy-preserving collaboration actually improve forecasting
> compared with each institution working alone?"

### E. Built-in resilience

A participating institution can disappear during a training round.

The system:

``` text
Round starts
   ↓
Node disconnects
   ↓
Timeout
   ↓
Node marked missing
   ↓
Check minimum participation
   ↓
Continue with valid nodes
   ↓
Aggregate
   ↓
Complete round
```

No fake update is generated for the missing institution.

### F. Qualification-test robustness

The solution is explicitly designed for judges changing an input,
participant, constraint, or system state that was not used in the
prepared demo.

The implementation must calculate outputs from actual data and model
logic rather than hard-coded demonstration values.

### G. Human-in-the-loop governance

The model never directly declares an operational public-health action.

It produces evidence:

-   forecast;
-   uncertainty;
-   shift score;
-   coverage status;
-   affected institution/region;
-   model version.

A reviewer then approves, rejects, or requests more evidence.

------------------------------------------------------------------------

# 5. What Is NOT Novel --- and How to Present It

Be honest during judging.

Do not say:

-   "We invented federated learning."
-   "We invented differential privacy."
-   "CUSUM is our new algorithm."
-   "Our model guarantees privacy because it is federated."
-   "The system predicts disease in individuals."

Instead say:

> "Our novelty is the privacy-first integration of federated
> community-level forecasting, calibrated uncertainty,
> distribution-shift detection, resilience, privacy enforcement, and
> human review into one auditable workflow designed around the S5
> constraints."

That is a much more defensible innovation claim.

------------------------------------------------------------------------

# 6. Final System Architecture

``` text
                         HEALTHSIGNAL
                              │
          ┌───────────────────┴───────────────────┐
          │                                       │
     LOCAL INSTITUTIONS                    CENTRAL SERVICES
          │                                       │
   ┌──────┼──────┬──────┐             ┌───────────┼───────────┐
   │      │      │      │             │           │           │
 Node A Node B Node C Node D       Coordinator  Forecast   Dashboard
   │      │      │      │             │           │           │
   │      │      │      │             │           │           │
 Raw    Raw    Raw    Raw             │           │           │
 Data   Data   Data   Data            │           │           │
   │      │      │      │             │           │           │
 Local preprocessing                 │           │           │
   │      │      │      │             │           │           │
 Aggregate features                 │           │           │
   │      │      │      │             │           │           │
 Privacy gate                        │           │           │
   └──────┼──────┼──────┘             │           │           │
          └──────┴────────────────────┘           │           │
                 Model updates                    │           │
                                                  │           │
                                      Global model version    │
                                                  │           │
                                      Forecast + uncertainty  │
                                                  │           │
                                      Shift detection         │
                                                  │           │
                                      Alert candidate ────────┤
                                                              │
                                                   Human Reviewer
                                                              │
                                                   Approve/Reject
                                                              │
                                                         Audit Log
```

------------------------------------------------------------------------

# 7. Institution Node Design

Each institution is an isolated service/container.

## 7.1 Local storage

``` text
institution-a/
├── raw/
├── processed/
├── features/
├── models/
└── local_config/
```

The raw directory must never be mounted into the central service.

The central database must not contain patient-level tables.

## 7.2 Local pipeline

``` text
Raw synthetic records
        ↓
Schema validation
        ↓
Data-quality checks
        ↓
Local preprocessing
        ↓
Approved feature dictionary
        ↓
Aggregation
        ↓
Privacy filter
        ↓
Local training
        ↓
Outbound update validation
        ↓
Coordinator
```

------------------------------------------------------------------------

# 8. Synthetic Data Strategy

The competition prototype should use synthetic data.

## 8.1 Why synthetic data

It allows:

-   controlled privacy;
-   reproducibility;
-   injected events;
-   known ground truth;
-   held-out testing;
-   safe demonstration;
-   non-identical institutional populations.

## 8.2 Four institution profiles

Example:

  -------------------------------------------------------------------------------
  Institution   Population        Baseline demand     Seasonality           Surge
                profile                                               sensitivity
  ------------- ----------------- --------------- --------------- ---------------
  A             Urban clinic               Medium          Medium            High

  B             Community center              Low            High          Medium

  C             Large clinic                 High             Low            High

  D             Rural/community        Low-medium          Medium      Low-medium
                node                                              
  -------------------------------------------------------------------------------

These are intentionally different.

The goal is to create **non-IID data** without making institutions
statistically unrelated.

## 8.3 Suggested aggregate target

The target should be:

``` text
daily_service_demand
```

for categories such as:

``` text
respiratory
gastrointestinal
fever-like
other approved syndrome category
```

The target is a **population-level service-demand count**, not an
individual diagnosis.

------------------------------------------------------------------------

# 9. Approved Feature Dictionary

Only approved aggregate features should be used.

Example:

  Feature                  Meaning
  ------------------------ --------------------------------------------
  daily_total_visits       Total daily service volume
  respiratory_count        Aggregate respiratory-category volume
  gastrointestinal_count   Aggregate gastrointestinal-category volume
  fever_like_count         Aggregate fever-like volume
  rolling_3d_mean          Three-day aggregate moving average
  rolling_7d_mean          Seven-day aggregate moving average
  rolling_7d_std           Seven-day variability
  day_of_week              Temporal feature
  holiday_flag             Synthetic calendar feature
  lag_1                    Previous-day demand
  lag_7                    Same-day-of-week lag
  coverage_ratio           Completeness of participating institutions
  missing_node_count       Number of unavailable nodes

No name, phone number, address, patient ID, diagnosis code tied to a
person, or free-text clinical note is permitted to cross the local
boundary.

------------------------------------------------------------------------

# 10. Privacy Architecture

## 10.1 Important privacy correction

Federated learning is **not automatically private**.

A model update can potentially leak information.

Therefore HealthSignal uses multiple layers.

### Layer 1 --- Raw-row isolation

Raw records never leave local nodes.

### Layer 2 --- Aggregate feature generation

The local node converts records into aggregate features.

### Layer 3 --- Minimum-group-size suppression

Any output that could reveal information about a group smaller than the
configured threshold is suppressed or coarsened.

A proposed engineering default is:

``` text
k = 11
```

The value must remain configurable and documented.

### Layer 4 --- Contribution clipping

Local model/update contributions are bounded before transmission.

### Layer 5 --- Outbound payload validation

Every outbound payload is inspected.

Conceptually:

``` text
Payload
   ↓
Schema check
   ↓
Row-level structure check
   ↓
Allowed-feature check
   ↓
Size/value bounds
   ↓
Privacy rules
   ↓
ALLOW / REJECT
```

### Layer 6 --- Privacy event logging

Every suppression and rejected transmission is logged.

## 10.2 Differential privacy

Formal differential privacy is a **future enhancement unless implemented
and evaluated**.

Do not claim an epsilon guarantee without:

-   a defined mechanism;
-   sensitivity calculation;
-   noise calibration;
-   composition/accounting across rounds;
-   a documented privacy budget.

## 10.3 Secure aggregation

Secure aggregation is also a future enhancement unless actually
implemented.

The prototype's primary privacy claim is therefore:

> Raw rows remain local, permitted aggregate information is constrained,
> model updates are validated and bounded, small groups are suppressed,
> and privacy leakage is actively tested.

This wording is technically safer than claiming absolute privacy.

------------------------------------------------------------------------

# 11. Federated Learning Design

## 11.1 Round flow

``` text
Coordinator
    ↓
Broadcast global model
    ↓
A trains locally ─┐
B trains locally ─┤
C trains locally ─┼──> privacy-filtered updates
D trains locally ─┘
    ↓
Validate updates
    ↓
Aggregate valid updates
    ↓
Create global model version
    ↓
Evaluate
    ↓
Publish
```

## 11.2 Federated algorithm

Start with **FedAvg**.

Weighted aggregation:

``` text
w_global = Σ(n_i / N) * w_i
```

where:

-   `w_i` = local model parameters;
-   `n_i` = eligible local training size;
-   `N` = total eligible training size.

If the selected model is not parameter-based, use an equivalent
federated aggregation strategy documented in the experiment
configuration.

## 11.3 Why start simple

The competition objective is not to win on model complexity.

A simpler model that is:

-   interpretable;
-   reproducible;
-   fast;
-   robust;
-   easy to evaluate;

is preferable to a complex model that is difficult to defend.

------------------------------------------------------------------------

# 12. Forecasting Engine

## 12.1 Forecast target

Forecast:

> Aggregate daily syndrome-category/service-demand volume for the next
> 7--14 days.

Default:

``` text
7 days
```

Configurable up to:

``` text
14 days
```

## 12.2 Recommended initial model

Start with a strong classical baseline such as:

-   regularized regression;
-   lag features;
-   rolling statistics;
-   calendar features;
-   quantile/regression intervals where appropriate.

Only move to LSTM/TCN/PyTorch if experiments demonstrate a meaningful
benefit.

## 12.3 Baselines

### Baseline 1 --- Local-only

Each institution trains independently.

### Baseline 2 --- Federated

Institutions collaboratively train without centralizing raw rows.

### Baseline 3 --- Pooled upper bound

All data are pooled only for offline benchmarking.

The pooled model is **not** a deployment candidate.

------------------------------------------------------------------------

# 13. Uncertainty

Every forecast must contain uncertainty.

Example:

``` text
Day +1
Prediction: 132
80% interval: 121–145
95% interval: 114–152
```

The exact method can be selected after validation.

Possible implementation path:

1.  establish point forecast;
2.  calculate residual distribution;
3.  construct prediction intervals;
4.  evaluate empirical coverage;
5.  calibrate intervals on held-out data.

The system must explicitly indicate reduced confidence when:

-   an institution is missing;
-   the historical window is short;
-   data coverage is incomplete;
-   uncertainty becomes unusually high.

------------------------------------------------------------------------

# 14. Distribution-Shift / Surge Detection

The first implementation should use an interpretable residual-based
detector such as **CUSUM**.

Conceptually:

``` text
Observed demand
      -
Expected demand
      =
Residual
      ↓
CUSUM / shift score
      ↓
Threshold
      ↓
Normal / Watch / Alert candidate
```

The detector should not be a single hard-coded threshold on one point.

It should use a statistical evidence window.

## 14.1 Detection states

``` text
NORMAL
WATCH
ALERT_CANDIDATE
```

A high shift score is not itself a diagnosis.

------------------------------------------------------------------------

# 15. Alert Logic

A candidate alert should include:

-   alert ID;
-   timestamp;
-   affected region/institution;
-   syndrome/service category;
-   observed trend;
-   expected trend;
-   shift score;
-   uncertainty;
-   data coverage;
-   model version;
-   evidence window.

Then:

``` text
Algorithmic detection
        ↓
Alert candidate
        ↓
Human public-health reviewer
        ├── Approve
        ├── Reject
        └── Request more evidence
```

Only an approved alert becomes actionable.

------------------------------------------------------------------------

# 16. Human Review

The reviewer dashboard should show:

1.  forecast trend;
2.  uncertainty interval;
3.  shift score;
4.  historical baseline;
5.  coverage status;
6.  participating institutions;
7.  missing nodes;
8.  model version;
9.  evidence window;
10. reviewer decision controls.

The reviewer cannot modify model training parameters through the
ordinary alert-review interface.

------------------------------------------------------------------------

# 17. Missing-Node Resilience

Suppose four nodes begin a round:

``` text
A ✓
B ✓
C ✓
D ✓
```

Then C disconnects.

Expected behavior:

``` text
A ✓
B ✓
C ✗
D ✓
```

The coordinator:

1.  times out C;
2.  records C as missing;
3.  does not fabricate a C update;
4.  checks minimum participation;
5.  aggregates valid updates;
6.  completes the round if the threshold is satisfied;
7.  records the missing-node event;
8.  marks affected forecasts with coverage limitations;
9.  widens or flags uncertainty as appropriate.

If the minimum participation threshold is not satisfied:

``` text
Round = INCOMPLETE
No new global model
Reason logged
```

------------------------------------------------------------------------

# 18. Invalid Update Handling

Every received update should pass:

-   authentication;
-   schema validation;
-   parameter-shape validation;
-   numerical-value validation;
-   contribution bounds;
-   privacy checks.

Invalid update:

``` text
Receive
  ↓
Validate
  ↓
Invalid
  ↓
Reject
  ↓
Log
  ↓
Continue if minimum participation remains satisfied
```

------------------------------------------------------------------------

# 19. Dashboard

## 19.1 Main views

### Regional Overview

-   current demand;
-   7-day forecast;
-   uncertainty;
-   active/watch signals;
-   coverage.

### Institution View

Only authorized aggregate information.

### Alert Review

-   candidate alerts;
-   evidence;
-   reviewer action.

### Federation Status

``` text
Round 17
A ✓
B ✓
C ✗
D ✓
```

### Model Performance

-   MAE;
-   MAPE;
-   interval coverage;
-   detection recall;
-   lead time;
-   local vs federated uplift.

### Privacy Center

-   suppressed queries;
-   rejected payloads;
-   privacy-test results.

### Audit Log

-   rounds;
-   participants;
-   failures;
-   privacy events;
-   reviewer decisions.

------------------------------------------------------------------------

# 20. Small-Group Privacy

Every dashboard and export must enforce the same privacy rule.

Bad:

``` text
Region X
Patients = 4
```

Correct:

``` text
Region X
Patients = < minimum group size
```

or a safe coarsening such as a larger geography/time window.

The rule must be applied **at query time**, not merely hidden visually
after the database query.

Attempts to circumvent suppression must be rejected/coarsened and
logged.

------------------------------------------------------------------------

# 21. Central Database

No patient-level table should exist.

Suggested entities:

``` text
Institutions
FeatureDefinitions
TrainingRounds
RoundParticipants
ModelVersions
Forecasts
ShiftDetections
Alerts
ReviewerDecisions
PrivacyEvents
SystemFailures
AuditLogs
```

Example trace:

``` text
Forecast
  ↓
Model Version
  ↓
Training Round
  ↓
Participating Institutions
```

No trace should lead to an individual patient record.

------------------------------------------------------------------------

# 22. Auditability

Every major operation should produce a structured audit event.

Log:

-   training round;
-   start/end;
-   participants;
-   failures;
-   invalid updates;
-   privacy suppression;
-   rejected transmissions;
-   model version;
-   forecast generation;
-   alert generation;
-   reviewer decision;
-   export;
-   system errors.

Use chained/hash-linked records where practical so that tampering
becomes detectable.

------------------------------------------------------------------------

# 23. Authentication and Authorization

Minimum roles:

### Federated System Administrator

Can:

-   register institutions;
-   start/stop rounds;
-   view system status;
-   configure approved parameters.

### Public-Health Reviewer

Can:

-   inspect forecasts;
-   inspect alert evidence;
-   approve/reject/request more evidence.

### System Auditor

Can:

-   read audit records;
-   inspect traceability;
-   inspect privacy and system events.

The reviewer should not be able to silently change training
configuration.

------------------------------------------------------------------------

# 24. Recommended Technology Stack

  Layer                Technology
  -------------------- ---------------------------------------------------
  Frontend             React / Next.js
  Charts               Recharts / Plotly
  Backend              Python + FastAPI
  Federated Learning   Flower
  ML                   scikit-learn initially; PyTorch only if justified
  Database             PostgreSQL
  Containers           Docker + Docker Compose
  Testing              pytest
  API                  REST/JSON
  Authentication       Token-based + role-based authorization

This stack is intentionally conventional and feasible for a student
competition prototype.

------------------------------------------------------------------------

# 25. Deployment

Single-machine demonstration:

``` text
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

The local institution containers must have isolated storage.

The central database stores only approved central metadata/results.

------------------------------------------------------------------------

# 26. End-to-End Data Flow

``` text
Synthetic local records
        ↓
Institution node
        ↓
Validation
        ↓
Preprocessing
        ↓
Aggregate feature generation
        ↓
Minimum-group/privacy rules
        ↓
Local model training
        ↓
Contribution clipping
        ↓
Outbound payload validator
        ↓
Federated Coordinator
        ↓
Update validation
        ↓
FedAvg
        ↓
Global model
        ↓
7–14 day forecast
        ↓
Uncertainty estimation
        ↓
Residual/CUSUM shift detection
        ↓
Alert candidate
        ↓
Reviewer dashboard
        ↓
Human decision
        ↓
Audit log
```

------------------------------------------------------------------------

# 27. Mandatory Evaluation

## 27.1 Forecast accuracy

Report:

-   MAE;
-   MAPE where mathematically meaningful;
-   optionally RMSE;
-   institution-wise performance;
-   regional performance.

## 27.2 Event detection

Report:

-   recall;
-   precision/false-alert rate where possible;
-   lead time;
-   detection delay.

## 27.3 Federated uplift

Compare:

``` text
Federated MAE
vs
Local-only MAE
```

Useful uplift expression:

``` text
Uplift (%) =
(Local Error - Federated Error) / Local Error × 100
```

Also report the pooled benchmark.

Do not manufacture uplift. If federation does not improve on a
particular configuration, report it and explain why.

## 27.4 Uncertainty calibration

For an 80% interval:

``` text
Empirical coverage ≈ 80%
```

within a documented tolerance.

Similarly for a 95% interval.

## 27.5 Privacy

Test:

-   row-level transmission;
-   unauthorized payload shapes;
-   small-group queries;
-   query narrowing;
-   repeated queries;
-   membership-inference leakage where feasible.

## 27.6 Resilience

Measure:

-   successful recovery after node loss;
-   round completion;
-   no fabricated update;
-   coverage warning;
-   uncertainty change.

------------------------------------------------------------------------

# 28. Three-Way Experimental Design

Use identical held-out evaluation periods where possible.

``` text
                    Same held-out test set
                             │
          ┌──────────────────┼──────────────────┐
          ↓                  ↓                  ↓
     Local-only         Federated         Pooled upper bound
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ↓
                   Compare performance
```

This is one of the most important evidence pieces for the project.

------------------------------------------------------------------------

# 29. Live Demonstration

## Scenario 1 --- Federated Training

Show:

``` text
A ✓  B ✓  C ✓  D ✓
```

Then demonstrate:

-   local datasets exist;
-   raw rows remain local;
-   training round begins;
-   local training occurs;
-   privacy-filtered updates leave;
-   global model is produced;
-   audit entry appears.

**Judge-facing proof:** show a network/API log or automated test proving
that row-level payloads were never transmitted.

------------------------------------------------------------------------

## Scenario 2 --- Regional Demand Surge

Start with normal demand.

Inject a regional surge.

Expected:

``` text
Demand rises
   ↓
Forecast residual increases
   ↓
Shift score increases
   ↓
Detector enters WATCH/ALERT_CANDIDATE
   ↓
Forecast updates
   ↓
Uncertainty displayed
   ↓
Reviewer sees evidence
```

Do not hard-code "surge = alert."

The detector must calculate the change.

------------------------------------------------------------------------

## Scenario 3 --- Institution Drop

Start:

``` text
A ✓ B ✓ C ✓ D ✓
```

Disconnect C mid-round.

Expected:

``` text
C ✗
   ↓
Timeout
   ↓
C marked missing
   ↓
A/B/D updates validated
   ↓
Round completes if threshold met
   ↓
Coverage limitation shown
   ↓
Audit event recorded
```

------------------------------------------------------------------------

## Scenario 4 --- Small-Group Query

Attempt:

``` text
very narrow geography
+
very narrow time window
+
small group
```

Expected:

``` text
Query
 ↓
Privacy check
 ↓
Suppressed / coarsened
 ↓
Privacy event logged
```

The raw value must never appear briefly in the API response and then get
hidden only by the frontend.

------------------------------------------------------------------------

# 30. Qualification Test

The judges may change something that was not in the prepared demo.

Examples:

-   different institution;
-   different syndrome category;
-   different surge magnitude;
-   different surge timing;
-   different missing node;
-   different forecast horizon;
-   different query filter;
-   different threshold;
-   different participant state.

The system must:

1.  accept the valid changed input;
2.  recompute from actual logic;
3.  update the forecast;
4.  recompute uncertainty;
5.  recompute shift detection;
6.  preserve privacy rules;
7.  preserve human review;
8.  log the changed event.

## Critical implementation rule

Avoid code like:

``` python
if demo_mode:
    alert = True
```

Prefer:

``` python
score = detector.compute(observed, expected)

if score >= configured_threshold:
    create_alert_candidate(...)
```

The demo should be a real execution of the system.

------------------------------------------------------------------------

# 31. Testing Strategy

## Unit tests

Test:

-   validation;
-   aggregation;
-   feature generation;
-   clipping;
-   suppression;
-   shift detection;
-   uncertainty;
-   update validation.

## Integration tests

Test:

``` text
Institution
 → Coordinator
 → Global model
 → Forecast
 → Detector
 → Dashboard
```

## Privacy tests

Test:

-   raw-row payload rejection;
-   unauthorized fields;
-   small-group suppression;
-   query narrowing;
-   export suppression.

## ML tests

Test:

-   temporal holdout;
-   MAE/MAPE;
-   calibration;
-   institution-level performance;
-   regional performance;
-   shift recall/lead time.

## Failure tests

Test:

-   missing institution;
-   invalid update;
-   insufficient participants;
-   bad local data;
-   incomplete coverage;
-   high uncertainty.

------------------------------------------------------------------------

# 32. Reproducibility

Version control:

-   synthetic-data seed;
-   institution profiles;
-   feature schema;
-   model configuration;
-   federated configuration;
-   shift-detector threshold;
-   uncertainty method;
-   experiment configuration;
-   evaluation outputs.

A result should be reproducible from a recorded configuration.

------------------------------------------------------------------------

# 33. Model Card

Every final model should record:

-   model version;
-   training round;
-   participating institutions;
-   feature schema;
-   algorithm;
-   training configuration;
-   evaluation period;
-   MAE/MAPE;
-   uncertainty calibration;
-   detection performance;
-   known limitations;
-   intended use;
-   prohibited use.

------------------------------------------------------------------------

# 34. Data Card

Record:

-   synthetic-data generation method;
-   institution profiles;
-   date range;
-   syndrome/service categories;
-   non-IID design;
-   injected-event design;
-   missing-data scenarios;
-   privacy transformations;
-   limitations.

------------------------------------------------------------------------

# 35. Project Phases

## Phase 1 --- Data Foundation

Build:

-   synthetic generator;
-   four institution profiles;
-   local storage;
-   aggregate targets;
-   feature schema.

## Phase 2 --- Local ML

Build:

-   preprocessing;
-   feature pipeline;
-   local forecasting;
-   held-out evaluation.

## Phase 3 --- Federation

Build:

-   coordinator;
-   institution registration;
-   training rounds;
-   FedAvg;
-   model versioning.

## Phase 4 --- Intelligence

Build:

-   forecasting;
-   uncertainty;
-   CUSUM/shift detection;
-   baseline comparison.

## Phase 5 --- Governance

Build:

-   alerts;
-   reviewer workflow;
-   dashboard;
-   audit logs.

## Phase 6 --- Privacy and Failure Hardening

Build:

-   outbound payload validator;
-   minimum-group suppression;
-   clipping;
-   privacy tests;
-   missing-node recovery;
-   invalid-update handling.

## Phase 7 --- Evaluation and Demo

Complete:

-   benchmark;
-   privacy assessment;
-   model/data cards;
-   all four scenarios;
-   qualification-test variations.

------------------------------------------------------------------------

# 36. Mandatory Deliverables Checklist

  Deliverable               Status requirement
  ------------------------- ----------------------------
  Federated simulation      Must work
  Review dashboard          Must work
  Privacy assessment        Must contain test evidence
  Forecast benchmark        Must compare baselines
  Model/data cards          Must be included
  Four institutions         Must participate
  Non-IID populations       Must be demonstrable
  7--14 day forecast        Must work
  Uncertainty               Must be visible
  Surge detection           Must work
  Missing-node recovery     Must work
  Small-group suppression   Must work
  Audit trail               Must work
  Human review              Must be enforced

------------------------------------------------------------------------

# 37. Risks and Mitigations

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Federated model does not beat       Tune realistic cross-institution
  local-only                          correlation; simplify model;
                                      evaluate honestly

  Synthetic data is too artificial    Use different base rates,
                                      seasonality, correlations and
                                      realistic noise

  Privacy claim is overstated         Explicitly separate federated
                                      learning from formal DP; test
                                      leakage

  Detector creates false alerts       Calibrate on held-out data and
                                      report false-alert rate

  Judge changes input                 Use configurable, data-driven logic
                                      and hold-out qualification tests

  Node failure breaks demo            Test actual disconnect/recovery

  Dashboard accidentally leaks small  Apply suppression in backend/query
  groups                              layer and test exports

  Model is too complex                Start with classical model and add
                                      complexity only if justified

  Live demo fails                     Docker Compose one-command startup
                                      plus backup evidence

  Team cannot explain system          Keep architecture modular and
                                      document every stage
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 38. Feasibility Assessment

## Technical feasibility: HIGH

The architecture is feasible with:

-   Python;
-   FastAPI;
-   Flower;
-   scikit-learn;
-   PostgreSQL;
-   React;
-   Docker.

The project does not require a large GPU cluster.

## Data feasibility: HIGH

Synthetic data removes dependency on real patient records.

## ML feasibility: HIGH

The first version can use classical forecasting/regression rather than a
deep neural network.

## Federated-learning feasibility: HIGH

Four simulated clients are straightforward to run with Docker Compose.

## Privacy feasibility: MEDIUM-HIGH

The basic architecture is feasible.

However, formal privacy guarantees such as differential privacy and
secure aggregation should not be added as superficial buzzwords.
Implement them only if the team has enough time to test them properly.

## Dashboard feasibility: HIGH

The dashboard is standard application engineering.

## Competition-demo feasibility: HIGH

The four mandatory scenarios can be deterministically reproduced while
still remaining data-driven.

------------------------------------------------------------------------

# 39. Overall Quality Assessment

### Problem alignment: 10/10

The architecture directly follows the stated problem.

### Feasibility: 9/10

Very achievable with a disciplined scope.

### Technical depth: 9/10

Federated learning + forecasting + uncertainty + shift detection +
privacy + resilience is a substantial prototype.

### Novelty: 8/10

The novelty is strongest at the **system/workflow level**, not at the
individual-algorithm level.

### Safety/governance: 9.5/10

The explicit non-diagnostic boundary and human review are major
strengths.

### Demonstration strength: 9.5/10

The scenarios are highly visual and judge-friendly.

### Risk of overengineering: 7/10

The biggest danger is trying to implement everything in the SRS at
production depth.

------------------------------------------------------------------------

# 40. What We Should NOT Build First

Do not start with:

-   LSTM;
-   sophisticated transformer forecasting;
-   real hospital integration;
-   blockchain;
-   full cryptographic secure aggregation;
-   formal differential privacy accounting;
-   mobile application;
-   cloud-scale deployment.

Start with the smallest end-to-end system:

``` text
4 nodes
 ↓
local aggregation
 ↓
FedAvg
 ↓
7-day forecast
 ↓
uncertainty
 ↓
CUSUM
 ↓
privacy suppression
 ↓
review dashboard
```

Then harden it.

------------------------------------------------------------------------

# 41. Recommended MVP

The first working version should contain exactly:

1.  Four local nodes.
2.  Synthetic non-IID data.
3.  Local aggregate features.
4.  One simple forecasting model.
5.  FedAvg.
6.  Local-only baseline.
7.  Pooled benchmark.
8.  7-day forecast.
9.  Prediction interval.
10. CUSUM shift detector.
11. Surge injection.
12. Missing-node simulation.
13. Minimum-group suppression.
14. Outbound payload validator.
15. Reviewer dashboard.
16. Audit log.

Once this works end-to-end, add improvements.

------------------------------------------------------------------------

# 42. Final Judge Pitch

A concise explanation:

> "HealthSignal allows multiple community-health institutions to learn
> regional service-demand trends without sending their raw records to a
> central system. Each institution keeps its data locally, creates
> approved aggregate features, trains locally, and sends only
> privacy-filtered contributions through a controlled federated
> pipeline. The shared model forecasts the next 7--14 days, reports
> uncertainty, and detects abnormal shifts such as a regional demand
> surge. If an institution drops during training, the system recovers
> without fabricating its contribution. If a user tries to query a small
> group, the system suppresses the result at the backend and records the
> privacy event. Most importantly, an algorithmic alert is never treated
> as a public-health decision by itself --- a human reviewer must
> examine the evidence and approve it. We evaluate the system against
> local-only and pooled-data baselines to prove whether
> privacy-preserving collaboration actually provides useful forecasting
> value."

------------------------------------------------------------------------

# 43. Final Technical Acceptance Criteria

The implementation is accepted only if all are true:

-   [ ] Four simulated institutions participate.
-   [ ] Institution populations are demonstrably non-identical.
-   [ ] Raw row-level data remains local.
-   [ ] Central APIs cannot receive raw row-level records.
-   [ ] Aggregate features are generated locally.
-   [ ] Federated training creates a global model.
-   [ ] Local-only baseline exists.
-   [ ] Pooled benchmark exists only for offline comparison.
-   [ ] Forecast horizon is 7--14 days.
-   [ ] Forecasts include uncertainty.
-   [ ] Shift detection works on injected events.
-   [ ] Missing-node recovery works.
-   [ ] Invalid updates are rejected.
-   [ ] Small-group outputs are suppressed.
-   [ ] Privacy events are logged.
-   [ ] Reviewer decisions are logged.
-   [ ] No individual diagnosis exists.
-   [ ] No individual risk score exists.
-   [ ] No re-identification function exists.
-   [ ] Forecast accuracy is evaluated on held-out data.
-   [ ] Federated vs local performance is reported.
-   [ ] Cross-institution performance is reported.
-   [ ] Privacy leakage testing is performed.
-   [ ] All four official demo scenarios pass.
-   [ ] At least one unrehearsed variation of each scenario passes.
-   [ ] No demo behavior depends on hard-coded output values.

------------------------------------------------------------------------

# 44. Final Call

**Proceed with HealthSignal.**

The project is technically feasible, strongly aligned with the problem
statement, and sufficiently differentiated for a competition if the team
demonstrates the complete workflow rather than merely showing a
federated-learning notebook.

The winning strategy is not "more AI."

It is:

``` text
PRIVACY
   +
FEDERATED COLLABORATION
   +
FORECASTING
   +
UNCERTAINTY
   +
ANOMALY DETECTION
   +
RESILIENCE
   +
HUMAN REVIEW
   +
AUDITABILITY
```

The most important implementation rule is to build the **real end-to-end
pipeline first** and only then add sophistication.

------------------------------------------------------------------------

# 45. Final Architecture in One View

``` text
             ┌─────────────────────────────────────┐
             │       COMMUNITY INSTITUTIONS        │
             │                                     │
             │ A       B       C       D           │
             │ │       │       │       │           │
             │ Raw     Raw     Raw     Raw         │
             │ │       │       │       │           │
             │ Local preprocessing                 │
             │ │       │       │       │           │
             │ Aggregate features                  │
             │ │       │       │       │           │
             │ Privacy + clipping + validation     │
             └───────┬───────┬───────┬─────────────┘
                     │       │       │
                     └───────┼───────┘
                             ↓
                  ┌────────────────────┐
                  │ FEDERATED          │
                  │ COORDINATOR        │
                  │                    │
                  │ validate updates   │
                  │ FedAvg              │
                  │ model versioning   │
                  │ failure handling   │
                  └─────────┬──────────┘
                            ↓
                  ┌────────────────────┐
                  │ FORECAST ENGINE    │
                  │                    │
                  │ 7–14 day forecast  │
                  │ uncertainty        │
                  └─────────┬──────────┘
                            ↓
                  ┌────────────────────┐
                  │ SHIFT DETECTOR     │
                  │                    │
                  │ residual/CUSUM     │
                  │ surge detection    │
                  └─────────┬──────────┘
                            ↓
                  ┌────────────────────┐
                  │ REVIEW DASHBOARD   │
                  │                    │
                  │ evidence           │
                  │ uncertainty        │
                  │ coverage           │
                  │ alert candidate    │
                  └─────────┬──────────┘
                            ↓
                  ┌────────────────────┐
                  │ HUMAN REVIEWER     │
                  │                    │
                  │ APPROVE            │
                  │ REJECT             │
                  │ MORE EVIDENCE      │
                  └─────────┬──────────┘
                            ↓
                  ┌────────────────────┐
                  │ AUDIT + GOVERNANCE │
                  └────────────────────┘
```

# 46. End State

HealthSignal should be presented as:

> **A privacy-first federated public-health intelligence platform that
> forecasts aggregate community health-service pressure across
> decentralized institutions while preserving local data ownership,
> quantifying uncertainty, detecting emerging distribution shifts,
> surviving participant failures, suppressing privacy-sensitive outputs,
> and keeping humans in control of operational decisions.**

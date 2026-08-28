# HealthSignal — Implementation Plan
## Data Collection Layer First

**Document status:** Working implementation plan  
**Master solution ref:** HealthSignal Final Master Solution — 28 August 2026  
**Scope:** All three phases of data collection, ordered by implementation priority  
**Core constraint:** Raw row-level records must never leave the institution. Only approved aggregate features cross the privacy boundary.

---

## Part 0 — Read This Before Writing Any Code

The master solution gives one rule that overrides all other decisions:

> **Raw rows stay local. Only approved aggregate information and privacy-filtered model updates cross the institutional boundary.**

Every table you design, every API endpoint you write, every job you schedule must be checked against this rule. If a payload could contain a row-level record, it must be blocked at the outbound validator — not just hidden in the frontend.

The second rule is equally important:

> **The data model is source-agnostic from day one.**

You are not building a community symptom form. You are building the extensible aggregate pipeline that community reporting, doctor observations, clinic demand, pharmacy demand, testing data, absenteeism, environmental signals, and wastewater surveillance will all eventually feed into. The form is just the first data source that writes into this pipeline.

Everything else follows from these two rules.

---

## Part 1 — The Canonical Data Model

Design this schema before writing any application code. All three phases of data collection produce rows in the same two tables.

### 1.1 Raw Symptom Record (local only — never transmitted)

```
symptom_report
├── report_id          UUID, primary key
├── reported_at        TIMESTAMP
├── node_id            FK → node registry
├── data_source        ENUM: community | doctor | clinic | pharmacy | testing
│                            | absenteeism | emergency | environmental | wastewater
├── age_band           ENUM: 0-4 | 5-14 | 15-29 | 30-44 | 45-59 | 60+
├── sex                ENUM: M | F | other | prefer_not_to_say
├── symptoms[]         ARRAY of symptom ENUM values
├── syndrome           ENUM: fever_like | respiratory | gastrointestinal
│                            | neurological | dermatological | other
├── symptom_onset      DATE
├── severity           ENUM: mild | moderate | severe
└── consent_token      HASH (audit only; not linkable to individual)
```

This table lives inside the institution node container. It is never mounted, joined, or queried from the central service.

### 1.2 Canonical Aggregate Record (crosses the privacy boundary)

This is the unit of federated collaboration. Every data source in every phase produces rows in this table after aggregation and privacy filtering.

```
aggregate_signal
├── record_id          UUID, primary key
├── data_source        ENUM: community | doctor | clinic | pharmacy | testing
│                            | absenteeism | emergency | environmental | wastewater
├── date               DATE  (day-level granularity only)
├── node_id            FK → node registry
├── zone_id            FK → geographic zone
├── syndrome           ENUM: fever_like | respiratory | gastrointestinal
│                            | neurological | dermatological | other
├── count              INTEGER
├── severity_mild      INTEGER
├── severity_moderate  INTEGER
├── severity_severe    INTEGER
├── growth_rate_7d     FLOAT  (week-over-week, computed locally)
├── rolling_3d_mean    FLOAT
├── rolling_7d_mean    FLOAT
├── rolling_7d_std     FLOAT
├── coverage_ratio     FLOAT  (fraction of expected nodes reporting)
├── privacy_k          INTEGER  (k-anonymity threshold applied; NULL = not computed)
└── created_at         TIMESTAMP
```

Adding a new data source in a later phase means inserting rows with a new `data_source` value. No schema migration is required.

### 1.3 Symptom → Syndrome Mapping

Stored as a versioned config file (`syndrome_map.yaml`), not hardcoded. Editable by the epidemiology team without a code deploy.

| Reported symptom | Syndrome |
|---|---|
| fever, chills, body ache, fatigue | fever_like |
| cough, sore throat, runny nose, shortness of breath, chest pain | respiratory |
| nausea, vomiting, diarrhea, abdominal pain | gastrointestinal |
| headache, confusion, stiff neck, seizure | neurological |
| rash, itching, skin lesion | dermatological |
| anything else | other |

One report can map to multiple syndromes. Each syndrome is counted independently in its own aggregate row.

### 1.4 Supporting Registry Tables (central — no patient data)

```
node                  institution/facility registry
zone                  geographic zone hierarchy
feature_definitions   approved aggregate features and their validation rules
```

The central database must not contain any patient-level table. The complete list of permitted central entities is: `Institutions`, `FeatureDefinitions`, `TrainingRounds`, `RoundParticipants`, `ModelVersions`, `Forecasts`, `ShiftDetections`, `Alerts`, `ReviewerDecisions`, `PrivacyEvents`, `SystemFailures`, `AuditLogs`.

---

## Part 2 — Privacy Architecture (applies to every phase)

Privacy is an architectural boundary, not a policy statement. Every data source added in every phase must pass through all six layers before its aggregates leave the node.

```
Layer 1 — Raw-row isolation
          Raw records never leave local nodes. Period.

Layer 2 — Aggregate feature generation
          The node converts records into approved aggregate features
          before anything moves toward the coordinator.

Layer 3 — Minimum-group-size suppression
          k = 11 (configurable, documented)
          Any cell with count < k is suppressed — not zeroed, not
          hidden in the frontend after the API returns it. Omitted
          entirely from the outbound payload.

Layer 4 — Contribution clipping
          Local model/update contributions are bounded before
          transmission to limit the influence of any single node.

Layer 5 — Outbound payload validator
          Every outbound payload is inspected before leaving the node:

          Payload
            ↓ Schema check
            ↓ Row-level structure check (reject if payload is shaped
              like individual records)
            ↓ Allowed-feature check (against FeatureDefinitions)
            ↓ Size and value bounds
            ↓ Privacy rules
            ↓ ALLOW / REJECT + LOG

Layer 6 — Privacy event logging
          Every suppression and every rejected transmission is logged
          to the central AuditLog with timestamp, node, reason, and
          field list — never the suppressed values.
```

Do not claim formal differential privacy unless you implement a defined mechanism with sensitivity calculation, noise calibration, composition accounting across rounds, and a documented privacy budget.

---

## Part 3 — Pipeline Flow (same for every data source)

```
Data source input (form / API / file / sensor)
      ↓
Schema validation
      ↓
Data-quality checks
      ↓
symptom_report table   ← local only, never transmitted
      ↓
Symptom → Syndrome mapping   ← syndrome_map.yaml
      ↓
Daily aggregation job   ← runs at 00:00 local time
      ↓
┌──────────────────────────────────┐
│  aggregate_signal rows           │
│  ─────────────────────────────   │
│  fever_like count                │
│  respiratory count               │
│  gastrointestinal count          │
│  severity distribution           │
│  growth_rate_7d                  │
│  rolling_3d_mean / 7d_mean / std │
└──────────────────────────────────┘
      ↓
Privacy filter (k-anonymity + clipping)
      ↓
Outbound payload validator
      ↓
Federated Coordinator (FedAvg)
      ↓
7–14 day forecast + uncertainty
      ↓
Residual / CUSUM shift detection
      ↓
Alert candidate → Human reviewer
      ↓
Audit log
```

---

## Part 4 — Implementation Phases

### Phase 1 — Core Data Collection

These are the five sources that produce the densest, most reliable syndromic signal. They share one pipeline and one schema.

---

#### Module 1 — Community Symptom Collection

**Why first:** Establishes the entire pipeline, data model, privacy layer, aggregation job, and outbound validator. Everything built here is reused by modules 2–11.

**Data collected (local only):**
- Age band, sex, symptom checklist, onset date, severity, zone

**Do not collect:** Name, address, phone, exact date of birth, precise GPS, free-text clinical notes.

**Input surface:**
- Web form (mobile-first, offline-capable via service worker + IndexedDB sync queue)
- USSD/SMS fallback for low-connectivity nodes (numeric codes map to symptom groups)

**Form fields (minimum viable):**

```
1. Approximate age band        dropdown
2. Sex                         radio
3. Symptoms experienced        multi-select checklist
4. When did symptoms start?    date picker; max 7 days ago
5. Severity today              mild / moderate / severe
6. Your location zone          dropdown or auto-detect
```

**Consent:** Required before submission. Plain language. Explain what is collected, what is not, and that individual reports are never shared.

**Aggregation job output:** One `aggregate_signal` row per syndrome per node per day, for `data_source = 'community'`.

**Definition of done:**
- Community member can submit via web form and USSD fallback
- Daily aggregation job runs automatically
- No row with count < k is written to the federated feature table
- All raw `symptom_report` rows remain in the local database

---

#### Module 2 — Doctor / Health-Worker Observations

**What changes from Module 1:** Input surface. The data model, aggregation job, privacy layer, and outbound validator are identical.

**Input surface:** Clinician-facing form or structured API endpoint. Authentication required (role: health-worker).

**Additional fields clinicians can record:**
- Clinical impression syndrome (from approved ENUM — no free-text diagnosis)
- Visit type: walk-in | referred | follow-up
- Patient age band and sex (already in schema)

**Aggregation job output:** Rows in `aggregate_signal` with `data_source = 'doctor'`. Same syndrome ENUM, same severity fields, same privacy rules.

**Key constraint:** Clinicians report syndrome categories, not diagnoses. The form must not present ICD codes or disease names as options.

---

#### Module 3 — Clinic / Hospital Service Demand

**What changes:** Source is an institution's existing visit/admission count, not a submitted form.

**Input surface:** Nightly extract from the institution's local records system, or a simple daily count entry form for clinics without an EMR.

**Fields extracted locally:**

```
date
node_id
visit_category   ENUM: outpatient | inpatient | emergency | referred_out
syndrome_category (mapped from visit chief complaint or triage code)
count
```

**Aggregation:** Daily totals by syndrome category and visit type. Rows written to `aggregate_signal` with `data_source = 'clinic'`.

**Important:** The extract script runs locally inside the institution container. Raw visit records never leave. Only the aggregated daily counts are included in the outbound payload.

---

#### Module 4 — Pharmacy Demand

**What changes:** Source is dispensing records, not clinical visits.

**Input surface:** Daily count entry form, or nightly extract from pharmacy management system.

**Fields:**

```
date
node_id
drug_category    ENUM: antipyretic | antibiotic | antidiarrheal | antihistamine
                       | electrolyte_replacement | antiviral | other
count_dispensed
```

**Syndrome mapping for pharmacy:** Antipyretic → fever_like. Antidiarrheal + electrolyte_replacement → gastrointestinal. Antihistamine → respiratory. This mapping is stored in `syndrome_map.yaml` alongside the symptom mapping.

**Aggregation output:** Rows in `aggregate_signal` with `data_source = 'pharmacy'`.

**Note:** Pharmacy demand is a leading indicator. A spike in antipyretic sales often precedes a clinic visit surge by 2–3 days. This is why it belongs in Phase 1.

---

#### Module 5 — Diagnostic / Testing Data

**What changes:** Source is test request and result counts, not patient records.

**Input surface:** Daily extract from lab management system, or manual count entry.

**Fields:**

```
date
node_id
test_type        ENUM: rapid_antigen | PCR | blood_culture | stool_culture | other
syndrome_proxy   ENUM (mapped from test type)
tests_requested  INTEGER
tests_positive   INTEGER
positivity_rate  FLOAT  (computed locally: positive / requested)
```

**Privacy note:** Positivity rate can be transmitted only if `tests_requested >= k`. If fewer than k tests were requested in a cell, suppress the entire row.

**Aggregation output:** Rows in `aggregate_signal` with `data_source = 'testing'`.

---

### Phase 2 — Supporting Signals

These sources enrich the aggregate signal but are not required for the federated pipeline to function. Build them only after Phase 1 is producing clean daily rows from all five core sources.

---

#### Module 6 — Geographic Zones

**Purpose:** Enables zone-level queries and cross-zone comparisons.

**What to build:**
- Zone hierarchy table: region → district → ward → node
- Zone assignment for all existing nodes
- Zone-level rollup view on `aggregate_signal`

**This is not a new data source.** It is a retrospective enrichment of existing aggregate rows using the `zone_id` field that was already in the schema.

**Query it enables:**
```sql
SELECT zone_id, syndrome, SUM(count), COUNT(DISTINCT node_id)
FROM aggregate_signal
WHERE date >= CURRENT_DATE - 5
GROUP BY zone_id, syndrome
HAVING COUNT(DISTINCT node_id) >= 3;
```

---

#### Module 7 — Time-Based Trends

**Purpose:** Adds computed temporal features to the aggregate signal for use by the forecasting model.

**What to build:** Extend the daily aggregation job to compute and store:
- `rolling_3d_mean`, `rolling_7d_mean`, `rolling_7d_std` (already in schema)
- `day_of_week`, `holiday_flag` (calendar features for the ML model)
- `lag_1`, `lag_7` (previous-day and same-weekday-last-week demand)

These are not new data sources. They are computed columns derived from existing `aggregate_signal` rows.

---

#### Module 8 — School / Workplace Absenteeism

**Input surface:** Weekly count submission from school or workplace administrators. Simple web form, authentication required.

**Fields:**

```
date (week-start)
node_id
reporting_institution   FK → node registry
expected_attendance     INTEGER
actual_attendance       INTEGER
absenteeism_rate        FLOAT  (computed locally)
reported_reason         ENUM: illness | unknown | other
```

**Aggregation output:** Rows in `aggregate_signal` with `data_source = 'absenteeism'`, syndrome mapped to `other` unless a specific illness reason is given.

**Privacy note:** Do not collect individual absence records. Only institution-level weekly counts enter the pipeline.

---

#### Module 9 — Emergency / Ambulance Demand

**Input surface:** Daily extract from dispatch/CAD system, or manual count entry from emergency coordinator.

**Fields:**

```
date
node_id
call_category    ENUM: respiratory | cardiac | trauma | unknown | other
calls_received   INTEGER
calls_dispatched INTEGER
```

**Aggregation output:** Rows in `aggregate_signal` with `data_source = 'emergency'`.

**Note:** Emergency call volume is a useful surge indicator but is noisier than clinic demand. Weight accordingly in the forecasting model.

---

#### Module 10 — Environmental Data

**Input surface:** Automated pull from a public meteorological API (no patient data involved). Run as a daily scheduled job.

**Fields collected:**

```
date
zone_id
temperature_max     FLOAT
temperature_min     FLOAT
humidity_mean       FLOAT
rainfall_mm         FLOAT
air_quality_index   INTEGER  (if available)
```

**Aggregation output:** Stored as environmental context in `aggregate_signal` with `data_source = 'environmental'`, syndrome set to `other`.

**Privacy note:** Environmental data contains no individual records. The k-anonymity rule does not apply, but the outbound validator still checks the payload structure.

---

### Phase 3 — Advanced

Build only after the full federated pipeline is running cleanly with Phase 1 and Phase 2 data.

---

#### Module 11 — Wastewater Surveillance

**Why last:** Requires laboratory infrastructure, sample collection logistics, and calibration against clinical data. The signal is powerful but setup cost is high.

**Input surface:** Laboratory result submission API or file upload from wastewater monitoring team.

**Fields:**

```
date
zone_id
sample_site_id      FK → node registry
pathogen_marker     ENUM: (approved list; no individual diagnosis)
concentration       FLOAT
sample_volume_ml    FLOAT
quality_flag        ENUM: valid | diluted | contaminated | missing
```

**Aggregation output:** Zone-level daily concentration summary in `aggregate_signal` with `data_source = 'wastewater'`.

**Note:** Wastewater signal typically leads clinical presentation by 4–7 days. Once this module is live, include the lagged wastewater concentration as a feature in the forecasting model.

---

## Part 5 — System Components (build order)

Build in this order. Do not move to the next component until the previous one is testable end-to-end.

### 5.1 Local institution node (build first)

```
institution-x/
├── raw/              symptom_report rows (never transmitted)
├── processed/        validated and mapped records
├── features/         aggregate_signal rows ready for export
├── models/           locally trained model weights
└── local_config/     syndrome_map.yaml, privacy thresholds, feature schema
```

### 5.2 Daily aggregation job

Runs at 00:00 local time. Inputs: all `symptom_report` rows where `symptom_onset` falls within the reporting window. Outputs: one or more `aggregate_signal` rows per syndrome per node per day. Computes growth rate, rolling means, rolling std.

### 5.3 Outbound payload validator

Runs before any aggregate leaves the node. Rejects payloads that:
- contain any field not in the approved `FeatureDefinitions` list
- are shaped like row-level records (presence of individual identifiers)
- contain cells where count < k
- contain values outside documented bounds

Logs every rejection to the central `PrivacyEvents` table.

### 5.4 Federated coordinator

Receives privacy-filtered aggregate updates. Runs FedAvg:

```
w_global = Σ(n_i / N) × w_i

where n_i = eligible local training size for node i
      N   = total eligible training size across participating nodes
```

Handles missing nodes without fabricating their updates. If participation drops below the minimum threshold, the round is marked INCOMPLETE and no new global model is produced.

### 5.5 Forecasting engine

Forecast target: aggregate daily syndrome-category demand for the next 7–14 days (default 7, configurable to 14).

Start with regularized regression + lag features + rolling statistics + calendar features. Move to LSTM or TCN only if experiments demonstrate meaningful improvement.

Every forecast must include calibrated uncertainty:
```
Day +3
Point forecast:    132
80% interval:      121 – 145
95% interval:      114 – 152
```

Report wider uncertainty when a node is missing, the historical window is short, or data coverage is incomplete.

### 5.6 CUSUM shift detector

```
Observed demand
    -
Expected demand (from forecast)
    =
Residual
    ↓
CUSUM score
    ↓
Threshold
    ↓
NORMAL / WATCH / ALERT_CANDIDATE
```

A high CUSUM score is not a diagnosis. It is evidence for a human reviewer.

### 5.7 Reviewer dashboard

Show, per alert candidate:
- Forecast trend and uncertainty interval
- CUSUM shift score and evidence window
- Historical baseline
- Coverage status (which nodes are participating)
- Missing nodes
- Model version
- Reviewer decision controls: APPROVE / REJECT / REQUEST MORE EVIDENCE

A reviewer decision is logged. Only an approved alert becomes actionable.

### 5.8 Audit log

Every major operation produces a structured audit event: training round start/end, participants, failures, invalid updates, privacy suppression, rejected transmissions, model version, forecast generation, alert generation, reviewer decision, export, system errors. Use hash-linked records where practical.

---

## Part 6 — Three-Way Evaluation (mandatory)

The federated approach is only defensible if you measure whether it actually helps.

```
                 Same held-out test set
                          │
       ┌──────────────────┼──────────────────┐
       ↓                  ↓                  ↓
  Local-only          Federated         Pooled upper bound
  (each node          (FedAvg,          (all raw data
   trains alone)       no raw sharing)   pooled offline only)
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ↓
                Compare MAE / MAPE / interval coverage

Uplift (%) = (Local Error − Federated Error) / Local Error × 100
```

The pooled model is for evaluation only. It is never a deployment mode. Do not manufacture uplift; if federation does not improve on a particular configuration, report it and explain why.

---

## Part 7 — What Not to Build First

The master solution is explicit on this. Do not start with:

- LSTM or transformer forecasting models
- Real hospital record integration
- Blockchain
- Full cryptographic secure aggregation
- Formal differential privacy accounting
- Mobile application
- Cloud-scale deployment

Start with the smallest end-to-end system:

```
4 nodes
  ↓ local aggregation
  ↓ FedAvg
  ↓ 7-day forecast
  ↓ uncertainty
  ↓ CUSUM
  ↓ privacy suppression
  ↓ reviewer dashboard
```

Then harden it. Add sophistication only after the end-to-end pipeline works.

Also do not put any of this in the system:
- Individual diagnosis
- Individual risk scoring
- Patient-level prediction
- Central storage of identifiable records
- Re-identification functions
- Clinical treatment recommendations
- Automatic emergency dispatch
- Automatic external alert communication

---

## Part 8 — Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React / Next.js |
| Charts | Recharts / Plotly |
| Backend | Python + FastAPI |
| Federated learning | Flower |
| ML | scikit-learn initially; PyTorch only if justified |
| Database | PostgreSQL |
| Containers | Docker + Docker Compose |
| Testing | pytest |
| API | REST / JSON |
| Authentication | Token-based + role-based authorization |

**Deployment (single-machine demo):**

```
Docker Compose
├── coordinator
├── institution-a
├── institution-b
├── institution-c
├── institution-d
├── backend-api
├── database
└── frontend
```

Institution containers must have isolated storage. The central database must not contain patient-level tables.

---

## Part 9 — System Capability Check

Once Module 1 is live, the following query must return a meaningful answer. This is the definition of done for the data model.

```sql
SELECT
    zone_id,
    syndrome,
    SUM(count)                       AS total_reports,
    AVG(growth_rate_7d)              AS avg_growth_rate,
    COUNT(DISTINCT node_id)          AS nodes_reporting
FROM aggregate_signal
WHERE
    data_source = 'community'
    AND syndrome = 'respiratory'
    AND date >= CURRENT_DATE - INTERVAL '5 days'
GROUP BY zone_id, syndrome
HAVING COUNT(DISTINCT node_id) >= 3
ORDER BY avg_growth_rate DESC;
```

Expected output shape:
> *"Respiratory symptoms increased 42% across 3 nodes over the last 5 days in Zone 7."*

Adding `data_source = 'doctor'` in a WHERE clause or UNION should require no schema change. That composability is the point of the shared data model.

---

## Part 10 — Final Acceptance Checklist

The implementation is accepted only when all are true. Tick each before competition submission.

**Data and privacy**
- [ ] Four simulated institutions participate with demonstrably non-identical populations
- [ ] Raw row-level data remains local in every institution container
- [ ] Central APIs cannot receive raw row-level records (verified by network/API log)
- [ ] Aggregate features are generated locally before transmission
- [ ] Minimum-group-size suppression enforced at query time, not display time
- [ ] Small-group outputs suppressed in API response, not only in the frontend
- [ ] Privacy events logged for every suppression and rejection

**Federated pipeline**
- [ ] Federated training creates a global model via FedAvg
- [ ] Local-only baseline exists and is evaluated on the same test set
- [ ] Pooled benchmark exists for offline comparison only
- [ ] Missing-node recovery works without fabricating the missing update
- [ ] Invalid updates are rejected and logged
- [ ] Round marked INCOMPLETE if minimum participation not met

**Forecasting and detection**
- [ ] Forecast horizon is 7–14 days
- [ ] Every forecast includes calibrated uncertainty (80% and 95% intervals)
- [ ] Uncertainty is reported as reduced when a node is missing
- [ ] CUSUM shift detector works on injected surge events
- [ ] Detection recall and lead time are reported

**Evaluation**
- [ ] Forecast accuracy reported as MAE and MAPE per institution and regionally
- [ ] Federated vs local-only uplift is calculated and reported honestly
- [ ] Interval calibration checked (empirical coverage ≈ stated coverage)
- [ ] Privacy leakage testing performed (row-level transmission, small-group, narrowing)

**Governance**
- [ ] Human reviewer must approve before any alert becomes actionable
- [ ] Reviewer decisions are logged in the audit trail
- [ ] No individual diagnosis exists anywhere in the system
- [ ] No individual risk score exists
- [ ] No re-identification function exists

**Demo robustness**
- [ ] All four official demo scenarios pass
- [ ] At least one unrehearsed variation of each scenario passes
- [ ] No demo behavior depends on hard-coded output values
- [ ] System recomputes from actual logic when judge changes an input

---

*The winning strategy is not more AI. It is privacy + federated collaboration + forecasting + uncertainty + anomaly detection + resilience + human review + auditability — working end-to-end.*


# HealthSignal — Additional Implementation Requirements

## 1. Four Simulated Node Profiles

HealthSignal will simulate four different community-health environments instead of connecting to real healthcare institutions.

The four nodes are:

1. Rural
2. Urban
3. Semi-Urban
4. Mixed

Each node must have a different population profile and different data characteristics. The purpose is to simulate real-world non-IID data, where every institution does not have the same population, healthcare access, reporting behavior, or baseline demand.

### Node A — Rural

Characteristics:

- Low population
- Lower healthcare access
- Lower baseline service demand
- Lower reporting frequency
- Higher travel distance to major healthcare facilities
- Potentially delayed reporting
- Higher probability of missing/incomplete data

Example:

```text
Node A — Rural

Population: Low
Healthcare access: Low
Baseline demand: Low
Reporting frequency: Low–Medium
Data completeness: Medium
Node B — Urban

Characteristics:

High population
High healthcare access
High baseline service demand
Frequent reporting
Faster access to clinics and testing
Higher pharmacy activity
Better data completeness

Example:

Node B — Urban

Population: High
Healthcare access: High
Baseline demand: High
Reporting frequency: High
Data completeness: High
Node C — Semi-Urban

Characteristics:

Medium population
Moderate healthcare access
Moderate baseline service demand
Moderate reporting frequency
Combination of urban and rural characteristics
Moderate data completeness

Example:

Node C — Semi-Urban

Population: Medium
Healthcare access: Medium
Baseline demand: Medium
Reporting frequency: Medium
Data completeness: Medium
Node D — Mixed

Characteristics:

Combination of rural and urban population characteristics
Variable healthcare access
Variable baseline service demand
Variable reporting frequency
Mixed data quality
Represents a heterogeneous community

Example:

Node D — Mixed

Population: Medium–High
Healthcare access: Variable
Baseline demand: Variable
Reporting frequency: Variable
Data completeness: Variable

The four nodes must not use identical distributions. Their differences should be visible in symptom frequency, healthcare demand, pharmacy demand, testing demand, reporting behavior, and other signals.

2. Symptom Master List

A separate symptom master configuration should be maintained instead of hard-coding symptoms throughout the application.

Suggested fields:

symptom_id
symptom_name
syndrome
severity_allowed
early_warning_weight

Example:

S001 | Fever                | fever_like       | mild/moderate/severe
S002 | Cough                | respiratory      | mild/moderate/severe
S003 | Sore throat          | respiratory      | mild/moderate
S004 | Runny nose           | respiratory      | mild/moderate
S005 | Shortness of breath  | respiratory      | moderate/severe
S006 | Chest pain           | respiratory      | moderate/severe
S007 | Chills               | fever_like      | mild/moderate
S008 | Body ache            | fever_like      | mild/moderate
S009 | Fatigue              | fever_like      | mild/moderate
S010 | Headache              | neurological     | mild/moderate
S011 | Confusion             | neurological     | moderate/severe
S012 | Stiff neck             | neurological     | moderate/severe
S013 | Seizure                | neurological     | severe
S014 | Nausea                 | gastrointestinal | mild/moderate
S015 | Vomiting               | gastrointestinal | mild/moderate/severe
S016 | Diarrhea               | gastrointestinal | mild/moderate/severe
S017 | Abdominal pain         | gastrointestinal | mild/moderate
S018 | Rash                   | dermatological   | mild/moderate
S019 | Itching                | dermatological   | mild/moderate
S020 | Skin lesion            | dermatological   | mild/moderate/severe
S021 | Other                  | other            | mild/moderate/severe

The symptom list should remain configurable so additional symptoms can be added without changing the core application logic.

3. Symptom → Syndrome Mapping

The system should convert individual reported symptoms into standardized syndrome categories.

Suggested mapping:

Fever + chills + body ache + fatigue
        ↓
FEVER-LIKE

Cough + sore throat + runny nose +
shortness of breath + chest pain
        ↓
RESPIRATORY

Nausea + vomiting + diarrhea +
abdominal pain
        ↓
GASTROINTESTINAL

Headache + confusion + stiff neck + seizure
        ↓
NEUROLOGICAL

Rash + itching + skin lesion
        ↓
DERMATOLOGICAL

Anything else
        ↓
OTHER

One report may map to more than one syndrome.

For example:

Fever + cough + fatigue
        ↓
FEVER-LIKE
+
RESPIRATORY

Each syndrome should then be counted independently during local aggregation.

The mapping should be stored in:

syndrome_map.yaml

and should be versioned.

4. Source Reliability

Since HealthSignal combines multiple data sources, the system should maintain configurable source reliability values.

Suggested initial classification:

Community symptoms      → Medium
Doctor observations     → High
Clinic demand           → High
Testing data             → Very High
Pharmacy demand          → Medium
Absenteeism              → Medium
Emergency demand         → Medium–High
Environmental data      → Contextual
Wastewater               → High / Contextual

These values are not fixed scientific truths.

They should be configurable and should be validated through experiments.

The purpose is to prevent every data source from being treated as equally informative.

5. Signal Weight

Each data source or signal may optionally have a configurable weight.

Example:

Community symptoms
        +
Doctor observations
        +
Clinic demand
        +
Pharmacy demand
        +
Testing positivity
        +
Environmental context
        ↓
Combined health signal

The model can use these signals to identify whether multiple independent sources are showing the same trend.

The weights must not be hard-coded as final values. They should be configurable and evaluated experimentally.

6. Outbreak / Event Simulator

Because HealthSignal is a simulated system, an outbreak/event simulator should be included.

The simulator allows the team to inject controlled health events into the synthetic data.

Example configuration:

EVENT SIMULATOR

Event type:
- respiratory outbreak
- gastrointestinal outbreak
- fever-like outbreak

Start day:
Day 60

Affected nodes:
Urban + Semi-Urban + Mixed

Intensity:
Low / Medium / High

Duration:
10 days

The event simulator should modify the appropriate data sources realistically.

Example:

Day 60
Respiratory symptoms increase

Day 61
Respiratory symptoms increase further

Day 62
Pharmacy demand increases

Day 63
Clinic visits increase

Day 64
Testing demand increases

Day 65
Multiple nodes show similar trends

        ↓

Forecast residual increases
        ↓
CUSUM score increases
        ↓
WATCH / ALERT_CANDIDATE

The system must calculate the alert from actual data and detector logic.

It must not contain hard-coded rules such as:

if event_type == "respiratory":
    alert = True

Instead:

score = detector.compute(observed, expected)

if score >= configured_threshold:
    create_alert_candidate(...)

The event simulator provides known ground truth for evaluating:

Detection recall
Detection delay
Lead time
False-alert rate
Forecast performance
7. Node-Specific Data Generation

Each node should generate different data.

The system should not simply copy the same dataset four times.

Example:

RURAL

Respiratory:
Day 1 → 12
Day 2 → 14
Day 3 → 18
Day 4 → 25
URBAN

Respiratory:
Day 1 → 80
Day 2 → 87
Day 3 → 105
Day 4 → 142
SEMI-URBAN

Respiratory:
Day 1 → 35
Day 2 → 39
Day 3 → 47
Day 4 → 61
MIXED

Respiratory:
Day 1 → 42
Day 2 → 44
Day 3 → 55
Day 4 → 73

The absolute values can differ because population sizes and healthcare access differ.

The important part is that the system should detect the underlying trend rather than relying on absolute numbers alone.

8. Data Quality Simulation

The four nodes should also simulate different data-quality conditions.

Example:

Rural:
10–20% missing or delayed reports

Urban:
2–5% missing reports

Semi-Urban:
5–10% missing reports

Mixed:
Variable missingness

The simulation should include:

Missing reports
Delayed reports
Duplicate reports
Incomplete reports
Invalid values
Temporary node failure
Reduced reporting frequency

This allows HealthSignal to demonstrate how the system behaves under realistic imperfect data conditions.

9. Data Quality Score

Each aggregate signal may include a data-quality score.

Suggested field:

data_quality_score

Example:

Node A

Respiratory count: 42
Coverage ratio: 0.82
Data quality score: 0.78

The score can consider:

Completeness
+
Timeliness
+
Validity
+
Duplicate rate
+
Expected reporting coverage

A low-quality signal should reduce confidence in the forecast or be flagged appropriately.

10. Multi-Source Early Warning

The main objective is not to identify a disease in an individual.

The objective is to detect an unusual change in community health patterns.

Example:

Community symptoms ↑
        +
Doctor observations ↑
        +
Clinic visits ↑
        +
Pharmacy demand ↑
        +
Testing demand ↑
        ↓
Regional health signal strengthens
        ↓
Forecast deviation increases
        ↓
CUSUM score increases
        ↓
WATCH
        ↓
ALERT CANDIDATE
        ↓
Human public-health reviewer

This should be described as:

Early outbreak / health-trend detection

and not:

Individual disease diagnosis
11. Recommended Final Data Architecture

The complete simulated system should follow this structure:

                  4 SIMULATED NODES

       ┌──────────┬──────────┬──────────┬──────────┐
       ↓          ↓          ↓          ↓
     Rural      Urban     Semi-Urban    Mixed
       │          │          │          │
       └──────────┴──────────┴──────────┘
                         ↓
                MULTIPLE DATA SOURCES
                         ↓
        ┌─────────────────────────────────┐
        │ Community symptoms              │
        │ Doctor observations             │
        │ Clinic demand                   │
        │ Pharmacy demand                 │
        │ Testing data                    │
        │ Absenteeism                     │
        │ Emergency demand                │
        │ Environmental data              │
        │ Wastewater                      │
        └─────────────────────────────────┘
                         ↓
                 LOCAL PROCESSING
                         ↓
              SYMPTOM → SYNDROME
                         ↓
                  DATA VALIDATION
                         ↓
                    AGGREGATION
                         ↓
                 DATA QUALITY CHECK
                         ↓
                  PRIVACY FILTER
                         ↓
              OUTBOUND VALIDATOR
                         ↓
              FEDERATED LEARNING
                         ↓
              FORECAST + UNCERTAINTY
                         ↓
                  CUSUM / SHIFT
                         ↓
               EARLY-WARNING SIGNAL
                         ↓
                  HUMAN REVIEW
                         ↓
                AUDIT / GOVERNANCE
12. Final Implementation Priority

Do not implement all data sources simultaneously.

Recommended order:

Phase 1 — Core
1. Four simulated nodes
2. Synthetic data generator
3. Symptom master list
4. Symptom → syndrome mapping
5. Community symptom collection
6. Doctor observations
7. Clinic demand
8. Pharmacy demand
9. Testing data
10. Local aggregation
11. Privacy filtering
12. Outbound validator
Phase 2 — Supporting
13. Geographic zones
14. Time-based features
15. School/workplace absenteeism
16. Emergency demand
17. Environmental data
18. Data-quality scoring
19. Missing/delayed data simulation
Phase 3 — Advanced
20. Wastewater surveillance
21. Advanced signal weighting
22. More complex outbreak scenarios
13. Final Principle

The system should follow this principle:

                RAW DATA
                   ↓
          LOCAL INSTITUTION
                   ↓
          LOCAL PROCESSING
                   ↓
         SYMPTOM / DATA MAPPING
                   ↓
          LOCAL AGGREGATION
                   ↓
           DATA QUALITY CHECK
                   ↓
           PRIVACY PROTECTION
                   ↓
          APPROVED AGGREGATES
                   ↓
         FEDERATED COORDINATOR
                   ↓
       FORECAST + UNCERTAINTY
                   ↓
          ANOMALY DETECTION
                   ↓
          EARLY-WARNING SIGNAL
                   ↓
             HUMAN REVIEW

The key innovation is not simply collecting more data. It is combining independent signals from four different simulated community environments while keeping raw data local and using the combined aggregate patterns for early detection of unusual health trends.


This fits your existing implementation plan and preserves its core privacy boundary: raw records remain inside each institution, while only approved aggregates cross to the federated system. :contentReference[oaicite:0]{index=0}

# Part 11 — Comprehensive Symptom, Syndrome and Disease Reference

## 11.1 Purpose

HealthSignal requires a comprehensive symptom and health-condition reference dataset so that the simulated four-node system can generate realistic and diverse community-health observations.

The reference dataset is used for:

* Community symptom collection
* Doctor/health-worker observations
* Synthetic data generation
* Symptom-to-syndrome mapping
* Disease/condition knowledge mapping
* Outbreak-event simulation
* Early-warning signal generation
* Testing different combinations of symptoms
* Evaluating the forecasting and anomaly-detection pipeline

The disease/condition list is a **reference and simulation layer**. HealthSignal must not use it to provide individual diagnosis.

The operational pipeline remains:

```text
Reported Symptoms
       ↓
Symptom Standardization
       ↓
Syndrome Classification
       ↓
Local Aggregation
       ↓
Privacy Filtering
       ↓
Federated Learning
       ↓
Trend / Forecast
       ↓
Anomaly Detection
       ↓
Early-Warning Signal
       ↓
Human Review
```

---

# 11.2 Standard Symptom Categories

Symptoms should be organized into broad categories to make the dataset easier to maintain.

```text
1. General / Systemic
2. Respiratory
3. Gastrointestinal
4. Neurological
5. Cardiovascular
6. Musculoskeletal
7. Dermatological
8. Eye / Ocular
9. Ear / Nose / Throat
10. Urinary / Renal
11. Reproductive
12. Oral / Dental
13. Allergy-related
14. Mental / Behavioral
15. Bleeding / Hematological
16. Dehydration / Fluid-related
17. Pregnancy-related
18. Pediatric-specific
19. Environmental / Exposure-related
20. Other
```

---

# 11.3 Comprehensive Symptom Master List

## A. General / Systemic Symptoms

```text
S001  Fever
S002  Chills
S003  Feeling cold
S004  Sweating
S005  Night sweats
S006  Fatigue
S007  Weakness
S008  Malaise
S009  Body ache
S010  Generalized pain
S011  Loss of appetite
S012  Increased appetite
S013  Weight loss
S014  Weight gain
S015  Dehydration
S016  Dizziness
S017  Fainting
S018  Feeling unwell
S019  Reduced activity
S020  Lethargy
```

---

## B. Respiratory Symptoms

```text
S021  Cough
S022  Dry cough
S023  Productive cough
S024  Cough with sputum
S025  Blood in sputum
S026  Shortness of breath
S027  Difficulty breathing
S028  Rapid breathing
S029  Wheezing
S030  Chest tightness
S031  Chest discomfort
S032  Chest pain
S033  Nasal congestion
S034  Stuffy nose
S035  Runny nose
S036  Sneezing
S037  Post-nasal drip
S038  Sore throat
S039  Throat irritation
S040  Hoarse voice
S041  Loss of voice
S042  Difficulty breathing during activity
S043  Difficulty breathing at rest
S044  Noisy breathing
S045  Increased respiratory rate
S046  Oxygen saturation below expected level
```

---

## C. Gastrointestinal Symptoms

```text
S047  Nausea
S048  Vomiting
S049  Repeated vomiting
S050  Diarrhea
S051  Loose stools
S052  Bloody stool
S053  Mucus in stool
S054  Abdominal pain
S055  Abdominal cramps
S056  Abdominal bloating
S057  Indigestion
S058  Heartburn
S059  Constipation
S060  Loss of appetite
S061  Difficulty swallowing
S062  Painful swallowing
S063  Excessive thirst
S064  Jaundice
S065  Dark urine
S066  Pale stool
```

---

## D. Neurological Symptoms

```text
S067  Headache
S068  Severe headache
S069  Migraine-like headache
S070  Confusion
S071  Disorientation
S072  Drowsiness
S073  Excessive sleepiness
S074  Difficulty concentrating
S075  Memory difficulty
S076  Loss of consciousness
S077  Fainting
S078  Seizure
S079  Tremor
S080  Numbness
S081  Tingling
S082  Weakness of limb
S083  Difficulty walking
S084  Loss of balance
S085  Dizziness
S086  Vertigo
S087  Muscle coordination difficulty
S088  Speech difficulty
S089  Slurred speech
S090  Sensitivity to light
S091  Sensitivity to sound
S092  Stiff neck
S093  Altered mental status
S094  Loss of smell
S095  Loss of taste
S096  Reduced smell
S097  Reduced taste
```

---

## E. Cardiovascular Symptoms

```text
S098  Palpitations
S099  Rapid heartbeat
S100  Slow heartbeat
S101  Irregular heartbeat
S102  Chest pressure
S103  Chest discomfort
S104  Chest pain
S105  Shortness of breath
S106  Breathlessness during activity
S107  Breathlessness at rest
S108  Leg swelling
S109  Ankle swelling
S110  Sudden weakness
S111  Fainting
S112  Cold extremities
S113  Bluish lips
S114  Reduced exercise tolerance
```

---

## F. Musculoskeletal Symptoms

```text
S115  Muscle pain
S116  Muscle weakness
S117  Joint pain
S118  Joint swelling
S119  Joint stiffness
S120  Back pain
S121  Neck pain
S122  Limb pain
S123  Bone pain
S124  Muscle cramps
S125  Difficulty moving joint
S126  Generalized body pain
```

---

## G. Dermatological Symptoms

```text
S127  Skin rash
S128  Itching
S129  Skin redness
S130  Skin swelling
S131  Skin lesion
S132  Blisters
S133  Hives
S134  Skin peeling
S135  Dry skin
S136  Excessive sweating
S137  Skin discoloration
S138  Bruising
S139  Small red spots
S140  Purple skin spots
S141  Ulcer
S142  Pus-filled lesion
S143  Painful skin lesion
S144  Hair loss
S145  Yellowing of skin
```

---

## H. Eye / Ocular Symptoms

```text
S146  Eye redness
S147  Eye pain
S148  Eye itching
S149  Watery eyes
S150  Eye discharge
S151  Blurred vision
S152  Reduced vision
S153  Light sensitivity
S154  Swollen eyelids
S155  Dry eyes
S156  Foreign-body sensation
S157  Excessive tearing
```

---

## I. Ear / Nose / Throat Symptoms

```text
S158  Ear pain
S159  Ear discharge
S160  Reduced hearing
S161  Hearing loss
S162  Ringing in ears
S163  Nasal congestion
S164  Runny nose
S165  Sneezing
S166  Nosebleed
S167  Sinus pressure
S168  Facial pressure
S169  Sore throat
S170  Throat swelling
S171  Hoarse voice
S172  Difficulty swallowing
S173  Loss of smell
S174  Loss of taste
```

---

## J. Urinary / Renal Symptoms

```text
S175  Painful urination
S176  Burning urination
S177  Frequent urination
S178  Urgent urination
S179  Reduced urine output
S180  Increased urine output
S181  Blood in urine
S182  Cloudy urine
S183  Dark urine
S184  Flank pain
S185  Lower abdominal pain
S186  Difficulty urinating
S187  Inability to urinate
```

---

## K. Reproductive Symptoms

```text
S188  Pelvic pain
S189  Abnormal vaginal bleeding
S190  Abnormal vaginal discharge
S191  Genital pain
S192  Genital swelling
S193  Pain during intercourse
S194  Testicular pain
S195  Testicular swelling
S196  Breast pain
S197  Breast swelling
S198  Menstrual irregularity
S199  Heavy menstrual bleeding
```

---

## L. Oral / Dental Symptoms

```text
S200  Toothache
S201  Gum pain
S202  Gum swelling
S203  Gum bleeding
S204  Mouth ulcer
S205  Mouth pain
S206  Tongue swelling
S207  Difficulty chewing
S208  Difficulty swallowing
S209  Dry mouth
S210  Excessive salivation
S211  Bad breath
S212  Loss of taste
```

---

## M. Allergy-related Symptoms

```text
S213  Sneezing
S214  Runny nose
S215  Nasal congestion
S216  Itchy nose
S217  Itchy eyes
S218  Watery eyes
S219  Skin itching
S220  Hives
S221  Facial swelling
S222  Lip swelling
S223  Tongue swelling
S224  Wheezing
S225  Breathing difficulty
S226  Throat tightness
```

---

## N. Mental / Behavioral Symptoms

```text
S227  Anxiety
S228  Restlessness
S229  Irritability
S230  Sleep disturbance
S231  Excessive sleepiness
S232  Difficulty concentrating
S233  Confusion
S234  Behavioral change
S235  Reduced responsiveness
S236  Altered mental status
```

These fields should be handled carefully and should not be used for individual mental-health diagnosis.

---

## O. Bleeding / Hematological Symptoms

```text
S237  Nosebleed
S238  Gum bleeding
S239  Easy bruising
S240  Unusual bleeding
S241  Blood in stool
S242  Blood in urine
S243  Blood in sputum
S244  Vomiting blood
S245  Heavy menstrual bleeding
S246  Pale appearance
S247  Severe weakness
```

---

## P. Dehydration / Fluid-related Symptoms

```text
S248  Excessive thirst
S249  Dry mouth
S250  Dry skin
S251  Reduced urination
S252  Dark urine
S253  Dizziness
S254  Weakness
S255  Fainting
S256  Sunken eyes
S257  Reduced alertness
```

---

# 11.4 Standard Syndrome Categories

The initial HealthSignal system should use the following syndrome categories:

```text
SY001  Fever-like
SY002  Respiratory
SY003  Gastrointestinal
SY004  Neurological
SY005  Cardiovascular
SY006  Musculoskeletal
SY007  Dermatological
SY008  Eye-related
SY009  ENT-related
SY010  Urinary
SY011  Reproductive
SY012  Oral/Dental
SY013  Allergy-related
SY014  Hematological
SY015  Dehydration
SY016  Other
```

The first competition implementation may prioritize:

```text
fever_like
respiratory
gastrointestinal
other
```

Additional syndrome categories can be enabled later.

---

# 11.5 Disease / Condition Reference Dataset

The following conditions are included as a reference knowledge base for synthetic-data generation, symptom association, testing scenarios, and outbreak simulation.

The system should not display these conditions as an individual diagnosis result.

---

## A. Respiratory / Airborne Conditions

```text
D001  Common cold
D002  Influenza
D003  COVID-19
D004  Respiratory syncytial virus infection
D005  Adenovirus respiratory infection
D006  Rhinovirus infection
D007  Human metapneumovirus infection
D008  Parainfluenza infection
D009  Viral bronchitis
D010  Acute bronchitis
D011  Pneumonia
D012  Viral pneumonia
D013  Bacterial pneumonia
D014  Tuberculosis
D015  Pertussis
D016  Diphtheria
D017  Sinusitis
D018  Pharyngitis
D019  Tonsillitis
D020  Laryngitis
D021  Bronchiolitis
D022  Asthma exacerbation
D023  Chronic obstructive pulmonary disease exacerbation
D024  Allergic rhinitis
D025  Respiratory syncytial disease
```

---

## B. Gastrointestinal / Food- and Water-related Conditions

```text
D026  Acute gastroenteritis
D027  Viral gastroenteritis
D028  Bacterial gastroenteritis
D029  Food poisoning
D030  Cholera
D031  Typhoid fever
D032  Paratyphoid fever
D033  Shigellosis
D034  Salmonellosis
D035  Campylobacter infection
D036  Norovirus infection
D037  Rotavirus infection
D038  Hepatitis A
D039  Hepatitis E
D040  Giardiasis
D041  Amoebiasis
D042  Dysentery
D043  Traveler's diarrhea
D044  Intestinal parasitic infection
D045  Acute diarrheal disease
```

---

## C. Mosquito / Vector-borne Conditions

```text
D046  Dengue
D047  Chikungunya
D048  Malaria
D049  Japanese encephalitis
D050  West Nile virus infection
D051  Zika virus infection
D052  Yellow fever
D053  Filariasis
D054  Scrub typhus
D055  Leishmaniasis
```

---

## D. Fever-associated Infectious Conditions

```text
D056  Influenza
D057  COVID-19
D058  Dengue
D059  Chikungunya
D060  Malaria
D061  Typhoid fever
D062  Paratyphoid fever
D063  Tuberculosis
D064  Measles
D065  Rubella
D066  Mumps
D067  Chickenpox
D068  Mpox
D069  Leptospirosis
D070  Scrub typhus
D071  Brucellosis
D072  Infectious mononucleosis
```

---

## E. Neurological / Neuroinfectious Conditions

```text
D073  Meningitis
D074  Viral meningitis
D075  Bacterial meningitis
D076  Encephalitis
D077  Japanese encephalitis
D078  Rabies
D079  Poliomyelitis
D080  Guillain-Barré syndrome
D081  Tetanus
D082  Cerebral malaria
```

---

## F. Skin / Rash-associated Conditions

```text
D083  Measles
D084  Rubella
D085  Chickenpox
D086  Mpox
D087  Dengue-associated rash
D088  Chikungunya-associated rash
D089  Hand-foot-and-mouth disease
D090  Impetigo
D091  Cellulitis
D092  Scabies
D093  Fungal skin infection
D094  Ringworm
D095  Viral exanthem
D096  Allergic dermatitis
D097  Contact dermatitis
```

---

## G. Eye-related Conditions

```text
D098  Viral conjunctivitis
D099  Bacterial conjunctivitis
D100  Allergic conjunctivitis
D101  Keratitis
D102  Trachoma
D103  Dengue-associated eye symptoms
```

---

## H. ENT-related Conditions

```text
D104  Common cold
D105  Influenza
D106  Sinusitis
D107  Pharyngitis
D108  Tonsillitis
D109  Laryngitis
D110  Otitis media
D111  Otitis externa
D112  Allergic rhinitis
D113  Diphtheria
D114  Pertussis
```

---

## I. Urinary / Renal Conditions

```text
D115  Urinary tract infection
D116  Cystitis
D117  Pyelonephritis
D118  Kidney infection
D119  Kidney stone
D120  Acute kidney injury
```

These conditions are included mainly for completeness of the synthetic symptom dataset and should not be central to the first outbreak-detection model.

---

## J. Cardiovascular Conditions

```text
D121  Myocarditis
D122  Pericarditis
D123  Endocarditis
D124  Heart failure
D125  Arrhythmia
D126  Acute coronary syndrome
D127  Hypertension-related emergency
```

These are mainly supporting/reference conditions.

---

## K. Musculoskeletal / Joint-associated Conditions

```text
D128  Chikungunya-associated arthralgia
D129  Viral myalgia
D130  Influenza-associated muscle pain
D131  Reactive arthritis
D132  Septic arthritis
D133  Viral arthritis
```

---

## L. Liver-related Infectious Conditions

```text
D134  Hepatitis A
D135  Hepatitis B
D136  Hepatitis C
D137  Hepatitis E
D138  Viral hepatitis
D139  Leptospirosis-associated hepatitis
```

---

## M. Zoonotic / Environmental Conditions

```text
D140  Leptospirosis
D141  Rabies
D142  Brucellosis
D143  Anthrax
D144  Hantavirus infection
D145  Q fever
D146  Plague
```

These should be used carefully and primarily for controlled simulation scenarios.

---

## N. Childhood / Pediatric Infectious Conditions

```text
D147  Measles
D148  Rubella
D149  Chickenpox
D150  Mumps
D151  Pertussis
D152  Rotavirus infection
D153  Respiratory syncytial virus infection
D154  Hand-foot-and-mouth disease
D155  Scarlet fever
D156  Pediatric pneumonia
D157  Pediatric gastroenteritis
```

---

# 11.6 High-Priority Conditions for Pandemic / Outbreak Simulation

The initial competition prototype should not simulate all conditions equally.

The following should receive higher priority because they can produce recognizable community-level syndromic patterns:

```text
D001  Common cold
D002  Influenza
D003  COVID-19
D011  Pneumonia
D014  Tuberculosis
D026  Acute gastroenteritis
D029  Food poisoning
D030  Cholera
D031  Typhoid fever
D046  Dengue
D047  Chikungunya
D048  Malaria
D049  Japanese encephalitis
D064  Measles
D067  Chickenpox
D068  Mpox
D069  Leptospirosis
D073  Meningitis
D076  Encephalitis
D089  Hand-foot-and-mouth disease
```

These conditions provide diverse patterns across:

```text
Respiratory
Fever-like
Gastrointestinal
Neurological
Dermatological
Vector-borne
Water-borne
Airborne
```

---

# 11.7 Example Symptom-to-Condition Knowledge Mapping

The knowledge base should allow multiple symptoms to be associated with multiple conditions.

Example:

```text
Fever
├── Influenza
├── COVID-19
├── Dengue
├── Chikungunya
├── Malaria
├── Typhoid
├── Pneumonia
├── Tuberculosis
└── Measles
```

```text
Cough
├── Common cold
├── Influenza
├── COVID-19
├── Pneumonia
├── Bronchitis
├── Tuberculosis
├── Pertussis
└── Asthma exacerbation
```

```text
Diarrhea
├── Gastroenteritis
├── Cholera
├── Typhoid
├── Shigellosis
├── Salmonellosis
├── Norovirus
├── Rotavirus
├── Giardiasis
└── Amoebiasis
```

```text
Rash
├── Measles
├── Rubella
├── Chickenpox
├── Mpox
├── Dengue
├── Chikungunya
├── Hand-foot-and-mouth disease
└── Allergic dermatitis
```

```text
Headache
├── Influenza
├── COVID-19
├── Dengue
├── Malaria
├── Meningitis
├── Encephalitis
└── Chikungunya
```

```text
Joint pain
├── Chikungunya
├── Dengue
├── Viral infections
└── Reactive arthritis
```

---

# 11.8 Multi-Symptom Patterns

The synthetic data generator should support combinations of symptoms rather than generating symptoms independently.

Example patterns:

### Respiratory Pattern

```text
Fever
+
Cough
+
Sore throat
+
Fatigue
+
Runny nose
```

Possible syndrome:

```text
RESPIRATORY + FEVER-LIKE
```

---

### Severe Respiratory Pattern

```text
Fever
+
Cough
+
Shortness of breath
+
Chest discomfort
+
Fatigue
```

Possible syndrome:

```text
RESPIRATORY + FEVER-LIKE
```

---

### Gastrointestinal Pattern

```text
Fever
+
Nausea
+
Vomiting
+
Diarrhea
+
Abdominal pain
```

Possible syndrome:

```text
GASTROINTESTINAL + FEVER-LIKE
```

---

### Vector-borne Fever Pattern

```text
Fever
+
Headache
+
Body ache
+
Fatigue
+
Joint pain
+
Rash
```

Possible syndrome:

```text
FEVER-LIKE + MUSCULOSKELETAL + DERMATOLOGICAL
```

---

### Neurological Warning Pattern

```text
Fever
+
Severe headache
+
Confusion
+
Stiff neck
```

Possible syndrome:

```text
FEVER-LIKE + NEUROLOGICAL
```

---

# 11.9 Symptom Severity

Each symptom report should support:

```text
Mild
Moderate
Severe
```

Example:

```text
Fever → Moderate
Cough → Mild
Shortness of breath → Severe
Fatigue → Moderate
```

Severity should be aggregated locally:

```text
Respiratory

Mild       → 42
Moderate   → 27
Severe     → 11
```

The individual-level severity record must never cross the privacy boundary.

---

# 11.10 Symptom Frequency for Synthetic Data

The four nodes should have different baseline symptom distributions.

Example:

```text
RURAL

Fever-like:
Low–Medium

Respiratory:
Medium

Gastrointestinal:
Medium

Doctor observations:
Low

Testing:
Low

Pharmacy:
Medium
```

```text
URBAN

Fever-like:
Medium–High

Respiratory:
High

Gastrointestinal:
Medium

Doctor observations:
High

Testing:
High

Pharmacy:
High
```

```text
SEMI-URBAN

Fever-like:
Medium

Respiratory:
Medium

Gastrointestinal:
Medium

Doctor observations:
Medium

Testing:
Medium

Pharmacy:
Medium
```

```text
MIXED

Fever-like:
Variable

Respiratory:
Medium–High

Gastrointestinal:
Medium

Doctor observations:
Variable

Testing:
Medium

Pharmacy:
Medium–High
```

These are starting distributions only and should be configurable.

---

# 11.11 Disease/Condition Simulation Rules

The synthetic generator should not randomly select a disease and generate identical symptoms every time.

Instead, it should use probabilistic symptom patterns.

Example:

```text
Event:
Respiratory outbreak

Affected nodes:
Urban + Semi-Urban + Mixed

Probability of respiratory symptoms:
High

Probability of fever:
Medium–High

Probability of cough:
High

Probability of sore throat:
Medium

Probability of fatigue:
Medium

Probability of severe breathing difficulty:
Low
```

The exact values should be configurable.

---

# 11.12 Outbreak Scenario Library

The following scenarios should be available for testing.

### Scenario 1 — Respiratory Outbreak

```text
Primary syndrome:
Respiratory

Secondary syndrome:
Fever-like

Affected nodes:
Urban
Semi-Urban
Mixed

Expected signals:
Cough ↑
Sore throat ↑
Fever ↑
Clinic visits ↑
Pharmacy demand ↑
Respiratory testing ↑
```

---

### Scenario 2 — Gastrointestinal Outbreak

```text
Primary syndrome:
Gastrointestinal

Secondary syndrome:
Fever-like

Affected nodes:
Rural
Semi-Urban

Expected signals:
Diarrhea ↑
Vomiting ↑
Abdominal pain ↑
ORS demand ↑
Antidiarrheal demand ↑
Clinic visits ↑
```

---

### Scenario 3 — Vector-borne Outbreak

```text
Primary syndrome:
Fever-like

Secondary syndromes:
Musculoskeletal
Dermatological

Expected signals:
Fever ↑
Headache ↑
Body ache ↑
Joint pain ↑
Rash ↑
Testing demand ↑
Clinic visits ↑
```

---

### Scenario 4 — Neurological Cluster

```text
Primary syndrome:
Neurological

Secondary syndrome:
Fever-like

Expected signals:
Headache ↑
Confusion ↑
Stiff neck ↑
Fever ↑

This scenario should remain a controlled simulation and should always require human review.
```

---

### Scenario 5 — Multi-Syndrome Outbreak

```text
Respiratory ↑
+
Fever-like ↑
+
Clinic demand ↑
+
Testing demand ↑
+
Pharmacy demand ↑

Affected nodes:
All four nodes

Expected:
Regional anomaly
+
Increasing forecast
+
CUSUM shift
+
ALERT_CANDIDATE
```

---

# 11.13 Data Generation Rule

The synthetic generator should generate:

```text
Node
+
Date
+
Zone
+
Data source
+
Symptom combination
+
Syndrome
+
Severity
+
Reporting probability
+
Event state
```

Example:

```text
Node:
Urban

Date:
Day 45

Symptoms:
Fever + cough + fatigue

Syndrome:
Fever-like + Respiratory

Severity:
Moderate

Event:
Normal
```

During an outbreak:

```text
Node:
Urban

Date:
Day 65

Symptoms:
Fever + cough + sore throat + fatigue

Syndrome:
Fever-like + Respiratory

Severity:
Moderate

Event:
Respiratory outbreak
```

---

# 11.14 Important Implementation Rule

The disease list must not become the primary prediction target for the federated forecasting model.

The primary model target remains:

```text
Aggregate daily syndrome/service demand
```

For example:

```text
respiratory_count
fever_like_count
gastrointestinal_count
```

The disease/condition reference dataset is used to generate realistic symptom combinations and outbreak scenarios.

This maintains the project's non-diagnostic scope.

---

# 11.15 Final Symptom Data Pipeline

```text
Community Member
       ↓
Symptom Checklist
       ↓
Symptom Master List
       ↓
Symptom Validation
       ↓
Symptom → Syndrome Mapping
       ↓
Local Raw Record
       ↓
Daily Aggregation
       ↓
Severity Aggregation
       ↓
Trend Calculation
       ↓
Privacy Suppression
       ↓
Approved Aggregate Signal
       ↓
Federated Learning
       ↓
Forecast
       ↓
CUSUM / Shift Detection
       ↓
Early-Warning Signal
       ↓
Human Reviewer
```

The disease/condition knowledge base supports the synthetic-data and scenario-generation layers but does not create individual diagnoses.

---

# 11.16 Recommended Initial Implementation

For the first working version, implement the following:

```text
SYMPTOMS
≈ 150–250 standardized symptom entries

SYNDROMES
≈ 10–16 standardized categories

CONDITIONS
≈ 100+ reference conditions

PRIMARY MODEL TARGETS
1. Fever-like
2. Respiratory
3. Gastrointestinal
4. Other

NODES
1. Rural
2. Urban
3. Semi-Urban
4. Mixed

DATA SOURCES
1. Community
2. Doctor
3. Clinic
4. Pharmacy
5. Testing

OUTBREAK SCENARIOS
1. Respiratory
2. Gastrointestinal
3. Vector-borne
4. Neurological
5. Multi-syndrome
```

The system should allow the symptom and condition reference lists to expand without requiring changes to the federated-learning architecture.

---

# 11.17 Key Principle

```text
More symptoms
       ↓
More realistic synthetic data
       ↓
More realistic syndrome patterns
       ↓
More realistic node differences
       ↓
Better outbreak simulations
       ↓
Better evaluation of early-warning detection
```

However:

```text
More diseases ≠ Better individual diagnosis
```

The purpose of the dataset is to create **realistic aggregate community-health patterns**, not to diagnose individual people.

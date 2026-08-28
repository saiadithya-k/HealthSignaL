---
title: "Software Requirements Specification — HealthSignal"
subtitle: "Federated Community Health Trend Forecasting"
date: "Document Version 1.0 — August 28, 2026"
---

**Prepared for:** Interdisciplinary Innovation Challenge 2026 — Problem S5 (Software Track, ML / Privacy-Preserving Public Health)
**Classification:** Academic / Competition Prototype Specification

## Executive Summary

HealthSignal is a federated analytics platform that forecasts short-term (7–14 day) aggregate daily syndrome-category service demand across multiple institutions without centralizing patient-level records. Four or more simulated institutions retain their row-level data locally, transform it into an approved set of aggregate, non-identifiable features, and participate in federated model training rounds coordinated by a central federated coordinator. Only permitted, privacy-filtered aggregates and model updates leave each institution — never raw records. Federated learning reduces the need to centralize raw data, but it does not by itself guarantee privacy; explicit privacy-preserving mechanisms and privacy leakage testing (Section 9, Section 17) enforce the data boundary.

The platform trains a shared forecasting model whose target is aggregate daily syndrome-category service demand for the next 7–14 days, detects distribution shifts (e.g., emerging outbreak-like surges), quantifies forecast uncertainty, and routes operationally significant alerts to a human public-health reviewer for approval before any downstream action is taken. A minimum-group-size suppression rule is enforced on every dashboard view and export to prevent small-group disclosure. Model rounds, participants, failures, and reviewer decisions are all recorded in an immutable audit trail, per the official S5 logging requirement.

HealthSignal is explicitly **not** a diagnostic system: it never processes identifiable patient records, never produces an individual risk score, and never attempts re-identification of any person. Its unit of analysis is the institution-day aggregate, not the individual.

This document specifies the functional and non-functional requirements, AI/ML requirements, data requirements, privacy and responsible-AI requirements, system architecture, use cases, database design, APIs, dashboard design, evaluation plan, failure/recovery behavior, security threat model, requirements traceability, testing strategy, live demonstration plan, deployment architecture, technology stack, project scope, and acceptance criteria as a competition-ready prototype satisfying the official S5 problem statement, including its mandatory qualification test in which judges may alter an input, constraint, sensor, or tool state not used in the rehearsed demonstration.

---

## 1. Introduction

### 1.1 Purpose

This SRS defines the complete set of functional, non-functional, AI/ML, data, privacy, architectural, and operational requirements for the HealthSignal platform. Its purpose is to give an implementation team sufficient, unambiguous detail to design, build, test, and demonstrate a working prototype directly from this document, and to give evaluators a traceable mapping from every mandatory requirement in the official S5 problem statement to a corresponding system capability and test.

### 1.2 Scope

HealthSignal simulates a federated network of at least four community health institutions with non-identical (non-IID) synthetic populations. Each institution ingests synthetic/de-identified daily records, converts them locally into an approved set of aggregate features, and participates in periodic federated training rounds. The platform's forecasting target is aggregate daily syndrome-category service demand for a 7–14 day horizon, at institution and regional granularity. It also detects statistically significant distribution shifts, reports calibrated uncertainty, and surfaces alerts through a review dashboard where a human public-health reviewer approves, modifies, or rejects any operational action. The system is a decision-support and research prototype; it does not diagnose individuals, does not compute individual risk scores, and does not perform or enable re-identification.

### 1.3 Intended Audience

- Implementers (backend, ML/federated learning, frontend, DevOps) building the prototype
- Course instructors and competition judges evaluating the design and live demonstration
- Public-health domain reviewers providing subject-matter feedback
- Future contributors extending the prototype beyond the initial submission

### 1.4 Product Overview

HealthSignal consists of: (1) four or more simulated local institution nodes, each with a local data store, preprocessing pipeline, and privacy filter; (2) a federated coordinator that orchestrates training rounds and aggregates permitted model updates; (3) a forecasting engine producing 7–14 day aggregate daily syndrome-category service-demand forecasts with uncertainty intervals; (4) a distribution-shift detector flagging anomalous regional patterns; (5) a privacy-preserving dashboard enforcing minimum-group-size suppression on all views and exports; (6) a human review workflow through which a public-health reviewer approves or rejects operational alerts; and (7) an audit-logging subsystem recording every training round, participant event, privacy event, and reviewer decision.

### 1.5 Definitions, Acronyms and Abbreviations

| Term | Definition |
|---|---|
| SRS | Software Requirements Specification |
| FL | Federated Learning — a training approach in which a model is trained across decentralized data holders without pooling raw data |
| Institution / Node | A simulated local data holder (e.g., clinic, community center) participating in federation |
| Federated Coordinator | The central service that orchestrates training rounds and aggregates model updates |
| Aggregate Feature | A statistic computed over a group of records at an institution (e.g., daily count of a syndrome category) that contains no individual-level identifiers |
| Syndrome Category | A non-diagnostic, coarse classification of presenting complaint used for population-level surveillance (e.g., "respiratory," "gastrointestinal") |
| Non-IID | Non-independent and identically distributed; institutions have different population characteristics and base rates |
| Distribution Shift | A statistically significant change in the pattern of aggregate data relative to a learned baseline, potentially indicating an emerging health event |
| Uncertainty Interval | A quantitative range (e.g., prediction interval) expressing the confidence of a forecast |
| Small-Group Suppression | Withholding or coarsening any output derived from a group smaller than a defined minimum size, to prevent re-identification risk |
| Privacy Budget | A bounded quantity (e.g., differential privacy epsilon) that limits the cumulative privacy loss from repeated queries or model releases |
| RUL | Not applicable to this project (reserved term from digital-twin problem S4; excluded here) |
| Reviewer | The Public-Health Reviewer role that approves, modifies, or rejects generated alerts |
| MAE / MAPE | Mean Absolute Error / Mean Absolute Percentage Error, forecast accuracy metrics |
| Pooled Baseline | A model trained as if all institutional data were centralized, used only as an upper-bound reference, never as a deployment mode |

### 1.6 References

- Official Problem Statement: *Interdisciplinary Innovation Challenge — Agentic Intelligence, Defensive Automation & Biotechnology, 2026*, Problem S5, "HealthSignal — Federated Community Health Trend Forecasting" (attached source of truth)
- Common Judging Contract and 100-point rubric, same challenge book
- McMahan et al., *Communication-Efficient Learning of Deep Networks from Decentralized Data* (foundational federated averaging reference, general knowledge)
- Dwork & Roth, *The Algorithmic Foundations of Differential Privacy* (general knowledge reference for privacy budget concepts)


## 2. Overall Description

### 2.1 Product Perspective

HealthSignal is a new, self-contained prototype system. It is not a replacement for regional public-health surveillance infrastructure; it is a research/educational demonstration of privacy-preserving federated forecasting that could, in a matured form, complement existing syndromic surveillance systems (e.g., emergency-department chief-complaint monitoring) by adding a decentralized, privacy-first training mode. The system operates as a closed simulation environment: institution nodes, the coordinator, and the dashboard are separate services communicating over defined APIs, deployable on a single machine (via containers) or across separate hosts for the live demonstration.

### 2.2 Product Functions

- Register and manage simulated institution participants
- Ingest, validate, and preprocess synthetic daily records at each institution
- Generate an approved dictionary of aggregate features locally, never exposing row-level data
- Apply a privacy filter (clipping, noise addition, and/or minimum-group-size suppression) before any data leaves a node
- Coordinate federated training rounds, including handling of disconnected or failed participants
- Aggregate permitted local model updates into a global forecasting model
- Produce 7–14 day aggregate daily syndrome-category service-demand forecasts with uncertainty intervals
- Detect distribution shifts and injected demand surges
- Compare federated model performance against local-only and pooled-upper-bound baselines
- Generate operational alerts and route them to a human public-health reviewer
- Provide a privacy-preserving dashboard (regional forecasts, participation status, uncertainty, alerts, model performance) with small-group suppression on every view and export
- Maintain an immutable audit log of training rounds, participant events, privacy events, and reviewer decisions
- Support safe failure and recovery across institution disconnects, invalid updates, poor data quality, and high-uncertainty forecasts

### 2.3 User Classes and Characteristics

| User Class | Description | Technical Level |
|---|---|---|
| Institution / Data Node Administrator | Configures and operates a simulated local institution node; manages local data ingestion | Moderate — comfortable with configuration files and local dashboards |
| ML / Federated System Administrator | Operates the federated coordinator; manages training rounds, model versions, and system health | High — ML/systems background |
| Public-Health Reviewer | Reviews and approves/rejects alerts through the dashboard; the human authority in the loop | Low to moderate — domain expert, not necessarily technical |
| System Auditor | Inspects audit logs, privacy events, and traceability records for compliance verification | Moderate — familiar with logs and reporting |

### 2.4 Operating Environment

- Server-side services (institution nodes, coordinator, forecasting/anomaly services, dashboard backend) run as containerized Python/FastAPI applications, deployable on Linux hosts (local development machine, university lab server, or cloud VM)
- Dashboard frontend runs in any modern evergreen web browser (Chrome, Firefox, Edge)
- Institution nodes and the coordinator communicate over HTTPS/REST (or gRPC where specified) within a private network or over the public internet with TLS in the deployed demonstration
- A relational database (PostgreSQL) persists institution metadata, training-round records, model versions, forecasts, alerts, reviewer decisions, privacy events, and audit logs
- The system is designed to run entirely on synthetic data generated by an included data generator; no external clinical data source is required

### 2.5 Design Constraints

- Row-level records shall never leave an institution node in any form (raw, lightly transformed, or reversible encoding)
- Only approved aggregate features and permitted model artifacts (gradients, weight deltas, or secure aggregates) may cross the institution/coordinator boundary
- All dashboard views and data exports shall enforce a configurable minimum group size threshold (default: 11, consistent with common small-cell suppression conventions), below which values are suppressed or coarsened
- The system shall not implement or expose any individual diagnosis, individual risk score, or patient-level prediction capability
- Federated learning shall not be represented or documented as automatically guaranteeing privacy; explicit privacy-preserving mechanisms and privacy leakage testing are required in addition to the federated architecture
- The prototype shall use only synthetic, de-identified, publicly derived, or safely generated non-clinical aggregate data
- Implementation shall use technologies suitable for building and demonstrating a working prototype within a competition timeline

### 2.6 Assumptions and Dependencies

- Institutions are simulated processes/containers on the same or networked infrastructure, not real external organizations, for the purposes of the prototype
- Synthetic data generation approximates realistic seasonality, institutional heterogeneity, and outbreak-like surge patterns sufficient for meaningful evaluation, but is not a substitute for real epidemiological validation
- Network connectivity between nodes and the coordinator is assumed available under normal operation, with explicit handling defined for its absence
- The evaluation environment provides sufficient compute to run four to eight simulated institution processes plus a coordinator concurrently on a single demonstration machine or small cluster

### 2.7 System Boundaries

**In boundary:** institution node services, local preprocessing and privacy filtering, federated coordinator, global forecasting model, distribution-shift detector, uncertainty estimator, reviewer dashboard, audit logging, synthetic data generator, evaluation harness.

**Out of boundary:** real hospital record systems, real patient identity systems, any clinical decision-support or diagnostic function, regional public-health command systems, and any automatic public communication of alerts without human review.

## 3. Problem Definition

Community health institutions such as clinics and community centers often observe early, localized signals of emerging health-service pressure — a cluster of respiratory complaints, a rise in gastrointestinal presentations — before those signals are visible in slower regional aggregation pipelines. Detecting such shifts early and forecasting near-term demand would let public-health teams pre-position staff, supplies, or communications. However, the row-level records that would make such forecasting most accurate (patient-level visit records) cannot be freely centralized: legal, ethical, and institutional-trust constraints prevent pooling identifiable or even lightly de-identified individual records across independent institutions.

**Why centralized machine learning is unsuitable here:** a centralized approach would require every institution to transmit row-level records to a single location. This creates a single point of data-breach risk, requires data-sharing agreements that are often infeasible between independent institutions, and conflicts with the principle of data minimization — most of the row-level detail in a visit record is irrelevant to the aggregate demand-forecasting task and need never leave the originating institution.

**How federated learning addresses the constraint:** federated learning allows each institution to train a local model (or compute local aggregate statistics) on its own retained data and transmit only model updates — such as gradients or weight deltas — to a central coordinator, which aggregates them into a shared global model. No row-level record ever leaves the institution. Critically, federated learning by itself does not guarantee privacy: model updates can leak information about the underlying data through inference attacks. HealthSignal therefore layers explicit privacy-preserving mechanisms (aggregation before transmission, clipping, minimum-group-size suppression, and privacy leakage testing) on top of the federated architecture rather than treating federation as a privacy guarantee in itself.

**Service-demand forecasting vs. individual diagnosis:** the forecasting target is aggregate daily service demand by syndrome category. The system does not diagnose individuals, predict individual patient outcomes, or generate individual risk scores. HealthSignal's unit of analysis is always an institution-day-syndrome_category aggregate — e.g., "Institution B recorded an estimated 42 respiratory-syndrome presentations on 2026-08-20." The system never operates on, stores, or outputs anything at the level of a single patient. It cannot and does not answer "does this person have condition X," "what is this person's risk," or "who is this person." This distinction is enforced architecturally (row-level data never crosses the local boundary) and functionally (no API, model, or dashboard view in the system accepts or emits individual-level records).


## 4. Proposed System

### 4.1 High-Level Architecture

HealthSignal is organized into five layers: (1) **Local Institution Layer** — four or more independent nodes, each owning its raw synthetic data, running preprocessing, feature generation, and a privacy filter; (2) **Federation Layer** — a coordinator orchestrating training rounds, participant management, and aggregation of privacy-filtered updates; (3) **Intelligence Layer** — the forecasting engine, distribution-shift detector, and uncertainty estimator operating on the global model; (4) **Governance Layer** — the review workflow, alerting, and audit logging; (5) **Presentation Layer** — the privacy-preserving dashboard consumed by all user roles. Data and control flow strictly downward/upward through defined APIs; no layer bypasses another (e.g., the dashboard never queries an institution node directly).

### 4.2 Four or More Simulated Local Institutions

The prototype shall simulate at least four institutions (e.g., Institution A–D) with distinct, non-identical synthetic populations: different baseline visit volumes, different syndrome-category mixes, different seasonality strength, and independently injected surge events. Each institution runs as an isolated process/container with its own local data store, so that no institution can read another's row-level records.

### 4.3 Local Data Processing and the Data Boundary

Each institution ingests daily synthetic records, validates them against a defined schema, cleans and imputes missing values according to a documented policy, and computes the approved aggregate feature set (Section 8) for each syndrome category and day. This processing occurs entirely within the institution's boundary. Within each institution, data moves through a fixed local pipeline before anything is eligible to leave the node:

```
Raw Local Records
        |
        v
Local Validation
        |
        v
Local Preprocessing
        |
        v
Approved Aggregate Feature Generation
        |
        v
Privacy / Transmission Check
        |
        v
Local Model Training
        |
        v
Permitted Federated Model Update
        |
        v
Federated Coordinator
```

Raw row-level records exist only above the "Approved Aggregate Feature Generation" step and never proceed past it in identifiable or reversible form. The Federated Coordinator receives only the permitted federated information produced at the bottom of this pipeline — an aggregated or privacy-filtered model update — and nothing upstream of it. Specifically, raw row-level records shall never be: uploaded to the federated coordinator; sent through any API; stored in the central database; included in any log; included in any dashboard payload; or transmitted as part of model training data leaving the institution. This boundary is architectural, not merely procedural: no component outside an institution's own process/container has any code path capable of requesting or receiving row-level data.

### 4.4 Privacy Layer

Before any aggregate feature, gradient, or model update leaves an institution, it passes through a privacy filter that: (a) suppresses or coarsens any aggregate derived from fewer than the configured minimum group size; (b) clips per-round model-update magnitude to bound the influence of any single institution or record; (c) optionally adds calibrated noise consistent with a tracked privacy budget, where differential-privacy noise addition is a future/optional enhancement (Section 27) and not a mandatory requirement of the initial prototype unless separately implemented. The privacy layer is the only path by which data may leave a node, and it performs the mandatory pre-transmission check specified in FR-017: any outbound payload that is row-level-shaped, or that does not conform to the approved aggregate feature schema, is rejected and logged as a privacy event (PRIV-10) rather than transmitted. Federated learning reduces the need to centralize raw records, but the federated architecture alone does not guarantee privacy; the privacy layer's explicit checks — not federation by itself — are what enforce the data boundary, and they are complemented by the privacy leakage testing described in Section 9 and Section 17.

### 4.5 Federated Coordinator

The coordinator manages the registry of participating institutions, initiates and tracks training rounds, receives permitted updates, performs aggregation (e.g., federated averaging) into a new global model version, and records round-level metadata (participants, timing, aggregation method, failures) to the audit log. Cryptographic secure aggregation protocols (Section 27) are a future/optional enhancement that would further reduce the coordinator's ability to inspect individual institution updates; they are not assumed or required by the baseline architecture described here.

### 4.6 Federated Model Training

Training proceeds in rounds: the coordinator broadcasts the current global model to available institutions; each institution trains locally for a bounded number of epochs on its local aggregate feature history; each institution returns a privacy-filtered update; the coordinator aggregates received updates (weighted by an agreed, non-identifying scheme such as reported record count bucketed to protect small institutions) into the next global model version.

### 4.7 Forecasting Engine

The global model produces a 7–14 day forecast of aggregate daily syndrome-category service demand per institution and in regional aggregate, using recent aggregate feature history as input. This is the system's single primary forecasting target; it is not an individual-level prediction.

### 4.8 Distribution-Shift Detector

A statistical/ML detector compares incoming aggregate data and forecast residuals against learned baselines to flag distribution shifts — including injected demand surges — at institution and regional granularity, with a confidence score.

### 4.9 Uncertainty Estimation

Every forecast is accompanied by a calibrated uncertainty interval (e.g., prediction interval from quantile regression or ensemble spread), and every distribution-shift flag is accompanied by a confidence score, so reviewers can distinguish high-confidence from borderline signals.

### 4.10 Alert Generation

When a forecast, shift-detection score, or uncertainty measure crosses configured operational thresholds, the system generates a structured alert (institution/region, syndrome category, metric, threshold crossed, confidence, evidence window) and places it in the reviewer queue. No alert is transmitted externally without human approval.

### 4.11 Human Public-Health Review

A Public-Health Reviewer inspects each alert, its supporting evidence (forecast trend, shift score, data-coverage notes), and approves, modifies, or rejects it. Every decision is logged with reviewer identity, timestamp, and rationale.

### 4.12 Dashboard and Visualization

The dashboard (Section 16) presents regional and institutional forecasts, participation and connectivity status, uncertainty, shift alerts, model performance versus baselines, federated round status, and reviewer decision history — all filtered through minimum-group-size suppression.

### 4.13 Audit Logging

Every training round, participant join/leave/failure event, privacy-filter action, alert generation, and reviewer decision is written to an append-only audit log with timestamp and actor, queryable by the System Auditor role.


## 5. Detailed Functional Requirements

Requirements use "shall" for mandatory behavior. Each requirement is uniquely identified and independently testable.

#### Institution / Client Registration

- **FR-001:** The system shall allow a Federated System Administrator to register a new institution node with a unique institution ID, display name, and public key/credential for authenticated communication.
- **FR-002:** The system shall reject training-round participation from any institution whose credential fails authentication.
- **FR-003:** The system shall allow an Institution Administrator to view their own institution's registration status and connection health.
- **FR-004:** The system shall support deregistering or suspending an institution without deleting its historical audit records.

#### Local Data Ingestion

- **FR-005:** Each institution node shall ingest daily synthetic record batches from a configured local data source (file, generator API, or streaming feed).
- **FR-006:** The system shall timestamp and version every ingested batch at the institution.
- **FR-007:** The system shall reject ingestion of any record schema containing direct identifiers (name, national ID, exact date of birth, exact address) and log the rejection.

#### Data Validation

- **FR-008:** The system shall validate every ingested record against a defined schema (required fields, allowed syndrome-category values, valid date range) before processing.
- **FR-009:** The system shall quarantine records that fail validation and report a daily validation-failure count per institution, without exposing failing record content outside the institution.

#### Data Preprocessing

- **FR-010:** The system shall impute missing non-critical fields at each institution using a documented, deterministic policy (e.g., category-wise median for continuous fields).
- **FR-011:** The system shall flag and, per policy, exclude records with missing critical fields (date, syndrome category) from aggregate computation for that day.
- **FR-012:** The system shall detect and log statistical outliers in daily aggregate counts using a documented method (e.g., interquartile range) prior to feature generation.

#### Aggregate Feature Generation

- **FR-013:** The system shall compute, for each institution and calendar day, the approved aggregate feature set defined in the Feature Dictionary (Section 8), including per-syndrome-category visit counts, rolling averages, and day-of-week indicators.
- **FR-014:** The system shall never compute or store any feature keyed to an individual record identifier.
- **FR-015:** The system shall version the feature dictionary and reject federated participation from a node using an unapproved or outdated feature schema.

#### Prevention of Row-Level Data Leaving Local Institutions

- **FR-016:** The system shall architecturally prevent any API, log, database record, dashboard payload, export, or model-training payload at or beyond the institution/coordinator boundary from containing row-level records; only the boundary-crossing artifacts explicitly enumerated in Section 9 (aggregate features under privacy filtering, permitted model updates) are permitted to cross that boundary.
- **FR-017 (hard requirement):** The system shall run an automated pre-transmission check on every outbound payload from an institution node — including feature submissions, model updates, and any log or diagnostic payload — and shall reject and log the attempt as a privacy event (PRIV-10) if row-level-shaped data is detected (e.g., a record count below the minimum group size, a payload keyed to an individual identifier, or a payload whose shape does not match the approved aggregate/model-update schema). No payload shall be transmitted past this check without passing it.

#### Federated Training Rounds

- **FR-018:** The coordinator shall initiate federated training rounds on a configurable schedule (e.g., daily) or on manual trigger by the Federated System Administrator.
- **FR-019:** The coordinator shall broadcast the current global model version and round configuration to all registered, connected institutions at round start.
- **FR-020:** Each institution shall train locally for a configurable, bounded number of epochs using only its own retained aggregate feature history.
- **FR-021:** Each institution shall return its privacy-filtered model update to the coordinator before a configurable round deadline.

#### Participant Management

- **FR-022:** The coordinator shall track, for each round, which institutions were invited, which responded, and which failed to respond within the deadline.
- **FR-023:** The system shall support a configurable minimum-participant threshold below which a round is marked incomplete rather than aggregated.

#### Model Aggregation

- **FR-024:** The coordinator shall aggregate received, privacy-filtered updates into a new global model version using a documented aggregation method (e.g., federated averaging weighted by bucketed record-count tiers).
- **FR-025:** The system shall reject and log any received update that fails integrity/format validation (e.g., wrong shape, out-of-bound values, replay of a previous round's update) without incorporating it into aggregation.
- **FR-026:** The system shall version every aggregated global model and retain prior versions for rollback and comparison.

#### Handling Missing / Disconnected Institutions

- **FR-027:** If an institution disconnects mid-round, the coordinator shall exclude that institution's update from the current round, complete aggregation with remaining valid updates (subject to FR-023), and log the disconnection event.
- **FR-028:** The system shall re-invite a disconnected institution to the next scheduled round automatically, without requiring the round configuration to be redefined.
- **FR-029:** The dashboard shall visibly distinguish forecasts produced with full institutional participation from those produced with one or more institutions missing.

#### Forecast Generation

- **FR-030:** The forecasting engine shall generate an aggregate daily syndrome-category service-demand forecast for each participating institution and for the regional aggregate, using the current global model and recent aggregate feature history.
- **FR-031:** The system shall regenerate forecasts whenever a new global model version is produced or when new daily aggregate data becomes available for an institution.

#### 7–14 Day Forecasting

- **FR-032:** The system shall produce forecasts for a configurable horizon between 7 and 14 days, selectable by the Federated System Administrator, with a default of 7 days.
- **FR-033:** The system shall report forecast values at daily granularity across the full requested horizon.

#### Distribution-Shift Detection

- **FR-034:** The system shall compute a distribution-shift score for each institution and the regional aggregate on each new day of data, comparing observed values against the model's expected distribution.
- **FR-035:** The system shall flag a distribution shift when the shift score exceeds a configurable threshold, and shall record the evidence window (recent data points and expected range) supporting the flag.
- **FR-036:** The system shall distinguish shift detection from simple threshold breach by using a statistically grounded method (e.g., residual-based CUSUM, quantile-exceedance rate) rather than a single-point rule.

#### Uncertainty Reporting

- **FR-037:** Every forecast value shall be accompanied by a calibrated uncertainty interval (e.g., 80% and 95% prediction intervals).
- **FR-038:** The system shall widen or explicitly flag reduced-confidence forecasts when input data coverage is incomplete (e.g., a missing institution or a short history window).

#### Privacy-Preserving Dashboard / Export

- **FR-039:** The dashboard shall apply minimum-group-size suppression to every displayed value and every exported file, replacing suppressed values with a defined placeholder (e.g., "< min group size") rather than omitting the row silently.
- **FR-040:** The system shall log every dashboard export (who, what, when) to the audit log.

#### Minimum-Group-Size Suppression

- **FR-041 (official requirement, default is a proposed target):** The system shall enforce a configurable minimum group size on any query or view that could return a count derived from fewer underlying records than that threshold, at query time, not only at display time. A default of 11 is proposed as the engineering target for this implementation.
- **FR-042:** The system shall reject or coarsen (e.g., aggregate to a larger time window or geography) any query explicitly constructed to circumvent minimum-group-size suppression by narrowing filters, and shall log the attempt as a privacy event.

#### Model-Round Logging

- **FR-043:** The system shall log, for every training round: round ID, start/end time, global model version produced, participating institutions, excluded institutions and reasons, and aggregation method used.

#### Participant / Failure Logging

- **FR-044:** The system shall log every institution connection, disconnection, authentication failure, and update-validation failure with timestamp and institution ID.

#### Human Reviewer Workflow

- **FR-045:** The system shall present all open alerts to the Public-Health Reviewer role in a prioritized queue (e.g., by confidence and recency).
- **FR-046:** The system shall allow a reviewer to view full evidence for an alert (forecast trend, shift score, uncertainty, data-coverage notes, affected institution/region) before deciding.

#### Alert Generation

- **FR-047:** The system shall generate an alert automatically when a distribution-shift flag (FR-035) or a forecast threshold crossing occurs, and shall not require manual initiation for detection.
- **FR-048:** Each alert shall include a unique ID, generation timestamp, triggering metric and value, evidence window, and current review status.

#### Reviewer Approval / Rejection

- **FR-049:** The system shall allow the reviewer to approve, reject, or request more evidence for an alert, and to attach a free-text rationale.
- **FR-050:** The system shall prevent any downstream notification or dashboard "active alert" state from taking effect until a reviewer has approved the alert.

#### Audit Trail

- **FR-051:** The system shall maintain an append-only audit log covering all events enumerated in FR-043, FR-044, FR-040, FR-042, and FR-049, queryable by institution, time range, and event type.
- **FR-052:** The system shall prevent modification or deletion of existing audit log entries through any user-facing interface.

#### Error Handling

- **FR-053:** The system shall catch and log all data-validation, network, and model-training errors without crashing the affected service, returning a defined error response to any caller.
- **FR-054:** The system shall surface unresolved errors affecting forecast validity on the dashboard rather than silently producing a forecast from incomplete processing.

#### Recovery from Failed Federation Participants

- **FR-055:** The system shall support automatic retry (configurable count/backoff) for an institution that fails to submit an update before falling back to exclusion for that round (see FR-027).
- **FR-056:** The system shall allow manual re-inclusion of a previously failed institution once connectivity is restored, without restarting the whole training pipeline.

#### System Status Monitoring

- **FR-057:** The dashboard shall display live status (connected / disconnected / degraded) for every registered institution and for the coordinator.
- **FR-058:** The system shall display current model version, last successful round timestamp, and time since last forecast refresh.


## 6. Non-Functional Requirements

The official S5 problem statement specifies mandatory behaviors (e.g., simulate at least four institutions, forecast 7–14 days, prevent small-group disclosure, log rounds/participants/failures/reviewer decisions) without prescribing specific numeric thresholds for latency, uptime, or similar engineering parameters. Every specific number in this section (default group size, timing targets, uptime percentages, retention windows) is therefore a **proposed engineering target** set for this implementation, not a value drawn from the official problem statement, and is explicitly labeled as such. The one exception is the minimum-group-size mechanism itself, which is an official requirement ("prevent small-group disclosure in every dashboard/export"); only its specific default numeric value (11) is a proposed target, configurable by the implementation.

### 6.1 Security
- **NFR-SEC-01:** All institution-to-coordinator and dashboard-to-backend communication shall use TLS 1.2 or higher.
- **NFR-SEC-02:** All API endpoints shall require authenticated, role-scoped access tokens; no anonymous write access shall be permitted.
- **NFR-SEC-03 (proposed target):** Institution credentials shall be rotated on a configurable interval (default 90 days, proposed engineering target) and immediately revocable by the Federated System Administrator.

### 6.2 Privacy
- **NFR-PRIV-01:** No row-level record shall exist outside its originating institution's storage at any point in the system's operation, verified by automated pre-transmission checks (FR-017).
- **NFR-PRIV-02:** Minimum-group-size suppression shall be enforced on 100% of dashboard views and exports (official S5 requirement: "prevent small-group disclosure in every dashboard/export"), verified by a dedicated privacy test suite (Section 22). The default threshold of 11 is a proposed engineering target, configurable by the implementation.
- **NFR-PRIV-03:** The system shall pass a defined membership-inference privacy leakage test (Section 17) with leakage below a documented acceptable threshold before being presented as privacy-preserving in any deliverable.

### 6.3 Performance
- **NFR-PERF-01 (proposed target):** A daily forecast refresh across four institutions shall complete within 5 minutes on the reference demonstration hardware.
- **NFR-PERF-02 (proposed target):** Dashboard pages shall render initial content within 3 seconds under normal network conditions.
- **NFR-PERF-03 (proposed target):** A single federated training round with four institutions shall complete aggregation within 2 minutes of the round deadline, excluding local training time.

### 6.4 Availability
- **NFR-AVAIL-01 (proposed target):** The coordinator and dashboard backend shall target 99% uptime during the demonstration and evaluation window.
- **NFR-AVAIL-02:** Loss of connectivity to a single institution shall not degrade dashboard availability for data from the remaining institutions.

### 6.5 Reliability
- **NFR-REL-01 (proposed target, structure required by official statement):** the underlying capability — completing/handling a round with a missing institution — is required by the official statement's "drop one institution mid-round and recover safely" demonstration; the specific default of 3-of-4 is a proposed engineering target for the minimum-participant threshold (FR-023).
- **NFR-REL-02:** No single component failure (one institution node, one dashboard replica) shall cause data loss for previously committed audit records.

### 6.6 Scalability
- **NFR-SCALE-01 (proposed target):** The architecture shall support scaling from 4 to at least 12 simulated institutions without changes to the coordinator's external API contract.
- **NFR-SCALE-02 (proposed target):** The database schema shall support at least 2 years of simulated daily aggregate history per institution without redesign.

### 6.7 Usability
- **NFR-USE-01 (proposed target):** A Public-Health Reviewer with no ML background shall be able to review and act on an alert within 2 minutes of first viewing the dashboard, verified by a task-based usability check.
- **NFR-USE-02:** All dashboard error and suppression states shall be shown in plain language, not raw error codes.

### 6.8 Maintainability
- **NFR-MAINT-01:** All services shall expose structured (JSON) logs suitable for centralized log aggregation.
- **NFR-MAINT-02:** The codebase shall maintain a documented module boundary between institution-node code, coordinator code, and dashboard code, permitting independent modification.

### 6.9 Reproducibility
- **NFR-REPRO-01:** Every experiment run (Section 18) shall be reproducible from a fixed random seed and a versioned configuration file.
- **NFR-REPRO-02:** Model and data cards (Section 17) shall be regenerated automatically as build artifacts, not hand-maintained documents that can drift from the code.

### 6.10 Explainability
- **NFR-EXP-01:** Every forecast and shift alert displayed to the reviewer shall be accompanied by the evidence window (recent data points, expected range, contributing features) that produced it.
- **NFR-EXP-02:** The system shall report feature importance or comparable local explanation for at least the top contributing features behind each shift alert.

### 6.11 Auditability
- **NFR-AUDIT-01:** 100% of training rounds, privacy events, and reviewer decisions shall be present in the audit log, verified by a log-completeness test comparing expected vs. logged event counts.
- **NFR-AUDIT-02:** Audit log entries shall be tamper-evident (e.g., hash-chained) so that any post-hoc modification is detectable.

## 7. AI/ML Requirements

- **AI-01 Forecasting problem:** Multi-horizon time-series regression predicting aggregate daily syndrome-category service demand per institution and regionally. This is the system's single primary forecasting target.
- **AI-02 Input features:** Aggregate feature dictionary values (Section 8) — historical daily counts, rolling averages, day-of-week/seasonality indicators, institution identifier (non-identifying categorical), and prior shift-detection flags.
- **AI-03 Target variable:** Next-day (and cumulative 7–14 day) syndrome-category visit count per institution and region.
- **AI-04 Forecast horizon:** 7 to 14 days, configurable (FR-032).
- **AI-05 Local model training:** Each institution trains a local copy of the shared model architecture on its own aggregate feature history for a bounded number of local epochs per round (FR-020).
- **AI-06 Federated aggregation:** Global model updated via federated averaging (or a documented alternative) weighted by bucketed, non-identifying record-count tiers (FR-024).
- **AI-07 Non-IID institutional data:** The model architecture and training procedure shall be validated to converge across institutions with materially different base rates and syndrome mixes; per-institution personalization (e.g., a lightweight local fine-tuning head) is permitted as an enhancement.
- **AI-08 Missing-node resilience:** Training and forecasting shall degrade gracefully (wider uncertainty, visible coverage flag) rather than fail when one institution is missing (FR-027, FR-038).
- **AI-09 Distribution-shift detection:** A dedicated statistical or ML-based detector (Section 4.8) operating on forecast residuals and/or raw aggregate trends.
- **AI-10 Uncertainty estimation:** Calibrated prediction intervals via quantile regression, conformal prediction, or ensemble spread; calibration shall be evaluated (Section 17).
- **AI-11 Model calibration:** Interval coverage shall be evaluated against nominal confidence level (e.g., 80% intervals should contain the true value ~80% of the time on held-out data).
- **AI-12 Model versioning:** Every aggregated global model shall be assigned a unique, immutable version identifier and be retrievable for comparison and rollback (FR-026).
- **AI-13 Training/validation/test separation:** Each institution's local history shall be split chronologically into training, validation, and held-out test windows; the held-out window shall never be used for hyperparameter tuning.
- **AI-14 Held-out evaluation:** Final reported metrics (Section 17) shall be computed exclusively on the held-out test window and on judge-injected unseen scenarios, never on training data.
- **AI-15 Baseline comparison (official S5 requirement):** The system shall compute and report all three of the following models for every evaluation:
  - **A. Local-only model** — each institution trains independently using only its own local data, with no federation. This represents the accuracy achievable without any cross-institution collaboration and serves as the lower bound the federated approach must beat to justify federation.
  - **B. Federated model** — institutions collaboratively train without centralizing row-level data, via the architecture described in Sections 4 and 10. This is the operational, privacy-preserving system under evaluation and the only one of the three baselines that is ever deployed.
  - **C. Pooled-data upper-bound model** — a centralized experimental baseline trained on combined raw data across all institutions. This model exists solely for offline evaluation and comparison; it is never the operational architecture, its training data is never centralized outside the evaluation harness, and it shall not be presented, deployed, or described anywhere in this document as a production or privacy-preserving mode of the system.

  This three-way comparison is necessary because it is the only way to demonstrate that (i) federation meaningfully improves on what any single institution could achieve alone, and (ii) the accuracy cost of not pooling raw data is small relative to the theoretical upper bound — i.e., that federation is worth doing without centralizing identifiable records.


## 8. Data Requirements

### 8.1 Synthetic / De-identified Aggregate Data
All data used by HealthSignal shall be synthetic, generated by an included data generator, or otherwise safely de-identified aggregate data with no path back to an identifiable individual. No real clinical row-level data shall be used.

### 8.2 Institution-Level Data
Each institution maintains its own local store of daily synthetic records and derived daily aggregates. Institutions shall have distinct configured population sizes, syndrome-category base rates, and seasonal patterns to ensure genuine non-IID behavior. Synthetic records represent non-clinical, non-diagnostic syndrome categories such as: respiratory illness / respiratory symptoms; gastrointestinal illness; fever / flu-like symptoms; and other appropriate syndromic categories defined in the approved feature dictionary (Section 8.4). These categories describe presenting-complaint groupings for surveillance purposes only and do not constitute or imply a clinical diagnosis.

### 8.3 Time-Series Structure
Data is structured as one row per (institution, date, syndrome_category) with associated aggregate count and derived features, forming a regular daily time series per institution per category.

### 8.4 Feature Dictionary (approved, non-exhaustive starting set)

| Feature | Description | Level |
|---|---|---|
| daily_visit_count | Count of visits for a syndrome category on a given day | Institution-day-category |
| rolling_7day_avg | 7-day rolling average of daily_visit_count | Institution-day-category |
| rolling_14day_avg | 14-day rolling average of daily_visit_count | Institution-day-category |
| day_of_week | Categorical day-of-week indicator | Day |
| is_holiday | Boolean holiday indicator (configurable calendar) | Day |
| week_of_year | ISO week number, for seasonality | Day |
| prior_shift_flag | Whether a distribution shift was flagged in the previous 7 days | Institution-category |
| data_completeness_pct | Fraction of expected records successfully validated that day | Institution-day |

### 8.5 Target Variables
The primary forecasting target is aggregate daily syndrome-category service demand: next-day and cumulative 7–14-day forward visit counts per syndrome category, per institution and regionally aggregated. No target variable at or below the individual-record level exists anywhere in the data model.

### 8.6 Data Validation
Defined in FR-008–FR-012: schema validation, missing-value handling, and outlier detection, executed entirely within each institution's boundary before feature values are eligible for transmission.

### 8.7 Missing Values
Missing non-critical fields are imputed per a documented deterministic policy (FR-010); missing critical fields (date, syndrome category) exclude the record from that day's aggregate (FR-011), with the exclusion count itself logged (not the record content).

### 8.8 Outliers
Detected via a documented statistical method (e.g., IQR) at ingestion; flagged outliers are retained but marked, allowing the shift detector to distinguish a data-quality outlier from a genuine surge.

### 8.9 Seasonality
The synthetic data generator shall produce configurable weekly and annual seasonality patterns per institution, so the forecasting model must learn to separate seasonal variation from anomalous shifts.

### 8.10 Injected Demand Surges / Outbreak-Like Events
The data generator shall support injecting a configurable regional or institutional demand surge (magnitude, duration, syndrome category, onset date) for use in evaluation scenarios and the live demonstration (Section 23).

### 8.11 Data Retention
Institution-local raw synthetic records shall be retained per a configurable policy (proposed engineering target: 2 years) after which they are purged; aggregate feature history and model artifacts are retained separately per Section 9's retention policy.

### 8.12 Data Access Restrictions
Row-level data is accessible only to the owning institution's local processes; aggregate feature data crossing the privacy filter is accessible to the coordinator and downstream forecasting components; dashboard consumers see only minimum-group-size-suppressed views appropriate to their role.

### 8.13 Minimum Group-Size Requirements
No query, view, export, or log entry visible outside an institution's own boundary shall expose a count derived from fewer than the configured minimum group size (official S5 requirement; proposed default engineering target: 11); see FR-041–FR-042.

## 9. Privacy and Responsible AI Requirements

This section governs the system's core responsible-AI posture and is treated as of equal priority to functional correctness.

- **PRIV-01:** No raw row-level data shall leave a local institution in any form, at any layer of the system (FR-016, FR-017, NFR-PRIV-01).
- **PRIV-02:** The system shall not perform, expose, or support individual diagnosis of any kind.
- **PRIV-03:** The system shall not compute, store, or expose any individual-level risk score.
- **PRIV-04:** The system shall not perform, or provide functionality that materially assists, re-identification of any individual from aggregate outputs.
- **PRIV-05:** Small-group suppression (minimum group size, default 11) shall apply to every dashboard view and export without exception (FR-039–FR-042).
- **PRIV-06:** Privacy leakage testing (e.g., a membership-inference attack simulation against the trained global model) shall be run before every model version is presented as production-ready, with results included in the model card (Section 17, Section 18).
- **PRIV-07:** Only features present in the versioned, approved feature dictionary (Section 8.4) may be computed, transmitted, or used in training; any code change adding a new feature requires updating and re-approving the dictionary version.
- **PRIV-08:** A documented data retention policy (Section 8.11) shall govern deletion of raw synthetic records, aggregate history, and model artifacts.
- **PRIV-09:** Access to row-level data, aggregate feature stores, and audit logs shall be role-restricted per Section 12, with access attempts logged.
- **PRIV-10:** All privacy-relevant events (suppression triggers, rejected transmissions, leakage-test results) shall be recorded in the audit log (FR-042, FR-051).
- **PRIV-11:** Every model card shall explicitly state known model limitations (e.g., degraded accuracy for institutions with sparse history) and data-coverage limitations (e.g., which institutions were included in a given forecast).
- **PRIV-12:** No alert shall be treated as actionable or communicated externally without explicit human public-health reviewer approval (FR-050).

**Distinguishing three related but different concepts:**
- **Privacy-preserving analytics** is the set of technical mechanisms (local retention of raw data, aggregation, clipping, suppression, leakage testing) that bound what any party outside an institution can learn about individuals.
- **Aggregate forecasting** is the analytic task HealthSignal performs — predicting population-level, institution-day-category demand — which by construction operates on groups, not individuals, and is undefined below the minimum group size.
- **Individual healthcare prediction** (diagnosis, individual risk scoring, patient-level prognosis) is a categorically different task that HealthSignal does not perform, has no data pathway to perform, and is explicitly out of scope (Section 26).


## 10. System Architecture

```
 Institution A   Institution B   Institution C   Institution D
      |               |               |               |
      v               v               v               v
  Local preprocessing (schema validation, imputation, outlier flagging)
      |               |               |               |
      v               v               v               v
  Privacy filter (min-group suppression, clipping, [noise])
      |               |               |               |
      v               v               v               v
  Local model training (bounded local epochs on retained aggregate history)
      |               |               |               |
      v               v               v               v
  Federated updates  ---------------->  Federated Coordinator
                                              |
                                              v
                                         Global Model
                                              |
                                              v
                                        Trend Forecast (7-14 day)
                                              |
                                              v
                              Anomaly / Distribution-Shift Detector
                                              |
                                              v
                                    Uncertainty Estimator
                                              |
                                              v
                              Public Health Review Dashboard
                                              |
                                              v
                                       Human Reviewer
```

**Data flow between components:**
1. **Institutions → Local preprocessing:** raw synthetic daily records enter validation, cleaning, and outlier flagging entirely within the institution boundary.
2. **Local preprocessing → Privacy filter:** cleaned records are converted to approved aggregate features; the privacy filter suppresses small groups and clips values. This is the last point at which anything resembling raw structure exists; only aggregate, filtered output proceeds.
3. **Privacy filter → Local model training:** filtered aggregate feature history is used to train a local copy of the shared model for the current round.
4. **Local model training → Federated updates:** the locally trained model's update (weight delta/gradient), itself passed back through the privacy filter's clipping/suppression checks, is packaged for transmission.
5. **Federated updates → Federated Coordinator:** updates from all responding institutions arrive at the coordinator over authenticated TLS channels.
6. **Coordinator → Global Model:** the coordinator aggregates valid updates (FR-024/FR-025) into a new versioned global model.
7. **Global Model → Trend Forecast:** the forecasting engine runs the global model against each institution's (and the region's) recent aggregate history to produce the 7–14 day forecast.
8. **Trend Forecast → Anomaly/Distribution-Shift Detector:** forecast residuals and raw aggregate trends are analyzed for statistically significant shifts.
9. **Trend Forecast + Shift Detector → Uncertainty Estimator:** prediction intervals and shift-confidence scores are computed and attached to every output value.
10. **Uncertainty Estimator → Public Health Review Dashboard:** all forecast, shift, and coverage information — pre-filtered through minimum-group-size suppression — populates the dashboard views (Section 16).
11. **Dashboard → Human Reviewer:** the reviewer inspects alerts and evidence and records an approve/reject/modify decision, which is written back to the audit log and reflected in dashboard alert state (FR-049–FR-050).

## 11. Use Cases

### UC-001 Institution Data Preparation
- **Actors:** Institution Administrator, Institution Node (system)
- **Preconditions:** Institution is registered (FR-001); local data source configured.
- **Main flow:** (1) Administrator triggers or schedules ingestion. (2) Node ingests daily batch. (3) Node validates schema. (4) Node imputes/excludes per policy. (5) Node computes approved aggregate features. (6) Node applies privacy filter. (7) Node marks batch ready for training.
- **Alternative flow:** Partial batch received (e.g., late feed) — node processes available records and flags incomplete coverage for the day.
- **Exception flow:** Schema validation fails entirely — batch is quarantined, error logged (FR-009), Administrator notified; no aggregate features are generated from the quarantined batch.
- **Postconditions:** A versioned, privacy-filtered aggregate feature set exists locally, ready for the next training round.

### UC-002 Federated Training Round
- **Actors:** Federated System Administrator, Federated Coordinator, Institution Nodes
- **Preconditions:** At least the minimum-participant threshold of institutions are registered and have ready aggregate data.
- **Main flow:** (1) Coordinator initiates round. (2) Coordinator broadcasts current global model. (3) Each institution trains locally. (4) Each institution returns a privacy-filtered update. (5) Coordinator validates and aggregates updates. (6) Coordinator publishes new global model version. (7) Round metadata logged.
- **Alternative flow:** An institution submits late but before round close — update is accepted if received before deadline.
- **Exception flow:** Fewer than minimum-participant threshold respond — round is marked incomplete, no new global model is published, event logged (FR-023).
- **Postconditions:** Either a new global model version exists, or the round is logged as incomplete with reasons.

### UC-003 Generate Health-Service Forecast
- **Actors:** Forecasting Engine (system), Federated System Administrator
- **Preconditions:** A current global model version exists.
- **Main flow:** (1) Engine retrieves each institution's recent aggregate history. (2) Engine runs the global model to produce 7–14 day forecast per institution and region. (3) Engine computes uncertainty intervals. (4) Forecast is persisted and versioned. (5) Dashboard reflects new forecast.
- **Alternative flow:** Institution history has a short window — engine flags reduced confidence and widens intervals (FR-038).
- **Exception flow:** Model inference fails for an institution — that institution's forecast is marked unavailable; other institutions' forecasts proceed.
- **Postconditions:** A versioned, timestamped forecast set with uncertainty is available on the dashboard.

### UC-004 Detect Regional Demand Surge
- **Actors:** Distribution-Shift Detector (system), Public-Health Reviewer
- **Preconditions:** Current forecast and recent aggregate data exist for the region.
- **Main flow:** (1) Detector compares recent regional aggregate trend to expected baseline. (2) Shift score exceeds threshold. (3) Alert generated with evidence window (FR-047–FR-048). (4) Reviewer is notified via dashboard queue.
- **Alternative flow:** Shift score is elevated but below alert threshold — flagged as "watch" status on dashboard without generating a full alert.
- **Exception flow:** Underlying data for the region has a coverage gap (missing institution) — shift score is computed with widened uncertainty and a coverage caveat rather than suppressed entirely.
- **Postconditions:** A logged, reviewer-visible alert (or watch flag) exists with supporting evidence.

### UC-005 Detect Distribution Shift
- **Actors:** Distribution-Shift Detector (system)
- **Preconditions:** Forecast residual history is available for an institution or region.
- **Main flow:** (1) Detector computes a statistical shift score (e.g., CUSUM) each new day. (2) Score compared to threshold. (3) If exceeded, shift flagged and evidence window captured. (4) Flag propagates to alerting (UC-004) when applicable.
- **Alternative flow:** A known, previously acknowledged shift (e.g., a confirmed seasonal transition) is in progress — detector suppresses duplicate alerts for the same ongoing event per a cooldown policy.
- **Exception flow:** Insufficient history to compute a stable baseline (new institution) — shift detection is deferred and flagged as "insufficient history" rather than producing an unreliable score.
- **Postconditions:** Shift score and evidence are recorded and available to downstream alerting and the dashboard.

### UC-006 Institution Disconnects During Training
- **Actors:** Federated Coordinator (system), Federated System Administrator
- **Preconditions:** A training round is in progress.
- **Main flow:** (1) Institution fails to respond before deadline. (2) Coordinator logs disconnection (FR-027). (3) Coordinator proceeds with remaining valid updates if the minimum-participant threshold is still met. (4) Global model is published, flagged as trained with N-1 participants.
- **Alternative flow:** Institution reconnects mid-round before the deadline — its update is accepted normally.
- **Exception flow:** Remaining participants fall below minimum threshold after the disconnection — round is marked incomplete (UC-002 exception flow) rather than aggregating from too few institutions.
- **Postconditions:** Disconnection event is logged; system state (complete/incomplete round) is accurately reflected on the dashboard.

### UC-007 Public-Health Reviewer Reviews Alert
- **Actors:** Public-Health Reviewer
- **Preconditions:** At least one open alert exists in the review queue.
- **Main flow:** (1) Reviewer opens alert from queue. (2) Reviewer inspects evidence window, forecast trend, uncertainty, and data-coverage notes. (3) Reviewer approves, rejects, or requests more evidence, with rationale. (4) Decision is logged and dashboard alert state updates.
- **Alternative flow:** Reviewer requests more evidence — alert remains open, additional detail (e.g., extended evidence window) is surfaced, and re-queued for review.
- **Exception flow:** Reviewer attempts to approve an alert whose supporting data has since been superseded by a newer forecast — system blocks the action and prompts re-review against current evidence.
- **Postconditions:** Alert has a recorded reviewer decision; only approved alerts are shown as active/actionable elsewhere in the dashboard.

### UC-008 Small-Group Query Suppression
- **Actors:** Any Dashboard User, Privacy Filter (system)
- **Preconditions:** User submits a dashboard query or export request (e.g., narrow date range + specific institution + specific syndrome category).
- **Main flow:** (1) Query is evaluated against underlying group size. (2) If group size is at or above the minimum threshold, results are returned normally. (3) If below threshold, values are suppressed and replaced with a defined placeholder.
- **Alternative flow:** User narrows filters incrementally to attempt to isolate a small group — each narrowing is independently checked; suppression is reapplied at every step.
- **Exception flow:** Repeated narrowing attempts matching a known circumvention pattern are logged as a privacy event and, per policy, may trigger a rate limit on that user's query rate (FR-042).
- **Postconditions:** No output ever exposes a count below the minimum group size; suppression attempts are logged where applicable.

### UC-009 Generate Forecast Report
- **Actors:** Public-Health Reviewer, Federated System Administrator
- **Preconditions:** A current forecast set exists.
- **Main flow:** (1) User requests a forecast report for a date range/institution/region. (2) System compiles forecast values, uncertainty, model version, and data-coverage notes. (3) Minimum-group-size suppression is applied. (4) Report is generated (CSV/PDF) and export is logged.
- **Alternative flow:** User requests a report at a granularity that would violate suppression — system automatically coarsens to the nearest permissible granularity and notes the adjustment in the report.
- **Exception flow:** Underlying forecast data is stale (older than a configured freshness threshold) — report generation proceeds but is watermarked "stale data" with the last-refresh timestamp.
- **Postconditions:** A logged, suppression-compliant report artifact is produced.

### UC-010 Audit Federated Training
- **Actors:** System Auditor
- **Preconditions:** One or more training rounds have occurred.
- **Main flow:** (1) Auditor queries audit log by date range/institution/event type. (2) System returns matching immutable log entries. (3) Auditor cross-checks round completeness, participant events, privacy events, and reviewer decisions against expected counts.
- **Alternative flow:** Auditor requests a full traceability export mapping S5 requirements to logged evidence (Section 21) — system compiles and exports the traceability report.
- **Exception flow:** Auditor query matches zero records for a time range expected to have activity — system explicitly reports "no matching records" rather than an ambiguous empty state, to distinguish "nothing happened" from a possible logging gap.
- **Postconditions:** Auditor has verifiable, tamper-evident evidence of system operation for the queried period.


## 12. User Roles

| Role | Permissions |
|---|---|
| Institution / Data Node Administrator | Configure and monitor own institution's ingestion and connectivity; view own institution's local processing status and validation-failure counts; cannot view other institutions' raw or aggregate data; cannot approve alerts. |
| ML / Federated System Administrator | Register/suspend institutions; configure and trigger training rounds; view global model versions and system-wide status; configure thresholds (minimum group size, shift-detection sensitivity, forecast horizon); cannot alter audit log entries. |
| Public-Health Reviewer | View forecasts, alerts, and evidence (suppression-compliant); approve/reject/request-more-evidence on alerts; generate forecast reports; cannot alter model configuration or training schedule. |
| System Auditor | Read-only access to the full audit log and traceability export; cannot approve alerts, alter configuration, or modify training; can flag anomalous log patterns for administrator follow-up. |

## 13. System Workflow

The end-to-end operational workflow proceeds: **local data** ingestion at each institution → **preprocessing** (validation, imputation, outlier flagging) → **privacy filtering** (aggregate feature generation, clipping, minimum-group-size suppression) → **local training** (bounded local epochs against retained aggregate history) → **federated aggregation** (coordinator validates and combines privacy-filtered updates) → **global model** (new versioned model published) → **forecasting** (7–14 day service-demand prediction per institution and region) → **anomaly detection** (distribution-shift scoring against learned baselines) → **uncertainty analysis** (calibrated intervals and confidence attached to every output) → **human review** (Public-Health Reviewer inspects evidence and decides) → **alert/action** (only reviewer-approved alerts become active/visible as actionable) → **audit log** (every step above is recorded immutably, closing the loop for traceability and auditor verification).

## 14. Database / Data Storage Requirements

Conceptual entity model (no patient-level tables are defined anywhere in this schema):

| Entity | Key Attributes |
|---|---|
| Institutions | institution_id (PK), display_name, status, registered_at, credential_ref |
| FeatureDefinitions | feature_id (PK), name, description, schema_version, approved_at |
| TrainingRounds | round_id (PK), start_time, end_time, model_version_produced (FK), status (complete/incomplete) |
| RoundParticipants | round_id (FK), institution_id (FK), response_status, submitted_at |
| ModelVersions | model_version_id (PK), created_at, aggregation_method, parent_version_id, metrics_ref |
| Forecasts | forecast_id (PK), model_version_id (FK), institution_id (nullable for regional), syndrome_category, forecast_date, horizon_day, predicted_value, interval_low, interval_high |
| ShiftDetections | detection_id (PK), institution_id (nullable for regional), syndrome_category, detected_at, shift_score, evidence_ref |
| Alerts | alert_id (PK), detection_id (FK, nullable), forecast_id (FK, nullable), generated_at, status, evidence_ref |
| ReviewerDecisions | decision_id (PK), alert_id (FK), reviewer_id, decision, rationale, decided_at |
| PrivacyEvents | event_id (PK), event_type (suppression/rejected_transmission/leakage_test), institution_id (nullable), occurred_at, detail_ref |
| SystemFailures | failure_id (PK), component, failure_type, occurred_at, resolved_at, detail_ref |
| AuditLogs | log_id (PK), event_type, actor, occurred_at, reference_entity, reference_id, hash_prev |

All foreign-key relationships preserve traceability from a dashboard-visible forecast or alert back to the training round and institutions that produced it, without ever storing or referencing individual patient records.

## 15. API Requirements

All APIs are internal to the HealthSignal system (institution nodes, coordinator, forecasting service, dashboard backend, reviewer interface) and are specified at SRS level; no implementation code is provided here.

| Endpoint (purpose) | Request | Response | Auth | Error Conditions |
|---|---|---|---|---|
| Register Institution (Coordinator) | institution_id, display_name, credential | registration confirmation, assigned status | FSA-scoped token | duplicate ID; invalid credential format |
| Submit Aggregate Features (Institution → Coordinator, pre-training) | institution_id, feature_batch (privacy-filtered), schema_version | acceptance/rejection status | Institution-scoped token | schema mismatch; failed pre-transmission row-level check (FR-017); stale schema version |
| Broadcast Round (Coordinator → Institution) | round_id, global_model_version, deadline | acknowledgment | Coordinator-signed | institution unreachable (timeout) |
| Submit Model Update (Institution → Coordinator) | round_id, institution_id, privacy-filtered update payload | acceptance/rejection status | Institution-scoped token | integrity/format validation failure (FR-025); deadline passed; replay detected |
| Get Forecast (Dashboard → Forecasting Service) | institution_id or "regional", syndrome_category, horizon | forecast values with uncertainty, model_version, coverage flags | Role-scoped token (min-group suppression applied server-side) | model unavailable; institution not registered |
| Get Alerts (Dashboard → Reviewer Service) | filter params (status, date range) | list of alerts with evidence refs | Reviewer/Auditor-scoped token | none beyond standard auth failure |
| Submit Reviewer Decision (Dashboard → Reviewer Service) | alert_id, decision, rationale, reviewer_id | confirmation | Reviewer-scoped token | alert evidence stale (UC-007 exception); alert already decided |
| Query Audit Log (Auditor tool → Audit Service) | filter params (event_type, date range, institution) | list of immutable log entries | Auditor-scoped token | none beyond standard auth failure |
| Export Report (Dashboard → Reporting Service) | scope params, format | suppression-compliant file (CSV/PDF) | Role-scoped token | requested granularity below minimum group size (auto-coarsened per UC-009) |

## 16. Dashboard Requirements

- **Regional forecast view:** 7–14 day forecast curve with uncertainty band, per syndrome category, at regional aggregate level.
- **Institution participation view:** live connect/disconnect status, last successful round per institution.
- **Forecast confidence/uncertainty view:** interval width and coverage-gap flags alongside every forecast series.
- **Distribution-shift alerts view:** current open, watch, and resolved shift alerts with evidence links.
- **Demand surge visualization:** highlighted overlay on the forecast/actuals chart showing detected or injected surge periods.
- **Model performance view:** current model's MAE/MAPE and shift-detection recall vs. the local-only and pooled-upper-bound baselines (Section 7, AI-15).
- **Federated round status view:** most recent rounds, participants, completion status.
- **Missing-node status view:** explicit indicator whenever a displayed forecast reflects fewer than all registered institutions.
- **Privacy suppression indicators:** visible marker wherever a value has been suppressed or coarsened, rather than silently omitted.
- **Reviewer decisions view:** history of approved/rejected/pending alerts with rationale.
- **Audit history view (Auditor role only):** searchable, read-only audit log.


## 17. AI/ML Evaluation Plan

Evaluation shall use the official S5 metrics, computed on held-out data and judge-injected unseen scenarios only (never on training data):

- **Forecast MAE/MAPE:** Mean Absolute Error and Mean Absolute Percentage Error between predicted and actual daily syndrome-category counts over the forecast horizon, computed per institution and regionally, on the held-out test window.
- **Event detection recall:** Fraction of known injected surge events (Section 8.10) correctly flagged by the shift detector within a defined detection window.
- **Event detection lead time:** Number of days between the shift detector's flag and the peak (or defined onset threshold) of the actual surge; measures how early a genuine signal is caught.
- **Federated vs. local uplift:** Percentage improvement in MAE/MAPE of the federated model (baseline B) over the local-only model (baseline A), demonstrating the value of federation.
- **Privacy leakage tests:** Simulated membership-inference and small-group re-identification attempts against the global model and dashboard outputs; leakage rate must remain below a documented acceptable threshold, and any successful suppression bypass attempt (UC-008 exception flow) is logged as a failed test case.
- **Performance across institutions:** MAE/MAPE reported per institution, not only in aggregate, to reveal whether the federated model under-serves any particular institution's population.
- **Missing-node resilience:** Forecast MAE/MAPE and shift-detection recall recomputed with one institution deliberately withheld from a round, compared against full-participation performance, to quantify degradation.

## 18. Baseline and Experimental Design

Experiments comparing local-only, federated, and pooled-upper-bound training (Section 7, AI-15) shall be run under each of the following conditions, with results reported per condition:

- **Normal demand:** baseline seasonal pattern, no injected events.
- **Injected regional demand surge:** a configured surge (Section 8.10) applied to one or more institutions.
- **Missing institution:** one institution withheld from a training round and/or from forecast input.
- **Non-identical institution populations:** evaluation stratified by each institution's distinct population profile to confirm the model generalizes across non-IID conditions rather than overfitting to the largest institution.
- **Missing data:** a configured fraction of records dropped or delayed at ingestion to test imputation and coverage-flagging behavior.
- **Distribution shift:** a gradual (non-surge) drift injected to test the shift detector's sensitivity to slow change, not only sudden spikes.
- **Small-group query:** a query deliberately constructed to isolate a group below the minimum threshold, to verify suppression (UC-008).
- **Privacy attack/leakage attempt:** a simulated membership-inference or re-identification attempt against the trained model and dashboard exports (Section 17).

Each experiment shall be reproducible from a fixed seed and versioned configuration (NFR-REPRO-01), with results contributing to the model/data cards and the final evaluation report.

## 19. Failure and Recovery Requirements

The system shall fail safely and never silently produce misleading results:

- **Institution disconnects:** excluded from the current round (FR-027); re-invited to the next round (FR-028); dashboard shows reduced-participation status (FR-029).
- **Training round fails:** round marked incomplete; no new global model published; prior model version remains active; event logged (FR-023, FR-043).
- **Model update invalid:** rejected without incorporation into aggregation; event logged (FR-025).
- **Data quality is poor:** affected records/day excluded per policy; data_completeness_pct feature reflects the gap; forecast confidence is reduced accordingly (FR-011, FR-038).
- **Forecast has high uncertainty:** dashboard visibly flags reduced confidence rather than presenting the point estimate alone (FR-037–FR-038).
- **Distribution shift detected:** routed through alert generation and mandatory human review before being treated as actionable (FR-047, FR-050).
- **Small-group query attempted:** suppressed/coarsened at query time; repeated circumvention attempts logged as a privacy event (FR-041–FR-042).
- **Dashboard/API unavailable:** clients receive an explicit unavailability status rather than a stale or blank view presented as current; last-known-good timestamp is shown.

## 20. Security Threat Model

| Threat | Impact | Mitigation | Detection |
|---|---|---|---|
| Unauthorized institution joins federation | Poisoned or fabricated updates degrade the global model | Credentialed registration (FR-001–FR-002); authenticated TLS channels | Failed authentication attempts logged (FR-044) |
| Malicious model update (poisoning) | Skews global model toward attacker's goal | Update integrity/format validation and clipping (FR-025, privacy filter) | Update-validation failure logs; anomalous update-magnitude alerts |
| Data leakage via model update | Reconstruction of institution-level patterns beyond intended aggregate | Clipping, minimum-group suppression, optional noise addition before transmission | Privacy leakage testing (Section 17) |
| Membership inference / privacy leakage | Attacker infers whether specific aggregate/individual pattern was in training data | Bounded privacy budget, aggregation, held-out leakage testing | Scheduled leakage-test suite (Section 22) |
| Unauthorized dashboard access | Exposure of suppression-protected views to unentitled users | Role-scoped access tokens (NFR-SEC-02) | Access logs reviewed by Auditor |
| Small-group inference (filter narrowing) | Re-identification risk via successive narrow queries | Per-query suppression enforcement, not just per-view (FR-041–FR-042) | Circumvention-pattern logging |
| Compromised client (institution node) | Attacker submits fabricated updates from a valid credential | Update integrity checks; per-round anomaly bounds on submitted values | Statistical outlier detection on submitted updates |
| Replay / duplicate training update | Attacker resubmits a captured earlier update to bias aggregation | Round-scoped nonce/ID checks reject duplicate submissions (FR-025) | Replay detection logged as validation failure |
| Tampered audit records | Loss of trustworthy evidence for judging/compliance | Append-only, hash-chained audit log (NFR-AUDIT-02) | Hash-chain verification job flags any break |

## 21. Requirements Traceability Matrix

This matrix maps every mandatory requirement of the official S5 problem statement (mandatory core build, safety/ethics boundary, required evaluation, mandatory deliverables, and mandatory live-demonstration sequence) to the SRS requirement IDs that implement it, the responsible system module, and the verification method.

### 21.1 Mandatory Core Build

| Official S5 Requirement | SRS Requirement ID(s) | System Module | Verification / Test | Evaluation Metric / Demonstration |
|---|---|---|---|---|
| Simulate at least four institutions with non-identical populations | FR-001–FR-004; Sections 2.2, 4.2 | Institution Layer | Population profile divergence check across institution configs | Demo Step 1 |
| Keep row-level records at the local node | FR-016–FR-017, PRIV-01, NFR-PRIV-01 | Privacy Filter | Automated pre-transmission check; privacy test suite | Demo Step 1; Acceptance criterion "100% row-level non-transmission" |
| Train a federated model and compare with local-only and pooled upper-bound baselines | FR-018–FR-026, AI-06, AI-15 | Coordinator, Forecasting Engine | Held-out evaluation across all three models (Section 18) | Evaluation report; Federated-vs-local uplift metric |
| Forecast service volume or syndrome-category demand for 7–14 days | FR-030–FR-033, AI-01–AI-04 | Forecasting Engine | Held-out forecast accuracy evaluation | Demo Step 2; Forecast MAE/MAPE |
| Detect distribution shift and report uncertainty | FR-034–FR-038, AI-09–AI-11 | Shift Detector, Uncertainty Estimator | Injected-surge and gradual-drift detection tests; interval calibration check | Demo Steps 3–4; Event detection recall/lead time; interval coverage |
| Prevent small-group disclosure in every dashboard/export | FR-039–FR-042, PRIV-05 | Dashboard, Privacy Filter | Privacy test suite (adversarial query narrowing) | Demo Steps 7–8; Suppression compliance = 100% |
| Log model rounds, participants, failures, and reviewer decisions | FR-043–FR-052 | Audit Service | Log-completeness test (expected vs. logged event counts) | Auditor query; NFR-AUDIT-01 |

### 21.2 Safety, Ethics, and Operational Boundary

| Official S5 Requirement | SRS Requirement ID(s) | System Module | Verification / Test |
|---|---|---|---|
| No diagnosis | PRIV-02 | System-wide (architectural) | Design review + code audit against Section 26 (Out of Scope) |
| No individual risk score | PRIV-03 | System-wide (architectural) | Design review + code audit against Section 26 |
| No re-identification | PRIV-04 | System-wide (architectural) | Privacy leakage testing (Section 17); design review |
| Operational alerts require public-health review | FR-045–FR-050, PRIV-12 | Reviewer Workflow | UC-007 test; acceptance criterion "no alert active without reviewer decision" |
| Must state data coverage limitations | FR-029, FR-038, PRIV-11 | Forecasting Engine, Dashboard | Missing-node/coverage-flag display check (Demo Steps 5–6) |

### 21.3 Required Evaluation

| Official S5 Evaluation Item | SRS Requirement ID(s) | Evaluation Section |
|---|---|---|
| Forecast MAE/MAPE | AI-13, AI-14 | Section 17 |
| Event detection recall and lead time | AI-09 | Section 17 |
| Federated vs. local uplift | AI-15 | Section 17, Section 18 |
| Privacy leakage tests | PRIV-06, NFR-PRIV-03 | Section 17, Section 22 |
| Performance across institutions and missing-node resilience | AI-08, AI-13 | Section 17, Section 18 |

### 21.4 Mandatory Deliverables

| Official S5 Deliverable | Corresponding SRS Section / Artifact |
|---|---|
| Federated simulation | Sections 4, 10, 24 (Deployment) — containerized institution nodes and coordinator |
| Review dashboard | Section 16 (Dashboard Requirements) |
| Privacy assessment | Section 9 (Privacy and Responsible AI Requirements), Section 17 (privacy leakage tests) |
| Forecast benchmark | Section 17 (Evaluation Plan), Section 18 (Baseline and Experimental Design) |
| Model/data cards | NFR-REPRO-02, PRIV-11 |

### 21.5 Mandatory Live-Demonstration Sequence

| Official S5 Demo Step | SRS Section 23 Step |
|---|---|
| Train across four simulated institutions without moving raw rows | Step 1 |
| Show a normal forecast | Step 2 |
| Inject a regional demand surge | Step 3 |
| Demonstrate detection of the resulting change | Step 4 |
| Drop one institution during a federated training round | Step 5 |
| Demonstrate safe recovery | Step 6 |
| Attempt a small-group query | Step 7 |
| Demonstrate privacy suppression | Step 8 |
| Qualification test (judge-altered input/constraint/state) | Section 23, Qualification Test Readiness; Section 28 acceptance criterion |

## 22. Testing Strategy

- **Unit testing:** individual functions for validation, imputation, feature computation, suppression logic, and aggregation math.
- **Integration testing:** end-to-end institution → coordinator → forecast → dashboard flow across simulated rounds.
- **ML testing:** held-out evaluation of forecast accuracy, calibration, and shift-detection recall/lead time (Section 17).
- **Privacy testing:** automated suite verifying (a) no row-level payload ever crosses the institution boundary, (b) 100% suppression compliance under adversarial query narrowing (UC-008), (c) membership-inference leakage below threshold.
- **Security testing:** authentication bypass attempts, replay-attack submission, malformed/poisoned update submission, unauthorized dashboard access attempts — each checked against the threat model (Section 20).
- **Performance testing:** round-aggregation time, forecast-refresh time, and dashboard load time against NFR targets (Section 6.3).
- **Failure/recovery testing:** each scenario in Section 19 exercised explicitly, confirming safe, visible failure states rather than silent incorrect output.
- **User acceptance testing:** task-based review with a non-technical reviewer persona to confirm NFR-USE-01/02.
- **Unseen/held-out scenario testing:** the qualification-test class of scenario — an input, constraint, or state not used in the rehearsed demo — is exercised prior to submission using scenarios are deliberately withheld from rehearsal, to validate genuine (not memorized) recomputation.

## 23. Live Demonstration Plan

The official S5 demonstration sequence is reproduced below as eight steps, each specified with its initial state, trigger, expected system behavior, expected output, evidence/log generated, and pass/fail criterion.

### Step 1 — Train across four simulated institutions without moving raw rows
- **Initial state:** four institution nodes and the coordinator are running; each institution has locally ingested and processed its daily synthetic data.
- **Trigger:** a training round is initiated (scheduled or manually triggered by the Federated System Administrator).
- **Expected system behavior:** the coordinator broadcasts the current global model; each institution trains locally and returns a privacy-filtered update; the coordinator aggregates valid updates into a new global model version.
- **Expected output:** a new global model version appears on the dashboard with round-completion status showing all four institutions as participants.
- **Evidence/log generated:** training-round log entry (FR-043); pre-transmission check log confirming every outbound payload passed the row-level check (FR-017).
- **Pass/fail criterion:** the round completes with a new model version, and the pre-transmission check log shows zero row-level-shaped payloads across all four institutions.

### Step 2 — Show a normal forecast
- **Initial state:** a current global model version exists from Step 1.
- **Trigger:** the forecasting engine is run (or the dashboard's forecast view is opened).
- **Expected system behavior:** the forecasting engine produces a 7–14 day aggregate daily syndrome-category service-demand forecast per institution and regionally, with uncertainty intervals.
- **Expected output:** a forecast curve with an uncertainty band displayed on the dashboard for the current syndrome category and horizon.
- **Evidence/log generated:** a versioned, timestamped forecast record (Section 14, Forecasts entity).
- **Pass/fail criterion:** a forecast is displayed for the full requested horizon with a non-degenerate uncertainty interval at every horizon day.

### Step 3 — Inject a regional demand surge
- **Initial state:** the normal forecast from Step 2 is displayed.
- **Trigger:** the synthetic data generator injects a configured demand surge (magnitude, duration, syndrome category, onset date) into one or more institutions' incoming data.
- **Expected system behavior:** the next data ingestion and forecast refresh incorporate the surged data.
- **Expected output:** the forecast curve and/or recent actuals visibly diverge from the pre-surge baseline.
- **Evidence/log generated:** updated aggregate feature records reflecting the surge; refreshed forecast record.
- **Pass/fail criterion:** the injected surge is reflected in the institution's (and, where applicable, the region's) subsequent aggregate data and forecast within one data-refresh cycle.

### Step 4 — Demonstrate detection of the resulting change
- **Initial state:** surged data from Step 3 has been ingested and processed.
- **Trigger:** the distribution-shift detector runs on the new data (automatically, on schedule, or on demand).
- **Expected system behavior:** the shift score for the affected institution/region exceeds the configured threshold; an alert is generated (FR-047) with an evidence window and confidence score, and placed in the reviewer queue.
- **Expected output:** a new alert appears on the dashboard's shift-alerts view with supporting evidence.
- **Evidence/log generated:** shift-detection record (Section 14, ShiftDetections entity); alert record (Section 14, Alerts entity).
- **Pass/fail criterion:** the injected surge produces a shift alert with a confidence score and an evidence window referencing the actual surged data points.

### Step 5 — Drop one institution during a federated training round
- **Initial state:** a new training round is initiated with all four institutions invited.
- **Trigger:** one institution node is manually disconnected before submitting its update.
- **Expected system behavior:** the coordinator logs the disconnection (FR-027) and, if the remaining participants still meet the minimum-participant threshold, completes aggregation with the remaining institutions.
- **Expected output:** the dashboard's missing-node indicator (FR-029) shows the round as completed with reduced participation.
- **Evidence/log generated:** disconnection event log (FR-044); round metadata showing the excluded institution and reason (FR-043).
- **Pass/fail criterion:** the round either completes with the remaining valid institutions and a visible missing-node indicator, or is correctly marked incomplete if the minimum-participant threshold is not met — in either case, without the pipeline halting or crashing.

### Step 6 — Demonstrate safe recovery
- **Initial state:** the disconnected institution from Step 5 remains offline after the round.
- **Trigger:** the institution's connectivity is restored.
- **Expected system behavior:** the institution is automatically re-invited to the next scheduled round (FR-028) without requiring reconfiguration; the dashboard status updates from disconnected to connected.
- **Expected output:** the institution appears as a full participant in the next round's completion status.
- **Evidence/log generated:** reconnection event log; next round's participant record showing the institution included.
- **Pass/fail criterion:** the previously dropped institution participates successfully in the following round without manual pipeline restart.

### Step 7 — Attempt a small-group query
- **Initial state:** the dashboard or a direct API call is available to a demonstration user.
- **Trigger:** a query is submitted narrowed to a group below the configured minimum group size (e.g., a single small institution, a single day, and a single rare syndrome category).
- **Expected system behavior:** the query is evaluated against the underlying group size at query time (FR-041) before any value is returned.
- **Expected output:** a suppression placeholder (e.g., "< minimum group size") is returned instead of the true count.
- **Evidence/log generated:** privacy event log entry recording the suppressed query (FR-042, PRIV-10).
- **Pass/fail criterion:** no numeric value derived from fewer than the minimum group size is ever returned; the suppression event is present in the audit log.

### Step 8 — Demonstrate privacy suppression under a modified query
- **Initial state:** the suppressed result from Step 7 has been shown.
- **Trigger:** the query is narrowed further or reformulated in an attempt to isolate the same small group by a different filter path.
- **Expected system behavior:** suppression is reapplied independently at each new query, per FR-042, rather than being bypassable by filter reformulation.
- **Expected output:** the suppression placeholder is returned again; repeated narrowing attempts are flagged as a privacy event.
- **Evidence/log generated:** additional privacy event log entries; if a configured circumvention-pattern threshold is reached, a rate-limit or flag event.
- **Pass/fail criterion:** suppression holds under at least one reformulated query, and the attempt pattern is logged.

### Qualification Test Readiness

Per the Common Judging Contract, judges may alter one input, constraint, participant state, or tool/system state not explicitly used in the prepared demonstration — for example: a different surge magnitude, a different institution population distribution, a different institution dropped in Step 5, a different forecast horizon within the supported 7–14 day range, a different (e.g., gradual rather than sudden) distribution shift, or a different small-group query filter combination. The system shall respond using its actual detection, forecasting, and suppression logic rather than any value hard-coded for the rehearsed demonstration, recomputing forecasts, uncertainty, and shift scores live and continuing to require human review before any alert is treated as actionable. This is a testable acceptance requirement (Section 28).

## 24. Deployment Requirements

- **Local institution nodes:** four or more containerized services, each with its own isolated local data volume; deployable on separate hosts or as separate containers on one demonstration machine.
- **Federated coordinator:** a containerized service with its own network-addressable endpoint, reachable by all institution nodes.
- **Model registry:** a versioned artifact store (can be a simple directory/database-backed store for the prototype) holding every published global model version.
- **Database:** a single PostgreSQL instance (or managed equivalent) hosting the schema in Section 14.
- **Dashboard:** a containerized frontend/backend pair, reachable over HTTPS by all user roles, with role-based views.
- **Authentication:** a token-issuing service (or lightweight equivalent for the prototype) providing role-scoped tokens to institutions and dashboard users.
- **Monitoring:** basic health-check endpoints on every service, aggregated into the dashboard's system status view (FR-057–FR-058).
- **Logging:** centralized structured log collection feeding the audit service and general operational logs.

## 25. Technology Stack

| Layer | Recommendation | Rationale |
|---|---|---|
| Frontend | React (or Next.js) | Broadly available charting/dashboard ecosystem; fast to build role-scoped views. |
| Backend / APIs | Python + FastAPI | Fast to develop, strong typing via Pydantic maps cleanly onto the schema/API tables in this SRS, and shares a language with the ML stack, easing integration between coordinator, forecasting service, and dashboard backend. |
| ML / Forecasting | scikit-learn and/or PyTorch | scikit-learn is sufficient and simpler for classical time-series/quantile regression baselines; PyTorch is recommended if a sequence model (e.g., LSTM/temporal convolution) is implemented for the forecasting engine — starting with the simpler scikit-learn baseline and adopting PyTorch only if the added complexity is justified by accuracy gains over the local-only baseline is a proposed engineering approach, not an official requirement. |
| Federated Learning | Flower (flwr) | Purpose-built federated learning framework with a straightforward client/server abstraction that maps directly onto the Institution Node / Federated Coordinator split in this SRS, and integrates with both scikit-learn and PyTorch models. |
| Database | PostgreSQL | Mature relational engine, strong support for the normalized schema in Section 14, and widely available as a managed or local Docker service. |
| Visualization | Recharts (frontend) and/or Plotly (analysis/reporting) | Recharts integrates naturally with a React dashboard for live views; Plotly is well-suited for the offline evaluation-report generation in Section 17–18. |
| Containerization | Docker (with Docker Compose for local multi-institution simulation) | Enables running four-plus institution nodes, the coordinator, database, and dashboard as isolated, reproducible services on a single demonstration machine — directly satisfying NFR-REPRO-01. |
| Cloud deployment (optional) | A single small VM or low-cost cloud account, if a persistently reachable demo is desired | Not required for a laptop/Docker Compose demonstration; recommended only if judges require remote access ahead of the live session. |

These are recommendations, not mandates; an equally suitable framework (e.g., a different FL library) may be substituted provided it fulfills the same architectural role, and any substitution should be documented in the reproducibility artifacts (Section 6.9).


## 26. Project Scope

**IN SCOPE**
- Federated training and coordination across four or more simulated institutions
- Local aggregate feature generation and privacy filtering
- 7–14 day aggregate daily syndrome-category service-demand forecasting with uncertainty
- Distribution-shift / demand-surge detection with confidence scoring
- Minimum-group-size suppression across all dashboard views and exports
- Human public-health reviewer workflow and approval gating
- Immutable audit logging of rounds, participants, privacy events, and reviewer decisions
- Local-only, federated, and pooled-upper-bound baseline comparison
- Failure/recovery handling for disconnected institutions, invalid updates, and poor data quality
- Synthetic data generation, including injected seasonality and surge events

**OUT OF SCOPE**
- Individual diagnosis of any kind
- Individual-level risk scoring or patient-level prediction
- Storage, transmission, or processing of identifiable health records
- Re-identification of any individual, directly or via inference
- Automatic external communication of alerts without human review
- Integration with real hospital record systems or real patient data
- Any clinical decision-support or treatment-recommendation function
- Enforcement action or automatic resource dispatch (the system informs; it does not act)

## 27. Future Enhancements

The following are realistic extensions for a future iteration and are explicitly not required for the first prototype: differential-privacy noise calibration with a formally tracked epsilon budget across rounds; secure multi-party aggregation (e.g., secure aggregation protocols) to further reduce coordinator trust requirements; per-institution personalized model heads for improved non-IID performance; integration with a real (properly governed, IRB-approved) syndromic surveillance data feed; automated reviewer-decision-quality monitoring (inter-reviewer agreement); expansion beyond four institutions to a larger regional simulation; and a mobile-friendly reviewer interface for field public-health staff.

## 28. Acceptance Criteria

- **100% of federation training rounds must pass the row-level data non-transmission test** (FR-017): every outbound payload from every institution, across every training round, passes the automated pre-transmission check with zero row-level-shaped payloads detected.
- The system trains a federated model across at least four simulated institutions with non-identical populations, satisfying the official S5 mandatory core-build requirement.
- The federated model demonstrates measurable uplift over the local-only model, and the pooled-data upper-bound model's accuracy is reported for comparison only, never as a deployment candidate (AI-15).
- Forecasts of aggregate daily syndrome-category service demand are produced for a 7–14 day horizon with calibrated uncertainty intervals whose empirical coverage matches nominal confidence within a documented tolerance (proposed engineering target; see Section 17).
- Injected demand surges are detected by the distribution-shift detector, with recall and lead time reported on held-out/unseen scenarios (Section 17).
- Every dashboard view and export enforces minimum-group-size suppression with zero violations across the privacy test suite (official S5 requirement).
- The system recovers from a mid-round institution disconnection without halting the training pipeline, completing the round with remaining participants when the minimum-participant threshold is met (Section 23, Steps 5–6).
- No alert becomes "active" or actionable on the dashboard without a recorded human public-health reviewer decision.
- 100% of training rounds, participant events, privacy events, and reviewer decisions appear in the audit log, verified by a log-completeness check.
- **Qualification-test acceptance requirement:** when an input, constraint, participant state, or system state not used in the rehearsed demonstration is altered by an evaluator, the system correctly recomputes forecasts, shift scores, and uncertainty from its actual logic (not a hard-coded demo value), and continues to require human review before any alert is treated as actionable (Section 23, Qualification Test Readiness).
- No individual diagnosis, individual risk score, or re-identification capability exists anywhere in the delivered system, verified by architecture review and code audit against Section 26 (Out of Scope).

## 29. Conclusion

HealthSignal satisfies the official S5 problem statement by implementing a federated analytics platform in which four or more institutions retain their row-level data locally and share only privacy-filtered aggregates and model updates through a coordinator that trains a shared forecasting model. The system forecasts 7–14 day service-category demand with calibrated uncertainty, detects distribution shifts including injected surges, enforces minimum-group-size suppression on every output, and requires human public-health review before any alert is treated as actionable. Federated performance is evaluated against both a local-only lower bound and a pooled-data upper bound to demonstrate that federation delivers meaningful uplift without centralizing identifiable records. Comprehensive functional, non-functional, AI/ML, privacy, architectural, testing, and demonstration requirements in this document give a direct path from specification to a working, defensible prototype — one that forecasts community health-service pressure while remaining, by architecture and not merely by policy, incapable of individual diagnosis, individual risk scoring, or re-identification.

---

## Appendix A — One-Page Executive Summary

See Executive Summary at the beginning of this document (Section preceding 1. Introduction).

## Appendix B — Complete List of Functional Requirements

FR-001 through FR-058, grouped by subsystem (Institution Registration, Data Ingestion, Validation, Preprocessing, Feature Generation, Privacy Boundary Enforcement, Federated Training, Participant Management, Model Aggregation, Missing-Node Handling, Forecast Generation, Shift Detection, Uncertainty Reporting, Dashboard/Export Suppression, Round/Participant Logging, Reviewer Workflow, Alerting, Audit Trail, Error Handling, Federation Recovery, System Monitoring) — see Section 5 for full text of each requirement.

## Appendix C — Complete List of Non-Functional Requirements

NFR-SEC-01–03, NFR-PRIV-01–03, NFR-PERF-01–03, NFR-AVAIL-01–02, NFR-REL-01–02, NFR-SCALE-01–02, NFR-USE-01–02, NFR-MAINT-01–02, NFR-REPRO-01–02, NFR-EXP-01–02, NFR-AUDIT-01–02 — see Section 6 for full text of each requirement.

## Appendix D — Complete List of AI/ML Requirements

AI-01 through AI-15, including the mandatory three-way baseline comparison (local-only, federated, pooled upper bound) — see Section 7 for full text of each requirement.

## Appendix E — Complete List of Security / Privacy Requirements

NFR-SEC-01–03 (Section 6.1), NFR-PRIV-01–03 (Section 6.2), PRIV-01 through PRIV-12 (Section 9), and the full Security Threat Model (Section 20).

## Appendix F — Requirement Traceability Matrix

See Section 21 for the complete matrix mapping every mandatory S5 requirement (core build, safety/ethics boundary, required evaluation, mandatory deliverables, and mandatory live-demonstration sequence) to its SRS requirement ID(s), system module, and verification/test. Section 21 is the authoritative traceability matrix for this document; a supplementary spreadsheet mapping each of the 58 individual functional requirements to test cases may be maintained separately for implementation-level change tracking, without altering the mandatory-requirement mapping already contained in Section 21.

## Appendix G — Recommended Technology Stack

See Section 25: React/Next.js frontend, Python + FastAPI backend, scikit-learn/PyTorch for forecasting, Flower for federated learning, PostgreSQL for storage, Recharts/Plotly for visualization, Docker/Docker Compose for containerized multi-institution simulation.

## Appendix H — Recommended Development Phases

| Phase | Focus | Key Deliverables |
|---|---|---|
| Phase 1 | Foundations | Synthetic data generator; institution node skeleton; schema validation; database schema (Section 14) |
| Phase 2 | Privacy layer & local processing | Aggregate feature generation; minimum-group-size suppression; pre-transmission checks (FR-016–FR-017) |
| Phase 3 | Federation core | Coordinator; registration; training-round orchestration; federated averaging; model versioning |
| Phase 4 | Intelligence layer | Forecasting engine; distribution-shift detector; uncertainty estimation; baseline comparisons (local-only, pooled) |
| Phase 5 | Governance & dashboard | Alerting; reviewer workflow; audit logging; full dashboard (Section 16) |
| Phase 6 | Failure handling & hardening | Disconnect/recovery scenarios; security threat mitigations; privacy leakage testing |
| Phase 7 | Evaluation & demonstration prep | Held-out evaluation report; experiment matrix (Section 18); rehearsal of all four demo scenarios plus qualification-test readiness |

## Appendix I — Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Federated model shows little or no uplift over local-only baseline on non-IID synthetic data | Tune synthetic data generator for realistic but learnable cross-institution correlation; consider lightweight per-institution personalization (Section 27) if uplift remains marginal |
| Privacy filter accidentally allows a row-level-shaped payload through | Automated pre-transmission check (FR-017) as a hard gate, plus dedicated privacy test suite (Section 22) run in CI before every deployment |
| Non-IID synthetic data is not heterogeneous enough to produce a meaningful federated-vs-local uplift, undermining the core evaluation claim | Explicitly configure divergent per-institution base rates, syndrome mixes, and seasonality strength in the data generator; validate uplift on held-out data before finalizing evaluation results |
| Distribution-shift detector produces excessive false alerts, causing reviewer fatigue | Calibrate threshold against the held-out evaluation set; report false-alert rate explicitly as part of Section 17 metrics and validate before the demonstration, not on the judge scenario itself |
| Judges' qualification-test alteration exposes a hard-coded assumption (e.g., a fixed institution ID or fixed syndrome category) | Explicitly validate the system against at least one held-back, unrehearsed variation of each demo scenario before submission (Section 22, "Unseen/held-out scenario testing") |
| Live demonstration network/hardware failure during judging | Provide a one-command containerized startup, a pre-recorded fallback walkthrough as backup evidence only (not a substitute for the live run), and validate recovery from a genuinely dropped institution node (Scenario 5) before the demonstration |


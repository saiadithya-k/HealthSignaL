---
subtitle: Final revision/change log
title: HealthSignal --- Changes from Previous Solution
version: 28 August 2026
---

# 1. Purpose

This document records the substantive changes made while validating the
original solution against the S5 problem statement and tightening the
project for feasibility, judging, privacy, and implementation.

It is intentionally **not** a copy of the full master solution.

------------------------------------------------------------------------

# 2. Decision

**Final decision: PROCEED with HealthSignal.**

The solution remains strongly aligned with S5. The revisions mainly
remove overclaims, sharpen the privacy boundary, reduce unnecessary
complexity, and make the mandatory demonstrations and qualification test
executable.

------------------------------------------------------------------------

# 3. Change Summary

  ----------------------------------------------------------------------------------
  Area                    Previous direction      Final change
  ----------------------- ----------------------- ----------------------------------
  Overall scope           Broad federated health  Explicit aggregate public-health
                          platform                forecasting/decision-support scope

  Privacy claim           Federated learning +    Explicit statement that FL alone
                          privacy mechanisms      does not guarantee privacy

  Raw data                Local records           Hard architectural rule: raw rows
                                                  never cross institution boundary

  Privacy mechanism       Broad "privacy layer"   Aggregate features + minimum-group
                                                  suppression + clipping + outbound
                                                  payload validation

  Differential privacy    Could be interpreted as Formal DP moved to future
                          present                 enhancement unless actually
                                                  implemented and measured

  Secure aggregation      Could be interpreted as Secure aggregation moved to future
                          required                enhancement unless actually
                                                  implemented

  Forecast target         Health trends           More precise: aggregate
                                                  syndrome-category/service-demand
                                                  volume

  Forecast horizon        7--14 days              Configurable 7--14 days, default 7
                                                  days

  Forecast uncertainty    Required concept        Made explicit as a mandatory
                                                  output with calibration evaluation

  Anomaly detection       General anomaly         Prefer interpretable
                          detector                residual-based CUSUM/shift scoring

  Model complexity        Could drift toward deep Start with classical
                          learning                forecasting/regression; use deep
                                                  learning only if justified

  Evaluation              Forecast performance    Three-way local vs federated vs
                                                  pooled upper-bound comparison

  Pooled data             Potentially confusing   Explicitly offline benchmark only;
                                                  never deployment mode

  Non-IID data            Required                Explicit institution profiles with
                                                  different base rates/seasonality

  Missing node            Failure scenario        Formal recovery logic with no
                                                  fabricated update

  Small groups            Dashboard suppression   Suppression moved to query/backend
                                                  layer, including exports

  Human review            Alerting                Explicit rule: no actionable alert
                                                  without reviewer decision

  Audit                   General logging         Round, participant, privacy,
                                                  failure and reviewer events
                                                  explicitly required

  Qualification test      Demo preparation        Added data-driven, non-hard-coded
                                                  requirement for judge-altered
                                                  inputs

  Novelty                 Could imply algorithmic Reframed novelty as
                          novelty                 system/workflow integration

  Implementation          Large architecture      Added MVP-first build order

  Safety                  General boundary        Explicitly excludes diagnosis,
                                                  individual risk, re-identification
                                                  and clinical action

  Demonstration           Four scenarios          Each scenario now has explicit
                                                  expected system behavior

  Feasibility             Broad feature set       Clear "do not build first" list to
                                                  prevent overengineering
  ----------------------------------------------------------------------------------

------------------------------------------------------------------------

# 4. Privacy Changes

## 4.1 Most important correction

The final solution no longer implies:

> "Federated learning = private."

Instead:

> Federated learning reduces the need to centralize raw data, but model
> updates and aggregates can still create leakage risks. HealthSignal
> therefore enforces a layered privacy boundary and tests it.

## 4.2 Final privacy layers

``` text
Raw-row isolation
        ↓
Local aggregation
        ↓
Minimum-group-size suppression
        ↓
Contribution clipping
        ↓
Outbound payload validation
        ↓
Privacy event logging
```

## 4.3 Formal DP clarification

Differential privacy with an explicit epsilon budget is now treated as a
**future enhancement unless actually implemented, calibrated and
evaluated**.

This prevents an unsupported formal privacy claim.

## 4.4 Secure aggregation clarification

Secure multi-party aggregation is also treated as a future enhancement
unless the team implements and tests it.

------------------------------------------------------------------------

# 5. Forecasting Changes

The forecast target was made more precise.

## Previous broad idea

Health trends / health pressure.

## Final target

**Aggregate daily syndrome-category/service-demand volume for the next
7--14 days.**

This avoids accidentally turning the project into an individual
disease-prediction system.

The forecast is:

-   aggregate;
-   daily;
-   7--14 days;
-   institution and regional level;
-   uncertainty-aware.

------------------------------------------------------------------------

# 6. AI Model Changes

## Final model strategy

Start simple.

``` text
Classical regression / lag-based forecasting
             ↓
Evaluate
             ↓
Only add LSTM/TCN/PyTorch if it provides measurable value
```

The change is deliberate.

The project is judged on:

-   federated learning;
-   privacy;
-   forecasting;
-   detection;
-   uncertainty;
-   resilience;
-   governance.

A complicated neural network is not automatically better.

------------------------------------------------------------------------

# 7. Anomaly Detection Change

The anomaly component was narrowed to an interpretable statistical
design.

## Final direction

Use residual-based shift detection such as **CUSUM**.

``` text
Observed
   -
Expected
   =
Residual
   ↓
CUSUM
   ↓
Shift score
   ↓
Normal / Watch / Alert candidate
```

This is easier to:

-   explain;
-   calibrate;
-   test;
-   defend before judges.

------------------------------------------------------------------------

# 8. Evaluation Changes

The final evaluation explicitly contains three models:

``` text
LOCAL-ONLY
     vs
FEDERATED
     vs
POOLED UPPER BOUND
```

The pooled model is **offline only**.

The main scientific/engineering question becomes:

> Does federated collaboration improve forecasting compared with each
> institution working independently while avoiding raw-data
> centralization?

This is stronger than reporting only one model's MAE.

------------------------------------------------------------------------

# 9. Uncertainty Changes

Uncertainty is now treated as a first-class system output.

Every forecast must contain an interval.

The evaluation must measure empirical coverage.

Example:

``` text
80% interval → measured coverage should be approximately 80%
95% interval → measured coverage should be approximately 95%
```

The system must also communicate reduced confidence when:

-   a node is missing;
-   coverage is incomplete;
-   history is short.

------------------------------------------------------------------------

# 10. Non-IID Data Changes

The four institutions must not be identical copies.

The final design explicitly uses different:

-   base rates;
-   syndrome mixes;
-   seasonality;
-   population profiles;
-   surge sensitivity.

This makes the federated-vs-local comparison meaningful.

------------------------------------------------------------------------

# 11. Missing-Node Changes

The missing-node scenario was strengthened.

The system must **never fabricate** an update for a missing institution.

Final behavior:

``` text
Node disconnects
      ↓
Timeout
      ↓
Mark missing
      ↓
Check minimum participants
      ↓
Continue with valid nodes
      OR
Mark round incomplete
```

The system also reports coverage limitations and uncertainty changes.

------------------------------------------------------------------------

# 12. Small-Group Privacy Changes

Suppression is no longer treated as merely a frontend display feature.

Final rule:

> The privacy check must happen at query time/backend level.

Therefore:

``` text
User query
    ↓
Privacy validation
    ↓
Safe result
```

rather than:

``` text
Database returns sensitive result
    ↓
Frontend hides it
```

Exports must obey the same rule.

Attempts to narrow queries to bypass suppression are rejected/coarsened
and logged.

------------------------------------------------------------------------

# 13. Human Review Changes

The final system explicitly separates:

``` text
Detection
    ≠
Decision
```

The model creates an **alert candidate**.

A human public-health reviewer decides:

-   approve;
-   reject;
-   request more evidence.

No actionable alert can bypass that decision.

------------------------------------------------------------------------

# 14. Auditability Changes

The final audit scope is explicit.

Every round must record:

-   round ID;
-   participating nodes;
-   excluded/missing nodes;
-   failure reason;
-   model version;
-   aggregation method.

Also record:

-   privacy events;
-   rejected updates;
-   reviewer decisions;
-   exports;
-   major system failures.

------------------------------------------------------------------------

# 15. Qualification-Test Changes

The qualification test is now treated as a core engineering requirement.

The system must survive changes such as:

-   different institution;
-   different category;
-   different surge size;
-   different surge timing;
-   different missing node;
-   different horizon;
-   different query;
-   changed participant state.

The final solution explicitly prohibits hard-coded demo outputs.

------------------------------------------------------------------------

# 16. Novelty Reframing

The novelty claim was made more defensible.

## Removed implication

"Novel federated-learning algorithm."

## Final claim

The novelty is the **integrated system workflow**:

``` text
Privacy-preserving federation
        +
Aggregate forecasting
        +
Calibrated uncertainty
        +
Distribution-shift detection
        +
Missing-node resilience
        +
Small-group suppression
        +
Human review
        +
Auditability
```

This is a stronger and more honest competition claim.

------------------------------------------------------------------------

# 17. Scope Changes

The final solution explicitly excludes:

-   individual diagnosis;
-   individual risk scoring;
-   patient-level prediction;
-   re-identification;
-   clinical treatment recommendations;
-   automatic resource dispatch;
-   automatic external alerting;
-   real hospital integration for the prototype.

This reduces technical and ethical risk.

------------------------------------------------------------------------

# 18. MVP Changes

The final build order was simplified.

## Build first

``` text
4 nodes
 ↓
Synthetic non-IID data
 ↓
Local aggregation
 ↓
Simple forecasting model
 ↓
FedAvg
 ↓
7-day forecast
 ↓
Uncertainty
 ↓
CUSUM
 ↓
Privacy suppression
 ↓
Dashboard
```

## Add later

-   advanced deep learning;
-   formal differential privacy;
-   secure aggregation;
-   personalization;
-   larger regional simulation;
-   real governed data feeds.

------------------------------------------------------------------------

# 19. Technology Strategy Changes

The final stack remains deliberately practical:

-   React/Next.js;
-   Python/FastAPI;
-   Flower;
-   scikit-learn first;
-   PostgreSQL;
-   Docker Compose;
-   pytest.

The change is not necessarily a technology replacement; it is a
**priority change toward implementation simplicity and
reproducibility**.

------------------------------------------------------------------------

# 20. Demonstration Changes

The official four scenarios are now treated as first-class acceptance
tests.

### Scenario 1

Federated training with four institutions and proof that raw rows do not
leave.

### Scenario 2

Injected demand surge followed by computed shift detection, forecast
update and uncertainty.

### Scenario 3

Real institution disconnect and safe recovery.

### Scenario 4

Small-group query followed by backend suppression and privacy logging.

Each scenario must be executed by actual system logic.

------------------------------------------------------------------------

# 21. Final Impact of the Changes

The revised solution is:

-   **less over-engineered;**
-   **more technically honest;**
-   **more privacy-defensible;**
-   **easier to implement;**
-   **easier to demonstrate;**
-   **better aligned with the qualification test;**
-   **clearer about novelty;**
-   **safer in public-health terms.**

The project direction has therefore changed from:

> "Build a very broad federated health-AI platform"

to:

> **"Build a focused, auditable, privacy-first federated forecasting
> system that can survive the exact S5 requirements and judge
> interventions."**

------------------------------------------------------------------------

# 22. Final Change Decision

No major architectural change is required after these revisions.

**Proceed to implementation.**

The next priority should be the working MVP, not more specification
expansion.

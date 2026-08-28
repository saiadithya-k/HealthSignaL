from datetime import datetime, date
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.syndrome_mapping import syndrome_service
from app.core.data_collection import (
    data_collection_manager,
    RawSymptomReport,
    CanonicalAggregateSignal
)
from app.data_generation.cli import generate_and_analyze
from app.data_generation.schemas import ScenarioType

router = APIRouter(prefix="/data-collection", tags=["Data Collection & Knowledge"])

# -------------------------------------------------------------------------
# Request Models
# -------------------------------------------------------------------------

class CommunityReportRequest(BaseModel):
    node_id: str
    symptoms: List[str]
    symptom_onset: str
    severity: str = "mild"
    age_band: str = "15-29"
    sex: str = "prefer_not_to_say"
    zone_id: str = "zone-1"
    consent_accepted: bool = True

class DoctorObservationRequest(BaseModel):
    node_id: str
    syndrome: str
    severity: str = "moderate"
    visit_type: str = "walk-in"
    age_band: str = "30-44"
    sex: str = "prefer_not_to_say"
    symptom_onset: Optional[str] = None
    zone_id: str = "zone-1"

class ClinicDemandRequest(BaseModel):
    node_id: str
    date: str
    syndrome: str
    count: int
    visit_category: str = "outpatient"
    zone_id: str = "zone-1"

class PharmacyDemandRequest(BaseModel):
    node_id: str
    date: str
    drug_category: str
    count_dispensed: int
    zone_id: str = "zone-1"

class TestingDataRequest(BaseModel):
    node_id: str
    date: str
    test_type: str
    tests_requested: int
    tests_positive: int
    zone_id: str = "zone-1"

class AbsenteeismRequest(BaseModel):
    node_id: str
    date: str
    expected_attendance: int
    actual_attendance: int
    institution_name: str = "Metro District Schools"
    category: str = "school"
    zone_id: str = "zone-1"

class EmergencyCallsRequest(BaseModel):
    node_id: str
    date: str
    call_category: str
    calls_received: int
    calls_dispatched: int
    zone_id: str = "zone-1"

class WastewaterRequest(BaseModel):
    node_id: str
    date: str
    sample_site: str
    pathogen_marker: str
    copies_per_ul: float
    sample_volume_ml: float = 100.0
    quality_flag: str = "PASS"
    zone_id: str = "zone-1"

class EventSimulationRequest(BaseModel):
    scenario: ScenarioType
    seed: int = 42
    days: int = 365

# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------

@router.get("/symptom-master", response_model=Dict[str, Any])
def get_symptom_master():
    """Returns the standardized master list of 257 symptoms across 20 clinical categories."""
    return {
        "symptoms": syndrome_service.get_symptom_master_list(),
        "total_symptoms": len(syndrome_service.symptoms),
        "total_syndromes": len(syndrome_service.syndromes)
    }

@router.get("/syndrome-master", response_model=Dict[str, Any])
def get_syndrome_master():
    """Returns the 45 standardized syndrome categories covering infectious, respiratory, enteric, neuro, etc."""
    return {
        "syndromes": syndrome_service.get_syndrome_master_list(),
        "total_syndromes": len(syndrome_service.syndromes)
    }

@router.get("/disease-reference", response_model=Dict[str, Any])
def get_disease_reference():
    """Returns the 100+ reference disease/condition profiles for synthetic scenario modeling (non-diagnostic)."""
    return {
        "conditions": syndrome_service.get_disease_reference_catalog(),
        "total_conditions": len(syndrome_service.diseases)
    }

@router.get("/source-weights", response_model=Dict[str, Any])
def get_source_weights():
    """Returns the source reliability scores and leading indicator mappings."""
    return {
        "source_reliability": syndrome_service.source_reliability,
        "pharmacy_mapping": syndrome_service.pharmacy_mapping,
        "testing_mapping": syndrome_service.testing_mapping
    }

@router.post("/community-report", response_model=Dict[str, Any])
def submit_community_report(req: CommunityReportRequest):
    """
    Submits a community symptom checklist report into the local node raw storage.
    Raw patient record NEVER crosses the institutional boundary.
    """
    try:
        report = data_collection_manager.ingest_community_report(
            node_id=req.node_id,
            symptoms=req.symptoms,
            symptom_onset=req.symptom_onset,
            severity=req.severity,
            age_band=req.age_band,
            sex=req.sex,
            zone_id=req.zone_id,
            consent_accepted=req.consent_accepted
        )
        return {
            "status": "ACCEPTED_LOCAL_ONLY",
            "report_id": report.report_id,
            "node_id": report.node_id,
            "mapped_syndromes": report.syndromes,
            "privacy_notice": "Raw report saved locally. Only approved aggregate counts cross privacy boundary."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/doctor-observation", response_model=Dict[str, Any])
def submit_doctor_observation(req: DoctorObservationRequest):
    """Submits a structured clinician observation locally."""
    try:
        report = data_collection_manager.ingest_doctor_observation(
            node_id=req.node_id,
            syndrome=req.syndrome,
            severity=req.severity,
            visit_type=req.visit_type,
            age_band=req.age_band,
            sex=req.sex,
            symptom_onset=req.symptom_onset,
            zone_id=req.zone_id
        )
        return {
            "status": "ACCEPTED_LOCAL_ONLY",
            "report_id": report.report_id,
            "node_id": report.node_id,
            "syndrome": req.syndrome
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/clinic-demand", response_model=Dict[str, Any])
def submit_clinic_demand(req: ClinicDemandRequest):
    """Submits daily clinic volume demand counts locally."""
    return data_collection_manager.ingest_clinic_demand(
        node_id=req.node_id,
        date_str=req.date,
        syndrome=req.syndrome,
        count=req.count,
        visit_category=req.visit_category,
        zone_id=req.zone_id
    )

@router.post("/pharmacy-demand", response_model=Dict[str, Any])
def submit_pharmacy_demand(req: PharmacyDemandRequest):
    """Submits pharmacy OTC dispensing counts (leading indicator)."""
    return data_collection_manager.ingest_pharmacy_demand(
        node_id=req.node_id,
        date_str=req.date,
        drug_category=req.drug_category,
        count_dispensed=req.count_dispensed,
        zone_id=req.zone_id
    )

@router.post("/testing-data", response_model=Dict[str, Any])
def submit_testing_data(req: TestingDataRequest):
    """Submits diagnostic test counts and computed positivity rate."""
    return data_collection_manager.ingest_testing_data(
        node_id=req.node_id,
        date_str=req.date,
        test_type=req.test_type,
        tests_requested=req.tests_requested,
        tests_positive=req.tests_positive,
        zone_id=req.zone_id
    )

@router.post("/absenteeism", response_model=Dict[str, Any])
def submit_absenteeism(req: AbsenteeismRequest):
    """Submits school or workplace attendance/absenteeism metrics."""
    return data_collection_manager.ingest_absenteeism(
        node_id=req.node_id,
        date_str=req.date,
        expected_attendance=req.expected_attendance,
        actual_attendance=req.actual_attendance,
        institution_name=req.institution_name,
        category=req.category,
        zone_id=req.zone_id
    )

@router.post("/emergency-calls", response_model=Dict[str, Any])
def submit_emergency_calls(req: EmergencyCallsRequest):
    """Submits ambulance and emergency dispatch call metrics."""
    return data_collection_manager.ingest_emergency_calls(
        node_id=req.node_id,
        date_str=req.date,
        call_category=req.call_category,
        calls_received=req.calls_received,
        calls_dispatched=req.calls_dispatched,
        zone_id=req.zone_id
    )

@router.post("/wastewater", response_model=Dict[str, Any])
def submit_wastewater(req: WastewaterRequest):
    """Submits genomic wastewater pathogen viral copy surveillance data."""
    return data_collection_manager.ingest_wastewater(
        node_id=req.node_id,
        date_str=req.date,
        sample_site=req.sample_site,
        pathogen_marker=req.pathogen_marker,
        copies_per_ul=req.copies_per_ul,
        sample_volume_ml=req.sample_volume_ml,
        quality_flag=req.quality_flag,
        zone_id=req.zone_id
    )

@router.get("/weather", response_model=Dict[str, Any])
def get_weather_context(
    node_id: str = Query("inst-a"),
    query_date: Optional[str] = Query(None)
):
    """Fetches regional weather context from Open-Meteo or high-fidelity climate fallback."""
    from app.core.weather import fetch_regional_weather
    return fetch_regional_weather(node_id=node_id, query_date=query_date)

@router.post("/aggregate-now", response_model=Dict[str, Any])
def run_aggregation(
    node_id: Optional[str] = Query(None, description="Specific node ID or all if omitted"),
    k_threshold: int = Query(11, description="Small-group k-anonymity suppression threshold")
):
    """
    Executes the local daily aggregation job with k-suppression.
    Transforms raw reports into approved canonical aggregate signals.
    """
    nodes = [node_id] if node_id else ["inst-a", "inst-b", "inst-c", "inst-d"]
    total_aggregates = 0
    node_results = {}

    for nid in nodes:
        aggs = data_collection_manager.run_daily_aggregation(nid, k_threshold=k_threshold)
        node_results[nid] = len(aggs)
        total_aggregates += len(aggs)

    return {
        "status": "COMPLETED",
        "nodes_processed": nodes,
        "k_suppression_threshold": k_threshold,
        "aggregate_records_produced": total_aggregates,
        "breakdown_by_node": node_results
    }

@router.get("/zone-rollup", response_model=Dict[str, Any])
def get_zone_rollup(
    zone_id: Optional[str] = Query(None),
    syndrome: Optional[str] = Query(None),
    data_source: Optional[str] = Query(None),
    days_lookback: int = Query(7)
):
    """
    Executes Zone-level rollup query (Part 9 SQL Capability Check).
    Groups by zone and syndrome, calculating 7d growth and node participation.
    """
    rollups = data_collection_manager.query_zone_rollup(
        zone_id=zone_id,
        syndrome=syndrome,
        data_source=data_source,
        days_lookback=days_lookback
    )
    return {
        "query_timestamp": datetime.utcnow().isoformat(),
        "days_lookback": days_lookback,
        "results_count": len(rollups),
        "zone_rollups": rollups
    }

@router.post("/simulate-event", response_model=Dict[str, Any])
def simulate_outbreak_event(req: EventSimulationRequest):
    """
    Triggers one of the 5 realistic outbreak scenarios across the 4 nodes.
    Generates multi-source synthetic observations with known ground truth.
    """
    results = generate_and_analyze(
        output_dir="data",
        scenario=req.scenario,
        seed=req.seed,
        days=req.days
    )
    return {
        "status": "SIMULATION_GENERATED",
        "scenario": req.scenario.value,
        "seed": req.seed,
        "days": req.days,
        "total_records": results.get("total_records", 0),
        "non_iid_divergence": results.get("non_iid_divergence", {})
    }

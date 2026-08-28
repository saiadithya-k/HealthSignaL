from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SyndromeCategory(str, Enum):
    RESPIRATORY = "respiratory"
    GASTROINTESTINAL = "gastrointestinal"
    FEVER_FLU = "fever_flu"
    OTHER = "other"

class ScenarioType(str, Enum):
    NORMAL = "NORMAL"
    REGIONAL_SURGE = "REGIONAL_SURGE"
    DISTRIBUTION_SHIFT = "DISTRIBUTION_SHIFT"
    MISSING_DATA = "MISSING_DATA"

PROHIBITED_IDENTIFYING_FIELDS = {
    "patient_id", "name", "first_name", "last_name", "ssn", "national_id",
    "email", "phone", "address", "zipcode_exact", "dob", "exact_date_of_birth",
    "mrn", "medical_record_number", "ip_address"
}

REQUIRED_DATA_COLUMNS = [
    "date", "institution_id", "syndrome_category", "service_count",
    "rolling_7day_avg", "rolling_14day_avg", "day_of_week", "is_holiday",
    "data_completeness"
]

class GroundTruthEvent(BaseModel):
    scenario_name: ScenarioType
    affected_institution: str
    start_date: str
    end_date: str
    syndrome_category: Optional[str] = None
    magnitude_factor: float
    description: str

class DatasetMetadata(BaseModel):
    institution_id: str
    institution_name: str
    profile: str
    seed: int
    scenario: ScenarioType
    start_date: str
    end_date: str
    total_records: int
    syndrome_counts: Dict[str, int]
    missing_rate_pct: float
    ground_truth_events: List[GroundTruthEvent] = []
    generated_at: str

class ValidationResult(BaseModel):
    is_valid: bool
    institution_id: str
    total_records: int
    missing_values_count: int
    missing_rate_pct: float
    prohibited_fields_found: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

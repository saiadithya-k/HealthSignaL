from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from app.data_generation.schemas import ScenarioType, GroundTruthEvent

def apply_scenario_modifiers(
    scenario: ScenarioType,
    institution_id: str,
    current_date: datetime,
    start_date: datetime,
    cat_counts: Dict[str, int],
    base_volume: float
) -> Tuple[Dict[str, int], float, List[GroundTruthEvent]]:
    """
    Applies scenario-specific modifications (Surge, Shift, Missingness) to daily category counts.
    Returns (modified_counts, data_completeness, list_of_ground_truth_events).
    """
    day_index = (current_date - start_date).days
    modified_counts = cat_counts.copy()
    completeness = 1.0
    ground_truth = []
    
    if scenario == ScenarioType.NORMAL:
        pass

    elif scenario == ScenarioType.REGIONAL_SURGE:
        # Regional surge: Respiratory demand surges by +75% in inst-a and inst-b between Days 180 and 210
        surge_start = start_date + timedelta(days=180)
        surge_end = start_date + timedelta(days=210)
        
        if surge_start <= current_date <= surge_end:
            if institution_id in ["inst-a", "inst-b"]:
                surge_mult = 1.75
                modified_counts["respiratory"] = int(round(modified_counts.get("respiratory", 0) * surge_mult))
                ground_truth.append(GroundTruthEvent(
                    scenario_name=ScenarioType.REGIONAL_SURGE,
                    affected_institution=institution_id,
                    start_date=surge_start.strftime("%Y-%m-%d"),
                    end_date=surge_end.strftime("%Y-%m-%d"),
                    syndrome_category="respiratory",
                    magnitude_factor=1.75,
                    description=f"Regional respiratory surge (+75%) in {institution_id}"
                ))

    elif scenario == ScenarioType.DISTRIBUTION_SHIFT:
        # Distribution shift: Persistent baseline increase of +50% in inst-d starting from Day 220 onwards
        shift_start = start_date + timedelta(days=220)
        shift_end = start_date + timedelta(days=365)
        
        if current_date >= shift_start and institution_id == "inst-d":
            for cat in modified_counts:
                modified_counts[cat] = int(round(modified_counts[cat] * 1.50))
            ground_truth.append(GroundTruthEvent(
                scenario_name=ScenarioType.DISTRIBUTION_SHIFT,
                affected_institution=institution_id,
                start_date=shift_start.strftime("%Y-%m-%d"),
                end_date=shift_end.strftime("%Y-%m-%d"),
                syndrome_category=None,
                magnitude_factor=1.50,
                description=f"Structural population expansion (+50% base volume) in {institution_id}"
            ))

    elif scenario == ScenarioType.MISSING_DATA:
        # Missing data: inst-c experiences sporadic missing observation days (~10% missing rate)
        if institution_id == "inst-c":
            if (day_index * 17 + 3) % 10 == 0:
                completeness = 0.0
                for cat in modified_counts:
                    modified_counts[cat] = 0
                ground_truth.append(GroundTruthEvent(
                    scenario_name=ScenarioType.MISSING_DATA,
                    affected_institution=institution_id,
                    start_date=current_date.strftime("%Y-%m-%d"),
                    end_date=current_date.strftime("%Y-%m-%d"),
                    syndrome_category=None,
                    magnitude_factor=0.0,
                    description=f"Data collection outage in {institution_id}"
                ))

    elif scenario == ScenarioType.RESPIRATORY_OUTBREAK:
        # Scenario 1: Respiratory Outbreak in Urban (inst-a), Semi-Urban (inst-b), and Mixed (inst-d)
        surge_start = start_date + timedelta(days=60)
        surge_end = start_date + timedelta(days=90)
        if surge_start <= current_date <= surge_end and institution_id in ["inst-a", "inst-b", "inst-d"]:
            modified_counts["respiratory"] = int(round(modified_counts.get("respiratory", 0) * 1.85))
            modified_counts["fever_flu"] = int(round(modified_counts.get("fever_flu", 0) * 1.40))
            ground_truth.append(GroundTruthEvent(
                scenario_name=ScenarioType.RESPIRATORY_OUTBREAK,
                affected_institution=institution_id,
                start_date=surge_start.strftime("%Y-%m-%d"),
                end_date=surge_end.strftime("%Y-%m-%d"),
                syndrome_category="respiratory",
                magnitude_factor=1.85,
                description=f"Multi-source respiratory epidemic surge (+85% resp, +40% fever) in {institution_id}"
            ))

    elif scenario == ScenarioType.GASTROINTESTINAL_OUTBREAK:
        # Scenario 2: GI Outbreak in Rural (inst-c) and Semi-Urban (inst-b)
        surge_start = start_date + timedelta(days=120)
        surge_end = start_date + timedelta(days=145)
        if surge_start <= current_date <= surge_end and institution_id in ["inst-b", "inst-c"]:
            modified_counts["gastrointestinal"] = int(round(modified_counts.get("gastrointestinal", 0) * 2.20))
            modified_counts["fever_flu"] = int(round(modified_counts.get("fever_flu", 0) * 1.30))
            ground_truth.append(GroundTruthEvent(
                scenario_name=ScenarioType.GASTROINTESTINAL_OUTBREAK,
                affected_institution=institution_id,
                start_date=surge_start.strftime("%Y-%m-%d"),
                end_date=surge_end.strftime("%Y-%m-%d"),
                syndrome_category="gastrointestinal",
                magnitude_factor=2.20,
                description=f"Water-borne enteric gastrointestinal outbreak (+120% GI) in {institution_id}"
            ))

    elif scenario == ScenarioType.VECTOR_BORNE_OUTBREAK:
        # Scenario 3: Vector-borne Fever Outbreak in Rural (inst-c) and Mixed (inst-d)
        surge_start = start_date + timedelta(days=200)
        surge_end = start_date + timedelta(days=235)
        if surge_start <= current_date <= surge_end and institution_id in ["inst-c", "inst-d"]:
            modified_counts["fever_flu"] = int(round(modified_counts.get("fever_flu", 0) * 2.10))
            modified_counts["other"] = int(round(modified_counts.get("other", 0) * 1.70))
            ground_truth.append(GroundTruthEvent(
                scenario_name=ScenarioType.VECTOR_BORNE_OUTBREAK,
                affected_institution=institution_id,
                start_date=surge_start.strftime("%Y-%m-%d"),
                end_date=surge_end.strftime("%Y-%m-%d"),
                syndrome_category="fever_flu",
                magnitude_factor=2.10,
                description=f"Seasonal vector-borne fever surge (+110% fever/flu) in {institution_id}"
            ))

    elif scenario == ScenarioType.NEUROLOGICAL_CLUSTER:
        # Scenario 4: Neurological Cluster (severe headache, confusion, stiff neck)
        surge_start = start_date + timedelta(days=150)
        surge_end = start_date + timedelta(days=170)
        if surge_start <= current_date <= surge_end and institution_id in ["inst-a", "inst-c"]:
            modified_counts["fever_flu"] = int(round(modified_counts.get("fever_flu", 0) * 1.50))
            modified_counts["other"] = int(round(modified_counts.get("other", 0) * 2.50))
            ground_truth.append(GroundTruthEvent(
                scenario_name=ScenarioType.NEUROLOGICAL_CLUSTER,
                affected_institution=institution_id,
                start_date=surge_start.strftime("%Y-%m-%d"),
                end_date=surge_end.strftime("%Y-%m-%d"),
                syndrome_category="other",
                magnitude_factor=2.50,
                description=f"High-priority neurological cluster surge (+150% other/neuro) in {institution_id}"
            ))

    elif scenario == ScenarioType.MULTI_SYNDROME_OUTBREAK:
        # Scenario 5: Multi-Syndrome Surge across all four institutions
        surge_start = start_date + timedelta(days=100)
        surge_end = start_date + timedelta(days=130)
        if surge_start <= current_date <= surge_end:
            for cat in modified_counts:
                modified_counts[cat] = int(round(modified_counts[cat] * 1.70))
            ground_truth.append(GroundTruthEvent(
                scenario_name=ScenarioType.MULTI_SYNDROME_OUTBREAK,
                affected_institution=institution_id,
                start_date=surge_start.strftime("%Y-%m-%d"),
                end_date=surge_end.strftime("%Y-%m-%d"),
                syndrome_category=None,
                magnitude_factor=1.70,
                description=f"Pan-institutional multi-syndrome surge (+70% all categories) in {institution_id}"
            ))

    return modified_counts, completeness, ground_truth

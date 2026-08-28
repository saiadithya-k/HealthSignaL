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

    return modified_counts, completeness, ground_truth

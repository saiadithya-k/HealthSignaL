import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Any, Optional

from app.data_generation.config import INSTITUTION_PROFILES
from app.data_generation.schemas import (
    SyndromeCategory,
    ScenarioType,
    DatasetMetadata,
    GroundTruthEvent
)
from app.data_generation.distributions import (
    compute_daily_base_demand,
    partition_demand_by_syndrome
)
from app.data_generation.scenarios import apply_scenario_modifiers
from app.data_generation.validator import DatasetValidator

class SyntheticDataGenerator:
    """Reproducible engine for generating non-IID local synthetic healthcare demand datasets."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def generate_institution_dataset(
        self,
        institution_id: str,
        start_date: datetime = datetime(2025, 1, 1),
        days: int = 365,
        scenario: ScenarioType = ScenarioType.NORMAL,
        disease_outbreak_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[pd.DataFrame, DatasetMetadata]:
        if institution_id not in INSTITUTION_PROFILES:
            raise ValueError(f"Unknown institution_id: {institution_id}")

        profile = INSTITUTION_PROFILES[institution_id]
        base_volume = profile["base_volume"]
        from app.data_generation.syndrome_weights import get_institution_syndrome_weights
        syndrome_ratios = get_institution_syndrome_weights(institution_id)
        dow_mults = profile["day_of_week_multipliers"]
        season_amp = profile["seasonality_amplitude"]
        season_phase = profile["seasonality_phase_days"]
        noise_std = profile["noise_std"]

        # Deterministic node-specific RNG to ensure baseline reproducibility across calls
        inst_idx = list(INSTITUTION_PROFILES.keys()).index(institution_id) if institution_id in INSTITUTION_PROFILES else 0
        node_rng = np.random.RandomState(self.seed + (inst_idx * 1000))

        rows = []
        raw_ground_truth: List[GroundTruthEvent] = []

        # Generate day-by-day observations
        for day_idx in range(days):
            current_date = start_date + timedelta(days=day_idx)
            date_str = current_date.strftime("%Y-%m-%d")
            day_of_week = current_date.weekday()
            is_holiday = int(day_of_week >= 5)  # Weekend indicator

            # 1. Base expected demand
            expected_demand = compute_daily_base_demand(
                current_date=current_date,
                start_date=start_date,
                base_volume=base_volume,
                day_of_week_multipliers=dow_mults,
                seasonality_amplitude=season_amp,
                seasonality_phase_days=season_phase
            )

            # 2. Partition across all 45 canonical syndrome categories (and aliases)
            cat_counts = partition_demand_by_syndrome(
                total_demand=expected_demand,
                syndrome_ratios=syndrome_ratios,
                noise_std=noise_std,
                rng=node_rng
            )

            # 3. Apply Scenario Modifiers (Surge, Shift, Missingness, Disease Outbreak)
            modified_counts, completeness, gt_events = apply_scenario_modifiers(
                scenario=scenario,
                institution_id=institution_id,
                current_date=current_date,
                start_date=start_date,
                cat_counts=cat_counts,
                base_volume=base_volume,
                disease_outbreak_config=disease_outbreak_config
            )

            if gt_events:
                raw_ground_truth.extend(gt_events)

            # Append rows for all generated syndrome categories
            for cat, count in modified_counts.items():
                rows.append({
                    "date": date_str,
                    "institution_id": institution_id,
                    "syndrome_category": cat,
                    "service_count": count,
                    "day_of_week": day_of_week,
                    "is_holiday": is_holiday,
                    "data_completeness": completeness
                })

        df = pd.DataFrame(rows)
        df.sort_values(by=["date", "syndrome_category"], inplace=True)

        # Compute rolling features per syndrome category
        df["rolling_7day_avg"] = (
            df.groupby("syndrome_category")["service_count"]
            .transform(lambda x: x.rolling(7, min_periods=1).mean().round(2))
        )
        df["rolling_14day_avg"] = (
            df.groupby("syndrome_category")["service_count"]
            .transform(lambda x: x.rolling(14, min_periods=1).mean().round(2))
        )

        # Deduplicate ground truth events
        unique_gt: List[GroundTruthEvent] = []
        seen_keys = set()
        for gt in raw_ground_truth:
            key = (gt.scenario_name, gt.affected_institution, gt.start_date, gt.end_date, gt.syndrome_category, gt.condition_id)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_gt.append(gt)

        # Calculate metadata summary
        syndrome_counts = df.groupby("syndrome_category")["service_count"].sum().to_dict()
        zero_or_null_count = (df["service_count"] == 0).sum()
        missing_rate_pct = round((zero_or_null_count / len(df)) * 100.0, 2)

        metadata = DatasetMetadata(
            institution_id=institution_id,
            institution_name=profile["name"],
            profile=profile["profile"],
            seed=self.seed,
            scenario=scenario,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=(start_date + timedelta(days=days-1)).strftime("%Y-%m-%d"),
            total_records=len(df),
            syndrome_counts=syndrome_counts,
            missing_rate_pct=missing_rate_pct,
            ground_truth_events=unique_gt,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        )

        return df, metadata

    def generate_all_institutions(
        self,
        output_dir: str = "data",
        scenario: ScenarioType = ScenarioType.NORMAL,
        days: int = 365,
        start_date: datetime = datetime(2025, 1, 1),
        disease_outbreak_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Tuple[pd.DataFrame, DatasetMetadata]]:
        results = {}
        for inst_id in INSTITUTION_PROFILES.keys():
            df, metadata = self.generate_institution_dataset(
                institution_id=inst_id,
                start_date=start_date,
                days=days,
                scenario=scenario,
                disease_outbreak_config=disease_outbreak_config
            )

            # Validate generated dataframe
            val_result = DatasetValidator.validate_dataframe(df, inst_id)
            if not val_result.is_valid:
                raise ValueError(f"Generated dataset for {inst_id} failed validation: {val_result.errors}")

            # Save to isolated local institution folder
            inst_dir = os.path.join(output_dir, inst_id)
            os.makedirs(inst_dir, exist_ok=True)

            csv_path = os.path.join(inst_dir, "data.csv")
            meta_path = os.path.join(inst_dir, "metadata.json")

            df.to_csv(csv_path, index=False)
            with open(meta_path, "w") as f:
                f.write(metadata.model_dump_json(indent=2))

            results[inst_id] = (df, metadata)

        return results

    def generate_disease_outbreak(
        self,
        condition_id: str = "C002",
        start_day: int = 60,
        duration_days: int = 21,
        affected_nodes: Optional[List[str]] = None,
        intensity: float = 0.75,
        output_dir: str = "data",
        days: int = 365,
        start_date: datetime = datetime(2025, 1, 1)
    ) -> Dict[str, Tuple[pd.DataFrame, DatasetMetadata]]:
        """
        Executes a disease-reference driven outbreak simulation across the four nodes.
        Uses the condition profile in disease_reference.json to target relevant syndromes and symptoms.
        """
        nodes = affected_nodes or ["inst-a", "inst-b", "inst-c", "inst-d"]
        cfg = {
            "condition_id": condition_id,
            "start_day": start_day,
            "duration_days": duration_days,
            "affected_nodes": nodes,
            "intensity": intensity
        }
        return self.generate_all_institutions(
            output_dir=output_dir,
            scenario=ScenarioType.DISEASE_OUTBREAK,
            days=days,
            start_date=start_date,
            disease_outbreak_config=cfg
        )


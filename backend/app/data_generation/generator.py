import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

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
        scenario: ScenarioType = ScenarioType.NORMAL
    ) -> Tuple[pd.DataFrame, DatasetMetadata]:
        if institution_id not in INSTITUTION_PROFILES:
            raise ValueError(f"Unknown institution_id: {institution_id}")

        profile = INSTITUTION_PROFILES[institution_id]
        base_volume = profile["base_volume"]
        syndrome_ratios = profile["syndrome_ratios"]
        dow_mults = profile["day_of_week_multipliers"]
        season_amp = profile["seasonality_amplitude"]
        season_phase = profile["seasonality_phase_days"]
        noise_std = profile["noise_std"]

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

            # 2. Partition across syndrome categories
            cat_counts = partition_demand_by_syndrome(
                total_demand=expected_demand,
                syndrome_ratios=syndrome_ratios,
                noise_std=noise_std,
                rng=self.rng
            )

            # 3. Apply Scenario Modifiers (Surge, Shift, Missingness)
            modified_counts, completeness, gt_events = apply_scenario_modifiers(
                scenario=scenario,
                institution_id=institution_id,
                current_date=current_date,
                start_date=start_date,
                cat_counts=cat_counts,
                base_volume=base_volume
            )

            if gt_events:
                raw_ground_truth.extend(gt_events)

            # Append rows per syndrome category
            for cat_enum in SyndromeCategory:
                cat = cat_enum.value
                count = modified_counts.get(cat, 0)
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
            key = (gt.scenario_name, gt.affected_institution, gt.start_date, gt.end_date, gt.syndrome_category)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_gt.append(gt)

        # Calculate metadata summary
        syndrome_counts = df.groupby("syndrome_category")["service_count"].sum().to_dict()
        total_cells = df.size
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
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )

        return df, metadata

    def generate_all_institutions(
        self,
        output_dir: str = "data",
        scenario: ScenarioType = ScenarioType.NORMAL,
        days: int = 365,
        start_date: datetime = datetime(2025, 1, 1)
    ) -> Dict[str, Tuple[pd.DataFrame, DatasetMetadata]]:
        results = {}
        for inst_id in INSTITUTION_PROFILES.keys():
            df, metadata = self.generate_institution_dataset(
                institution_id=inst_id,
                start_date=start_date,
                days=days,
                scenario=scenario
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

import os
import json
import scipy.stats as stats
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any

from app.data_generation.schemas import ScenarioType
from app.data_generation.generator import SyntheticDataGenerator

def analyze_non_iid_properties(data_dir: str = "data") -> Dict[str, Any]:
    """
    Computes distribution metrics and pairwise distance tests demonstrating non-IID properties: P(A) != P(B) != P(C) != P(D).
    """
    inst_ids = ["inst-a", "inst-b", "inst-c", "inst-d"]
    node_data = {}

    for inst_id in inst_ids:
        csv_path = os.path.join(data_dir, inst_id, "data.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Missing local dataset for {inst_id} at {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Calculate daily aggregate service demand per institution
        daily_total = df.groupby("date")["service_count"].sum()
        
        # Syndrome proportions
        syndrome_totals = df.groupby("syndrome_category")["service_count"].sum()
        total_demand = syndrome_totals.sum()
        syndrome_props = {cat: round(count / total_demand, 4) for cat, count in syndrome_totals.items()} if total_demand > 0 else {}
        legacy_cats = ["respiratory", "gastrointestinal", "fever_flu", "other"]
        legacy_sum = sum(syndrome_totals.get(c, 0) for c in legacy_cats)
        if legacy_sum > 0:
            for c in legacy_cats:
                syndrome_props[c] = round(syndrome_totals.get(c, 0) / legacy_sum, 4)
        
        node_data[inst_id] = {
            "mean_daily_demand": float(round(daily_total.mean(), 2)),
            "std_daily_demand": float(round(daily_total.std(), 2)),
            "min_daily_demand": int(daily_total.min()),
            "max_daily_demand": int(daily_total.max()),
            "syndrome_proportions": syndrome_props,
            "daily_series": daily_total.values
        }

    # Compute Pairwise Distribution Distances (Kolmogorov-Smirnov Test & Wasserstein Distance)
    pairwise_distances = {}
    for i in range(len(inst_ids)):
        for j in range(i + 1, len(inst_ids)):
            id1, id2 = inst_ids[i], inst_ids[j]
            series1 = node_data[id1]["daily_series"]
            series2 = node_data[id2]["daily_series"]
            
            ks_stat, p_value = stats.ks_2samp(series1, series2)
            wasserstein = stats.wasserstein_distance(series1, series2)
            
            pair_key = f"{id1}_vs_{id2}"
            pairwise_distances[pair_key] = {
                "ks_statistic": float(round(ks_stat, 4)),
                "p_value": float(p_value),
                "wasserstein_distance": float(round(wasserstein, 2)),
                "statistically_significantly_different": bool(p_value < 0.05)
            }

    # Clean output dictionary for export
    total_recs = sum(len(pd.read_csv(os.path.join(data_dir, inst, "data.csv"))) for inst in inst_ids if os.path.exists(os.path.join(data_dir, inst, "data.csv")))
    summary_report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "total_records": total_recs,
        "non_iid_demonstration": "P(inst-a) != P(inst-b) != P(inst-c) != P(inst-d)",
        "non_iid_divergence": pairwise_distances,
        "institutions": {
            inst_id: {
                "mean_daily_demand": info["mean_daily_demand"],
                "std_daily_demand": info["std_daily_demand"],
                "min_daily_demand": info["min_daily_demand"],
                "max_daily_demand": info["max_daily_demand"],
                "syndrome_proportions": info["syndrome_proportions"]
            } for inst_id, info in node_data.items()
        },
        "pairwise_tests": pairwise_distances
    }

    # Save summary report
    summary_path = os.path.join(data_dir, "non_iid_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary_report, f, indent=2)

    return summary_report


def generate_and_analyze(
    output_dir: str = "data",
    scenario: ScenarioType = ScenarioType.NORMAL,
    seed: int = 42,
    days: int = 365
) -> Dict[str, Any]:
    generator = SyntheticDataGenerator(seed=seed)
    generator.generate_all_institutions(
        output_dir=output_dir,
        scenario=scenario,
        days=days
    )
    report = analyze_non_iid_properties(data_dir=output_dir)
    return report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HealthSignal Synthetic Data Generator")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--days", type=int, default=365, help="Number of days")
    parser.add_argument("--scenario", type=str, default="NORMAL", choices=["NORMAL", "REGIONAL_SURGE", "DISTRIBUTION_SHIFT", "MISSING_DATA"])
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory")

    args = parser.parse_args()
    scen_enum = ScenarioType(args.scenario)
    rep = generate_and_analyze(output_dir=args.output_dir, scenario=scen_enum, seed=args.seed, days=args.days)
    print(json.dumps(rep, indent=2))

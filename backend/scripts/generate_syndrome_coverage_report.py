import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List

def generate_syndrome_coverage_report(backend_dir: str = "backend", data_dir: str = "data"):
    # 1. Load canonical 45 syndromes dynamically
    syndrome_master_path = os.path.join(backend_dir, "app", "core", "syndrome_master.json")
    if not os.path.exists(syndrome_master_path):
        syndrome_master_path = os.path.join("app", "core", "syndrome_master.json")

    with open(syndrome_master_path, "r", encoding="utf-8") as f:
        master_data = json.load(f)
    canonical_syndromes = master_data.get("syndromes", [])
    canonical_codes = [s["code"] for s in canonical_syndromes]

    # 2. Gather records across all 4 decentralized nodes
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    node_records: Dict[str, pd.DataFrame] = {}
    combined_rows = []

    for nid in nodes:
        # Check primary data paths
        csv_path = os.path.join(data_dir, nid, "data.csv")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(backend_dir, data_dir, nid, "data.csv")
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            node_records[nid] = df
            combined_rows.append(df)

    if not combined_rows:
        raise FileNotFoundError(f"No node data found in {data_dir}")

    full_df = pd.concat(combined_rows, ignore_index=True)
    full_df["date"] = pd.to_datetime(full_df["date"])

    # Also inspect multi-source raw files
    sources_observed = set(["clinic"])
    for nid in nodes:
        node_dir = os.path.join(data_dir, nid)
        if not os.path.exists(node_dir):
            node_dir = os.path.join(backend_dir, data_dir, nid)
        for src_file in ["community_reports.json", "doctor_observations.json", "pharmacy_records.json", "testing_records.json", "wastewater_records.json"]:
            if os.path.exists(os.path.join(node_dir, src_file)):
                src_name = src_file.replace(".json", "").replace("_reports", "").replace("_records", "").replace("_observations", "")
                sources_observed.add(src_name)

    total_records = int(len(full_df))
    records_per_node = {nid: int(len(df)) for nid, df in node_records.items()}
    records_per_syndrome = full_df["syndrome_category"].value_counts().to_dict()
    records_per_day = {str(d.date()): int(c) for d, c in full_df.groupby("date").size().items()}

    # 3. Analyze coverage for all 45 canonical syndromes
    syndromes_detail: List[Dict[str, Any]] = []
    forecastable_count = 0
    insufficient_count = 0

    for s_obj in canonical_syndromes:
        code = s_obj["code"]
        name = s_obj.get("name", code)
        synd_df = full_df[full_df["syndrome_category"] == code]

        records_count = int(len(synd_df))
        if records_count > 0:
            active_days = int(synd_df["date"].nunique())
            contributing_nodes = int(synd_df["institution_id"].nunique())
            service_counts = synd_df["service_count"].values
            h_mean = float(round(np.mean(service_counts), 3))
            h_std = float(round(np.std(service_counts), 3))
            completeness = float(round(synd_df["data_completeness"].mean(), 3)) if "data_completeness" in synd_df.columns else 1.0
            
            # Forecastable if >= 14 days and non-zero mean
            is_forecastable = (active_days >= 14 and h_mean > 0.0)
            status = "VALID" if is_forecastable else "INSUFFICIENT_HISTORY"
            sources_count = len(sources_observed)
        else:
            active_days = 0
            contributing_nodes = 0
            h_mean = 0.0
            h_std = 0.0
            completeness = 0.0
            is_forecastable = False
            status = "INSUFFICIENT_HISTORY"
            sources_count = 0

        if is_forecastable:
            forecastable_count += 1
        else:
            insufficient_count += 1

        syndromes_detail.append({
            "syndrome": code,
            "syndrome_name": name,
            "domain": s_obj.get("domain", "General"),
            "early_warning_weight": s_obj.get("early_warning_weight", 0.75),
            "records": records_count,
            "days": active_days,
            "nodes": contributing_nodes,
            "sources": sources_count,
            "mean": h_mean,
            "std": h_std,
            "completeness": completeness,
            "forecastable": is_forecastable,
            "status": status
        })

    report = {
        "total_canonical_syndromes": len(canonical_syndromes),
        "total_raw_records": total_records,
        "forecastable_syndromes": forecastable_count,
        "insufficient_history_syndromes": insufficient_count,
        "records_per_node": records_per_node,
        "sources_tracked": list(sources_observed),
        "total_active_days": int(full_df["date"].nunique()),
        "syndromes": syndromes_detail
    }

    # Save to data/ and backend/data/
    paths = [
        os.path.join("data", "syndrome_data_coverage_report.json"),
        os.path.join(backend_dir, "data", "syndrome_data_coverage_report.json")
    ]
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    print(f"[OK] Generated syndrome data coverage report: {total_records} records across {len(canonical_syndromes)} syndromes ({forecastable_count} forecastable).")
    return report

if __name__ == "__main__":
    generate_syndrome_coverage_report()

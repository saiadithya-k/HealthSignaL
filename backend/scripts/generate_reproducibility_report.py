import os
import sys
import json
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data_generation.generator import SyntheticDataGenerator
from app.ml.features import FEATURE_COLUMNS, build_supervised_features
from app.ml.model import LocalForecastModel
from app.ml.forecasting import load_global_model, generate_multiday_forecast

def generate_reproducibility_report(backend_dir: str = "backend", data_dir: str = "data"):
    seeds_to_test = [42, 123, 2024, 2025]
    reproducibility_results = []

    for s in seeds_to_test:
        gen1 = SyntheticDataGenerator(seed=s)
        gen2 = SyntheticDataGenerator(seed=s)

        df1, _ = gen1.generate_institution_dataset("inst-a", days=90)
        df2, _ = gen2.generate_institution_dataset("inst-a", days=90)

        # Hash check
        h1 = hashlib.sha256(pd.util.hash_pandas_object(df1).values).hexdigest()
        h2 = hashlib.sha256(pd.util.hash_pandas_object(df2).values).hexdigest()
        data_match = (h1 == h2) and len(df1) == len(df2) and (df1["service_count"].values == df2["service_count"].values).all()

        # Features determinism
        feat1 = build_supervised_features(df1, forecast_horizon=7)
        feat2 = build_supervised_features(df2, forecast_horizon=7)
        feat_match = (feat1[FEATURE_COLUMNS].values == feat2[FEATURE_COLUMNS].values).all()

        # Model training determinism
        m1 = LocalForecastModel("inst-a", alpha=1.0, forecast_horizon=7).fit(feat1[FEATURE_COLUMNS], feat1["target"])
        m2 = LocalForecastModel("inst-a", alpha=1.0, forecast_horizon=7).fit(feat2[FEATURE_COLUMNS], feat2["target"])
        pred1 = m1.predict(feat1[FEATURE_COLUMNS])
        pred2 = m2.predict(feat2[FEATURE_COLUMNS])
        model_match = np.allclose(pred1, pred2, atol=1e-6)

        reproducibility_results.append({
            "seed": s,
            "sample_records": int(len(df1)),
            "data_checksum": str(h1[:16]),
            "dataset_deterministic": bool(data_match),
            "features_deterministic": bool(feat_match),
            "model_predictions_deterministic": bool(model_match),
            "status": "PASS" if bool(data_match and feat_match and model_match) else "FAIL"
        })

    all_passed = all(r["status"] == "PASS" for r in reproducibility_results)
    report = {
        "title": "HealthSignal Reproducibility & Deterministic Seed Validation Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_seeds_tested": len(seeds_to_test),
        "overall_status": "REPRODUCIBLE" if all_passed else "NON_DETERMINISTIC",
        "known_nondeterministic_factors": "None (all pseudo-random state generators are explicitly seeded)",
        "seed_evaluations": reproducibility_results
    }

    for p in [os.path.join("data", "reproducibility_report.json"), os.path.join(backend_dir, "data", "reproducibility_report.json")]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    print(f"[OK] Generated Reproducibility Report across {len(seeds_to_test)} seeds (Status: {report['overall_status']}).")
    return report

if __name__ == "__main__":
    generate_reproducibility_report()

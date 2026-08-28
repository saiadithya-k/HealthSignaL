import os
import pandas as pd
from app.data_generation.cli import analyze_non_iid_properties
from app.data_generation.generator import SyntheticDataGenerator
from app.data_generation.schemas import ScenarioType

def test_institutions_are_demonstrably_non_iid(tmp_path):
    """Asserts statistical divergence P(A) != P(B) != P(C) != P(D) across all four institutions."""
    test_dir = str(tmp_path / "data")
    gen = SyntheticDataGenerator(seed=42)
    gen.generate_all_institutions(output_dir=test_dir, scenario=ScenarioType.NORMAL, days=180)

    report = analyze_non_iid_properties(data_dir=test_dir)

    inst_data = report["institutions"]
    assert len(inst_data) == 4

    # 1. Base demand volume divergence
    mean_a = inst_data["inst-a"]["mean_daily_demand"]
    mean_b = inst_data["inst-b"]["mean_daily_demand"]
    mean_c = inst_data["inst-c"]["mean_daily_demand"]
    mean_d = inst_data["inst-d"]["mean_daily_demand"]

    assert mean_a > mean_b > mean_c, f"Expected mean_a > mean_b > mean_c, got {mean_a}, {mean_b}, {mean_c}"
    assert mean_d != mean_a and mean_d != mean_b

    # 2. Syndrome ratio divergence
    props_a = inst_data["inst-a"]["syndrome_proportions"]
    props_b = inst_data["inst-b"]["syndrome_proportions"]
    props_c = inst_data["inst-c"]["syndrome_proportions"]

    # Inst A is respiratory heavy (>35%)
    assert props_a["respiratory"] > 0.35
    # Inst B is gastro heavy (>40%)
    assert props_b["gastrointestinal"] > 0.40
    # Inst C is fever/flu heavy (>50%)
    assert props_c["fever_flu"] > 0.50

    # 3. Statistical Kolmogorov-Smirnov pairwise divergence tests
    pairwise = report["pairwise_tests"]
    for pair_key, p_test in pairwise.items():
        assert p_test["statistically_significantly_different"], f"Pair {pair_key} failed Non-IID test (p={p_test['p_value']})"
        assert p_test["p_value"] < 0.01

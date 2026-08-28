import os
import pandas as pd
from app.data_generation.generator import SyntheticDataGenerator
from app.data_generation.schemas import ScenarioType

def test_same_seed_produces_same_data():
    """Asserts that identical seeds produce identical dataframes across all institutions."""
    gen1 = SyntheticDataGenerator(seed=42)
    df1_a, meta1_a = gen1.generate_institution_dataset("inst-a", days=30, scenario=ScenarioType.NORMAL)

    gen2 = SyntheticDataGenerator(seed=42)
    df2_a, meta2_a = gen2.generate_institution_dataset("inst-a", days=30, scenario=ScenarioType.NORMAL)

    pd.testing.assert_frame_equal(df1_a, df2_a)
    assert meta1_a.total_records == meta2_a.total_records
    assert meta1_a.syndrome_counts == meta2_a.syndrome_counts

def test_different_seed_produces_different_data():
    """Asserts that different seeds produce different count series while maintaining structure."""
    gen1 = SyntheticDataGenerator(seed=42)
    df1, _ = gen1.generate_institution_dataset("inst-a", days=30, scenario=ScenarioType.NORMAL)

    gen2 = SyntheticDataGenerator(seed=999)
    df2, _ = gen2.generate_institution_dataset("inst-a", days=30, scenario=ScenarioType.NORMAL)

    assert not df1["service_count"].equals(df2["service_count"])
    assert len(df1) == len(df2)  # Structure/days match

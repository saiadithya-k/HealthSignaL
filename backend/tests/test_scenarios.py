from datetime import datetime, timedelta
import pandas as pd
from app.data_generation.generator import SyntheticDataGenerator
from app.data_generation.schemas import ScenarioType

def test_scenario_normal(tmp_path):
    gen = SyntheticDataGenerator(seed=42)
    df, meta = gen.generate_institution_dataset("inst-a", days=60, scenario=ScenarioType.NORMAL)
    assert meta.scenario == ScenarioType.NORMAL
    assert len(df) >= 60 * 4  # 60 days * at least 4 syndrome categories
    assert len(meta.ground_truth_events) == 0

def test_scenario_regional_surge(tmp_path):
    gen = SyntheticDataGenerator(seed=42)
    # Generate 220 days to cover surge window (days 180 to 210)
    df, meta = gen.generate_institution_dataset("inst-a", days=220, scenario=ScenarioType.REGIONAL_SURGE)
    
    assert meta.scenario == ScenarioType.REGIONAL_SURGE
    assert len(meta.ground_truth_events) > 0
    gt = meta.ground_truth_events[0]
    assert gt.scenario_name == ScenarioType.REGIONAL_SURGE
    assert gt.affected_institution == "inst-a"
    assert gt.syndrome_category == "respiratory"
    assert gt.magnitude_factor == 1.75

    # Check that respiratory demand during surge is significantly higher than before surge
    df["date"] = pd.to_datetime(df["date"])
    surge_start = datetime(2025, 1, 1) + timedelta(days=180)
    surge_end = datetime(2025, 1, 1) + timedelta(days=210)

    pre_surge = df[(df["syndrome_category"] == "respiratory") & (df["date"] < surge_start)]["service_count"].mean()
    during_surge = df[(df["syndrome_category"] == "respiratory") & (df["date"] >= surge_start) & (df["date"] <= surge_end)]["service_count"].mean()

    assert during_surge > pre_surge * 1.4

def test_scenario_distribution_shift(tmp_path):
    gen = SyntheticDataGenerator(seed=42)
    # Days 220+ in inst-d have structural shift
    df, meta = gen.generate_institution_dataset("inst-d", days=250, scenario=ScenarioType.DISTRIBUTION_SHIFT)
    
    assert meta.scenario == ScenarioType.DISTRIBUTION_SHIFT
    assert len(meta.ground_truth_events) > 0
    gt = meta.ground_truth_events[0]
    assert gt.scenario_name == ScenarioType.DISTRIBUTION_SHIFT
    assert gt.affected_institution == "inst-d"
    assert gt.magnitude_factor == 1.50

def test_scenario_missing_data(tmp_path):
    gen = SyntheticDataGenerator(seed=42)
    df, meta = gen.generate_institution_dataset("inst-c", days=60, scenario=ScenarioType.MISSING_DATA)
    
    assert meta.scenario == ScenarioType.MISSING_DATA
    assert len(meta.ground_truth_events) > 0
    gt = meta.ground_truth_events[0]
    assert gt.scenario_name == ScenarioType.MISSING_DATA
    assert gt.affected_institution == "inst-c"
    
    # Check completeness dropped below 1.0 on missing days
    assert (df["data_completeness"] < 1.0).any()

def test_scenario_respiratory_outbreak():
    gen = SyntheticDataGenerator(seed=42)
    df, meta = gen.generate_institution_dataset("inst-a", days=100, scenario=ScenarioType.RESPIRATORY_OUTBREAK)
    assert meta.scenario == ScenarioType.RESPIRATORY_OUTBREAK
    assert len(meta.ground_truth_events) > 0
    gt = meta.ground_truth_events[0]
    assert gt.syndrome_category == "respiratory"
    assert gt.magnitude_factor == 1.85

def test_scenario_gastrointestinal_outbreak():
    gen = SyntheticDataGenerator(seed=42)
    df, meta = gen.generate_institution_dataset("inst-c", days=160, scenario=ScenarioType.GASTROINTESTINAL_OUTBREAK)
    assert meta.scenario == ScenarioType.GASTROINTESTINAL_OUTBREAK
    assert len(meta.ground_truth_events) > 0
    gt = meta.ground_truth_events[0]
    assert gt.syndrome_category == "gastrointestinal"
    assert gt.magnitude_factor == 2.20

def test_scenario_vector_borne_outbreak():
    gen = SyntheticDataGenerator(seed=42)
    df, meta = gen.generate_institution_dataset("inst-c", days=240, scenario=ScenarioType.VECTOR_BORNE_OUTBREAK)
    assert meta.scenario == ScenarioType.VECTOR_BORNE_OUTBREAK
    assert len(meta.ground_truth_events) > 0
    gt = meta.ground_truth_events[0]
    assert gt.syndrome_category == "fever_flu"
    assert gt.magnitude_factor == 2.10

def test_scenario_neurological_cluster():
    gen = SyntheticDataGenerator(seed=42)
    df, meta = gen.generate_institution_dataset("inst-a", days=180, scenario=ScenarioType.NEUROLOGICAL_CLUSTER)
    assert meta.scenario == ScenarioType.NEUROLOGICAL_CLUSTER
    assert len(meta.ground_truth_events) > 0
    gt = meta.ground_truth_events[0]
    assert gt.syndrome_category == "other"
    assert gt.magnitude_factor == 2.50

def test_scenario_multi_syndrome_outbreak():
    gen = SyntheticDataGenerator(seed=42)
    df, meta = gen.generate_institution_dataset("inst-b", days=140, scenario=ScenarioType.MULTI_SYNDROME_OUTBREAK)
    assert meta.scenario == ScenarioType.MULTI_SYNDROME_OUTBREAK
    assert len(meta.ground_truth_events) > 0
    gt = meta.ground_truth_events[0]
    assert gt.magnitude_factor == 1.70


def test_disease_driven_outbreak_influenza(tmp_path):
    gen = SyntheticDataGenerator(seed=42)
    results = gen.generate_disease_outbreak(
        condition_id="C002",
        start_day=60,
        duration_days=21,
        affected_nodes=["inst-a", "inst-b"],
        intensity=0.85,
        output_dir=str(tmp_path),
        days=120
    )
    assert len(results) == 4
    df_a, meta_a = results["inst-a"]
    assert meta_a.scenario == ScenarioType.DISEASE_OUTBREAK
    assert len(meta_a.ground_truth_events) > 0
    gt_a = meta_a.ground_truth_events[0]
    assert gt_a.condition_id == "C002"
    assert "respiratory" in gt_a.syndrome_category
    assert gt_a.magnitude_factor == 1.85

    # Check non-affected nodes (inst-c, inst-d) do not have surge ground truth
    df_c, meta_c = results["inst-c"]
    assert len(meta_c.ground_truth_events) == 0


def test_disease_driven_outbreak_cholera(tmp_path):
    gen = SyntheticDataGenerator(seed=42)
    results = gen.generate_disease_outbreak(
        condition_id="C023",
        start_day=45,
        duration_days=15,
        affected_nodes=["inst-b", "inst-c"],
        intensity=1.20,
        output_dir=str(tmp_path),
        days=90
    )
    df_b, meta_b = results["inst-b"]
    gt_b = meta_b.ground_truth_events[0]
    assert gt_b.condition_id == "C023"
    assert "gastrointestinal" in gt_b.syndrome_category
    assert gt_b.magnitude_factor == 2.20


def test_disease_driven_outbreak_dengue(tmp_path):
    gen = SyntheticDataGenerator(seed=42)
    results = gen.generate_disease_outbreak(
        condition_id="C036",
        start_day=50,
        duration_days=20,
        affected_nodes=["inst-c", "inst-d"],
        intensity=1.00,
        output_dir=str(tmp_path),
        days=100
    )
    df_d, meta_d = results["inst-d"]
    gt_d = meta_d.ground_truth_events[0]
    assert gt_d.condition_id == "C036"
    assert "fever_flu" in gt_d.syndrome_category


def test_disease_selection_valid_and_invalid(tmp_path):
    import pytest
    gen = SyntheticDataGenerator(seed=42)
    
    # Valid condition IDs
    for valid_id in ["C001", "C002", "C023", "C036", "C105"]:
        df, meta = gen.generate_institution_dataset(
            "inst-a",
            days=30,
            scenario=ScenarioType.DISEASE_OUTBREAK,
            disease_outbreak_config={"condition_id": valid_id, "start_day": 5, "duration_days": 10}
        )
        assert len(df) >= 30 * 4

    # Invalid condition ID raises ValueError
    with pytest.raises(ValueError, match="Unknown condition_id"):
        gen.generate_institution_dataset(
            "inst-a",
            days=30,
            scenario=ScenarioType.DISEASE_OUTBREAK,
            disease_outbreak_config={"condition_id": "C999_INVALID", "start_day": 5, "duration_days": 10}
        )



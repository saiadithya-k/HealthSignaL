import os
import json
import shutil
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.data_collection import LocalDataCollectionManager
from app.data_generation.config import NODE_ZONE_MAPPING, INSTITUTION_PROFILES

client = TestClient(app)

@pytest.fixture
def temp_zone_manager():
    temp_dir = tempfile.mkdtemp()
    mgr = LocalDataCollectionManager(data_dir=temp_dir)
    yield mgr
    shutil.rmtree(temp_dir, ignore_errors=True)


def helper_create_node_aggregates(manager, node_id, zone_id, syndrome, source, counts_by_date):
    """Helper to write local canonical aggregate signals for a node."""
    node_dir = os.path.join(manager.data_dir, node_id)
    os.makedirs(node_dir, exist_ok=True)
    agg_file = os.path.join(node_dir, "aggregate_signals.json")

    existing = []
    if os.path.exists(agg_file):
        try:
            with open(agg_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    for dt_str, count in counts_by_date.items():
        existing.append({
            "data_source": source,
            "date": dt_str,
            "node_id": node_id,
            "zone_id": zone_id,
            "syndrome": syndrome,
            "count": count,
            "severity_mild": int(count * 0.6),
            "severity_moderate": int(count * 0.3),
            "severity_severe": int(count * 0.1),
            "growth_rate_7d": 0.0,
            "rolling_3d_mean": float(count),
            "rolling_7d_mean": float(count),
            "rolling_7d_std": 1.0,
            "coverage_ratio": 0.95,
            "privacy_k": 11,
            "data_quality_score": 0.90
        })

    with open(agg_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def test_node_zone_mapping_configuration():
    """Verifies that the deterministic node-to-zone configuration exists and maps all 4 institutions."""
    assert "inst-a" in NODE_ZONE_MAPPING
    assert "inst-b" in NODE_ZONE_MAPPING
    assert "inst-c" in NODE_ZONE_MAPPING
    assert "inst-d" in NODE_ZONE_MAPPING
    assert "zone-metro-1" in NODE_ZONE_MAPPING["inst-a"]
    assert "zone-metro-1" in NODE_ZONE_MAPPING["inst-b"]
    assert "zone-metro-1" in NODE_ZONE_MAPPING["inst-d"]


def test_distinct_node_rule_1_node_suppression_even_with_high_counts(temp_zone_manager):
    """
    CRITICAL PRIVACY TEST:
    100+ records from a single node in a zone must REMAIN SUPPRESSED because
    COUNT(DISTINCT node_id) == 1 (< 3 distinct nodes).
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Write 500 total counts from inst-a only
    helper_create_node_aggregates(
        manager=temp_zone_manager,
        node_id="inst-a",
        zone_id="zone-solo-1",
        syndrome="influenza_like_illness",
        source="community",
        counts_by_date={today_str: 500}
    )

    rollups = temp_zone_manager.query_zone_rollup(zone_id="zone-solo-1", days_lookback=7, min_distinct_nodes=3)
    assert len(rollups) == 0, "Zone with 1 distinct node must be strictly suppressed despite high count"


def test_distinct_node_rule_2_nodes_suppressed(temp_zone_manager):
    """Verifies that a zone with only 2 distinct contributing nodes is suppressed."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    helper_create_node_aggregates(temp_zone_manager, "inst-a", "zone-duo-1", "acute_watery_diarrhea", "clinic", {today_str: 50})
    helper_create_node_aggregates(temp_zone_manager, "inst-b", "zone-duo-1", "acute_watery_diarrhea", "clinic", {today_str: 40})

    rollups = temp_zone_manager.query_zone_rollup(zone_id="zone-duo-1", days_lookback=7, min_distinct_nodes=3)
    assert len(rollups) == 0, "Zone with 2 distinct nodes must be suppressed"


def test_distinct_node_rule_3_nodes_allowed(temp_zone_manager):
    """Verifies that a zone with 3 distinct contributing nodes is exposed with aggregate statistics."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    helper_create_node_aggregates(temp_zone_manager, "inst-a", "zone-metro-1", "influenza_like_illness", "community", {today_str: 80})
    helper_create_node_aggregates(temp_zone_manager, "inst-b", "zone-metro-1", "influenza_like_illness", "community", {today_str: 50})
    helper_create_node_aggregates(temp_zone_manager, "inst-d", "zone-metro-1", "influenza_like_illness", "community", {today_str: 40})

    rollups = temp_zone_manager.query_zone_rollup(zone_id="zone-metro-1", days_lookback=7, min_distinct_nodes=3)
    assert len(rollups) == 1
    res = rollups[0]
    assert res["zone_id"] == "zone-metro-1"
    assert res["syndrome"] == "influenza_like_illness"
    assert res["count"] == 170
    assert res["node_count"] == 3
    assert res["privacy_status"] == "APPROVED_3_PLUS_NODES"
    # Ensure no patient identifiers or unsuppressed raw data leakage
    assert "patient_name" not in res
    assert "individual_records" not in res


def test_distinct_node_rule_4_nodes_allowed(temp_zone_manager):
    """Verifies that a zone with 4 distinct contributing nodes is exposed."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    helper_create_node_aggregates(temp_zone_manager, "inst-a", "zone-regional-core", "acute_febrile_illness", "testing", {today_str: 45})
    helper_create_node_aggregates(temp_zone_manager, "inst-b", "zone-regional-core", "acute_febrile_illness", "testing", {today_str: 35})
    helper_create_node_aggregates(temp_zone_manager, "inst-c", "zone-regional-core", "acute_febrile_illness", "testing", {today_str: 20})
    helper_create_node_aggregates(temp_zone_manager, "inst-d", "zone-regional-core", "acute_febrile_illness", "testing", {today_str: 30})

    rollups = temp_zone_manager.query_zone_rollup(zone_id="zone-regional-core", days_lookback=7, min_distinct_nodes=3)
    assert len(rollups) == 1
    res = rollups[0]
    assert res["zone_id"] == "zone-regional-core"
    assert res["count"] == 130
    assert res["node_count"] == 4


def test_seven_day_growth_calculation_and_zero_division(temp_zone_manager):
    """
    Verifies 7-day growth rate calculation:
    - Previous 7-day total = 100, Current 7-day total = 125 -> +25.0%
    - Previous 7-day total = 0 -> growth = 0.0 without ZeroDivisionError
    """
    now = datetime.now(timezone.utc)
    # Current period (within last 3 days)
    t_curr = now.strftime("%Y-%m-%d")
    # Previous period (8-10 days ago)
    t_prev = (now - timedelta(days=10)).strftime("%Y-%m-%d")

    # 1. Standard +25% growth case: 100 previous vs 125 current across 3 nodes
    helper_create_node_aggregates(temp_zone_manager, "inst-a", "zone-metro-1", "respiratory", "clinic", {t_prev: 40, t_curr: 50})
    helper_create_node_aggregates(temp_zone_manager, "inst-b", "zone-metro-1", "respiratory", "clinic", {t_prev: 35, t_curr: 45})
    helper_create_node_aggregates(temp_zone_manager, "inst-d", "zone-metro-1", "respiratory", "clinic", {t_prev: 25, t_curr: 30})

    rollups = temp_zone_manager.query_zone_rollup(zone_id="zone-metro-1", syndrome="respiratory", days_lookback=14)
    assert len(rollups) == 1
    res = rollups[0]
    assert res["count"] == 225
    assert res["growth_7d"] == 25.0

    # 2. Zero-division safe case (previous period = 0)
    helper_create_node_aggregates(temp_zone_manager, "inst-a", "zone-metro-2", "respiratory", "clinic", {t_curr: 50})
    helper_create_node_aggregates(temp_zone_manager, "inst-b", "zone-metro-2", "respiratory", "clinic", {t_curr: 45})
    helper_create_node_aggregates(temp_zone_manager, "inst-d", "zone-metro-2", "respiratory", "clinic", {t_curr: 30})

    rollups_zero = temp_zone_manager.query_zone_rollup(zone_id="zone-metro-2", syndrome="respiratory", days_lookback=14)
    assert len(rollups_zero) == 1
    assert rollups_zero[0]["growth_7d"] == 0.0


def test_syndrome_and_source_coverage(temp_zone_manager):
    """Verifies that zone aggregation generically covers multiple syndromes and all 5 data sources."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    syndromes_to_test = [
        ("influenza_like_illness", "community"),
        ("acute_watery_diarrhea", "pharmacy"),
        ("febrile_arthritic", "doctor"),
        ("lower_respiratory_illness", "clinic"),
        ("viral_encephalitis_meningitis", "testing")
    ]

    for synd, src in syndromes_to_test:
        for nid in ["inst-a", "inst-b", "inst-d"]:
            helper_create_node_aggregates(temp_zone_manager, nid, "zone-metro-1", synd, src, {today_str: 30})

    for synd, src in syndromes_to_test:
        res = temp_zone_manager.query_zone_rollup(zone_id="zone-metro-1", syndrome=synd, data_source=src)
        assert len(res) >= 1
        assert res[0]["syndrome"] == synd
        assert res[0]["data_source"] == src
        assert res[0]["node_count"] == 3


def test_four_node_spatial_scenario_simulation(temp_zone_manager):
    """
    Tests 4 nodes contributing across heterogeneous zones:
    - zone-metro-1: inst-a, inst-b, inst-d (3 distinct nodes) -> VISIBLE
    - zone-rural-1: inst-c, inst-d (2 distinct nodes) -> SUPPRESSED
    - zone-rural-2: inst-c (1 distinct node) -> SUPPRESSED
    """
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # zone-metro-1 (3 nodes)
    helper_create_node_aggregates(temp_zone_manager, "inst-a", "zone-metro-1", "acute_febrile_illness", "community", {today_str: 70})
    helper_create_node_aggregates(temp_zone_manager, "inst-b", "zone-metro-1", "acute_febrile_illness", "community", {today_str: 40})
    helper_create_node_aggregates(temp_zone_manager, "inst-d", "zone-metro-1", "acute_febrile_illness", "community", {today_str: 35})

    # zone-rural-1 (2 nodes)
    helper_create_node_aggregates(temp_zone_manager, "inst-c", "zone-rural-1", "acute_febrile_illness", "community", {today_str: 25})
    helper_create_node_aggregates(temp_zone_manager, "inst-d", "zone-rural-1", "acute_febrile_illness", "community", {today_str: 20})

    # zone-rural-2 (1 node)
    helper_create_node_aggregates(temp_zone_manager, "inst-c", "zone-rural-2", "acute_febrile_illness", "community", {today_str: 30})

    # Query all zones
    all_rollups = temp_zone_manager.query_zone_rollup(syndrome="acute_febrile_illness", days_lookback=7)
    visible_zones = [r["zone_id"] for r in all_rollups]

    assert "zone-metro-1" in visible_zones, "zone-metro-1 (3 nodes) must be exposed"
    assert "zone-rural-1" not in visible_zones, "zone-rural-1 (2 nodes) must be strictly suppressed"
    assert "zone-rural-2" not in visible_zones, "zone-rural-2 (1 node) must be strictly suppressed"


def test_api_aggregate_zones_and_rollup_endpoints():
    """Verifies that API endpoints expose only privacy-approved aggregates."""
    resp1 = client.get("/api/v1/aggregate/zones")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "SUCCESS_PRIVACY_APPROVED_ZONES"
    for z in data1["zones"]:
        assert z["node_count"] >= 3
        assert z["privacy_status"] == "APPROVED_3_PLUS_NODES"

    resp2 = client.get("/api/v1/data-collection/zone-rollup")
    assert resp2.status_code == 200
    data2 = resp2.json()
    for z in data2["zone_rollups"]:
        assert z["node_count"] >= 3

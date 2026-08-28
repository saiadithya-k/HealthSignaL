import os
import pytest
from app.db.init_db import init_db
from app.data_generation.cli import generate_and_analyze
from app.data_generation.schemas import ScenarioType

@pytest.fixture(scope="session", autouse=True)
def setup_test_database_and_data():
    """Ensure database tables and initial synthetic data exist before running tests."""
    init_db()
    if not os.path.exists("data/inst-a/data.csv"):
        generate_and_analyze(output_dir="data", scenario=ScenarioType.NORMAL, seed=42, days=365)
    yield

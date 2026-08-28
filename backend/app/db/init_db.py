import os
from sqlalchemy import text
from app.db.database import engine, Base, SessionLocal
from app.db.models import Institution, ModelVersion
from app.data_generation.cli import generate_and_analyze
from app.data_generation.schemas import ScenarioType

def migrate_schema_if_needed():
    """Idempotently adds any missing columns to existing SQLite database tables."""
    with engine.connect() as conn:
        try:
            # Check forecasts table columns
            result = conn.execute(text("PRAGMA table_info(forecasts);"))
            columns = [row[1] for row in result.fetchall()]
            
            missing_cols = {
                "lower_bound_80": "FLOAT",
                "upper_bound_80": "FLOAT",
                "lower_bound_95": "FLOAT",
                "upper_bound_95": "FLOAT",
                "confidence_score": "FLOAT DEFAULT 1.0",
                "coverage_ratio": "FLOAT DEFAULT 1.0",
                "missing_node_count": "INTEGER DEFAULT 0"
            }
            
            for col_name, col_type in missing_cols.items():
                if col_name not in columns and len(columns) > 0:
                    conn.execute(text(f"ALTER TABLE forecasts ADD COLUMN {col_name} {col_type};"))
            
            conn.commit()
        except Exception:
            pass

def seed_institutions_and_models():
    """Idempotently seeds database metadata for the 4 institutions and initial model version."""
    db = SessionLocal()
    try:
        initial_nodes = [
            {"id": "inst-a", "name": "Institution A", "profile": "Urban (High Volume)"},
            {"id": "inst-b", "name": "Institution B", "profile": "Semi-urban (Moderate Volume)"},
            {"id": "inst-c", "name": "Institution C", "profile": "Rural (Low Volume, High Var)"},
            {"id": "inst-d", "name": "Institution D", "profile": "Mixed (Seasonal Shift)"},
        ]
        
        for node in initial_nodes:
            existing = db.query(Institution).filter(Institution.id == node["id"]).first()
            if not existing:
                db.add(Institution(
                    id=node["id"],
                    name=node["name"],
                    profile=node["profile"],
                    status="ACTIVE"
                ))
        
        existing_model = db.query(ModelVersion).filter(ModelVersion.version == "v1.0.0").first()
        if not existing_model:
            db.add(ModelVersion(
                version="v1.0.0",
                algorithm="Ridge Regression (FedAvg)",
                metrics={"initial_status": "initialized"}
            ))
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def ensure_default_datasets_exist(data_dir: str = "data"):
    """Idempotently checks if all 4 institution datasets exist; generates defaults if absent."""
    nodes = ["inst-a", "inst-b", "inst-c", "inst-d"]
    all_exist = all(os.path.exists(os.path.join(data_dir, node, "data.csv")) for node in nodes)
    
    if not all_exist:
        generate_and_analyze(output_dir=data_dir, scenario=ScenarioType.NORMAL, seed=42, days=365)

def init_db():
    """Full system startup initialization function."""
    Base.metadata.create_all(bind=engine)
    migrate_schema_if_needed()
    seed_institutions_and_models()
    ensure_default_datasets_exist()

if __name__ == "__main__":
    init_db()

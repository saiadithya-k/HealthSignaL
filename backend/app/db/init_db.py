import os
from app.db.database import engine, Base, SessionLocal
from app.db.models import Institution, ModelVersion
from app.data_generation.cli import generate_and_analyze
from app.data_generation.schemas import ScenarioType

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
    seed_institutions_and_models()
    ensure_default_datasets_exist()

if __name__ == "__main__":
    init_db()

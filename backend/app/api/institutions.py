from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Institution
from app.data_generation.schemas import ScenarioType
from app.data_generation.cli import generate_and_analyze, analyze_non_iid_properties
from app.core.local_node import LocalInstitutionClient

router = APIRouter()

@router.get("/status", tags=["Institutions"])
def get_institutions_status(db: Session = Depends(get_db)):
    """Returns safe aggregate metadata status for all 4 institutions."""
    inst_records = db.query(Institution).all()
    statuses = []

    for inst in inst_records:
        client = LocalInstitutionClient(inst.id, data_dir="data")
        try:
            summary = client.get_local_summary()
            dataset_ready = True
        except Exception:
            summary = None
            dataset_ready = False

        statuses.append({
            "id": inst.id,
            "name": inst.name,
            "profile": inst.profile,
            "status": inst.status,
            "dataset_ready": dataset_ready,
            "summary": summary
        })

    return {
        "institutions": statuses,
        "total_nodes": len(statuses)
    }

@router.post("/generate-data", tags=["Institutions"])
def generate_synthetic_datasets(
    scenario: ScenarioType = ScenarioType.NORMAL,
    seed: int = 42,
    days: int = 365,
    db: Session = Depends(get_db)
):
    """Triggers generation of non-IID datasets for Institutions A-D. Returns safe summary."""
    try:
        report = generate_and_analyze(output_dir="data", scenario=scenario, seed=seed, days=days)
        
        # Update PostgreSQL metadata database
        for inst_id in ["inst-a", "inst-b", "inst-c", "inst-d"]:
            inst = db.query(Institution).filter(Institution.id == inst_id).first()
            if inst:
                inst.status = "ACTIVE"
        db.commit()

        return {
            "status": "success",
            "message": f"Generated non-IID datasets for scenario '{scenario.value}' (seed={seed}, days={days})",
            "report": report
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/non-iid-summary", tags=["Institutions"])
def get_non_iid_summary():
    """Returns statistical non-IID analysis demonstrating distribution differences across institutions."""
    try:
        summary = analyze_non_iid_properties(data_dir="data")
        return summary
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Datasets not generated yet. Run /generate-data first.")

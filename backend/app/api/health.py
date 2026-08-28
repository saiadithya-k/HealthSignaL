from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from app.config import settings

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint verifying system and DB connection."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online" if db_status == "healthy" else "degraded",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status
    }

@router.get("/version", tags=["Health"])
def version_check():
    """Version metadata endpoint."""
    return {
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
        "min_group_size_default": settings.MIN_GROUP_SIZE,
        "forecast_horizon_default": settings.DEFAULT_FORECAST_HORIZON
    }

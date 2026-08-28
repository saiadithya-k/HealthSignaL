from fastapi import APIRouter
from app.api import health, institutions, models, federation, forecasts, alerts

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(institutions.router, prefix="/institutions")
api_router.include_router(models.router, prefix="/models")
api_router.include_router(federation.router, prefix="/federation")
api_router.include_router(forecasts.router, prefix="/forecasts")
api_router.include_router(alerts.router, prefix="/alerts")

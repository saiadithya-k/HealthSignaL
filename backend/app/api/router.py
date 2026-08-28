from fastapi import APIRouter
from app.api import health, institutions, models

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(institutions.router, prefix="/institutions")
api_router.include_router(models.router, prefix="/models")

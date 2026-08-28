from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.router import api_router
from app.db.init_db import init_db

description = """
### HealthSignal — Federated Community Health Trend Forecasting & Surge Detection API

HealthSignal is a decentralized, privacy-preserving federated forecasting and decision-support system for public health service demand.

#### Core Pillars:
1. **Decentralized Data Locality**: Row-level healthcare records remain strictly isolated inside local institution nodes (A, B, C, D).
2. **Pre-Transmission Privacy Gate (`FR-017`)**: Outbound updates are validated for zero raw patient records, zero patient IDs, bounded coefficients, and small-group suppression.
3. **Flower FedAvg Coordinator**: Aggregates local Ridge forecasting models to build a versioned global forecast model.
4. **7–14 Day Recursive Forecast Engine**: Multi-day forecasting with 80% and 95% residual-based prediction intervals.
5. **CUSUM Surge Detection & Reviewer Queue**: Statistical process control flags candidate surges for human analyst approval or rejection.

> **Disclaimer:** *Forecasts and alerts represent aggregate public-health service-demand indicators with statistical uncertainty bounds. System outputs do NOT represent medical predictions, clinical diagnoses, or individual patient risk factors.*
"""

tags_metadata = [
    {"name": "Health", "description": "System operational health status and version verification."},
    {"name": "Institutions", "description": "Decentralized local institution node status, data summaries, and Non-IID proofs."},
    {"name": "Models", "description": "Baseline forecasting model comparison (Naive, Local Ridge, Pooled Upper Bound)."},
    {"name": "Federation", "description": "Flower FedAvg federated training coordinator and round status."},
    {"name": "Forecasts", "description": "7–14 day recursive multi-day forecast generation and prediction intervals."},
    {"name": "Alerts", "description": "CUSUM surge detection trigger, candidate alerts queue, and reviewer actions (Approve/Reject)."}
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent DB initialization on startup
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=description,
    openapi_tags=tags_metadata,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Health"])
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "version": settings.VERSION
    }

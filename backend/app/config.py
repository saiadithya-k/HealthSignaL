import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "HealthSignal — Federated Community Health Trend Forecasting"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database Settings
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "healthsignal")
    
    # Computed Database URL (defaults to SQLite if postgres not running locally)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./healthsignal.db"
    )

    # Privacy & Forecasting Defaults
    MIN_GROUP_SIZE: int = int(os.getenv("MIN_GROUP_SIZE", "11"))
    DEFAULT_FORECAST_HORIZON: int = int(os.getenv("DEFAULT_FORECAST_HORIZON", "7"))
    RANDOM_SEED: int = int(os.getenv("RANDOM_SEED", "42"))

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()

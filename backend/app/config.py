from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "OpenSpotter"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "change-me-in-production-use-long-random-string"

    # Database (use SQLite for local dev, PostgreSQL for production)
    database_url: str = "sqlite+aiosqlite:///./openspotter.db"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Email (optional, for verification emails)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "noreply@openspotter.local"

    # S3-compatible storage (optional, for media uploads)
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_bucket: str = "openspotter-media"
    s3_region: str = "us-east-1"

    # Location settings
    location_history_ttl_hours: int = 24
    location_update_interval_seconds: int = 10

    # Rate limiting
    api_rate_limit: int = 100  # requests per minute

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()

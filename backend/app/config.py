"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# Human: Central settings model; override defaults via env vars or `.env` (see `.env.example`).
# Agent: READS env vars and `.env`; env vars: DATABASE_URL, JWT_*, ADMIN_*, USGS_*; failure modes: missing required secrets in prod.
class Settings(BaseSettings):
    """Runtime settings for API and sync worker."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database and auth ---
    database_url: str = "mysql+pymysql://earthquake:earthquake_secret@localhost:3306/earthquake"
    jwt_secret: str = "change-me"
    jwt_expire_hours: int = 8
    jwt_algorithm: str = "HS256"
    admin_username: str = "admin"
    admin_password_hash: str = ""
    admin_password: str = "admin"

    # --- USGS sync worker ---
    usgs_backfill_start: str = "2010-01-01"
    usgs_sync_interval_minutes: int = 15
    usgs_request_timeout_seconds: int = 60
    usgs_base_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"


# Human: Cached singleton so settings are parsed once per process.
# Agent: READS Settings from env; RETURNS cached Settings; CALLS lru_cache; failure modes: stale cache if env changes at runtime.
@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()

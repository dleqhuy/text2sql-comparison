"""Settings for the local dashboard; no account or JWT configuration."""

from pathlib import Path

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    FRONTEND_HOST: str = "http://127.0.0.1:5173"
    PROJECT_NAME: str = "SQL / Lab"
    DATABASE_URL: PostgresDsn

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: str | PostgresDsn) -> str:
        url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if url.startswith(scheme):
                return url.replace(scheme, "postgresql+psycopg://", 1)
        return url


settings = Settings()

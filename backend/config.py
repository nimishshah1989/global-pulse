"""Application configuration using pydantic-settings.

Loads settings from environment variables and .env file.
Fails loudly on missing required variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Default to SQLite for development; production uses PostgreSQL via env var
    DATABASE_URL: str = "sqlite+aiosqlite:///./momentum_compass.db"

    # Optional with defaults
    REDIS_URL: str = "redis://localhost:6379"
    STOOQ_BASE_URL: str = "https://stooq.com/q/d/l/"
    DATA_REFRESH_HOUR: int = 2
    APP_ENV: str = "development"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.APP_ENV == "production"


def get_settings() -> Settings:
    """Create and return application settings.

    Raises:
        ValidationError: If required environment variables are missing.
    """
    return Settings()  # type: ignore[call-arg]

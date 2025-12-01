"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mylar3 settings
    mylar_url: str = "http://localhost:8090"
    mylar_api_key: str = ""

    # Komga settings
    komga_url: str = "http://localhost:25600"
    komga_username: str = ""
    komga_password: str = ""
    komga_api_key: str = ""

    # App settings
    database_url: str = "sqlite+aiosqlite:///./data/pulllist.db"
    secret_key: str = "change-this-to-a-random-string"

    # Schedule settings
    schedule_day_of_week: str = "wed"
    schedule_hour: int = 10
    schedule_minute: int = 0
    timezone: str = "America/New_York"

    @property
    def komga_auth(self) -> tuple[str, str] | None:
        """Return Komga basic auth tuple if credentials are set."""
        if self.komga_username and self.komga_password:
            return (self.komga_username, self.komga_password)
        return None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

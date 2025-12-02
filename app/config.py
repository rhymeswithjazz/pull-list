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
    app_url: str = "http://localhost:8282"

    # JWT settings
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    magic_link_expire_minutes: int = 15

    # SMTP settings (for magic link emails)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    # Schedule settings
    # Default: daily at 10:00 AM to catch new comics throughout the week
    # Notifications are only sent once per week when issues first appear
    schedule_day_of_week: str = "*"  # "*" = daily, "wed" = Wednesday only
    schedule_hour: int = 10
    schedule_minute: int = 0
    timezone: str = "America/New_York"

    # Notification settings
    notification_email: str = ""  # Email to send pull-list notifications to

    @property
    def komga_auth(self) -> tuple[str, str] | None:
        """Return Komga basic auth tuple if credentials are set."""
        if self.komga_username and self.komga_password:
            return (self.komga_username, self.komga_password)
        return None

    @property
    def smtp_configured(self) -> bool:
        """Return True if SMTP is configured for magic link emails."""
        return bool(self.smtp_host and self.smtp_from_email)

    @property
    def notifications_enabled(self) -> bool:
        """Return True if pull-list notifications are enabled."""
        return self.smtp_configured and bool(self.notification_email)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

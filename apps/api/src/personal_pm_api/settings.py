"""Typed application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Process-level settings. Product domain configuration lives in Planning Core."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"
    database_url: str = Field(
        default=(
            "postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm"
        ),
        validation_alias="DATABASE_URL",
    )

    def model_post_init(self, __context: object) -> None:
        # Invariant: the local-only default credential must never reach
        # a non-local environment.
        if self.environment not in ("local", "test") and (
            "local_only_password" in self.database_url or "localhost" in self.database_url
        ):
            raise ValueError(
                f"environment={self.environment!r} requires a real DATABASE_URL; "
                "the local default is forbidden outside local/test"
            )

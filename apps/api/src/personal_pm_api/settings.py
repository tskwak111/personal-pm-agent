"""Typed application settings loaded from environment variables."""

import base64

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Process-level settings. Product domain configuration lives in Planning Core."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    environment: str = "local"
    log_level: str = "INFO"
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = Field(default=None, repr=False)
    google_oauth_redirect_uri: str = "http://localhost:8000/api/v1/calendar/oauth/callback"
    google_oauth_authorize_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_oauth_token_url: str = "https://oauth2.googleapis.com/token"
    token_encryption_key: SecretStr | None = Field(default=None, repr=False)
    database_url: str = Field(
        default=(
            "postgresql+asyncpg://personal_pm:local_only_password@localhost:15432/personal_pm"
        ),
        validation_alias="DATABASE_URL",
    )

    @field_validator("token_encryption_key")
    @classmethod
    def _valid_token_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        try:
            key = base64.b64decode(
                value.get_secret_value().encode("ascii"),
                altchars=b"-_",
                validate=True,
            )
        except (ValueError, UnicodeError) as error:
            raise ValueError("token_encryption_key must be URL-safe base64") from error
        if len(key) != 32:
            raise ValueError("token_encryption_key must decode to 32 bytes")
        return value

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
        if self.environment not in ("local", "test") and self.google_oauth_client_id:
            oauth_urls = (
                self.google_oauth_redirect_uri,
                self.google_oauth_authorize_url,
                self.google_oauth_token_url,
            )
            if not all(url.startswith("https://") for url in oauth_urls):
                raise ValueError("production OAuth URLs must use HTTPS")

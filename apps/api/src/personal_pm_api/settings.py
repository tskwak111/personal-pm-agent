"""Typed application settings loaded from environment variables."""

import base64

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Process-level settings. Product domain configuration lives in Planning Core."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    environment: str = "local"
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    google_oauth_client_id: str | None = Field(
        default=None, validation_alias="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: SecretStr | None = Field(
        default=None,
        validation_alias="GOOGLE_OAUTH_CLIENT_SECRET",
        repr=False,
    )
    google_oauth_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/calendar/oauth/callback",
        validation_alias="GOOGLE_OAUTH_REDIRECT_URI",
    )
    google_oauth_authorize_url: str = Field(
        default="https://accounts.google.com/o/oauth2/v2/auth",
        validation_alias="GOOGLE_OAUTH_AUTHORIZE_URL",
    )
    google_oauth_token_url: str = Field(
        default="https://oauth2.googleapis.com/token",
        validation_alias="GOOGLE_OAUTH_TOKEN_URL",
    )
    token_encryption_key: SecretStr | None = Field(
        default=None,
        validation_alias="TOKEN_VAULT_KEY",
        repr=False,
    )
    operator_metrics_token: SecretStr | None = Field(
        default=None,
        validation_alias="OPERATOR_METRICS_TOKEN",
        repr=False,
    )
    s3_endpoint: str = Field(
        default="http://localhost:9000",
        validation_alias="S3_ENDPOINT",
    )
    s3_region: str = Field(default="us-east-1", validation_alias="S3_REGION")
    s3_bucket: str = Field(default="personal-pm-local", validation_alias="S3_BUCKET")
    s3_access_key_id: str = Field(
        default="personal_pm",
        validation_alias="S3_ACCESS_KEY_ID",
    )
    s3_secret_access_key: SecretStr = Field(
        default=SecretStr("local_only_password"),
        validation_alias="S3_SECRET_ACCESS_KEY",
        repr=False,
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
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
        if self.environment not in ("local", "test") and (
            not self.s3_endpoint.startswith("https://")
            or self.s3_access_key_id == "personal_pm"
            or "local_only_password" in self.s3_secret_access_key.get_secret_value()
        ):
            raise ValueError("production object storage requires HTTPS and non-local credentials")
        if self.environment not in ("local", "test") and "localhost" in self.redis_url:
            raise ValueError("production rate limiting requires a non-local REDIS_URL")

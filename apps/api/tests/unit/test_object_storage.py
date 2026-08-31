from __future__ import annotations

import base64
from io import BytesIO

import pytest
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from personal_pm_api.storage import S3ObjectStorage


class _Client:
    def __init__(self, *, bucket_exists: bool = False) -> None:
        self.bucket_exists = bucket_exists
        self.created = False
        self.objects: dict[str, bytes] = {}

    def head_bucket(self, *, Bucket: str) -> None:  # noqa: N803
        if not self.bucket_exists:
            raise ClientError({"Error": {"Code": "404"}}, "HeadBucket")

    def create_bucket(self, **_: object) -> None:
        self.bucket_exists = True
        self.created = True

    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:  # noqa: N803
        self.objects[Key] = Body

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, BytesIO]:  # noqa: N803
        return {"Body": BytesIO(self.objects[Key])}

    def delete_object(self, *, Bucket: str, Key: str) -> None:  # noqa: N803
        self.objects.pop(Key, None)


async def test_local_s3_storage_creates_bucket_and_round_trips_bytes() -> None:
    client = _Client()
    storage = S3ObjectStorage(
        client,
        "sources",
        allow_bucket_creation=True,
        region="us-east-1",
    )

    await storage.put("workspaces/one/source.pdf", b"raw source")

    assert client.created is True
    assert await storage.get("workspaces/one/source.pdf") == b"raw source"


async def test_production_s3_storage_does_not_create_missing_bucket() -> None:
    client = _Client()
    storage = S3ObjectStorage(
        client,
        "sources",
        allow_bucket_creation=False,
        region="us-east-1",
    )

    with pytest.raises(RuntimeError, match="bucket is missing"):
        await storage.put("source.pdf", b"raw source")

    assert client.created is False


def test_settings_load_documented_provider_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from personal_pm_api.settings import ApiSettings

    token_key = base64.urlsafe_b64encode(b"k" * 32).decode()
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setenv("TOKEN_VAULT_KEY", token_key)

    settings = ApiSettings()

    assert settings.log_level == "DEBUG"
    assert settings.google_oauth_client_id == "client-id"
    assert settings.google_oauth_client_secret is not None
    assert settings.google_oauth_client_secret.get_secret_value() == "client-secret"
    assert settings.google_oauth_redirect_uri == "http://localhost/callback"
    assert settings.token_encryption_key is not None
    assert settings.token_encryption_key.get_secret_value() == token_key

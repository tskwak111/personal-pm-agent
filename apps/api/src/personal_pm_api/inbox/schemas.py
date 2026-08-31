"""Inbox DTOs and upload validation rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from personal_pm_api.security.uploads import (
    MAX_UPLOAD_BYTES,
    SUPPORTED_UPLOAD_TYPES,
)

ALLOWED_SOURCE_TYPES = SUPPORTED_UPLOAD_TYPES
MAX_SOURCE_BYTES = MAX_UPLOAD_BYTES


class UploadInitiationRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(gt=0)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)


class UploadInitiationResponse(BaseModel):
    id: str
    storage_key: str
    status: str
    upload_url: str | None = None


def validate_source_upload(content_type: str, size_bytes: int) -> None:
    """Raise typed domain errors for disallowed or oversized uploads."""
    from personal_pm_api.shared.errors import DomainRuleError

    if content_type not in ALLOWED_SOURCE_TYPES:
        raise DomainRuleError("UNSUPPORTED_SOURCE_TYPE", f"unsupported type {content_type}")
    if size_bytes <= 0 or size_bytes > MAX_SOURCE_BYTES:
        raise DomainRuleError("SOURCE_TOO_LARGE", f"size {size_bytes} exceeds limit")


def validate_source_filename(filename: str) -> None:
    from personal_pm_api.shared.errors import DomainRuleError

    if (
        filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or any(ord(character) < 32 for character in filename)
    ):
        raise DomainRuleError("INVALID_SOURCE_FILENAME", "filename must be a single safe segment")

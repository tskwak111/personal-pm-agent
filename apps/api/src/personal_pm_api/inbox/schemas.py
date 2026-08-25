"""Inbox DTOs and upload validation rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

ALLOWED_SOURCE_TYPES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)
MAX_SOURCE_BYTES = 25 * 1024 * 1024


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

"""Structured logging with sensitive-field redaction.

Sensitive values never reach log output; workspace identifiers are
hashed before emission.
"""

from __future__ import annotations

import hashlib
from typing import Any

SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "code",
        "cookie",
        "oauth_token",
        "refresh_token",
        "document_text",
        "file_content",
        "prompt_text",
        "personal_note",
        "calendar_description",
    }
)
REDACTED = "[REDACTED]"


def hash_workspace_id(workspace_id: str) -> str:
    return hashlib.sha256(workspace_id.encode("utf-8")).hexdigest()


class StructuredLogger:
    def __init__(self) -> None:
        self._bindings: dict[str, Any] = {}

    def bind(self, **fields: Any) -> StructuredLogger:
        merged = {**self._bindings, **fields}
        child = StructuredLogger()
        child._bindings = merged
        return self._sanitize_into(child)

    @staticmethod
    def _sanitize_into(logger: StructuredLogger) -> StructuredLogger:
        sanitized: dict[str, Any] = {}
        for key, value in logger._bindings.items():
            if key.casefold() in SENSITIVE_KEYS:
                sanitized[key] = REDACTED
            elif key == "workspace_id" and value is not None:
                sanitized["workspace_hash"] = hash_workspace_id(str(value))
            else:
                sanitized[key] = value
        logger._bindings = sanitized
        return logger

    def capture(self, message: str) -> dict[str, Any]:
        return {"message": message, **self._bindings}


__all__ = ["SENSITIVE_KEYS", "StructuredLogger", "hash_workspace_id"]

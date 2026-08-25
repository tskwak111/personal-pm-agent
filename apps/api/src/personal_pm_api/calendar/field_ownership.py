"""Field ownership matrix for calendar event reconciliation."""

from __future__ import annotations

FIELD_OWNER = {
    "external_title": "PROVIDER",
    "start_at": "LAST_EXPLICIT_USER_ACTION",
    "end_at": "LAST_EXPLICIT_USER_ACTION",
    "task_id": "PLANNING_CORE",
    "managed_marker": "PLANNING_CORE",
    "provider_version": "PROVIDER",
}


def field_owner(field: str) -> str:
    owner = FIELD_OWNER.get(field)
    if owner is None:
        raise KeyError(f"unknown field: {field}")
    return owner


__all__ = ["FIELD_OWNER", "field_owner"]

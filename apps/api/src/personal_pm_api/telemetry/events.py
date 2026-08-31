"""Privacy-safe telemetry event schemas.

Sensitive content (document text, tokens, prompts, personal notes,
calendar descriptions) can never enter a telemetry payload: construction
is rejected at the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from personal_pm_api.telemetry.logging import SENSITIVE_KEYS

SCHEMA_VERSION = 1

SENSITIVE_FIELD_NAMES = SENSITIVE_KEYS


class SensitiveTelemetryFieldError(Exception):
    def __init__(self, fields: frozenset[str] | set[str]) -> None:
        super().__init__(f"sensitive fields rejected from telemetry: {sorted(fields)}")


def validate_no_sensitive_fields(payload: dict[str, Any]) -> None:
    found = SENSITIVE_FIELD_NAMES & set(payload.keys())
    if found:
        raise SensitiveTelemetryFieldError(found)


@dataclass(frozen=True, slots=True)
class PlannerRunEvent:
    schema_version: int
    trace_id: str
    workspace_hash: str
    code_version: str
    planner_version: str
    input_size: int
    latency_ms: int
    result: str


@dataclass(frozen=True, slots=True)
class ExternalExecutionEvent:
    schema_version: int
    trace_id: str
    workspace_hash: str
    code_version: str
    command_type: str
    outcome: str
    attempts: int


@dataclass(frozen=True, slots=True)
class UxEvent:
    schema_version: int
    trace_id: str
    workspace_hash: str
    code_version: str
    name: str
    duration_ms: int


__all__ = [
    "ExternalExecutionEvent",
    "PlannerRunEvent",
    "SENSITIVE_FIELD_NAMES",
    "SCHEMA_VERSION",
    "SensitiveTelemetryFieldError",
    "UxEvent",
    "validate_no_sensitive_fields",
]

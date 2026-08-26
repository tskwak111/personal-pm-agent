"""Telemetry event factory: validates payloads before emission."""

from __future__ import annotations

from typing import Any

from personal_pm_api.telemetry.events import (
    ExternalExecutionEvent,
    PlannerRunEvent,
    UxEvent,
    validate_no_sensitive_fields,
)


class TelemetryEmitter:
    def __init__(self, code_version: str) -> None:
        self.code_version = code_version

    def planner_run(
        self,
        *,
        trace_id: str,
        workspace_hash: str,
        planner_version: str,
        input_size: int,
        latency_ms: int,
        result: str | dict[str, Any],
    ) -> PlannerRunEvent:
        validate_no_sensitive_fields(
            {
                "trace_id": trace_id,
                "workspace_hash": workspace_hash,
                "planner_version": planner_version,
            }
        )
        if isinstance(result, dict):
            # Structured result payloads are screened like any other source.
            validate_no_sensitive_fields({k: None for k in result.keys() if isinstance(k, str)})
            outcome = ",".join(sorted(str(k) for k in result.keys()))
        else:
            outcome = str(result)
        return PlannerRunEvent(
            schema_version=1,
            trace_id=trace_id,
            workspace_hash=workspace_hash,
            code_version=self.code_version,
            planner_version=planner_version,
            input_size=input_size,
            latency_ms=latency_ms,
            result=outcome,
        )

    def external_execution(
        self,
        *,
        trace_id: str,
        workspace_hash: str,
        command_type: str,
        outcome: str,
        attempts: int,
    ) -> ExternalExecutionEvent:
        return ExternalExecutionEvent(
            schema_version=1,
            trace_id=trace_id,
            workspace_hash=workspace_hash,
            code_version=self.code_version,
            command_type=command_type,
            outcome=outcome,
            attempts=attempts,
        )

    def ux_event(
        self,
        *,
        trace_id: str,
        workspace_hash: str,
        name: str,
        duration_ms: int,
    ) -> UxEvent:
        return UxEvent(
            schema_version=1,
            trace_id=trace_id,
            workspace_hash=workspace_hash,
            code_version=self.code_version,
            name=name,
            duration_ms=duration_ms,
        )


__all__ = ["TelemetryEmitter"]

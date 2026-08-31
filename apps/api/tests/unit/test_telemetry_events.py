from __future__ import annotations

import pytest
from personal_pm_api.telemetry.emitter import TelemetryEmitter
from personal_pm_api.telemetry.events import (
    SensitiveTelemetryFieldError,
    validate_no_sensitive_fields,
)


@pytest.mark.parametrize(
    "field",
    (
        "authorization",
        "calendar_description",
        "code",
        "cookie",
        "document_text",
        "file_content",
        "oauth_token",
        "personal_note",
        "prompt_text",
        "refresh_token",
    ),
)
def test_event_schema_rejects_sensitive_fields(field: str) -> None:
    with pytest.raises(SensitiveTelemetryFieldError):
        validate_no_sensitive_fields({"trace_id": "t", "workspace_hash": "w", field: "secret"})


def test_metric_events_include_version_dimensions() -> None:
    emitter = TelemetryEmitter(code_version="test-1")
    event = emitter.planner_run(
        trace_id="t",
        workspace_hash="w",
        planner_version="planner-spec-1.0",
        input_size=10,
        latency_ms=5,
        result="OK",
    )
    assert event.planner_version == "planner-spec-1.0"
    assert event.code_version == "test-1"
    assert event.schema_version == 1


def test_external_and_ux_events_are_supported() -> None:
    emitter = TelemetryEmitter(code_version="test-1")
    ext = emitter.external_execution(
        trace_id="t",
        workspace_hash="w",
        command_type="CREATE_FOCUS_BLOCK",
        outcome="SUCCEEDED",
        attempts=1,
    )
    assert ext.outcome == "SUCCEEDED"
    ux = emitter.ux_event(trace_id="t", workspace_hash="w", name="task_started", duration_ms=120)
    assert ux.duration_ms == 120


def test_emitter_rejects_sensitive_payloads() -> None:
    emitter = TelemetryEmitter(code_version="test-1")
    with pytest.raises(SensitiveTelemetryFieldError):
        emitter.planner_run(  # type: ignore[arg-type]
            trace_id="t",
            workspace_hash="w",
            planner_version="v",
            input_size=1,
            latency_ms=1,
            result={"prompt_text": "leak"},  # type: ignore[arg-type]
        )

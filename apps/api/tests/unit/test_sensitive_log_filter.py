from __future__ import annotations

import pytest
from personal_pm_api.telemetry.logging import StructuredLogger


@pytest.fixture
def structured_logger() -> StructuredLogger:
    return StructuredLogger()


def test_sensitive_values_are_redacted(structured_logger: StructuredLogger) -> None:
    event = structured_logger.bind(
        oauth_token="secret", document_text="private", trace_id="t"
    ).capture("test")
    assert event["oauth_token"] == "[REDACTED]"
    assert event["document_text"] == "[REDACTED]"


def test_workspace_identifier_is_hashed(structured_logger: StructuredLogger) -> None:
    event = structured_logger.bind(workspace_id="00000000-0000-0000-0000-000000000001").capture(
        "test"
    )
    assert event.get("workspace_hash") != "00000000-0000-0000-0000-000000000001"
    assert len(str(event.get("workspace_hash"))) == 64


def test_trace_id_passes_through(structured_logger: StructuredLogger) -> None:
    event = structured_logger.bind(trace_id="trace-42").capture("test")
    assert event["trace_id"] == "trace-42"


def test_trace_propagation_context(structured_logger: StructuredLogger) -> None:
    from personal_pm_api.telemetry.tracing import TraceContext

    ctx = TraceContext.new()
    child = ctx.child_span("planner.run")
    assert child.trace_id == ctx.trace_id
    assert child.span_id != ctx.span_id

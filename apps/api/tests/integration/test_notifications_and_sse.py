from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest_asyncio


@pytest_asyncio.fixture
async def notif_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from personal_pm_api.notifications.policy import (
        DeliveryMode,
        NotificationIntent,
        NotificationSeverity,
    )
    from personal_pm_api.notifications.service import NotificationService

    class Settings:
        quiet_start = 22
        quiet_end = 8

        def is_quiet(self, now: datetime) -> bool:
            hour = now.hour
            return hour >= self.quiet_start or hour < self.quiet_end

    ids: dict[str, Any] = {
        "service": NotificationService(),
        "settings": Settings(),
        "DeliveryMode": DeliveryMode,
        "NotificationSeverity": NotificationSeverity,
    }

    def make_intent(severity: Any = None) -> NotificationIntent:
        return NotificationIntent(
            dedupe_key=f"risk-{uuid4().hex[:8]}",
            severity=severity or NotificationSeverity.ACTIONABLE,
            title="마감 임박",
            body="2시간 남은 작업이 있습니다",
        )

    ids["make_intent"] = make_intent
    yield ids


async def test_same_risk_is_deduplicated(notif_env: dict[str, Any]) -> None:
    service: Any = notif_env["service"]
    intent = notif_env["make_intent"]()
    first = await service.enqueue(intent)
    second = await service.enqueue(intent)
    assert second.id == first.id
    assert await service.pending_count(intent.dedupe_key) == 1


async def test_quiet_hours_defer_non_critical(notif_env: dict[str, Any]) -> None:
    DeliveryMode = notif_env["DeliveryMode"]
    Severity = notif_env["NotificationSeverity"]
    settings = notif_env["settings"]
    from personal_pm_api.notifications.policy import delivery_mode

    night = datetime(2026, 9, 1, 23, 0, tzinfo=UTC)
    intent = notif_env["make_intent"](severity=Severity.SUMMARY)
    assert delivery_mode(intent, settings, night) == DeliveryMode.NEXT_SUMMARY


async def test_critical_bypasses_quiet_hours(notif_env: dict[str, Any]) -> None:
    DeliveryMode = notif_env["DeliveryMode"]
    Severity = notif_env["NotificationSeverity"]
    settings = notif_env["settings"]
    from personal_pm_api.notifications.policy import delivery_mode

    night = datetime(2026, 9, 1, 23, 0, tzinfo=UTC)
    intent = notif_env["make_intent"](severity=Severity.CRITICAL)
    assert delivery_mode(intent, settings, night) == DeliveryMode.IMMEDIATE


async def test_silent_is_record_only(notif_env: dict[str, Any]) -> None:
    DeliveryMode = notif_env["DeliveryMode"]
    Severity = notif_env["NotificationSeverity"]
    settings = notif_env["settings"]
    from personal_pm_api.notifications.policy import delivery_mode

    day = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    intent = notif_env["make_intent"](severity=Severity.SILENT)
    assert delivery_mode(intent, settings, day) == DeliveryMode.RECORD_ONLY


def test_sse_frame_has_stable_public_fields() -> None:
    """SSE frames carry stable sequence IDs and typed public fields only."""
    from personal_pm_api.agent.operations import StepEventView
    from personal_pm_api.agent.router import _encode_event

    frame = _encode_event(StepEventView(step="OBSERVE", status="SUCCEEDED", sequence=3))
    assert frame == (
        "id: 3\nevent: operation.step\ndata: "
        '{"step":"OBSERVE","status":"SUCCEEDED","sequence":3}\n\n'
    )

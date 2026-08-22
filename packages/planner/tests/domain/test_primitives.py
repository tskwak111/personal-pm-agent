from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from personal_pm_planner.domain.enums import DeadlineType, TaskStatus
from personal_pm_planner.domain.identifiers import WorkspaceId
from personal_pm_planner.domain.time import require_aware_utc


def test_identifiers_are_typed_uuid_values() -> None:
    raw = UUID("00000000-0000-0000-0000-000000000001")
    assert WorkspaceId(raw).value == raw


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        require_aware_utc(datetime(2026, 8, 23, 12, 0))


def test_aware_datetime_is_normalized_to_utc() -> None:
    value = datetime(2026, 8, 23, 21, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    normalized = require_aware_utc(value)
    assert normalized.utcoffset() == UTC.utcoffset(None)
    assert (normalized.hour, normalized.minute) == (12, 0)


def test_task_status_enum_is_canonical() -> None:
    expected = {
        "draft",
        "planned",
        "ready",
        "in_progress",
        "waiting",
        "blocked",
        "done",
        "deferred",
        "cancelled",
    }
    assert {status.value for status in TaskStatus} == expected


def test_deadline_types_are_canonical() -> None:
    expected = {"hard_deadline", "external_commitment", "internal_target", "soft_goal"}
    assert {deadline_type.value for deadline_type in DeadlineType} == expected

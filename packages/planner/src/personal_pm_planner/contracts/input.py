"""Frozen Planner input contract with canonical serialization.

The planner receives everything explicitly: it never reads wall-clock time,
global random state or locale settings. Canonical bytes are order-independent
so identical inputs produce identical hashes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from personal_pm_planner.domain.availability import (
    AvailabilityWindow,
    CalendarEventSnapshot,
    ExternalDependencySnapshot,
)
from personal_pm_planner.domain.dependency import TaskDependency
from personal_pm_planner.domain.identifiers import TaskId
from personal_pm_planner.domain.task import TaskSnapshot
from personal_pm_planner.domain.time import require_aware_utc
from personal_pm_planner.domain.work import MilestoneSnapshot


@dataclass(frozen=True, slots=True)
class PlannerInput:
    """Canonical snapshot handed to :func:`personal_pm_planner.plan`."""

    planner_version: str
    now_utc: datetime
    user_timezone: str
    horizon_end_utc: datetime
    slot_minutes: int
    availability_windows: tuple[AvailabilityWindow, ...]
    calendar_events: tuple[CalendarEventSnapshot, ...]
    tasks: tuple[TaskSnapshot, ...]
    milestones: tuple[MilestoneSnapshot, ...]
    task_dependencies: tuple[TaskDependency, ...]
    external_dependencies: tuple[ExternalDependencySnapshot, ...]
    pinned_task_ids: frozenset[TaskId]
    excluded_dates: tuple[date, ...]

    def __post_init__(self) -> None:
        if not self.planner_version.strip():
            raise ValueError("planner_version must not be empty")
        require_aware_utc(self.now_utc)
        require_aware_utc(self.horizon_end_utc)
        if self.horizon_end_utc <= self.now_utc:
            raise ValueError("horizon must end after now")
        if self.slot_minutes <= 0:
            raise ValueError("slot_minutes must be positive")
        if not self.user_timezone.strip():
            raise ValueError("user_timezone must not be empty")
        try:
            ZoneInfo(self.user_timezone)
        except Exception as error:
            raise ValueError("user_timezone must be a valid IANA name") from error

        workspaces = {
            entity.workspace_id
            for collection in (
                self.tasks,
                self.milestones,
                self.calendar_events,
                self.external_dependencies,
            )
            for entity in collection
        }
        if len(workspaces) > 1:
            raise ValueError("all input entities must belong to one workspace")

        known_task_ids = {task.id for task in self.tasks}
        unknown = [
            endpoint
            for item in self.task_dependencies
            for endpoint in (item.predecessor_id, item.successor_id)
            if endpoint not in known_task_ids
        ]
        if unknown:
            raise ValueError("task dependencies reference unknown tasks")
        orphan_affected = [
            task_id
            for item in self.external_dependencies
            for task_id in item.affected_task_ids
            if task_id not in known_task_ids
        ]
        if orphan_affected:
            raise ValueError("external dependencies affect unknown tasks")


_SORTED_COLLECTIONS = frozenset(
    {
        "availability_windows",
        "calendar_events",
        "tasks",
        "milestones",
        "task_dependencies",
        "external_dependencies",
        "excluded_dates",
    }
)


def _convert_planner_input(value: PlannerInput) -> dict[str, Any]:
    from dataclasses import fields as dataclass_fields

    payload: dict[str, Any] = {}
    for field in dataclass_fields(value):
        item = getattr(value, field.name)
        if field.name in _SORTED_COLLECTIONS:
            converted = [_convert(entity) for entity in item]
            converted.sort(key=_sort_key)
            payload[field.name] = converted
        else:
            payload[field.name] = _convert(item)
    return payload


def _convert(value: Any) -> Any:  # noqa: ANN401 - canonicalization boundary
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return require_aware_utc(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, PlannerInput):
        return _convert_planner_input(value)
    if isinstance(value, (frozenset, set)):
        converted = (_convert(item) for item in value)
        return sorted(converted, key=_sort_key)
    if isinstance(value, (tuple, list)):
        return [_convert(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _convert(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _convert(item) for key, item in asdict(value).items()}
    return value


def _sort_key(item: Any) -> str:  # noqa: ANN401
    return json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_input_bytes(value: PlannerInput) -> bytes:
    payload = _convert(value)
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def input_hash(value: PlannerInput) -> str:
    return hashlib.sha256(canonical_input_bytes(value)).hexdigest()


__all__ = [
    "PlannerInput",
    "canonical_input_bytes",
    "input_hash",
]

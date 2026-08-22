"""Canonical typed identifiers scoped to a workspace."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, order=True)
class WorkspaceId:
    value: UUID


@dataclass(frozen=True, slots=True, order=True)
class AreaId:
    value: UUID


@dataclass(frozen=True, slots=True, order=True)
class WorkstreamId:
    value: UUID


@dataclass(frozen=True, slots=True, order=True)
class MilestoneId:
    value: UUID


@dataclass(frozen=True, slots=True, order=True)
class TaskId:
    value: UUID


@dataclass(frozen=True, slots=True, order=True)
class CalendarEventId:
    value: UUID


@dataclass(frozen=True, slots=True, order=True)
class ExternalDependencyId:
    value: UUID

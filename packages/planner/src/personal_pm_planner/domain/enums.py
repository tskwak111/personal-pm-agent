"""Canonical enums shared by Planning Core domain snapshots."""

from enum import StrEnum


class TaskStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    BLOCKED = "blocked"
    DONE = "done"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class DeadlineType(StrEnum):
    HARD_DEADLINE = "hard_deadline"
    EXTERNAL_COMMITMENT = "external_commitment"
    INTERNAL_TARGET = "internal_target"
    SOFT_GOAL = "soft_goal"


class ImportanceLevel(StrEnum):
    PROTECTED = "protected"
    IMPORTANT = "important"
    NORMAL = "normal"
    OPTIONAL = "optional"
    ON_HOLD = "on_hold"


class WorkstreamStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Uncertainty(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

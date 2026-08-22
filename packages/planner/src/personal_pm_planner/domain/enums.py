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


class DependencyType(StrEnum):
    BLOCKS_START = "blocks_start"
    BLOCKS_COMPLETION = "blocks_completion"
    WAITING_EXTERNAL = "waiting_external"
    RELATED = "related"


class CalendarEventKind(StrEnum):
    FIXED_BUSY = "fixed_busy"
    MOVABLE_COMMITMENT = "movable_commitment"
    TENTATIVE = "tentative"
    ALL_DAY_INFO = "all_day_info"


class AuthorizationLevel(StrEnum):
    AUTOMATIC = "automatic"
    AUTOMATIC_NOTIFY = "automatic_notify"
    APPROVAL = "approval"
    RECONFIRM = "reconfirm"


class ActionType(StrEnum):
    CLASSIFY_INPUT = "classify_input"
    PRODUCE_DRAFT_PLAN = "produce_draft_plan"
    CALCULATE_PRIORITY = "calculate_priority"
    CREATE_LOW_HARM_TASK = "create_low_harm_task"
    RESCHEDULE_LOW_RISK_TASK = "reschedule_low_risk_task"
    CREATE_FOCUS_BLOCK = "create_focus_block"
    CHANGE_SCOPE = "change_scope"
    CHANGE_HARD_DEADLINE = "change_hard_deadline"
    CHANGE_FIXED_EVENT = "change_fixed_event"
    SEND_EXTERNAL_MESSAGE = "send_external_message"
    SUBMIT_EXTERNAL_ARTIFACT = "submit_external_artifact"
    CANCEL_PROJECT = "cancel_project"
    IRREVERSIBLE_ACTION = "irreversible_action"


class ProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    EXECUTED = "executed"
    FAILED = "failed"

"""Immutable audit events for every accepted state change."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from personal_pm_planner.domain.identifiers import WorkspaceId
from personal_pm_planner.domain.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: UUID
    workspace_id: WorkspaceId
    actor_user_id: UUID
    entity_kind: str
    entity_id: str
    before_state: str | None
    after_state: str | None
    reason: str
    rule_basis: tuple[str, ...]
    approval_id: UUID | None
    trace_id: str
    reversible: bool
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not self.entity_kind.strip() or not self.entity_id.strip():
            raise ValueError("audit event requires an entity reference")
        if not self.reason.strip():
            raise ValueError("audit event requires a reason")
        if not self.trace_id.strip():
            raise ValueError("audit event requires a trace id")
        require_aware_utc(self.occurred_at)

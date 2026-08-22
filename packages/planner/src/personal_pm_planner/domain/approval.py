"""Version-bound approvals.

An approval binds a proposal version, an exact command payload hash, target
object versions and an action class. If anything changes, the approval is
stale and the proposal must be regenerated.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from personal_pm_planner.domain.enums import ActionType
from personal_pm_planner.domain.identifiers import WorkspaceId
from personal_pm_planner.domain.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class ApprovalTarget:
    object_kind: str
    object_id: str
    expected_version: int

    def __post_init__(self) -> None:
        if not self.object_kind.strip() or not self.object_id.strip():
            raise ValueError("approval target requires kind and id")
        if self.expected_version < 1:
            raise ValueError("expected_version must be positive")


@dataclass(frozen=True, slots=True)
class Approval:
    id: UUID
    workspace_id: WorkspaceId
    actor_user_id: UUID
    proposal_id: UUID
    proposal_version: int
    action_type: ActionType
    command_hash: str
    targets: tuple[ApprovalTarget, ...]
    granted_at: datetime
    expires_at: datetime | None

    def __post_init__(self) -> None:
        require_aware_utc(self.granted_at)
        if self.expires_at is not None:
            require_aware_utc(self.expires_at)
        object.__setattr__(self, "action_type", ActionType(self.action_type))
        if not self.command_hash.strip():
            raise ValueError("command hash must not be empty")
        if not self.targets:
            raise ValueError("approval requires at least one bound target")

    def validate_use(
        self,
        *,
        now: datetime,
        proposal_version: int,
        command_hash: str,
        targets: tuple[ApprovalTarget, ...],
        workspace_id: WorkspaceId,
        action_type: ActionType,
    ) -> None:
        """Raise ValueError when the approval cannot be used for this command."""
        if workspace_id != self.workspace_id:
            raise ValueError("approval belongs to another workspace")
        if ActionType(action_type) is not self.action_type:
            raise ValueError("stale approval: action class differs")
        if proposal_version != self.proposal_version or command_hash != self.command_hash:
            raise ValueError("stale approval: proposal or command payload changed")
        if tuple(sorted(targets, key=lambda item: (item.object_kind, item.object_id))) != tuple(
            sorted(self.targets, key=lambda item: (item.object_kind, item.object_id))
        ):
            raise ValueError("stale approval: bound targets changed")
        for expected in self.targets:
            actual = next(
                (candidate for candidate in targets if candidate.object_id == expected.object_id),
                None,
            )
            if actual is None or actual.expected_version != expected.expected_version:
                raise ValueError("stale approval: target object versions changed")
        require_aware_utc(now)
        if self.expires_at is not None and now >= self.expires_at:
            raise ValueError("approval expired")

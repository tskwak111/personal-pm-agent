"""Application services for Planning Core commands.

HTTP routers stay thin: this service enforces workspace ownership, runs the
planner domain state machine, persists with optimistic version checks and
writes audit events in the same transaction. Hard-deadline changes become
RECONFIRM proposals instead of direct edits.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from personal_pm_planner.domain.enums import TaskStatus, Uncertainty
from personal_pm_planner.domain.identifiers import (
    MilestoneId,
    TaskId,
    WorkspaceId,
    WorkstreamId,
)
from personal_pm_planner.domain.state_machine import (
    transition_task as domain_transition_task,
)
from personal_pm_planner.domain.task import TaskSnapshot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.approvals.models import ProposalModel
from personal_pm_api.audit.repository import AuditRepository
from personal_pm_api.planning.models import MilestoneModel, TaskModel
from personal_pm_api.shared.concurrency import update_with_version
from personal_pm_api.shared.errors import DomainRuleError, NotFoundError
from personal_pm_api.workspaces.schemas import TaskTransitionRequest


def _snapshot_from_model(model: TaskModel) -> TaskSnapshot:
    return TaskSnapshot(
        id=TaskId(model.id),
        workspace_id=WorkspaceId(model.workspace_id),
        workstream_id=WorkstreamId(model.workstream_id),
        milestone_id=MilestoneId(model.milestone_id) if model.milestone_id else None,
        title=model.title,
        status=TaskStatus(model.status),
        deadline_date=model.deadline_date,
        deadline_at=model.deadline_at,
        deadline_time_known=model.deadline_time_known,
        start_after=model.start_after,
        base_duration_minutes=model.base_duration_minutes,
        safety_duration_minutes=model.safety_duration_minutes,
        remaining_base_minutes=model.remaining_base_minutes,
        remaining_safety_minutes=model.remaining_safety_minutes,
        uncertainty=Uncertainty(model.uncertainty),
        splittable=model.splittable,
        min_chunk_minutes=model.min_chunk_minutes,
        pinned=model.pinned,
        waiting_reason=model.waiting_reason,
        version=model.version,
    )


def _map_domain_value_error(error: ValueError) -> DomainRuleError:
    message = str(error)
    if "remaining" in message:
        return DomainRuleError("TASK_HAS_REMAINING_TIME", message)
    if "not allowed" in message:
        return DomainRuleError("INVALID_TRANSITION", message)
    if "waiting" in message:
        return DomainRuleError("WAITING_CONDITION_UNSATISFIED", message)
    return DomainRuleError("DOMAIN_RULE_VIOLATED", message)


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _owned_task(self, workspace_id: UUID, task_id: str) -> TaskModel:
        statement = select(TaskModel).where(
            TaskModel.id == UUID(task_id),
            TaskModel.workspace_id == workspace_id,
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        if model is None:
            raise NotFoundError()
        return model

    async def transition_task(
        self,
        *,
        actor_user_id: UUID,
        workspace_id: UUID,
        session_id: UUID,
        task_id: str,
        request: TaskTransitionRequest,
    ) -> TaskModel:
        existing = await self._owned_task(workspace_id, task_id)
        snapshot = _snapshot_from_model(existing)
        try:
            candidate = domain_transition_task(
                snapshot,
                TaskStatus(request.target_status),
                waiting_resolved=request.waiting_resolved,
                blocker_resolved=request.blocker_resolved,
                completion_confirmed=request.completion_confirmed,
                waiting_reason=request.waiting_reason,
            )
        except ValueError as error:
            raise _map_domain_value_error(error) from error

        updated: TaskModel = await update_with_version(
            self._session,
            TaskModel,
            task_id,
            request.expected_version,
            {
                "status": candidate.status.value,
                "waiting_reason": candidate.waiting_reason,
                "remaining_base_minutes": candidate.remaining_base_minutes,
                "remaining_safety_minutes": candidate.remaining_safety_minutes,
            },
            workspace_id=str(workspace_id),
        )

        audits = AuditRepository(self._session)
        await audits.append(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            entity_kind="task",
            entity_id=task_id,
            reason=f"task.transition:{candidate.status.value}",
            rule_basis=("REQ-CORE-004",),
            trace_id=f"sess:{session_id}",
            reversible=True,
            occurred_at=datetime.now(UTC),
            before_state={"status": snapshot.status.value},
            after_state={"status": candidate.status.value},
        )
        await self._session.commit()
        return updated

    async def _owned_milestone(self, workspace_id: UUID, milestone_id: str) -> MilestoneModel:
        statement = select(MilestoneModel).where(
            MilestoneModel.id == UUID(milestone_id),
            MilestoneModel.workspace_id == workspace_id,
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        if model is None:
            raise NotFoundError()
        return model

    async def request_milestone_deadline_change(
        self,
        *,
        actor_user_id: UUID,
        workspace_id: UUID,
        session_id: UUID,
        milestone_id: str,
        expected_version: int,
        deadline_date: date | None,
    ) -> tuple[MilestoneModel | None, ProposalModel | None]:
        """Hard deadlines become RECONFIRM proposals; soft goals apply directly."""
        milestone = await self._owned_milestone(workspace_id, milestone_id)

        payload = {"deadline_date": deadline_date.isoformat() if deadline_date else None}
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        if milestone.deadline_type == "hard_deadline":
            proposal = ProposalModel(
                id=uuid4(),
                workspace_id=workspace_id,
                kind="CHANGE_HARD_DEADLINE",
                approval_level="RECONFIRM",
                payload_hash=payload_hash,
                targets_json=[
                    {
                        "object_kind": "milestone",
                        "object_id": str(milestone.id),
                        "expected_version": expected_version,
                    }
                ],
                status="pending",
                milestone_id=milestone.id,
            )
            self._session.add(proposal)
            await self._session.flush()

            audits = AuditRepository(self._session)
            await audits.append(
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                entity_kind="milestone",
                entity_id=milestone_id,
                reason="proposal.created:CHANGE_HARD_DEADLINE",
                rule_basis=("REQ-CORE-009", "SAFE-001"),
                trace_id=f"sess:{session_id}",
                reversible=True,
                occurred_at=datetime.now(UTC),
                before_state={
                    "deadline_date": milestone.deadline_date.isoformat()
                    if milestone.deadline_date
                    else None
                },
                after_state=payload,
                approval_id=None,
            )
            await self._session.commit()
            return None, proposal

        updated: MilestoneModel = await update_with_version(
            self._session,
            MilestoneModel,
            milestone_id,
            expected_version,
            {
                "deadline_date": date.fromisoformat(payload["deadline_date"])
                if payload["deadline_date"]
                else None
            },
            workspace_id=str(workspace_id),
        )
        audits = AuditRepository(self._session)
        await audits.append(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            entity_kind="milestone",
            entity_id=milestone_id,
            reason="milestone.deadline_changed:soft_goal",
            rule_basis=("REQ-CORE-009",),
            trace_id=f"sess:{session_id}",
            reversible=True,
            occurred_at=datetime.now(UTC),
            after_state=payload,
        )
        await self._session.commit()
        return updated, None


__all__ = ["WorkspaceService"]

"""Focus block proposals: approval-bound, version-checked external commands."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True, slots=True)
class ApprovalOutcome:
    status: str
    reason: str | None = None
    outbox_event_id: str | None = None
    proposal_id: str = ""
    approval_level: str = ""


def _payload_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def proposal_targets_payload(proposal: Any) -> dict[str, object]:
    """Extract the first target payload dict from a proposal record."""
    targets = list(proposal.targets_json)
    return dict(targets[0]) if targets else {}


class FocusBlockApprovalService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def propose(
        self,
        actor: Any,
        *,
        task_id: str,
        expected_task_version: int,
        start_at: datetime,
        duration_minutes: int,
    ) -> ApprovalOutcome:
        """Create a pending proposal; the focus block is NOT created yet."""
        from personal_pm_api.approvals.models import ProposalModel

        payload: dict[str, object] = {
            "task_id": task_id,
            "target_version": int(expected_task_version),
            "start_at": start_at.isoformat(),
            "duration_minutes": duration_minutes,
        }
        async with self._factory() as session:
            proposal = ProposalModel(
                id=uuid4(),
                workspace_id=UUID(str(actor.workspace_id)),
                kind="FOCUS_BLOCK_CREATE",
                approval_level="CONFIRM",
                payload_hash=_payload_hash(payload),
                targets_json=[payload],
                status="pending",
                version=1,
            )
            session.add(proposal)
            await session.commit()
            return ApprovalOutcome(
                status="PENDING",
                proposal_id=str(proposal.id),
                approval_level=proposal.approval_level,
            )

    async def approve(
        self,
        actor: Any,
        *,
        proposal_id: str,
        proposal_version: int,
    ) -> ApprovalOutcome:
        from datetime import UTC

        from personal_pm_api.approvals.models import ApprovalModel, ProposalModel

        async with self._factory() as session:
            statement = select(ProposalModel).where(
                ProposalModel.id == UUID(proposal_id),
                ProposalModel.workspace_id == UUID(str(actor.workspace_id)),
            )
            proposal = (await session.execute(statement)).scalar_one_or_none()
            if proposal is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()
            if proposal.status != "pending":
                return ApprovalOutcome(status="SUPERSEDED", reason="ALREADY_RESOLVED")

            proposal.status = "approved"
            proposal.resolved_at = datetime.now(UTC)
            session.add(
                ApprovalModel(
                    id=uuid4(),
                    workspace_id=UUID(str(actor.workspace_id)),
                    proposal_id=proposal.id,
                    proposal_version=int(proposal_version),
                    actor_user_id=UUID(str(actor.user_id)),
                    action_type="APPROVE_FOCUS_BLOCK",
                    command_hash=proposal.payload_hash,
                    targets_json=list(proposal.targets_json),
                    granted_at=datetime.now(UTC),
                )
            )
            await session.commit()
            return ApprovalOutcome(
                status="APPROVED",
                proposal_id=str(proposal.id),
                approval_level=proposal.approval_level,
            )

    async def execute_approved(
        self,
        actor: Any,
        *,
        proposal_id: str,
    ) -> ApprovalOutcome:
        """Enqueue the outbox command only if the bound target version still matches."""
        from datetime import UTC

        from sqlalchemy import select

        from personal_pm_api.approvals.models import ProposalModel
        from personal_pm_api.execution.outbox import ExternalCommand, enqueue_external_command
        from personal_pm_api.planning.models import TaskModel
        from personal_pm_api.shared.unit_of_work import SqlAlchemyUnitOfWork

        async with self._factory() as session:
            statement = select(ProposalModel).where(
                ProposalModel.id == UUID(proposal_id),
                ProposalModel.workspace_id == UUID(str(actor.workspace_id)),
            )
            proposal = (await session.execute(statement)).scalar_one_or_none()
            if proposal is None:
                from personal_pm_api.shared.errors import NotFoundError

                raise NotFoundError()
            if proposal.status != "approved":
                return ApprovalOutcome(
                    status="SUPERSEDED",
                    reason="NOT_APPROVED",
                    proposal_id=str(proposal.id),
                    approval_level=proposal.approval_level,
                )

            target = proposal.targets_json[0]
            task = (
                (
                    await session.execute(
                        select(TaskModel).where(
                            TaskModel.id == UUID(str(target["task_id"])),
                            TaskModel.workspace_id == UUID(str(actor.workspace_id)),
                        )
                    )
                )
                .scalars()
                .one_or_none()
            )
            target_version_raw = target.get("target_version")
            target_version = (
                int(target_version_raw) if isinstance(target_version_raw, (int, str)) else -1
            )
            if task is None or task.version != target_version:
                # Version-bound approval: the world changed under this approval.
                proposal.status = "superseded"
                proposal.resolved_at = datetime.now(UTC)
                await session.commit()
                return ApprovalOutcome(
                    status="SUPERSEDED",
                    reason="TARGET_VERSION_CHANGED",
                    proposal_id=str(proposal.id),
                    approval_level=proposal.approval_level,
                )

        uow = SqlAlchemyUnitOfWork(self._factory)
        async with uow:
            command = ExternalCommand(
                workspace_id=UUID(str(actor.workspace_id)),
                operation_id=uuid4(),
                idempotency_key=f"focus-block:{proposal_id}",
                command_type="CREATE_FOCUS_BLOCK",
                payload=dict(proposal_targets_payload(proposal)),
            )
            record = await enqueue_external_command(uow, command)
            await uow.commit()

        return ApprovalOutcome(
            status="APPROVED",
            outbox_event_id=str(record.id),
            proposal_id=str(proposal.id),
            approval_level=proposal.approval_level,
        )

    async def _load_proposal(self, actor: Any, proposal_id: str) -> Any:
        from personal_pm_api.approvals.models import ProposalModel

        async with self._factory() as session:
            statement = select(ProposalModel).where(
                ProposalModel.id == UUID(proposal_id),
                ProposalModel.workspace_id == UUID(str(actor.workspace_id)),
            )
            return (await session.execute(statement)).scalar_one_or_none()


__all__ = ["ApprovalOutcome", "FocusBlockApprovalService"]

"""Version-bound approval decisions: approve / reject / supersede / undo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@dataclass(frozen=True, slots=True)
class ApprovalOutcome:
    status: str  # EXECUTED | SUPERSEDED | CONFLICT | REJECTED | UNDONE | NOT_FOUND
    executed_change: dict[str, object] | None = None


class ApprovalService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def approve(
        self,
        actor: Any,
        *,
        proposal_id: str,
        expected_version: int,
    ) -> ApprovalOutcome:
        """Execute exactly the proposed change if the target version still matches."""
        async with self._factory() as session:
            proposal = await self._owned(session, actor, proposal_id)
            if proposal is None:
                return ApprovalOutcome("NOT_FOUND")
            if proposal.version != expected_version:
                return ApprovalOutcome("CONFLICT")

            change = dict(proposal.targets_json[0])
            target = await self._load_target(session, actor, change)
            if target is None or target.version != int(change.get("target_version", -1)):
                # Version-bound: the world changed under this approval.
                proposal.status = "superseded"
                proposal.resolved_at = datetime.now(UTC)
                await session.commit()
                return ApprovalOutcome("SUPERSEDED", change)

            applied = await self._execute_exact(session, actor, change)
            proposal.status = "executed"
            proposal.resolved_at = datetime.now(UTC)
            await session.commit()
            return ApprovalOutcome("EXECUTED", applied)

    async def reject(
        self,
        actor: Any,
        *,
        proposal_id: str,
        expected_version: int,
    ) -> ApprovalOutcome:
        async with self._factory() as session:
            proposal = await self._owned(session, actor, proposal_id)
            if proposal is None:
                return ApprovalOutcome("NOT_FOUND")
            if proposal.version != expected_version:
                return ApprovalOutcome("CONFLICT")
            proposal.status = "rejected"
            proposal.resolved_at = datetime.now(UTC)
            await session.commit()
            return ApprovalOutcome("REJECTED")

    async def undo(
        self,
        actor: Any,
        *,
        proposal_id: str,
    ) -> ApprovalOutcome:
        """Undo an executed reversible change by restoring the prior values."""
        async with self._factory() as session:
            proposal = await self._owned(session, actor, proposal_id)
            if proposal is None or proposal.status != "executed":
                return ApprovalOutcome("NOT_FOUND")
            change = dict(proposal.targets_json[0])
            before = change.get("before_values")
            if not isinstance(before, dict) or not before:
                return ApprovalOutcome("CONFLICT")  # irreversible without prior state
            target = await self._load_target(session, actor, change)
            if target is None:
                return ApprovalOutcome("NOT_FOUND")
            for key, value in before.items():
                setattr(target, key, value)
            target.version += 1
            proposal.status = "undone"
            await session.commit()
            return ApprovalOutcome("UNDONE", dict(before))

    async def _owned(self, session: AsyncSession, actor: Any, proposal_id: str) -> Any | None:
        from personal_pm_api.approvals.models import ProposalModel

        statement = select(ProposalModel).where(
            ProposalModel.id == UUID(proposal_id),
            ProposalModel.workspace_id == UUID(str(actor.workspace_id)),
        )
        return (await session.execute(statement)).scalar_one_or_none()

    @staticmethod
    async def _load_target(
        session: AsyncSession, actor: Any, change: dict[str, object]
    ) -> Any | None:
        from personal_pm_api.planning.models import TaskModel

        if change.get("target_type") != "task":
            return None
        statement = select(TaskModel).where(
            TaskModel.id == UUID(str(change["target_id"])),
            TaskModel.workspace_id == UUID(str(actor.workspace_id)),
        )
        return (await session.execute(statement)).scalar_one_or_none()

    @staticmethod
    async def _execute_exact(
        session: AsyncSession, actor: Any, change: dict[str, object]
    ) -> dict[str, object]:

        target = await ApprovalService._load_target(session, actor, change)
        assert target is not None
        values_raw = change.get("values")
        values: dict[str, object] = dict(values_raw) if isinstance(values_raw, dict) else {}
        for key, value in values.items():
            setattr(target, key, value)
        target.version += 1
        return values


__all__ = ["ApprovalOutcome", "ApprovalService"]

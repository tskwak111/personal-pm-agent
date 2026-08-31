"""Version-bound, payload-bound and audited proposal decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, NotRequired, TypedDict
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

TASK_MUTABLE_FIELDS = frozenset({"title"})


class TaskChange(TypedDict):
    target_type: str
    target_id: str
    target_version: int
    values: dict[str, object]
    before_values: NotRequired[dict[str, object]]


def canonical_targets_hash(targets: object) -> str:
    payload = json.dumps(
        targets,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ApprovalOutcome:
    status: str
    executed_change: dict[str, object] | None = None
    reason: str | None = None
    approval_level: str = ""


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
        async with self._factory() as session:
            proposal = await self._owned(session, actor, proposal_id)
            if proposal is None:
                return ApprovalOutcome("NOT_FOUND")
            level = str(proposal.approval_level)
            conflict = self._decision_conflict(proposal, expected_version)
            if conflict is not None:
                return ApprovalOutcome("CONFLICT", reason=conflict, approval_level=level)
            if not self._hash_matches(proposal):
                return ApprovalOutcome(
                    "CONFLICT", reason="PAYLOAD_HASH_MISMATCH", approval_level=level
                )
            change = self._validated_task_change(proposal.targets_json)
            if change is None:
                return ApprovalOutcome(
                    "INVALID", reason="INVALID_PROPOSAL_PAYLOAD", approval_level=level
                )

            target = await self._load_target(session, actor, change)
            target_version = change["target_version"]
            if target is None or target.version != target_version:
                before = {"status": proposal.status, "version": proposal.version}
                proposal.status = "superseded"
                proposal.resolved_at = datetime.now(UTC)
                proposal.version += 1
                await self._append_audit(
                    session,
                    actor,
                    proposal,
                    reason="proposal.superseded:TARGET_VERSION_CHANGED",
                    before_state=before,
                    after_state={"status": proposal.status, "version": proposal.version},
                    approval_id=None,
                    reversible=False,
                )
                await session.commit()
                return ApprovalOutcome(
                    "SUPERSEDED",
                    dict(change),
                    "TARGET_VERSION_CHANGED",
                    level,
                )

            values = dict(change["values"])
            before_values = {key: getattr(target, key) for key in values}
            for key, value in values.items():
                setattr(target, key, value)
            target.version += 1
            before = {"status": proposal.status, "version": proposal.version}
            proposal.status = "executed"
            proposal.resolved_at = datetime.now(UTC)
            proposal.version += 1
            approval = await self._record_decision(
                session,
                actor,
                proposal,
                proposal_version=expected_version,
                action_type="APPROVE_TASK_CHANGE",
            )
            await self._append_audit(
                session,
                actor,
                proposal,
                reason="proposal.executed",
                before_state={**before, "target": before_values},
                after_state={
                    "status": proposal.status,
                    "version": proposal.version,
                    "target": values,
                },
                approval_id=approval.id,
                reversible=True,
            )
            await session.commit()
            return ApprovalOutcome("EXECUTED", values, approval_level=level)

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
            level = str(proposal.approval_level)
            conflict = self._decision_conflict(proposal, expected_version)
            if conflict is not None:
                return ApprovalOutcome("CONFLICT", reason=conflict, approval_level=level)
            if not self._hash_matches(proposal):
                return ApprovalOutcome(
                    "CONFLICT", reason="PAYLOAD_HASH_MISMATCH", approval_level=level
                )

            before = {"status": proposal.status, "version": proposal.version}
            proposal.status = "rejected"
            proposal.resolved_at = datetime.now(UTC)
            proposal.version += 1
            approval = await self._record_decision(
                session,
                actor,
                proposal,
                proposal_version=expected_version,
                action_type="REJECT_PROPOSAL",
            )
            await self._append_audit(
                session,
                actor,
                proposal,
                reason="proposal.rejected",
                before_state=before,
                after_state={"status": proposal.status, "version": proposal.version},
                approval_id=approval.id,
                reversible=False,
            )
            await session.commit()
            return ApprovalOutcome("REJECTED", approval_level=level)

    async def undo(self, actor: Any, *, proposal_id: str) -> ApprovalOutcome:
        async with self._factory() as session:
            proposal = await self._owned(session, actor, proposal_id)
            if (
                proposal is None
                or proposal.status != "executed"
                or not self._hash_matches(proposal)
            ):
                return ApprovalOutcome("NOT_FOUND")
            change = self._validated_task_change(proposal.targets_json)
            if change is None:
                return ApprovalOutcome("CONFLICT")
            before_values = change.get("before_values")
            if not isinstance(before_values, dict) or not before_values:
                return ApprovalOutcome("CONFLICT")
            if set(before_values) - TASK_MUTABLE_FIELDS:
                return ApprovalOutcome("CONFLICT")
            target = await self._load_target(session, actor, change)
            if target is None:
                return ApprovalOutcome("NOT_FOUND")
            for key, value in before_values.items():
                setattr(target, key, value)
            target.version += 1
            proposal.status = "undone"
            proposal.version += 1
            await session.commit()
            return ApprovalOutcome("UNDONE", dict(before_values))

    @staticmethod
    def _decision_conflict(proposal: Any, expected_version: int) -> str | None:
        if proposal.status != "pending":
            return "ALREADY_RESOLVED"
        if proposal.version != expected_version:
            return "PROPOSAL_VERSION_CHANGED"
        return None

    @staticmethod
    def _hash_matches(proposal: Any) -> bool:
        return canonical_targets_hash(proposal.targets_json) == str(proposal.payload_hash)

    @staticmethod
    def _validated_task_change(targets: object) -> TaskChange | None:
        if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
            return None
        change = dict(targets[0])
        target_id = change.get("target_id")
        values = change.get("values")
        version = change.get("target_version")
        if (
            change.get("target_type") != "task"
            or not isinstance(target_id, str)
            or isinstance(version, bool)
            or not isinstance(version, int)
            or not isinstance(values, dict)
            or not values
            or set(values) - TASK_MUTABLE_FIELDS
            or not isinstance(values.get("title"), str)
            or not values["title"].strip()
        ):
            return None
        result: TaskChange = {
            "target_type": "task",
            "target_id": target_id,
            "target_version": version,
            "values": dict(values),
        }
        before_values = change.get("before_values")
        if isinstance(before_values, dict):
            result["before_values"] = dict(before_values)
        return result

    async def _owned(self, session: AsyncSession, actor: Any, proposal_id: str) -> Any | None:
        from personal_pm_api.approvals.models import ProposalModel

        try:
            identifier = UUID(proposal_id)
        except ValueError:
            return None
        statement = (
            select(ProposalModel)
            .where(
                ProposalModel.id == identifier,
                ProposalModel.workspace_id == UUID(str(actor.workspace_id)),
            )
            .with_for_update()
        )
        return (await session.execute(statement)).scalar_one_or_none()

    @staticmethod
    async def _load_target(session: AsyncSession, actor: Any, change: TaskChange) -> Any | None:
        from personal_pm_api.planning.models import TaskModel

        try:
            target_id = UUID(str(change["target_id"]))
        except (KeyError, ValueError):
            return None
        statement = (
            select(TaskModel)
            .where(
                TaskModel.id == target_id,
                TaskModel.workspace_id == UUID(str(actor.workspace_id)),
            )
            .with_for_update()
        )
        return (await session.execute(statement)).scalar_one_or_none()

    @staticmethod
    async def _record_decision(
        session: AsyncSession,
        actor: Any,
        proposal: Any,
        *,
        proposal_version: int,
        action_type: str,
    ) -> Any:
        from personal_pm_api.approvals.models import ApprovalModel

        approval = ApprovalModel(
            id=uuid4(),
            workspace_id=UUID(str(actor.workspace_id)),
            proposal_id=proposal.id,
            proposal_version=proposal_version,
            actor_user_id=UUID(str(actor.user_id)),
            action_type=action_type,
            command_hash=proposal.payload_hash,
            targets_json=list(proposal.targets_json),
            granted_at=datetime.now(UTC),
        )
        session.add(approval)
        await session.flush()
        return approval

    @staticmethod
    async def _append_audit(
        session: AsyncSession,
        actor: Any,
        proposal: Any,
        *,
        reason: str,
        before_state: dict[str, object],
        after_state: dict[str, object],
        approval_id: UUID | None,
        reversible: bool,
    ) -> None:
        from personal_pm_api.audit.repository import AuditRepository

        await AuditRepository(session).append(
            workspace_id=UUID(str(actor.workspace_id)),
            actor_user_id=UUID(str(actor.user_id)),
            entity_kind="proposal",
            entity_id=str(proposal.id),
            reason=reason,
            rule_basis=("REQ-CORE-009", "REQ-CORE-014", "REQ-CORE-015"),
            trace_id=f"sess:{getattr(actor, 'session_id', 'unknown')}",
            reversible=reversible,
            occurred_at=datetime.now(UTC),
            before_state=before_state,
            after_state=after_state,
            approval_id=approval_id,
        )


__all__ = [
    "ApprovalOutcome",
    "ApprovalService",
    "canonical_targets_hash",
]

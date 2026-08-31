"""Deterministic browser fixture, reachable only through the local/test session endpoint."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from personal_pm_api.approvals.models import ProposalModel
from personal_pm_api.approvals.service import canonical_targets_hash
from personal_pm_api.inbox.models import CandidateFactModel, InboxItemModel
from personal_pm_api.planning.models import PlanSnapshotModel, TaskModel, WorkstreamModel
from personal_pm_api.workspaces.models import WorkspaceModel


async def reset_and_seed_browser_fixture(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(delete(WorkspaceModel).where(WorkspaceModel.owner_user_id == user_id))
    workspace = WorkspaceModel(owner_user_id=user_id, name="브라우저 테스트")
    session.add(workspace)
    await session.flush()

    workstream = WorkstreamModel(
        workspace_id=workspace.id,
        area_id=None,
        name="출시 준비",
        importance="high",
        status="active",
        version=1,
    )
    session.add(workstream)
    await session.flush()
    task = TaskModel(
        workspace_id=workspace.id,
        workstream_id=workstream.id,
        milestone_id=None,
        title="오늘의 핵심 작업",
        status="ready",
        deadline_date=None,
        deadline_at=None,
        deadline_time_known=False,
        start_after=None,
        base_duration_minutes=60,
        safety_duration_minutes=90,
        remaining_base_minutes=60,
        remaining_safety_minutes=90,
        uncertainty="medium",
        splittable=True,
        min_chunk_minutes=30,
        pinned=False,
        waiting_reason=None,
        version=1,
    )
    session.add(task)
    await session.flush()

    source = "금요일까지 제안서 초안"
    item = InboxItemModel(
        workspace_id=workspace.id,
        source_artifact_id=None,
        kind="text",
        raw_text=source,
        status="NEEDS_CONFIRMATION",
        failure_reason=None,
    )
    session.add(item)
    await session.flush()
    session.add(
        CandidateFactModel(
            inbox_item_id=item.id,
            operation_id=uuid4(),
            kind="task",
            payload_json={"title": "제안서 초안", "deadline_date": None},
            evidence_score=0.9,
            decision="HOLD",
        )
    )

    targets = [
        {
            "target_type": "task",
            "target_id": str(task.id),
            "target_version": task.version,
            "before_values": {"title": task.title},
            "values": {"title": "승인된 핵심 작업"},
        }
    ]
    session.add(
        ProposalModel(
            workspace_id=workspace.id,
            kind="TASK_UPDATE",
            approval_level="CONFIRM",
            payload_hash=canonical_targets_hash(targets),
            targets_json=targets,
            status="pending",
            version=1,
            milestone_id=None,
            minutes_saved_or_added=0,
        )
    )
    session.add(
        PlanSnapshotModel(
            workspace_id=workspace.id,
            planner_version="browser-fixture-v1",
            input_hash="e" * 64,
            reason="browser-test",
            output_json={
                "status": "OK",
                "base_allocations": [],
                "today": {
                    "core_result_task_id": str(task.id),
                    "must_do": [str(task.id)],
                    "next_queue": [],
                    "opportunistic": [],
                    "excluded": [],
                },
                "risks": [],
                "warnings": [],
            },
            is_current=True,
        )
    )


__all__ = ["reset_and_seed_browser_fixture"]

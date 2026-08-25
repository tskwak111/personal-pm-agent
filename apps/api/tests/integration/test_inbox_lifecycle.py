from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import select

INBOX_TRANSITIONS = {
    "NEW": {"PROCESSING", "IGNORED"},
    "PROCESSING": {"NEEDS_CONFIRMATION", "STRUCTURED", "FAILED"},
    "NEEDS_CONFIRMATION": {"STRUCTURED", "IGNORED", "PROCESSING"},
    "FAILED": {"PROCESSING", "IGNORED"},
    "STRUCTURED": set(),
    "IGNORED": set(),
}


@pytest_asyncio.fixture
async def inbox_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="inbox@example.com", display_name="I")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-inbox")
        session.add(workspace)
        await session.commit()
        ids["workspace"] = str(workspace.id)
        ids["user"] = str(user.id)

    class Actor:
        def __init__(self, uid: str, wid: str) -> None:
            self.user_id = uid
            self.workspace_id = wid

    ids["actor"] = Actor(ids["user"], ids["workspace"])
    ids["factory"] = factory
    yield ids
    await engine.dispose()


async def _count_candidates(session: Any, item_id: str) -> int:
    from personal_pm_api.inbox.models import CandidateFactModel

    rows = (
        (
            await session.execute(
                select(CandidateFactModel).where(CandidateFactModel.inbox_item_id == item_id)
            )
        )
        .scalars()
        .all()
    )
    return len(rows)


async def test_processing_failure_preserves_source_and_marks_inbox_failed(
    inbox_env: dict[str, Any],
) -> None:
    from personal_pm_api.inbox.service import InboxService
    from personal_pm_worker.files.jobs import FailingProcessingJob, ProcessingJob

    service = InboxService(inbox_env["factory"])
    actor = inbox_env["actor"]
    item = await service.create_from_text(actor, "금요일까지 과제")
    assert item.status == "NEW"
    assert item.source_artifact_id is not None

    job: ProcessingJob = FailingProcessingJob(inbox_env["factory"])
    with pytest.raises(RuntimeError):
        await job.run(item.id)

    reloaded = await service.get(actor, item.id)
    assert reloaded is not None
    assert reloaded.status == "FAILED"
    assert reloaded.source_artifact_id == item.source_artifact_id


async def test_duplicate_job_delivery_does_not_duplicate_candidates(
    inbox_env: dict[str, Any],
) -> None:
    from personal_pm_api.inbox.service import InboxService
    from personal_pm_worker.files.jobs import ProcessingJob

    service = InboxService(inbox_env["factory"])
    actor = inbox_env["actor"]
    item = await service.create_from_text(actor, "월요일 10시 팀 회의")

    job = ProcessingJob(inbox_env["factory"], operation_id=uuid4())
    await job.run(item.id)
    first_status = (await service.get(actor, item.id)).status
    assert first_status in ("STRUCTURED", "NEEDS_CONFIRMATION")

    # redeliver the SAME operation id — must be idempotent
    await job.run(item.id)

    async with inbox_env["factory"]() as session:
        count = await _count_candidates(session, item.id)
    assert count == 1


async def test_invalid_transition_is_rejected(inbox_env: dict[str, Any]) -> None:
    from personal_pm_api.inbox.models import transition_inbox
    from personal_pm_api.shared.errors import DomainRuleError

    # STRUCTURED is terminal
    with pytest.raises(DomainRuleError):
        transition_inbox("STRUCTURED", "IGNORED")
    # NEW cannot jump straight to FAILED
    with pytest.raises(DomainRuleError):
        transition_inbox("NEW", "FAILED")


async def test_lifecycle_happy_path_new_to_structured(inbox_env: dict[str, Any]) -> None:
    from personal_pm_api.inbox.service import InboxService
    from personal_pm_worker.files.jobs import ProcessingJob

    service = InboxService(inbox_env["factory"])
    actor = inbox_env["actor"]
    item = await service.create_from_text(actor, "다음 주 수요일까지 보고서 초안")

    job = ProcessingJob(inbox_env["factory"])
    await job.run(item.id)

    latest = await service.get(actor, item.id)
    assert latest is not None
    assert latest.status in ("STRUCTURED", "NEEDS_CONFIRMATION")


async def test_cross_workspace_get_is_not_disclosed(inbox_env: dict[str, Any]) -> None:
    from personal_pm_api.inbox.service import InboxService

    service = InboxService(inbox_env["factory"])
    actor = inbox_env["actor"]
    item = await service.create_from_text(actor, "비밀 메모")

    class OtherActor:
        def __init__(self) -> None:
            self.user_id = actor.user_id
            self.workspace_id = "00000000-0000-0000-0000-000000000000"

    assert await service.get(OtherActor(), item.id) is None

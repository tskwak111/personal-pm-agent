from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import select


@pytest_asyncio.fixture
async def reg_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from personal_pm_api.inbox.service import InboxService
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="reg@example.com", display_name="R")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-reg")
        session.add(workspace)
        await session.commit()
        ids["workspace"] = str(workspace.id)

    class Actor:
        def __init__(self, wid: str) -> None:
            self.user_id = "00000000-0000-0000-0000-000000000001"
            self.workspace_id = wid

    ids["actor"] = Actor(ids["workspace"])
    ids["factory"] = factory
    ids["service"] = InboxService(factory)
    yield ids
    await engine.dispose()


async def test_job_records_candidate_with_policy_decision(reg_env: dict[str, Any]) -> None:
    from personal_pm_api.inbox.models import CandidateFactModel
    from personal_pm_worker.files.jobs import ProcessingJob

    service: Any = reg_env["service"]
    item = await service.create_from_text(reg_env["actor"], "금요일까지 보고서 제출")

    job = ProcessingJob(reg_env["factory"], operation_id=uuid4())
    await job.run(item.id)

    factory: Any = reg_env["factory"]
    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(CandidateFactModel).where(CandidateFactModel.inbox_item_id == item.id)
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) >= 1
    for row in rows:
        assert row.decision in {"AUTO_REGISTER", "TEMPORARY", "NEEDS_CONFIRMATION", "HOLD"}
        assert row.operation_id == job.operation_id


async def test_duplicate_operation_keeps_single_candidate_row(
    reg_env: dict[str, Any],
) -> None:
    from personal_pm_api.inbox.models import CandidateFactModel
    from personal_pm_worker.files.jobs import ProcessingJob

    service: Any = reg_env["service"]
    item = await service.create_from_text(reg_env["actor"], "월요일 회의 준비")

    job = ProcessingJob(reg_env["factory"], operation_id=uuid4())
    await job.run(item.id)
    await job.run(item.id)

    factory: Any = reg_env["factory"]
    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(CandidateFactModel).where(CandidateFactModel.inbox_item_id == item.id)
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from collections.abc import AsyncIterator
from typing import Any

import pytest_asyncio


@pytest_asyncio.fixture
async def agent_env(clean_tables, database_url_session) -> AsyncIterator[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    ids: dict[str, Any] = {}
    async with factory() as session:
        from personal_pm_api.workspaces.models import UserModel, WorkspaceModel

        user = UserModel(email="agent@example.com", display_name="A")
        session.add(user)
        await session.flush()
        workspace = WorkspaceModel(owner_user_id=user.id, name="ws-agent")
        session.add(workspace)
        await session.commit()
        ids["workspace"] = str(workspace.id)

    class Actor:
        def __init__(self, wid: str) -> None:
            self.user_id = "00000000-0000-0000-0000-00000000000a"
            self.workspace_id = wid

    from personal_pm_api.agent.operations import AgentOperationService

    ids["factory"] = factory
    ids["actor"] = Actor(ids["workspace"])
    ids["other_actor"] = Actor("11111111-1111-1111-1111-111111111111")
    ids["service"] = AgentOperationService(factory)
    yield ids
    await engine.dispose()


async def test_operation_steps_are_append_only(agent_env: dict[str, Any]) -> None:
    service: Any = agent_env["service"]
    actor: Any = agent_env["actor"]

    operation = await service.start(actor, "오늘 일정 다시 짜줘")
    assert operation.status == "RUNNING"

    await service.append_step(operation.id, "OBSERVE", "SUCCEEDED")
    await service.append_step(operation.id, "PLAN", "SUCCEEDED")
    events = await service.events(actor, operation.id)
    assert [event.step for event in events] == ["OBSERVE", "PLAN"]


async def test_unknown_step_is_rejected(agent_env: dict[str, Any]) -> None:
    from personal_pm_api.shared.errors import DomainRuleError

    service: Any = agent_env["service"]
    actor: Any = agent_env["actor"]
    operation = await service.start(actor, "메모")
    with pytest.raises(DomainRuleError):
        await service.append_step(operation.id, "TELEPORT", "SUCCEEDED")


async def test_cross_workspace_operation_is_hidden(agent_env: dict[str, Any]) -> None:
    service: Any = agent_env["service"]
    owner: Any = agent_env["actor"]
    other: Any = agent_env["other_actor"]

    operation = await service.start(owner, "비밀 작업")
    assert await service.get(other, operation.id) is None
    # and the other workspace cannot append steps to it
    from personal_pm_api.shared.errors import NotFoundError

    with pytest.raises(NotFoundError):
        await service.append_step_for_actor(other, operation.id, "OBSERVE", "FAILED")

from __future__ import annotations

import json
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def web_env(clean_tables, database_url_session: str) -> AsyncIterator[dict[str, Any]]:
    from personal_pm_api.identity.models import UserSessionModel
    from personal_pm_api.identity.session import hash_session_token
    from personal_pm_api.main import create_app
    from personal_pm_api.shared.db import reset_engine
    from personal_pm_api.workspaces.models import UserModel, WorkspaceModel
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url_session)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    ids: dict[str, Any] = {"factory": factory}
    async with factory() as session:
        for label in ("owner", "other"):
            token = secrets.token_urlsafe(32)
            user = UserModel(email=f"{label}@example.com", display_name=label)
            session.add(user)
            await session.flush()
            workspace = WorkspaceModel(owner_user_id=user.id, name=f"{label}-workspace")
            session.add(workspace)
            session.add(
                UserSessionModel(
                    user_id=user.id,
                    token_hash=hash_session_token(token),
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )
            await session.flush()
            ids[f"workspace_{label}"] = workspace.id
            ids[f"token_{label}"] = token
        await session.commit()

    app = create_app()
    ids["app"] = app
    owner_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {ids['token_owner']}"},
    )
    other_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {ids['token_other']}"},
    )
    try:
        yield {**ids, "owner_client": owner_client, "other_client": other_client}
    finally:
        await owner_client.aclose()
        await other_client.aclose()
        await engine.dispose()
        await reset_engine()


async def test_read_models_require_auth_and_expose_explicit_empty_states(
    web_env: dict[str, Any],
) -> None:
    anonymous = AsyncClient(
        transport=ASGITransport(app=web_env["app"]),
        base_url="http://testserver",
    )
    try:
        assert (await anonymous.get("/api/v1/today")).status_code == 401
    finally:
        await anonymous.aclose()

    client: AsyncClient = web_env["owner_client"]
    today = await client.get("/api/v1/today")
    assert today.status_code == 200
    assert today.json() == {
        "plan_status": "EMPTY",
        "core_outcome": None,
        "fixed_events": [],
        "must_do": [],
        "queue": [],
        "not_today": [],
    }
    assert (await client.get("/api/v1/inbox")).json() == {"candidates": []}
    assert (await client.get("/api/v1/projects")).json() == {"projects": []}
    assert (await client.get("/api/v1/calendar")).json() == {
        "connections": [],
        "events": [],
        "flexible_tasks": [],
    }
    review = (await client.get("/api/v1/review")).json()
    assert review["planned_minutes"] == 0
    assert review["actual_minutes"] == 0
    assert review["missed_minutes"] == 0
    assert review["pending_proposals"] == []


async def _seed_read_models(web_env: dict[str, Any]) -> dict[str, str]:
    from personal_pm_api.approvals.models import ProposalModel
    from personal_pm_api.calendar.models import ExternalCalendarEventModel
    from personal_pm_api.inbox.models import CandidateFactModel, InboxItemModel
    from personal_pm_api.planning.models import (
        CalendarEventModel,
        PlanSnapshotModel,
        TaskModel,
        WorkstreamModel,
    )

    seeded: dict[str, str] = {}
    async with web_env["factory"]() as session:
        for label, title in (("owner", "Visible"), ("other", "Secret")):
            workspace_id: UUID = web_env[f"workspace_{label}"]
            workstream = WorkstreamModel(
                workspace_id=workspace_id,
                area_id=None,
                name=f"{title} project",
                importance="normal",
                status="active",
                version=1,
            )
            session.add(workstream)
            await session.flush()
            task = TaskModel(
                workspace_id=workspace_id,
                workstream_id=workstream.id,
                milestone_id=None,
                title=f"{title} task",
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
            local_date = datetime.now(ZoneInfo("Asia/Seoul")).date()
            fixed_start = datetime.combine(
                local_date, time(hour=10), ZoneInfo("Asia/Seoul")
            ).astimezone(UTC)
            session.add(
                CalendarEventModel(
                    workspace_id=workspace_id,
                    external_calendar_id=f"calendar-{label}",
                    external_event_id=f"fixed-{label}",
                    external_version=1,
                    title=f"{title} fixed event",
                    start_at=fixed_start,
                    end_at=fixed_start + timedelta(hours=1),
                    event_kind="fixed_busy",
                    deadline_date=None,
                    sync_status="synced",
                    version=1,
                )
            )
            inbox_item = InboxItemModel(
                workspace_id=workspace_id,
                source_artifact_id=None,
                kind="text",
                raw_text=f"{title} source",
                status="NEEDS_CONFIRMATION",
                failure_reason=None,
            )
            session.add(inbox_item)
            await session.flush()
            candidate = CandidateFactModel(
                inbox_item_id=inbox_item.id,
                operation_id=uuid4(),
                kind="task",
                payload_json={"title": f"{title} candidate"},
                evidence_score=0.8,
                decision="HOLD",
            )
            session.add(candidate)
            event = ExternalCalendarEventModel(
                workspace_id=workspace_id,
                external_event_id=f"event-{label}",
                title=f"{title} event",
                start_at=datetime(2026, 9, 1, 1, tzinfo=UTC),
                end_at=datetime(2026, 9, 1, 2, tzinfo=UTC),
                all_day=False,
                blocks_capacity=True,
                availability_type="busy",
                provider_status="confirmed",
                managed_focus_block=False,
                pending_internal_reconciliation=False,
                outbound_restore_requested=False,
                sync_status="SYNCED",
            )
            session.add(event)
            proposal = ProposalModel(
                workspace_id=workspace_id,
                kind="TASK_UPDATE",
                approval_level="CONFIRM",
                payload_hash="a" * 64,
                targets_json=[{"task_id": str(task.id)}],
                status="pending",
                version=1,
                milestone_id=None,
                minutes_saved_or_added=0,
            )
            session.add(proposal)
            session.add(
                PlanSnapshotModel(
                    workspace_id=workspace_id,
                    planner_version="test",
                    input_hash=("b" if label == "owner" else "c") * 64,
                    reason="test",
                    output_json={
                        "status": "OK",
                        "base_allocations": [],
                        "today": {
                            "core_result_task_id": task.id.hex,
                            "must_do": [task.id.hex],
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
            await session.flush()
            seeded[f"workstream_{label}"] = str(workstream.id)
            seeded[f"task_{label}"] = str(task.id)
            seeded[f"candidate_{label}"] = str(candidate.id)
        await session.commit()
    return seeded


async def test_read_models_never_cross_workspace_boundaries(web_env: dict[str, Any]) -> None:
    seeded = await _seed_read_models(web_env)
    client: AsyncClient = web_env["owner_client"]

    responses = [
        await client.get("/api/v1/today"),
        await client.get("/api/v1/inbox"),
        await client.get("/api/v1/projects"),
        await client.get(f"/api/v1/projects/{seeded['workstream_owner']}"),
        await client.get("/api/v1/calendar"),
        await client.get("/api/v1/review"),
    ]

    assert all(response.status_code == 200 for response in responses)
    assert responses[0].json()["core_outcome"]["title"] == "Visible task"
    assert responses[0].json()["fixed_events"][0]["title"] == "Visible fixed event"
    assert responses[1].json()["candidates"][0]["source_text"] == "Visible source"
    assert responses[2].json()["projects"][0]["title"] == "Visible project"
    assert responses[3].json()["project"]["title"] == "Visible project"
    assert responses[4].json()["events"][0]["title"] == "Visible event"
    assert responses[5].json()["pending_proposals"][0]["targets"] == [
        {"task_id": seeded["task_owner"]}
    ]
    rendered = json.dumps([response.json() for response in responses])
    assert "Visible" in rendered
    assert "Secret" not in rendered
    assert seeded["task_other"] not in rendered
    assert (await client.get(f"/api/v1/projects/{seeded['workstream_other']}")).status_code == 404


async def test_agent_sse_is_owned_and_replays_after_last_event_id(
    web_env: dict[str, Any],
) -> None:
    from personal_pm_api.agent.operations import AgentOperationService

    class Actor:
        workspace_id = web_env["workspace_owner"]

    service = AgentOperationService(web_env["factory"])
    operation = await service.start(Actor(), "safe operation")
    await service.append_step(operation.id, "OBSERVE", "SUCCEEDED")
    await service.append_step(operation.id, "PLAN", "SUCCEEDED")

    response = await web_env["owner_client"].get(
        f"/api/v1/agent/operations/{operation.id}/stream?last_event_id=0"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "id: 0" not in response.text
    assert "id: 1" in response.text
    assert '"step":"PLAN"' in response.text
    assert (
        await web_env["other_client"].get(f"/api/v1/agent/operations/{operation.id}/stream")
    ).status_code == 404


async def test_candidate_decision_is_owned_and_removes_resolved_candidate(
    web_env: dict[str, Any],
) -> None:
    seeded = await _seed_read_models(web_env)

    hidden = await web_env["owner_client"].post(
        f"/api/v1/inbox/candidates/{seeded['candidate_other']}/decision",
        json={"decision": "confirm"},
    )
    confirmed = await web_env["owner_client"].post(
        f"/api/v1/inbox/candidates/{seeded['candidate_owner']}/decision",
        json={"decision": "confirm"},
    )

    assert hidden.status_code == 404
    assert confirmed.status_code == 200
    assert confirmed.json()["decision"] == "CONFIRMED"
    assert (await web_env["owner_client"].get("/api/v1/inbox")).json() == {"candidates": []}


async def test_ux_events_use_server_workspace_hash_and_strict_allowlist(
    web_env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client: AsyncClient = web_env["owner_client"]
    messages: list[str] = []
    monkeypatch.setattr(
        "personal_pm_api.analytics.router.LOGGER.info",
        lambda message: messages.append(str(message)),
    )

    accepted = await client.post(
        "/api/v1/analytics/ux-events",
        json={"schema_version": 1, "name": "task_started", "duration_ms": 120},
    )
    unknown = await client.post(
        "/api/v1/analytics/ux-events",
        json={"schema_version": 1, "name": "invented_event", "duration_ms": 1},
    )
    extra = await client.post(
        "/api/v1/analytics/ux-events",
        json={
            "schema_version": 1,
            "name": "task_started",
            "duration_ms": 1,
            "workspace_id": str(web_env["workspace_other"]),
        },
    )

    assert accepted.status_code == 202
    assert unknown.status_code == 422
    assert extra.status_code == 422
    rendered = "\n".join(messages)
    assert str(web_env["workspace_owner"]) not in rendered
    assert str(web_env["workspace_other"]) not in rendered
    assert len(json.loads(messages[-1])["workspace_hash"]) == 64

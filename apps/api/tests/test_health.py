import hashlib
import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from personal_pm_api.main import check_database, create_app


def test_live_health_is_process_only() -> None:
    response = TestClient(create_app()).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_health_checks_database(
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "test")
    check = AsyncMock()
    monkeypatch.setattr("personal_pm_api.main.check_database", check)

    response = TestClient(create_app()).get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    check.assert_awaited_once()


def test_ready_health_returns_503_when_database_fails(
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    monkeypatch.setattr(
        "personal_pm_api.main.check_database",
        AsyncMock(side_effect=OSError("database unavailable")),
    )

    response = TestClient(create_app()).get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


async def test_database_check_executes_select_one(
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    connection = AsyncMock()
    engine = MagicMock()
    engine.connect.return_value.__aenter__.return_value = connection
    monkeypatch.setattr("personal_pm_api.main.get_engine", lambda _: engine)

    await check_database()

    statement = connection.execute.await_args.args[0]
    assert str(statement) == "SELECT 1"


def test_request_log_is_correlated_and_sanitized(
    caplog: "pytest.LogCaptureFixture",
) -> None:
    workspace_id = "00000000-0000-0000-0000-000000000001"
    token = "secret-session-token"
    app = create_app()

    @app.get("/request-log-probe")
    async def request_log_probe(request: Request, workspace_id: str) -> dict[str, str]:
        request.state.workspace_id = workspace_id
        return {"status": "ok"}

    caplog.set_level(logging.INFO, logger="personal_pm_api.requests")
    response = TestClient(app).get(
        "/request-log-probe",
        params={"workspace_id": workspace_id},
        headers={
            "Authorization": f"Bearer {token}",
            "Cookie": "session=also-secret",
            "X-Correlation-ID": "request-42",
        },
    )

    assert response.headers["X-Correlation-ID"] == "request-42"
    event = json.loads(caplog.records[-1].message)
    duration_ms = event.pop("duration_ms")
    assert isinstance(duration_ms, int)
    assert duration_ms >= 0
    assert event == {
        "correlation_id": "request-42",
        "message": "request.completed",
        "method": "GET",
        "path": "/request-log-probe",
        "status": 200,
        "workspace_hash": hashlib.sha256(workspace_id.encode()).hexdigest(),
    }
    assert workspace_id not in caplog.text
    assert token not in caplog.text
    assert "also-secret" not in caplog.text

import pytest
from fastapi.testclient import TestClient
from personal_pm_api.main import create_app


def test_live_health_is_process_only() -> None:
    response = TestClient(create_app()).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_health_reports_environment_without_domain_coupling(
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "test")
    response = TestClient(create_app()).get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"

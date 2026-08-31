from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient


def _alert_metric_names(path: Path) -> set[str]:
    source = yaml.safe_load(path.read_text(encoding="utf-8"))
    expressions = "\n".join(rule["condition"] for rule in source["alerts"])
    names = set(re.findall(r"\b[a-z][a-z0-9_:]*(?:_total|_bucket)\b", expressions))
    return {name.removesuffix("_bucket") for name in names}


def test_every_alert_metric_is_registered() -> None:
    from personal_pm_api.telemetry.metrics import REGISTERED_METRICS

    referenced = _alert_metric_names(Path("infra/monitoring/alerts.yaml"))
    assert referenced <= REGISTERED_METRICS


def test_every_dashboard_metric_is_registered() -> None:
    from personal_pm_api.telemetry.metrics import REGISTERED_METRICS

    expressions = "\n".join(
        panel["expr"]
        for path in Path("infra/monitoring/dashboards").glob("*.json")
        for panel in json.loads(path.read_text(encoding="utf-8"))["panels"]
    )
    names = set(re.findall(r"\b[a-z][a-z0-9_:]*(?:_total|_bucket)\b", expressions))
    referenced = {name.removesuffix("_bucket") for name in names}
    assert referenced <= REGISTERED_METRICS


def test_metric_labels_forbid_high_cardinality_identifiers() -> None:
    from personal_pm_api.telemetry.metrics import METRIC_LABELS

    forbidden = {"workspace_id", "task_id", "provider_event_id", "error", "error_message"}
    assert all(forbidden.isdisjoint(labels) for labels in METRIC_LABELS.values())


def test_registry_rejects_unknown_labels_and_renders_histograms() -> None:
    from personal_pm_api.telemetry.metrics import MetricsRegistry

    registry = MetricsRegistry()
    with pytest.raises(ValueError, match="labels"):
        registry.increment("http_requests_total", route="/", status="200", workspace_id="x")
    registry.increment("http_requests_total", method="GET", route="/health/live", status="200")
    registry.observe(
        "http_request_duration_seconds",
        0.01,
        method="GET",
        route="/health/live",
        status="200",
    )
    rendered = registry.render()
    assert 'http_requests_total{method="GET",route="/health/live",status="200"} 1' in rendered
    assert "http_request_duration_seconds_bucket" in rendered


def test_metrics_endpoint_requires_operator_token() -> None:
    from personal_pm_api.main import create_app
    from personal_pm_api.settings import ApiSettings

    app = create_app(ApiSettings(environment="test", operator_metrics_token="operator-secret"))
    with TestClient(app) as client:
        assert client.get("/internal/metrics").status_code == 401
        accepted = client.get(
            "/internal/metrics", headers={"Authorization": "Bearer operator-secret"}
        )
    assert accepted.status_code == 200
    assert "http_requests_total" in accepted.text

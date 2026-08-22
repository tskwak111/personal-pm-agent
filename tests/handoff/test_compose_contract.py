from pathlib import Path

import yaml


def test_compose_declares_required_services_and_healthchecks() -> None:
    data = yaml.safe_load(Path("compose.yaml").read_text())
    assert {"postgres", "redis", "minio"} <= set(data["services"])
    for service in ("postgres", "redis", "minio"):
        assert "healthcheck" in data["services"][service]

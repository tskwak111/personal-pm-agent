import json
from pathlib import Path

from personal_pm_api.main import create_app


ROOT = Path(__file__).resolve().parents[4]


def test_openapi_has_versioned_core_resources() -> None:
    paths = create_app().openapi()["paths"]
    assert "/api/v1/tasks/{task_id}/transition" in paths
    assert "/api/v1/plans" in paths
    assert "/api/v1/proposals/{proposal_id}/approve" in paths


def test_committed_openapi_matches_running_app() -> None:
    committed = json.loads((ROOT / "artifacts/openapi.json").read_text(encoding="utf-8"))
    assert committed == create_app().openapi()

from personal_pm_api.main import create_app


def test_openapi_has_versioned_core_resources() -> None:
    paths = create_app().openapi()["paths"]
    assert "/api/v1/tasks/{task_id}/transition" in paths
    assert "/api/v1/plans" in paths
    assert "/api/v1/proposals/{proposal_id}/approve" in paths

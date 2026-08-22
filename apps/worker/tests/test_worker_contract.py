import pytest
from personal_pm_worker.main import build_worker_identity


def test_worker_identity_is_stable() -> None:
    assert build_worker_identity("local") == "personal-pm-worker:local"


def test_worker_identity_rejects_empty_environment() -> None:
    with pytest.raises(ValueError):
        build_worker_identity("   ")

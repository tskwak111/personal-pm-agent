from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "smoke_deployment", _REPO_ROOT / "scripts" / "smoke_deployment.py"
)
assert _spec is not None and _spec.loader is not None
_mod: Any = importlib.util.module_from_spec(_spec)
sys.modules["smoke_deployment"] = _mod
_spec.loader.exec_module(_mod)


def test_images_run_as_non_root() -> None:
    docker_dir = _REPO_ROOT / "infra" / "docker"
    for df in sorted(docker_dir.glob("Dockerfile.*")):
        contract = _mod.inspect_dockerfile(df)
        assert _mod.validate_image_contract(contract).user not in {"", "0", "root"}


def test_migration_is_separate_from_api_start() -> None:
    root = _REPO_ROOT / "infra" / "deployment"
    api = (root / "api.yaml").read_text(encoding="utf-8")
    migrate = (root / "migrate.yaml").read_text(encoding="utf-8")
    assert "alembic" not in api
    assert "alembic" in migrate


def test_smoke_main_passes(tmp_path: Path, capsys: Any) -> None:
    import os

    os.chdir(_REPO_ROOT)
    assert _mod.main([]) == 0

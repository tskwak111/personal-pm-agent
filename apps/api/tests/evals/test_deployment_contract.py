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

_render_spec = importlib.util.spec_from_file_location(
    "render_deployment", _REPO_ROOT / "scripts" / "render_deployment.py"
)
assert _render_spec is not None and _render_spec.loader is not None
_render: Any = importlib.util.module_from_spec(_render_spec)
sys.modules["render_deployment"] = _render
_render_spec.loader.exec_module(_render)


def test_images_run_as_non_root() -> None:
    docker_dir = _REPO_ROOT / "infra" / "docker"
    for df in sorted(docker_dir.glob("Dockerfile.*")):
        contract = _mod.inspect_dockerfile(df)
        assert _mod.validate_image_contract(contract).user not in {"", "0", "root"}


def test_migration_is_separate_from_api_start() -> None:
    root = _REPO_ROOT / "infra" / "deployment"
    api = (root / "api.yaml.tmpl").read_text(encoding="utf-8")
    migrate = (root / "migrate.yaml.tmpl").read_text(encoding="utf-8")
    assert "alembic" not in api
    assert "alembic" in migrate


def test_web_build_mode_matches_docker_copy() -> None:
    config = (_REPO_ROOT / "apps" / "web" / "next.config.ts").read_text(encoding="utf-8")
    dockerfile = (_REPO_ROOT / "infra" / "docker" / "Dockerfile.web").read_text(encoding="utf-8")
    assert 'output: "standalone"' in config
    assert ".next/standalone" in dockerfile


def test_worker_image_copies_api_and_worker_sources() -> None:
    source = (_REPO_ROOT / "infra" / "docker" / "Dockerfile.worker").read_text(encoding="utf-8")
    assert "COPY apps/api" in source
    assert "COPY apps/worker" in source


def test_smoke_main_passes(tmp_path: Path, capsys: Any) -> None:
    import os

    os.chdir(_REPO_ROOT)
    _render.render_all(
        api_digest="sha256:" + "1" * 64,
        worker_digest="sha256:" + "2" * 64,
        web_digest="sha256:" + "3" * 64,
        output=tmp_path,
    )
    assert _mod.main(["--manifests", str(tmp_path)]) == 0


def test_render_requires_real_digest(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="sha256"):
        _render.render_all(
            api_digest="latest",
            worker_digest="latest",
            web_digest="latest",
            output=tmp_path,
        )


def test_rendered_deployment_selectors_match_pod_labels(tmp_path: Path) -> None:
    rendered = _render.render_all(
        api_digest="sha256:" + "1" * 64,
        worker_digest="sha256:" + "2" * 64,
        web_digest="sha256:" + "3" * 64,
        output=tmp_path,
    )

    deployments = [doc for doc in rendered.documents if doc.get("kind") == "Deployment"]
    assert len(deployments) == 3
    for deployment in deployments:
        assert (
            deployment["spec"]["selector"]["matchLabels"]
            == deployment["spec"]["template"]["metadata"]["labels"]
        )
        pod_spec = deployment["spec"]["template"]["spec"]
        assert pod_spec["securityContext"]["runAsNonRoot"] is True
        container = pod_spec["containers"][0]
        assert container["resources"]["requests"]
        assert container["resources"]["limits"]
        assert container["securityContext"]["allowPrivilegeEscalation"] is False
        assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
        if deployment["metadata"]["name"] in {"pma-api", "pma-web"}:
            assert container["readinessProbe"]
            assert container["livenessProbe"]
    assert all(":latest" not in path.read_text() for path in rendered.files)

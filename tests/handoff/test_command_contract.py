from pathlib import Path

MAKE_TARGETS = (
    "bootstrap:",
    "format-check:",
    "lint:",
    "typecheck:",
    "test-unit:",
    "test-integration:",
    "test-e2e:",
    "build:",
    "verify-planner:",
    "verify-api:",
    "verify-web:",
    "verify-docs:",
    "verify-repo:",
    "verify:",
)


def test_makefile_exposes_required_targets() -> None:
    text = Path("Makefile").read_text()
    for target in MAKE_TARGETS:
        assert target in text, target


def test_ci_workflow_runs_clean_checkout_verification() -> None:
    text = Path(".github/workflows/ci.yml").read_text()
    for marker in (
        "actions/checkout",
        "pnpm install",
        "uv sync",
        "make lint",
        "make typecheck",
        "make test-unit",
        "make build",
        "make verify-docs",
    ):
        assert marker in text, marker


def test_precommit_config_pins_ruff_hooks() -> None:
    text = Path(".pre-commit-config.yaml").read_text()
    assert "ruff" in text
    assert "rev:" in text


def test_verify_repo_script_exists() -> None:
    path = Path("scripts/verify_repo.py")
    assert path.is_file()
    compile(path.read_text(), str(path), "exec")

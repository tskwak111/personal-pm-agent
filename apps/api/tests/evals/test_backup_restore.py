from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "backup_restore_script", _REPO_ROOT / "scripts" / "test_backup_restore.py"
)
assert _spec is not None and _spec.loader is not None
_mod: Any = importlib.util.module_from_spec(_spec)
sys.modules["backup_restore_script"] = _mod
_spec.loader.exec_module(_mod)

verify_restore = _mod.verify_restore
Counts = _mod.Counts
RestoreResult = _mod.RestoreResult
main = _mod.main


@pytest.fixture
def test_environment() -> Any:
    return {
        "source": Counts(plan_snapshots=3, audit_events=5),
        "restored": Counts(plan_snapshots=3, audit_events=5),
        "broken_references": 0,
    }


def test_backup_restore_preserves_plan_and_audit_links(test_environment: Any) -> None:
    result = verify_restore(
        test_environment["source"],
        test_environment["restored"],
        broken_references=test_environment["broken_references"],
    )
    assert result.counts_match is True
    assert result.broken_references == 0
    assert result.passed is True


def test_restore_fails_on_count_mismatch() -> None:
    result = verify_restore(
        Counts(plan_snapshots=3, audit_events=5),
        Counts(plan_snapshots=2, audit_events=5),
        broken_references=0,
    )
    assert result.passed is False


def test_deleted_source_is_absent_after_retention_window() -> None:
    verifier = _mod.RetentionVerifier(retention_days=30)
    now = datetime(2026, 8, 31, tzinfo=UTC)
    result = verifier.verify_deleted("artifact-1", now_utc=now)
    assert result.primary_object_absent is True
    assert result.backup_expiry_at == datetime(2026, 9, 30, tzinfo=UTC)


def test_main_without_database_reports_blocked(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--compose", "compose.yaml"]) == 2
    assert "BLOCKED_EXTERNAL" in capsys.readouterr().out


def test_source_database_cannot_be_restore_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = "postgresql://localhost/pma"
    result = main(
        [
            "--source-url",
            database_url,
            "--restore-url",
            database_url,
            "--backup-file",
            str(tmp_path / "backup.age"),
            "--now-utc",
            "2026-08-31T00:00:00+00:00",
        ]
    )

    assert result == 1
    assert "source and restore databases must differ" in capsys.readouterr().out


def test_main_executes_backup_restore_and_queries_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_url = "postgresql://localhost/source"
    restore_url = "postgresql://localhost/restore"
    commands: list[str] = []
    monkeypatch.setenv("BACKUP_AGE_RECIPIENT", "age1test")
    monkeypatch.setenv("BACKUP_AGE_IDENTITY", "/secure/identity")
    monkeypatch.setattr(
        _mod,
        "_database_identity",
        lambda url: ("source" if url == source_url else "restore", "127.0.0.1", 5432),
    )
    monkeypatch.setattr(_mod, "_counts", lambda url: Counts(3, 5))
    monkeypatch.setattr(_mod, "_broken_audit_references", lambda url: 0)
    monkeypatch.setattr(
        _mod.subprocess,
        "run",
        lambda command, **kwargs: commands.append(Path(command[0]).name),
    )

    result = main(
        [
            "--source-url",
            source_url,
            "--restore-url",
            restore_url,
            "--backup-file",
            str(tmp_path / "backup.age"),
            "--now-utc",
            "2026-08-31T00:00:00+00:00",
        ]
    )

    assert result == 0
    assert commands == ["backup-postgres.sh", "restore-postgres.sh"]
    assert '"status": "PASS"' in capsys.readouterr().out

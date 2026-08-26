from __future__ import annotations

import importlib.util
import sys
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
    result = verifier.verify_deleted("artifact-1")
    assert result.primary_object_absent is True
    assert result.backup_expiry_at is not None

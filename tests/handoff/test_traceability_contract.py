from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("verify_repo", _ROOT / "scripts/verify_repo.py")
assert _SPEC is not None and _SPEC.loader is not None
_MODULE: Any = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
verify_traceability = _MODULE.verify_traceability
verify_phase_status = _MODULE.verify_phase_status


def test_traceability_rejects_missing_local_evidence(tmp_path: Path) -> None:
    doc = tmp_path / "traceability.md"
    doc.write_text("| R-1 | Implemented | tests/missing_test.py |\n", encoding="utf-8")

    assert verify_traceability(doc, repo_root=tmp_path) == [
        "R-1: missing evidence path tests/missing_test.py"
    ]


def test_traceability_accepts_existing_pytest_node(tmp_path: Path) -> None:
    test_file = tmp_path / "tests" / "test_real.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_real_contract():\n    pass\n", encoding="utf-8")
    doc = tmp_path / "traceability.md"
    doc.write_text("| R-1 | Implemented | tests/test_real.py::test_real_contract |\n")

    assert verify_traceability(doc, repo_root=tmp_path) == []


def test_traceability_accepts_external_block_and_not_implemented(tmp_path: Path) -> None:
    doc = tmp_path / "traceability.md"
    doc.write_text(
        "| R-1 | BLOCKED_EXTERNAL | reports/provider.json |\n"
        "| R-2 | Not Implemented | tests/missing.py |\n",
        encoding="utf-8",
    )

    assert verify_traceability(doc, repo_root=tmp_path) == []


def test_traceability_rejects_complete_without_evidence(tmp_path: Path) -> None:
    doc = tmp_path / "traceability.md"
    doc.write_text("| R-1 | Complete | none |\n", encoding="utf-8")

    assert verify_traceability(doc, repo_root=tmp_path) == ["R-1: Complete has no local evidence"]


def test_traceability_rejects_path_outside_repository(tmp_path: Path) -> None:
    doc = tmp_path / "traceability.md"
    doc.write_text("| R-1 | Implemented | ../secret.txt |\n", encoding="utf-8")

    assert verify_traceability(doc, repo_root=tmp_path) == [
        "R-1: evidence path escapes repository: ../secret.txt"
    ]


def test_complete_phase_has_checked_exit_criteria_or_external_block() -> None:
    assert verify_phase_status(_ROOT) == []

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "run_stage_a", _REPO_ROOT / "scripts" / "run_stage_a.py"
)
assert _spec is not None and _spec.loader is not None
_mod: Any = importlib.util.module_from_spec(_spec)
sys.modules["run_stage_a"] = _mod
_spec.loader.exec_module(_mod)

build_stage_a_report = _mod.build_stage_a_report


class FakeTestResults:
    def __init__(self, failures: dict[str, int] | None = None) -> None:
        self.failures = failures or {}

    def failures_for(self, gate: str) -> int:
        return self.failures.get(gate, 0)


def test_stage_a_fails_on_one_invariant_violation() -> None:
    results = FakeTestResults(failures={"PLAN-001": 1})
    report = build_stage_a_report(results, scenarios=25)
    assert report.overall == "FAIL"
    assert report.gates["PLAN-001"].failures == 1


def test_stage_a_passes_when_all_gates_clean() -> None:
    report = build_stage_a_report(FakeTestResults(), scenarios=20000)
    assert report.overall == "PASS"
    assert len(report.gates) >= 15  # SAFE-001..006 + PLAN-001..009


def test_stage_a_records_reference_environment() -> None:
    report = build_stage_a_report(FakeTestResults(), scenarios=25)
    assert report.environment.python_version
    assert report.environment.cpu_model
    assert report.environment.memory_bytes > 0


def test_scenario_count_is_recorded_in_report() -> None:
    report = build_stage_a_report(FakeTestResults(), scenarios=20000)
    assert report.scenarios == 20000

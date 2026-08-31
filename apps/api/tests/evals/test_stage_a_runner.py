from __future__ import annotations

import importlib.util
import json
import subprocess
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
GateObservation = _mod.GateObservation
HARD_GATES = _mod.HARD_GATES
property_command = _mod.property_command


class FakeTestResults:
    def __init__(
        self,
        failures: dict[str, int] | None = None,
        *,
        executed: set[str] | None = None,
    ) -> None:
        self.failures = failures or {}
        self.executed = executed if executed is not None else set(HARD_GATES)

    def observation_for(self, gate: str):  # noqa: ANN201
        if gate not in self.executed:
            return None
        return GateObservation(
            executed=True,
            checks=1,
            failures=self.failures.get(gate, 0),
            source=f"pytest:{gate}",
        )


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


def test_unexecuted_gate_cannot_pass() -> None:
    report = build_stage_a_report(
        FakeTestResults(executed={"PLAN-001"}),
        scenarios=25,
    )

    assert report.overall == "FAIL"
    assert report.gates["PLAN-002"].passed is False
    assert report.gates["PLAN-002"].executed is False


def test_property_command_receives_requested_count(tmp_path: Path) -> None:
    command = property_command(37, tmp_path / "observations.json")

    assert command[-4:-2] == ["--scenarios", "37"]


def test_incomplete_gate_map_returns_nonzero(tmp_path: Path) -> None:
    gate_map = tmp_path / "incomplete.json"
    gate_map.write_text(json.dumps({"PLAN-001": ["missing::node"]}), encoding="utf-8")
    result = subprocess.run(  # noqa: S603 - fixed local script
        [
            sys.executable,
            str(_REPO_ROOT / "scripts/run_stage_a.py"),
            "--scenarios",
            "1",
            "--gate-map",
            str(gate_map),
            "--output",
            str(tmp_path / "report.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1

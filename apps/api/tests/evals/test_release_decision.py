from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "verify_release", _REPO_ROOT / "scripts" / "verify_release.py"
)
assert _spec is not None and _spec.loader is not None
_mod: Any = importlib.util.module_from_spec(_spec)
sys.modules["verify_release"] = _mod
_spec.loader.exec_module(_mod)

decide_release = _mod.decide_release
main = _mod.main


@dataclass
class ThresholdChange:
    changed_before_or_after_evaluation: str = "BEFORE"


@dataclass
class Outcome:
    passed: bool = True
    within_ten_percent: bool = False


@pytest.fixture
def release_inputs() -> Any:
    @dataclass
    class Inputs:
        s0_incidents: int = 0
        system_caused_deadline_delays: int = 0
        threshold_changes: list[ThresholdChange] = field(default_factory=list)
        stage_a_passed: bool = True
        stage_b_required_passed: bool = True
        stage_c_passed: bool = True
        external_evidence_blocked: bool = False
        reevaluation_date: str | None = None
        outcomes: dict[str, Outcome] = field(
            default_factory=lambda: {f"OUT-{i:03d}": Outcome(True) for i in range(1, 11)}
        )

    return Inputs()


def test_one_s0_incident_always_fails_release(release_inputs: Any) -> None:
    release_inputs.s0_incidents = 1
    decision = decide_release(release_inputs)
    assert decision.decision == "FAIL"
    assert "CATASTROPHIC_GATE" in decision.reasons


def test_required_outcome_failure_cannot_be_conditional_pass(release_inputs: Any) -> None:
    release_inputs.outcomes["OUT-001"].passed = False
    assert decide_release(release_inputs).decision == "FAIL"


def test_threshold_change_after_evaluation_is_rejected(release_inputs: Any) -> None:
    release_inputs.threshold_changes.append(ThresholdChange("AFTER"))
    assert decide_release(release_inputs).decision == "FAIL"


def test_system_delay_blocks_release(release_inputs: Any) -> None:
    release_inputs.system_caused_deadline_delays = 1
    assert decide_release(release_inputs).decision == "FAIL"


def test_all_green_with_eight_outcomes_passes(release_inputs: Any) -> None:
    assert decide_release(release_inputs).decision == "PASS"


def test_two_optional_outcome_failures_fail(release_inputs: Any) -> None:
    release_inputs.outcomes["OUT-004"] = Outcome(False)
    release_inputs.outcomes["OUT-007"] = Outcome(False)
    assert decide_release(release_inputs).decision == "FAIL"


def test_one_near_threshold_optional_failure_can_be_conditional(release_inputs: Any) -> None:
    release_inputs.outcomes["OUT-004"] = Outcome(False, within_ten_percent=True)
    release_inputs.reevaluation_date = "2026-09-30"
    assert decide_release(release_inputs).decision == "CONDITIONAL_PASS"


def test_missing_mandatory_outcome_fails(release_inputs: Any) -> None:
    del release_inputs.outcomes["OUT-001"]
    assert decide_release(release_inputs).decision == "FAIL"


def test_blocked_external_evidence_fails(release_inputs: Any) -> None:
    release_inputs.external_evidence_blocked = True
    decision = decide_release(release_inputs)
    assert decision.decision == "FAIL"
    assert "EXTERNAL_EVIDENCE_BLOCKED" in decision.reasons


def test_fail_cli_returns_nonzero(tmp_path: Path) -> None:
    output = tmp_path / "release.json"
    assert main(["--output", str(output)]) == 1
    assert json.loads(output.read_text(encoding="utf-8"))["decision"] == "FAIL"


def test_cli_hashes_every_immutable_input(tmp_path: Path) -> None:
    paths = {
        name: tmp_path / f"{name}.json"
        for name in ("stage-a", "stage-b", "stage-c", "outcomes", "incidents", "threshold-changes")
    }
    for stage in ("stage-a", "stage-b", "stage-c"):
        paths[stage].write_text(
            json.dumps({"schema_version": "1.0", "overall": "PASS"}), encoding="utf-8"
        )
    paths["outcomes"].write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "outcomes": {
                    f"OUT-{index:03d}": {"passed": True, "within_ten_percent": False}
                    for index in range(1, 11)
                },
                "reevaluation_date": None,
            }
        ),
        encoding="utf-8",
    )
    paths["incidents"].write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "s0_incidents": 0,
                "system_caused_deadline_delays": 0,
            }
        ),
        encoding="utf-8",
    )
    paths["threshold-changes"].write_text(
        json.dumps({"schema_version": "1.0", "changes": []}), encoding="utf-8"
    )
    output = tmp_path / "release.json"
    arguments = ["--output", str(output)]
    for name, path in paths.items():
        arguments.extend([f"--{name}", str(path)])

    assert main(arguments) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["decision"] == "PASS"
    assert set(report["input_hashes"]) == set(paths)

from __future__ import annotations

import importlib.util
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


@dataclass
class ThresholdChange:
    changed_before_or_after_evaluation: str = "BEFORE"


@dataclass
class Outcome:
    passed: bool = True


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
        outcomes: dict[str, Outcome] = field(
            default_factory=lambda: {f"OUT-{i:03d}": Outcome(True) for i in range(1, 9)}
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


def test_fewer_than_eight_outcomes_is_conditional(release_inputs: Any) -> None:
    release_inputs.outcomes["OUT-004"] = Outcome(False)
    release_inputs.outcomes["OUT-007"] = Outcome(False)
    assert decide_release(release_inputs).decision == "CONDITIONAL_PASS"

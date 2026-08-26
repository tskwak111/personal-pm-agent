from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "run_stage_c", _REPO_ROOT / "scripts" / "run_stage_c.py"
)
assert _spec is not None and _spec.loader is not None
_mod: Any = importlib.util.module_from_spec(_spec)
sys.modules["run_stage_c"] = _mod
_spec.loader.exec_module(_mod)

build_stage_c_report = _mod.build_stage_c_report
ExtGate = _mod.ExtGateResult


@dataclass
class Latency:
    p95: int = 600


@pytest.fixture
def sample_ext_results() -> dict[str, Any]:
    return {
        "EXT-001": {"rate": 0.997},
        **{f"EXT-{i:03d}": ExtGate(failures=0) for i in range(2, 8)},
        "webhook_recovery_seconds": Latency(),
    }


def test_any_duplicate_external_event_fails_stage_c(
    sample_ext_results: dict[str, Any],
) -> None:
    sample_ext_results["EXT-002"].failures = 1  # type: ignore[index]
    assert build_stage_c_report(sample_ext_results).overall == "FAIL"


def test_recovery_window_threshold_is_fifteen_minutes(
    sample_ext_results: dict[str, Any],
) -> None:
    sample_ext_results["webhook_recovery_seconds"].p95 = 901  # type: ignore[index]
    assert build_stage_c_report(sample_ext_results).overall == "FAIL"


def test_clean_inputs_pass(sample_ext_results: dict[str, Any]) -> None:
    assert build_stage_c_report(sample_ext_results).overall == "PASS"

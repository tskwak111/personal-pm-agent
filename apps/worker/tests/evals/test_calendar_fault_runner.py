from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "run_calendar_faults", _REPO_ROOT / "scripts" / "run_calendar_faults.py"
)
assert _spec is not None and _spec.loader is not None
_mod: Any = importlib.util.module_from_spec(_spec)
sys.modules["run_calendar_faults"] = _mod
_spec.loader.exec_module(_mod)

run_fault_scenarios = _mod.run_fault_scenarios


def _sample_suite() -> list[dict[str, Any]]:
    return [
        {"scenario": "api-timeout"},
        {"scenario": "rate-limit-429"},
        {"scenario": "provider-5xx"},
        {"scenario": "oauth-expired"},
        {"scenario": "duplicate-worker-delivery"},
        {"scenario": "crash-after-db-commit"},
        {"scenario": "provider-success-response-lost"},
    ]


def test_fault_report_has_zero_duplicate_and_false_success() -> None:
    report = run_fault_scenarios(_sample_suite())
    for metric_id in ("EXT-002", "EXT-003", "EXT-006"):
        assert report.metrics[metric_id]["failures"] == 0


def test_all_required_scenarios_present_in_report() -> None:
    suite = _sample_suite()
    report = run_fault_scenarios(suite)
    assert report.total == len(suite)
    assert all(r.passed for r in report.results)


def test_missing_scenario_is_reported_as_failure() -> None:
    incomplete = [{"scenario": "api-timeout"}]
    report = run_fault_scenarios(incomplete, required=_mod.REQUIRED_SCENARIOS)
    missing = [r for r in report.results if not r.passed]
    assert len(missing) >= 1
